"""Stress detection — produces own_stress in [0, 1] for observable nodes.

A ladder of four signals, not two.  Availability varies enormously between
filers, so we compute whichever rungs have inputs and renormalise their weights
over exactly those: a company with only rung 1 available scores on rung 1 at
full weight.  A rung whose inputs are absent is dropped, never defaulted —
`null` (undisclosed) and `0.0` (disclosed nil) are different facts, AGENTS.md
section 3.6.

Evidence for every rung and threshold is in data/real/DATA_DICTIONARY.md §6 and
data/real/findings.md §5.  The ladder replaced the original two-signal spec
after collection found the designated primary field disclosed in 3 of 46
company-years, all in one control company.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine import config

# Rung identifiers, in ladder order.  Used as dict keys and in reason factors.
RUNG_INTEREST = "interest_direction"
RUNG_MIGRATION = "not_due_migration"
RUNG_PAYABLES = "payables_revenue"
RUNG_NONMSME = "nonmsme_ageing"

RUNG_WEIGHTS: dict[str, float] = {
    RUNG_INTEREST: config.W_INTEREST_DIRECTION,
    RUNG_MIGRATION: config.W_MIGRATION,
    RUNG_PAYABLES: config.W_PAYABLES_REVENUE,
    RUNG_NONMSME: config.W_NONMSME_AGEING,
}

# Human-readable, for reason_text.  Deterministic templates, never an LLM.
RUNG_LABELS: dict[str, str] = {
    RUNG_INTEREST: "MSMED interest rose",
    RUNG_MIGRATION: "dues moved from not-due to overdue",
    RUNG_PAYABLES: "payables grew faster than revenue",
    RUNG_NONMSME: "non-MSME aged payables grew",
}


@dataclass(frozen=True)
class StressDetail:
    """The own_stress value for one node, with enough detail to explain it."""

    node_id: str
    own_stress: float
    fy_latest: str | None = None
    fy_previous: str | None = None
    rungs_fired: tuple[str, ...] = ()
    rungs_available: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    interest_ratio: float | None = None  # latest/previous, for the reason template

    @property
    def is_stressed(self) -> bool:
        return self.own_stress > 0.0


def _fy_sort_key(fy: str) -> tuple[int, str]:
    """Order 'FY24' style labels numerically, falling back to the raw string."""
    digits = fy[2:]
    return (int(digits), fy) if digits.isdigit() else (-1, fy)


def _largest_interest(row: dict[str, Any]) -> float | None:
    """The largest of the three MSMED interest lines, or None if none disclosed.

    Interest accrues under the MSMED Act only past the appointed day, so any
    rise is a statutory admission of late payment.  Filers disclose different
    subsets of the three lines, so the largest disclosed value is the
    comparable quantity — see DATA_DICTIONARY.md §13 on note formats.
    """
    values = [
        row.get("msmed_interest_accrued_unpaid_cr"),
        row.get("msmed_interest_due_unpaid_cr"),
        row.get("msmed_interest_due_on_payments_beyond_appointed_day_cr"),
    ]
    disclosed = [v for v in values if v is not None]
    return max(disclosed) if disclosed else None


def _overdue_share(row: dict[str, Any]) -> float | None:
    """under_1yr / (not_due + under_1yr), or None where it is not comparable.

    Unavailable when has_not_due_column is false: that filer's under_1yr
    silently includes amounts not yet due, so the ratio means something
    different.  Do not substitute a default — drop the rung.
    """
    if not row.get("has_not_due_column"):
        return None
    not_due = row.get("msme_not_due_cr")
    under_1yr = row.get("msme_under_1yr_cr")
    if not_due is None or under_1yr is None:
        return None
    denominator = not_due + under_1yr
    if denominator <= 0.0:
        return None
    return under_1yr / denominator


def _payables_ratio(row: dict[str, Any]) -> float | None:
    """total_trade_payables / revenue, or None where either is undisclosed."""
    payables = row.get("total_trade_payables_cr")
    revenue = row.get("revenue_cr")
    if payables is None or revenue is None or revenue <= 0.0:
        return None
    return payables / revenue


def _nonmsme_aged(row: dict[str, Any]) -> float | None:
    """Payables aged beyond a year, normalised by revenue.

    Returns None unless at least one bucket is disclosed — an absent bucket is
    not an empty one.
    """
    revenue = row.get("revenue_cr")
    if revenue is None or revenue <= 0.0:
        return None
    buckets = [
        row.get("msme_1_2yr_cr"),
        row.get("msme_2_3yr_cr"),
        row.get("msme_over_3yr_cr"),
    ]
    disclosed = [b for b in buckets if b is not None]
    if not disclosed:
        return None
    return sum(disclosed) / revenue


def _comparable(latest: dict[str, Any], previous: dict[str, Any]) -> tuple[bool, str | None]:
    """Whether two consecutive years may be differenced at all.

    A series_break means a restatement, discontinued operation or GAAP
    transition sits between them, so the delta is meaningless.  A change of
    basis or ageing clock means the two rows measure different quantities under
    the same column names — DATA_DICTIONARY.md §5 traps 2 and 5.
    """
    if latest.get("series_break"):
        return False, f"series break at {latest['fy']}: {latest['series_break']}"
    if latest.get("basis") != previous.get("basis"):
        return False, "basis changed between years, standalone and consolidated are different entities"
    if latest.get("ageing_basis") != previous.get("ageing_basis"):
        return False, "ageing basis changed between years, due-date and transaction-date clocks differ"
    return True, None


def _evaluate_rungs(
    latest: dict[str, Any], previous: dict[str, Any]
) -> tuple[dict[str, float], list[str], float | None]:
    """Score each computable rung as 1.0 (fired) or 0.0 (did not).

    Returns the per-rung values, ordered notes, and the interest ratio for the
    reason template.  A rung absent from the returned dict was not computable
    and is excluded from the weight renormalisation entirely.
    """
    values: dict[str, float] = {}
    notes: list[str] = []
    interest_ratio: float | None = None

    interest_now, interest_before = _largest_interest(latest), _largest_interest(previous)
    if interest_now is not None and interest_before is not None:
        values[RUNG_INTEREST] = 1.0 if interest_now > interest_before else 0.0
        if interest_before > 0.0:
            interest_ratio = interest_now / interest_before
        elif interest_now > 0.0:
            notes.append("MSMED interest went nil to positive, the strongest form of this signal")

    share_now, share_before = _overdue_share(latest), _overdue_share(previous)
    if share_now is not None and share_before is not None:
        delta_pp = (share_now - share_before) * 100.0
        values[RUNG_MIGRATION] = 1.0 if delta_pp > config.MIGRATION_THRESHOLD_PP else 0.0
    elif not latest.get("has_not_due_column"):
        notes.append("no Not Due column, migration rung dropped rather than defaulted")

    ratio_now, ratio_before = _payables_ratio(latest), _payables_ratio(previous)
    if ratio_now is not None and ratio_before is not None:
        values[RUNG_PAYABLES] = 1.0 if ratio_now > ratio_before else 0.0

    aged_now, aged_before = _nonmsme_aged(latest), _nonmsme_aged(previous)
    if aged_now is not None and aged_before is not None:
        values[RUNG_NONMSME] = 1.0 if aged_now > aged_before else 0.0

    return values, notes, interest_ratio


def compute_node_stress(node_id: str, rows: list[dict[str, Any]]) -> StressDetail:
    """own_stress for one node from its stress_signal rows.

    Uses the two most recent comparable years.  Fewer than two years, or an
    incomparable pair, gives 0.0 — we never guess a change we cannot compute.
    """
    ordered = sorted(rows, key=lambda r: _fy_sort_key(r["fy"]))

    if len(ordered) < 2:
        return StressDetail(
            node_id=node_id,
            own_stress=0.0,
            fy_latest=ordered[-1]["fy"] if ordered else None,
            notes=("insufficient_history",),
        )

    latest, previous = ordered[-1], ordered[-2]

    comparable, reason = _comparable(latest, previous)
    if not comparable:
        return StressDetail(
            node_id=node_id,
            own_stress=0.0,
            fy_latest=latest["fy"],
            fy_previous=previous["fy"],
            notes=(reason,) if reason else (),
        )

    values, notes, interest_ratio = _evaluate_rungs(latest, previous)

    if not values:
        return StressDetail(
            node_id=node_id,
            own_stress=0.0,
            fy_latest=latest["fy"],
            fy_previous=previous["fy"],
            notes=tuple(notes) + ("no rung computable",),
        )

    weight_total = sum(RUNG_WEIGHTS[rung] for rung in values)
    raw = sum(RUNG_WEIGHTS[rung] / weight_total * value for rung, value in sorted(values.items()))

    return StressDetail(
        node_id=node_id,
        own_stress=min(max(raw, 0.0), 1.0),
        fy_latest=latest["fy"],
        fy_previous=previous["fy"],
        rungs_fired=tuple(sorted(r for r, v in values.items() if v > 0.0)),
        rungs_available=tuple(sorted(values)),
        notes=tuple(notes),
        interest_ratio=interest_ratio,
    )


def compute_own_stress(network: dict[str, Any]) -> dict[str, StressDetail]:
    """own_stress for every node in the network.

    Non-observable nodes get 0.0 — their stress is inferred entirely by
    propagation.  Every node appears in the result so downstream code never
    branches on presence.
    """
    by_node: dict[str, list[dict[str, Any]]] = {}
    for row in network["stress_signals"]:
        by_node.setdefault(row["node_id"], []).append(row)

    details: dict[str, StressDetail] = {}
    for node in sorted(network["nodes"], key=lambda n: n["node_id"]):
        node_id = node["node_id"]
        rows = by_node.get(node_id)
        if not node["is_observable"] or not rows:
            details[node_id] = StressDetail(node_id=node_id, own_stress=0.0)
        else:
            details[node_id] = compute_node_stress(node_id, rows)
    return details
