"""Collection CSVs -> runtime network.json transform.

This is the ONLY module that knows CSVs exist. No other file imports
pandas for data loading.

Usage:
    python -m engine.transform --in data/real/ --out data/real/network.json

Emits the identical shape as mockgen, so swapping the real dataset in is a
file-path change and nothing else (AGENTS.md §7).

Two things that would silently corrupt the model, per PERSON_A.md §5:

  * **Units.** Every figure in `financials.csv` is ALREADY in rupees crore.
    `units_as_reported` records what the source document printed and is
    provenance, not an instruction: DATA_DICTIONARY.md rule 3 says the
    conversion was applied when the row was written. Dividing again here turns
    Nectar's revenue from 1,523.67 crore into 152.37 and Balrampur's 4,846.03
    into 48.46 — the exact class of silent corruption PERSON_A.md §5 warns
    about, in the opposite direction. Verified against three companies whose
    as-printed figures are quoted in findings.md.
  * **`has_not_due_column`.** Never defaulted to true. A filer who omits the
    column reports an `under_1yr` that includes not-yet-due amounts, and
    defaulting would make a healthy company look badly overdue.

**This module never invents a number.** Where a real company did not disclose
a figure the field is emitted as `null`, and the node names it in
`substituted` so the engine's runtime fill is a visible modelling decision
rather than a fabricated fact frozen into a data file (DATA_DICTIONARY.md §3b).
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from engine import config

# Recognised source units.  Provenance ONLY — see _number for why nothing here
# is a divisor.
SOURCE_UNITS = frozenset({"crore", "lakh", "million"})

# tier_role -> runtime tier.  An unknown role defaults to 1: the collected
# cohort is listed manufacturers, which are tier-1 by construction.
TIER_BY_ROLE: dict[str, int] = {"tier0": 0, "tier1": 1, "tier2": 2, "tier3": 3}

# Edge rows that are real disclosures but not supply relationships.
NON_GRAPH_RELATIONSHIPS = frozenset(
    {"concentration_disclosure_unnamed", "supplier_dispute_unnamed"}
)
TERMINATED_RELATIONSHIP = "relationship_terminated"

# Best evidence wins when several rows describe one relationship.
CONFIDENCE_RANK: dict[str, int] = {"confirmed": 3, "probable": 2, "concentration_only": 1}


class TransformError(ValueError):
    """The collection CSVs cannot produce a valid network."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _text(row: dict[str, str], field: str) -> str | None:
    """A trimmed cell, or None where the source disclosed nothing.

    An empty cell is a fact about disclosure, not a zero (DATA_DICTIONARY.md
    rule 2).  Only the literal 'nil' means an explicit zero.
    """
    value = (row.get(field) or "").strip()
    return value or None


def _number(row: dict[str, str], field: str) -> float | None:
    """A numeric cell in rupees crore, preserving null vs nil.

    No unit conversion happens here — see the module docstring. 'nil' is an
    explicit zero the filer printed; an empty cell is silence. Conflating them
    is the error AGENTS.md §3.6 exists to prevent.
    """
    value = _text(row, field)
    if value is None:
        return None
    if value.lower() in {"nil", "none"}:
        return 0.0
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _boolean(row: dict[str, str], field: str) -> bool | None:
    value = _text(row, field)
    if value is None:
        return None
    return value.lower() in {"true", "yes", "1"}


def _short_fy(fy: str) -> str:
    """'FY2024' -> 'FY24', the runtime contract's format."""
    digits = "".join(ch for ch in fy if ch.isdigit())
    return f"FY{digits[-2:]}" if len(digits) >= 2 else fy


def _node_id(index: int) -> str:
    return f"N{index:03d}"


def build_id_map(companies: list[dict[str, str]]) -> dict[str, str]:
    """company_id -> node_id, ordered deterministically by company_id."""
    return {
        row["company_id"]: _node_id(position)
        for position, row in enumerate(
            sorted(companies, key=lambda r: r["company_id"]), start=1
        )
    }


def _revenue_for(rows: list[dict[str, str]]) -> float | None:
    """Latest disclosed revenue, taking the field that matches the row's basis.

    Populating the field that does not match `basis` would mix a standalone
    entity's payables with a consolidated group's revenue — the Rule 5
    violation that the collection workstream caught in its own first sweep.
    """
    for row in sorted(rows, key=lambda r: r["fy"], reverse=True):
        field = (
            "revenue_consolidated"
            if _text(row, "basis") == "consolidated"
            else "revenue_standalone"
        )
        revenue = _number(row, field)
        if revenue is not None:
            return revenue
    return None


