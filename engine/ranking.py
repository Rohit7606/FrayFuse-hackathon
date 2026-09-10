"""Final scoring, ranking, risk bands, and reason generation.

final_score = fragility x criticality — multiplicative, deliberately.  If either
factor is near zero the node does not belong on the list: a robust chokepoint is
fine, and a fragile commodity supplier is replaceable.  This is the argument the
product rests on; a weighted sum would destroy it.

Ties broken by node_id ascending for determinism.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from engine import config
from engine.contagion import ContagionResult
from engine.criticality import CriticalityDetail
from engine.disruption import DisruptionResult
from engine.stress import StressDetail
from engine.substitution import SubstitutionDetail

BAND_ORDER = ("critical", "high", "watch", "stable")


def band_for(final_score: float) -> str:
    """Map a final_score to its risk band.  Thresholds live in config.py."""
    if final_score >= config.BAND_CRITICAL:
        return "critical"
    if final_score >= config.BAND_HIGH:
        return "high"
    if final_score >= config.BAND_WATCH:
        return "watch"
    return "stable"


def disruption_band_for(supply_disruption: float) -> str:
    """Map a supply_disruption to its band.  Separate thresholds, in config.py.

    Deliberately not the same function as band_for: the two quantities measure
    different things and their thresholds are free to diverge, even though they
    currently hold the same values.
    """
    if supply_disruption >= config.DISRUPTION_BAND_CRITICAL:
        return "critical"
    if supply_disruption >= config.DISRUPTION_BAND_HIGH:
        return "high"
    if supply_disruption >= config.DISRUPTION_BAND_WATCH:
        return "watch"
    return "stable"


def _percent(fraction: float) -> str:
    """Render a 0-1 fraction as a whole-number percentage for a reason string."""
    return f"{round(fraction * 100)}%"


def _build_factors(
    graph: nx.DiGraph,
    node_id: str,
    stress: StressDetail,
    criticality: CriticalityDetail,
    contagion: ContagionResult,
    names: dict[str, str],
) -> list[dict[str, Any]]:
    """Structured contributors to this node's score, before normalisation.

    Each carries a raw share; the caller normalises them to sum to 1.0, which
    the schema enforces.  Ordered by descending share, ties by kind, so the
    sentence composed from the top factors is deterministic.
    """
    factors: list[tuple[str, str, float]] = []

    top_buyer = contagion.top_contributor.get(node_id)
    if top_buyer and contagion.inherited[node_id] > 0.0:
        exposure = graph.edges[node_id, top_buyer]["exposure_pct"]
        buyer_name = names.get(top_buyer, top_buyer)
        factors.append(
            (
                "exposure",
                f"{_percent(exposure)} revenue dependency on {buyer_name}",
                exposure,
            )
        )
        buyer_stress = contagion.fragility.get(top_buyer, 0.0)
        if buyer_stress > 0.0:
            factors.append(
                (
                    "upstream_stress",
                    f"{buyer_name} is under payment stress and is stretching its suppliers",
                    buyer_stress,
                )
            )

    if criticality.single_source_components:
        component = criticality.single_source_components[0]
        factors.append(
            (
                "single_source",
                f"Sole source for {component.replace('_', ' ')}",
                config.W_SINGLE_SOURCE,
            )
        )

    if criticality.betweenness_norm > 0.0 and criticality.downstream_count > 0:
        factors.append(
            (
                "chokepoint",
                f"{criticality.downstream_count} downstream suppliers route through this node",
                criticality.betweenness_norm * config.W_BETWEENNESS,
            )
        )

    buffer_days = graph.nodes[node_id]["cash_buffer_days"]
    if buffer_days < config.THIN_BUFFER_DAYS and contagion.fragility[node_id] > 0.0:
        factors.append(
            (
                "thin_buffer",
                f"{buffer_days} days of cash buffer",
                1.0 - buffer_days / max(config.THIN_BUFFER_DAYS, 1),
            )
        )

    if stress.own_stress > 0.0:
        fy = stress.fy_latest or "the latest year"
        detail = f"Own payment behaviour deteriorated in {fy}"
        if stress.interest_ratio and stress.interest_ratio > 1.0:
            detail = (
                f"Own late supplier payments rose {stress.interest_ratio:.1f}x in {fy}"
            )
        factors.append(("own_stress", detail, stress.own_stress))

    if not factors:
        # Every score must carry a non-empty reason — SCHEMA.md §4.1.
        factors.append(
            ("chokepoint", "No stress reached this node and it sits off the critical paths", 1.0)
        )

    factors.sort(key=lambda f: (-f[2], f[0]))
    return [{"kind": kind, "detail": detail, "weight": share} for kind, detail, share in factors]


def _normalise_weights(factors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scale factor weights to sum to exactly 1.0, as the schema requires.

    Rounding each weight independently can leave the sum off by a ulp, so the
    last factor absorbs the residual.  Deterministic because the order is fixed.
    """
    total = sum(f["weight"] for f in factors)
    if total <= 0.0:
        share = 1.0 / len(factors)
        normalised = [{**f, "weight": round(share, 4)} for f in factors]
    else:
        normalised = [{**f, "weight": round(f["weight"] / total, 4)} for f in factors]

    residual = round(1.0 - sum(f["weight"] for f in normalised), 4)
    normalised[-1]["weight"] = round(normalised[-1]["weight"] + residual, 4)
    return normalised


def _compose_reason(factors: list[dict[str, Any]]) -> str:
    """Build the sentence from the top factors.  Template-generated, no LLM."""
    leading = factors[:3]
    first = leading[0]["detail"]

    if len(leading) == 1:
        return f"{first}."

    if leading[0]["kind"] == "exposure" and leading[1]["kind"] == "upstream_stress":
        head = f"{first}, whose payment stress is propagating downstream"
        tail = [f["detail"] for f in leading[2:]]
        return ". ".join([head, *tail]) + "."

    return ". ".join(f["detail"] for f in leading) + "."


def _compose_disruption_reason(
    graph: nx.DiGraph,
    node_id: str,
    disruption: DisruptionResult,
    names: dict[str, str],
) -> str:
    """Why this node's line is or is not at risk of stopping.

    Template-generated and deterministic, like reason_text, and never empty —
    a node with no disruption says so rather than rendering blank.
    """
    stopped_by = disruption.top_source.get(node_id)
    at_risk = disruption.disrupted_inflow_cr[node_id]

    if disruption.disruption[node_id] <= 0.0 or not stopped_by:
        if disruption.halt_risk[node_id] > 0.0:
            return (
                "No supplier of its own has stopped; its own delivery risk is "
                "unpaid invoices, not missing parts."
            )
        return "No supplier failure reaches this node."

    edge = graph.edges[stopped_by, node_id]
    component = edge["component"].replace("_", " ")
    supplier_name = names.get(stopped_by, stopped_by)

    lead = f"{supplier_name} is at risk of halting {component} deliveries"
    if edge["is_single_source"] is True:
        lead += " — sole source, nothing else to buy it from"

    return f"{lead}. ₹{at_risk:.2f} cr of inbound supply at risk."