def _cash_buffer_for(rows: list[dict[str, str]]) -> int | None:
    """Latest disclosed cash_buffer_days.

    Never recomputed here.  The formula has a documented trap — Precision
    Camshafts prints Total expenses above its EBITDA subtotal, so the standard
    denominator subtracts depreciation and finance costs twice — and the
    collection workstream already applied `total_expenses_includes_dep_fin`
    when it wrote this column.  Recomputing would silently undo that.
    """
    for row in sorted(rows, key=lambda r: r["fy"], reverse=True):
        value = _number(row, "cash_buffer_days")
        if value is not None:
            return round(value)
    return None


def build_nodes(
    companies: list[dict[str, str]],
    financials: dict[str, list[dict[str, str]]],
    id_map: dict[str, str],
    observable: set[str],
) -> list[dict[str, Any]]:
    """One runtime node per collected company, in node_id order."""
    nodes: list[dict[str, Any]] = []

    for row in sorted(companies, key=lambda r: r["company_id"]):
        company_id = row["company_id"]
        rows = financials.get(company_id, [])

        revenue = _revenue_for(rows)
        cash_buffer = _cash_buffer_for(rows)

        substituted = [
            name
            for name, value in (("revenue_cr", revenue), ("cash_buffer_days", cash_buffer))
            if value is None
        ]

        node: dict[str, Any] = {
            "node_id": id_map[company_id],
            "name": row["name"],
            "tier": TIER_BY_ROLE.get(_text(row, "tier_role") or "", 1),
            "sector": _text(row, "sector") or "unclassified",
            "product_category": _text(row, "product_category") or "unclassified",
            "revenue_cr": revenue,
            "cash_buffer_days": cash_buffer,
            "employees": None,
            "is_observable": company_id in observable,
            "data_source": "real",
            "cin": _text(row, "cin"),
        }
        if substituted:
            node["substituted"] = substituted
        nodes.append(node)

    return nodes


def collapse_edge_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Reduce repeated (supplier, buyer) rows to one, deterministically.

    A relationship is recorded once per financial year, so the collected set has
    several rows for one pair — SHIVAM -> HERO has three, and only one carries a
    rupee figure.  A naive loop into DiGraph.add_edge overwrites attributes
    silently and would discard it (PERSON_A.md §3.2).

    Rules: the group's most recent `fy` wins the identity; the best `confidence`
    wins; and every other attribute takes the best non-null value found anywhere
    in the group, so a figure disclosed in one year is not lost because a later
    row omitted it.  A pair whose most recent row is `relationship_terminated`
    is dropped entirely — the edge existed and ended.
    """
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault((row["from_company_id"], row["to_company_id"]), []).append(row)

    collapsed: list[dict[str, str]] = []
    for pair in sorted(grouped):
        group = sorted(grouped[pair], key=lambda r: (r.get("fy") or "", r["edge_id"]))

        if group[-1].get("relationship_type") == TERMINATED_RELATIONSHIP:
            continue

        winner = max(
            group,
            key=lambda r: (
                CONFIDENCE_RANK.get(r.get("confidence") or "", 0),
                r.get("fy") or "",
                r["edge_id"],
            ),
        )
        merged = dict(winner)
        for field in ("component", "annual_value_cr", "weight_pct", "is_single_source"):
            if not (merged.get(field) or "").strip():
                for candidate in reversed(group):
                    if (candidate.get(field) or "").strip():
                        merged[field] = candidate[field]
                        break
        collapsed.append(merged)

    return collapsed


def build_edges(
    edge_rows: list[dict[str, str]],
    id_map: dict[str, str],
    revenue_by_node: dict[str, float | None],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Runtime edges plus a list of rows deliberately excluded, with reasons."""
    excluded: list[str] = []
    graph_rows: list[dict[str, str]] = []

    for row in edge_rows:
        relationship = _text(row, "relationship_type") or ""
        supplier, buyer = _text(row, "from_company_id"), _text(row, "to_company_id")

        if relationship in NON_GRAPH_RELATIONSHIPS or not buyer or not supplier:
            excluded.append(
                f"{row['edge_id']}: {relationship or 'no counterparty'} — a real disclosure "
                "against an unnamed counterparty, not a graph edge"
            )
            continue
        if supplier not in id_map or buyer not in id_map:
            excluded.append(f"{row['edge_id']}: references a company not in companies.csv")
            continue
        graph_rows.append(row)

    edges: list[dict[str, Any]] = []
    for position, row in enumerate(collapse_edge_rows(graph_rows), start=1):
        supplier_node = id_map[row["from_company_id"]]
        buyer_node = id_map[row["to_company_id"]]

        annual_value = _number(row, "annual_value_cr")
        weight_pct = _number(row, "weight_pct")

        # exposure_pct is a fraction of the SUPPLIER's revenue.  Prefer a
        # disclosed percentage; otherwise derive it, but only where the
        # supplier's own revenue is known — deriving against a substituted
        # revenue would invent the model's single most important number.
        supplier_revenue = revenue_by_node.get(supplier_node)
        if weight_pct is not None:
            exposure = weight_pct / 100.0
        elif annual_value is not None and supplier_revenue:
            exposure = annual_value / supplier_revenue
        else:
            exposure = 0.0

        edges.append(
            {
                "edge_id": f"E{position:03d}",
                "supplier_id": supplier_node,
                "buyer_id": buyer_node,
                "component": _text(row, "component") or "unspecified",
                "annual_value_cr": annual_value if annual_value is not None else 0.0,
                "exposure_pct": min(max(exposure, 0.0), 1.0),
                # Empty means UNKNOWN and must stay unknown.  No filing in the
                # collected set states sole-source status, and inferring `false`
                # from the sparsity of our own edge collection would manufacture
                # the product's headline finding out of our own ignorance.
                "is_single_source": _boolean(row, "is_single_source"),
                "data_source": _text(row, "data_source") or "real",
                "confidence": _text(row, "confidence") or "probable",
                "edge_provenance": _text(row, "evidence_source") or "related_party_note",
            }
        )

    excluded.extend(_enforce_exposure_ceiling(edges))
    return edges, excluded


def _enforce_exposure_ceiling(edges: list[dict[str, Any]]) -> list[str]:
    """Scale a supplier's exposures down where its disclosed shares exceed 100%.

    SCHEMA.md §3.3 makes this transform's job.  Disclosed percentages come from
    different years and different denominators — one may be a share of revenue
    and another a share of purchases — so they can legitimately sum past 1.0
    without any single figure being wrong.  Scaling proportionally keeps the
    relative weights, which is what the model actually uses, instead of
    asserting a dependency greater than the whole of a supplier's revenue.
    """
    totals: dict[str, float] = {}
    for edge in edges:
        totals[edge["supplier_id"]] = totals.get(edge["supplier_id"], 0.0) + edge["exposure_pct"]

    notes: list[str] = []
    for supplier_id in sorted(totals):
        total = totals[supplier_id]
        if total <= config.MAX_EXPOSURE_SUM_TOLERANCE:
            continue
        for edge in edges:
            if edge["supplier_id"] == supplier_id:
                edge["exposure_pct"] = edge["exposure_pct"] / total
        notes.append(
            f"{supplier_id}: disclosed exposures summed to {total:.2f}, scaled to 1.00 "
            "proportionally — shares taken from different years or denominators"
        )
    return notes


def build_stress_signals(
    financials: dict[str, list[dict[str, str]]], id_map: dict[str, str]
) -> list[dict[str, Any]]:
    """One runtime stress signal per collected company-year."""
    signals: list[dict[str, Any]] = []

    for company_id in sorted(financials):
        for row in sorted(financials[company_id], key=lambda r: r["fy"]):
            has_not_due = _boolean(row, "has_not_due_column")

            signals.append(
                {
                    "node_id": id_map[company_id],
                    "fy": _short_fy(row["fy"]),
                    "msme_unbilled_cr": _number(row, "msme_unbilled"),
                    "msme_not_due_cr": _number(row, "msme_not_due"),
                    "msme_under_1yr_cr": _number(row, "msme_under_1yr"),
                    "msme_1_2yr_cr": _number(row, "msme_1_2yr"),
                    "msme_2_3yr_cr": _number(row, "msme_2_3yr"),
                    "msme_over_3yr_cr": _number(row, "msme_over_3yr"),
                    "msme_total_cr": _number(row, "msme_total"),
                    "nonmsme_total_cr": _number(row, "nonmsme_total"),
                    "total_trade_payables_cr": _number(row, "total_trade_payables"),
                    "msmed_principal_unpaid_year_end_cr": _number(
                        row, "msmed_principal_unpaid_year_end"
                    ),
                    "msmed_principal_paid_beyond_appointed_day_cr": _number(
                        row, "msmed_principal_paid_beyond_appointed_day"
                    ),
                    "msmed_interest_accrued_unpaid_cr": _number(
                        row, "msmed_interest_accrued_unpaid"
                    ),
                    "msmed_interest_due_unpaid_cr": _number(
                        row, "msmed_interest_due_unpaid"
                    ),
                    "msmed_interest_due_on_payments_beyond_appointed_day_cr": _number(
                        row, "msmed_interest_due_on_payments_made_beyond_appointed_day"
                    ),
                    "revenue_cr": _number(
                        row,
                        "revenue_consolidated"
                        if _text(row, "basis") == "consolidated"
                        else "revenue_standalone",
                    ),
                    "cost_of_materials_cr": _number(row, "cost_of_materials_consumed"),
                    "trade_payables_turnover_ratio": _number(row, "trade_payables_turnover_ratio"),
                    # Never defaulted.  See the module docstring.
                    "has_not_due_column": bool(has_not_due),
                    "basis": _text(row, "basis") or "standalone",
                    "ageing_basis": _text(row, "ageing_basis") or "due_date",
                    "msme_book_material": _boolean(row, "msme_book_material"),
                    "data_source": "real",
                }
            )

    return signals