def build_scores(
    graph: nx.DiGraph,
    network: dict[str, Any],
    stress: dict[str, StressDetail],
    contagion: ContagionResult,
    criticality: dict[str, CriticalityDetail],
    costs: dict[str, float],
    exposures: dict[str, float],
    disruption: DisruptionResult,
    substitutions: dict[str, SubstitutionDetail] | None = None,
) -> list[dict[str, Any]]:
    """One Score object per node, ranked, with reasons.

    Rounding is applied here — at serialisation, never mid-calculation
    (AGENTS.md §3.1).  Monetary values to 2 places, scores to 4.
    """
    names = {n["node_id"]: n["name"] for n in network["nodes"]}
    node_ids = sorted(graph.nodes)

    scores: list[dict[str, Any]] = []
    for node_id in node_ids:
        fragility = contagion.fragility[node_id]
        node_criticality = criticality[node_id].criticality
        final_score = fragility * node_criticality

        factors = _normalise_weights(
            _build_factors(graph, node_id, stress[node_id], criticality[node_id], contagion, names)
        )

        scores.append(
            {
                "node_id": node_id,
                "own_stress": round(contagion.own_stress[node_id], 4),
                "inherited_stress": round(min(1.0, contagion.inherited[node_id]), 4),
                "fragility": round(fragility, 4),
                "criticality": round(node_criticality, 4),
                "final_score": round(final_score, 4),
                "risk_band": band_for(final_score),
                "rank": None,
                "reason_text": _compose_reason(factors),
                "reason_factors": factors,
                "intervention_cost_cr": round(costs[node_id], 2),
                "estimated_exposure_cr": round(exposures[node_id], 2),
                "propagation_depth": contagion.depth[node_id],
                "halt_risk": round(disruption.halt_risk[node_id], 4),
                "supply_disruption": round(disruption.disruption[node_id], 4),
                "disruption_band": disruption_band_for(disruption.disruption[node_id]),
                "disrupted_inflow_cr": round(disruption.disrupted_inflow_cr[node_id], 2),
                "disruption_reason": _compose_disruption_reason(
                    graph, node_id, disruption, names
                ),
            }
        )

        # null means "substitution was not considered for this node"; an empty
        # list means "it was considered and nobody qualified".  Two different
        # facts, kept apart exactly the way §3.6 keeps undisclosed apart from
        # disclosed-nil — and the same shape whether it comes out of the engine
        # or through pydantic, which serialises an unset optional as null.
        detail = (substitutions or {}).get(node_id)
        scores[-1]["substitution_candidates"] = (
            [
                {
                    "node_id": candidate.node_id,
                    "name": candidate.name,
                    "component": candidate.component,
                    "replaces_edge_id": candidate.replaces_edge_id,
                    "fitness": candidate.fitness,
                    "fragility": candidate.fragility,
                    "capacity_headroom_cr": candidate.capacity_headroom_cr,
                    "reason_text": candidate.reason_text,
                }
                for candidate in detail.candidates
            ]
            if detail is not None and detail.eligible
            else None
        )

    # Stressed origins are reported separately in summary.stressed_origin_nodes
    # and are deliberately not ranked.  The product's question is "which
    # suppliers are about to run out of cash *that you could not see*" — an
    # origin is stressed by its own published disclosures, so it is the thing
    # you already knew, not a finding.  SCHEMA.md §4.3/§4.4's own worked example
    # does exactly this: ranking lists N042, N118, N203 and N087 while N007, the
    # trigger, appears only under stressed_origin_nodes.  They keep their scores
    # and bands, so nothing is hidden — they simply do not compete for rank.
    origins = set(contagion.origins)
    ranked = sorted(
        (s for s in scores if s["risk_band"] != "stable" and s["node_id"] not in origins),
        key=lambda s: (-s["final_score"], s["node_id"]),
    )
    for position, score in enumerate(ranked, start=1):
        score["rank"] = position

    return scores


def ranking_of(scores: list[dict[str, Any]]) -> list[str]:
    """The ordered node_id list, so the UI does not re-sort.

    Contains only nodes whose risk_band is not "stable", ordered by final_score
    descending, ties broken by node_id ascending.
    """
    ranked = [s for s in scores if s["rank"] is not None]
    ranked.sort(key=lambda s: s["rank"])
    return [s["node_id"] for s in ranked]


def build_summary(
    scores: list[dict[str, Any]],
    contagion: ContagionResult,
    disruption: DisruptionResult,
    tier_of: dict[str, int],
) -> dict[str, Any]:
    """Network-level totals for the header panel."""
    band_counts = {band: 0 for band in BAND_ORDER}
    for score in scores:
        band_counts[score["risk_band"]] += 1

    at_risk = [s for s in scores if s["rank"] is not None]

    # The anchors, lifted out so the UI can drive DEMO_SCENARIO.md §6 without
    # scanning four hundred score objects for the three tier-0 nodes.  Ordered
    # by disruption descending, ties by node_id — the same tiebreak as ranking.
    anchors = sorted(
        (
            {
                "node_id": s["node_id"],
                "supply_disruption": s["supply_disruption"],
                "disruption_band": s["disruption_band"],
                "disrupted_inflow_cr": s["disrupted_inflow_cr"],
                "stopped_by": disruption.top_source.get(s["node_id"]),
            }
            for s in scores
            if tier_of.get(s["node_id"]) == 0
        ),
        key=lambda a: (-a["supply_disruption"], a["node_id"]),
    )

    return {
        "anchor_disruption": anchors,
        "disruption_iterations_to_converge": disruption.iterations,
        "total_nodes": len(scores),
        "stressed_origin_nodes": list(contagion.origins),
        "at_risk_count": len(at_risk),
        "band_counts": band_counts,
        "total_intervention_cost_cr": round(
            sum(s["intervention_cost_cr"] for s in at_risk), 2
        ),
        "total_estimated_exposure_cr": round(
            sum(s["estimated_exposure_cr"] for s in at_risk), 2
        ),
        "max_propagation_depth": max(
            (s["propagation_depth"] for s in scores if s["fragility"] > 0.0), default=0
        ),
        "iterations_to_converge": contagion.iterations,
    }