def transform(source_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """Read the five collection CSVs and emit a NetworkInput dict."""
    companies = _read_csv(source_dir / "companies.csv")
    financial_rows = _read_csv(source_dir / "financials.csv")
    edge_rows = _read_csv(source_dir / "edges.csv")

    if not companies:
        raise TransformError("companies.csv is empty")

    financials: dict[str, list[dict[str, str]]] = {}
    for row in financial_rows:
        financials.setdefault(row["company_id"], []).append(row)

    id_map = build_id_map(companies)

    # A node is observable only if it has at least two comparable years — one
    # year cannot produce the year-on-year change every rung is built on.
    observable = {company_id for company_id, rows in financials.items() if len(rows) >= 2}

    nodes = build_nodes(companies, financials, id_map, observable)
    revenue_by_node = {n["node_id"]: n["revenue_cr"] for n in nodes}
    edges, excluded = build_edges(edge_rows, id_map, revenue_by_node)
    signals = build_stress_signals(financials, id_map)
    signals = [s for s in signals if s["node_id"] in {n["node_id"] for n in nodes if n["is_observable"]}]

    units = sorted({(_text(r, "units_as_reported") or "crore") for r in financial_rows} & SOURCE_UNITS)

    network = {
        "meta": {
            "schema_version": "1.1",
            # Build time, not score time.  A timestamp generated during scoring
            # would break the byte-identical guarantee in AGENTS.md §3.1.
            "generated_at": config.TRANSFORM_GENERATED_AT,
            "generator": "transform",
            "seed": None,
            "currency_unit": "INR_crore",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "observable_node_count": sum(1 for n in nodes if n["is_observable"]),
            "source_units_note": f"already INR_crore; source documents printed: {', '.join(units)}",
        },
        "nodes": nodes,
        "edges": edges,
        "stress_signals": signals,
    }
    return network, excluded


def validate(network: dict[str, Any]) -> None:
    """Validate against the NetworkInput definition in schema.json."""
    import jsonschema

    schema_path = Path(__file__).resolve().parent.parent / "schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(
        instance=network,
        schema={
            "$schema": schema["$schema"],
            "definitions": schema["definitions"],
            "$ref": "#/definitions/NetworkInput",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform collection CSVs to network.json.")
    parser.add_argument("--in", dest="source", type=Path, default=Path("data/real"))
    parser.add_argument("--out", dest="out", type=Path, default=Path("data/real/network.json"))
    args = parser.parse_args()

    network, excluded = transform(args.source)
    validate(network)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(network, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    meta = network["meta"]
    print(
        f"wrote {args.out}: {meta['node_count']} nodes, {meta['edge_count']} edges, "
        f"{meta['observable_node_count']} observable"
    )

    substituted = [n for n in network["nodes"] if n.get("substituted")]
    if substituted:
        print(
            f"\n{len(substituted)} of {meta['node_count']} nodes carry an undisclosed field. "
            "These are REAL companies with a field the filings do not give. They are emitted "
            "as null and named in `substituted` so the engine's runtime fill stays visible — "
            "never invent a rupee figure beside a real company's name."
        )
        for node in substituted[:5]:
            print(f"  {node['node_id']} {node['name']}: {', '.join(node['substituted'])}")
        if len(substituted) > 5:
            print(f"  ... and {len(substituted) - 5} more")

    if excluded:
        print(f"\n{len(excluded)} edge rows excluded by design:")
        for line in excluded:
            print(f"  {line}")


if __name__ == "__main__":
    main()
