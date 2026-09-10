"""Which queue a supplier belongs in, and the de-risking plan for a watched one.

`final_score` says how much a supplier matters.  This module answers the next
question — what to DO about it — and the two are not the same, because the
product that makes the ranking honest also destroys the distinction the
decision needs:

    fragility 0.35 x criticality 0.20  =  0.070
    fragility 0.10 x criticality 0.70  =  0.070

The same number, and the opposite response.  The first supplier is running out
of money but somebody else makes the part; the second is irreplaceable but
solvent.  Writing a cheque to either one is a mistake.  So triage reads the two
factors separately and puts every node in exactly one of five queues:

    fund_now  fragile AND irreplaceable — the cheque is the answer
    derisk    fragile but relatively replaceable — watch it, second-source it,
              and hold the money for somebody who has no alternative
    monitor   stress has reached it but it is not yet fragile, or it is a
              chokepoint that is currently solvent
    clear     nothing meaningful reached it
    origin    the stress starts here.  It is a diagnosis, not a rescue target —
              the same reason `ranking` excludes origins (ranking.py)

Everything here is template-generated and deterministic.  No scoring happens in
this module: it reads figures the pipeline already computed and decides what to
call them.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from engine import config

# Ordered worst-first, the order a queue list is read in.
QUEUE_ORDER = ("fund_now", "derisk", "monitor", "clear", "origin")

QUEUE_LABEL = {
    "fund_now": "Fund now",
    "derisk": "Watch / de-risk",
    "monitor": "Monitor",
    "clear": "No action",
    "origin": "Stress origin",
}


def classify(fragility: float, criticality: float, is_origin: bool) -> str:
    """The queue this supplier belongs in.  Thresholds live in config.py."""
    if is_origin:
        return "origin"
    if fragility < config.TRIAGE_MONITOR_MIN:
        return "clear"
    if fragility >= config.TRIAGE_FRAGILE_MIN:
        if criticality >= config.TRIAGE_IRREPLACEABLE_MIN:
            return "fund_now"
        return "derisk"
    return "monitor"


def classify_all(
    fragility: dict[str, float],
    criticality: dict[str, float],
    origins: set[str],
) -> dict[str, str]:
    """One queue per node, iterated in sorted id order (AGENTS.md 3.1)."""
    return {
        node_id: classify(
            fragility[node_id], criticality.get(node_id, 0.0), node_id in origins
        )
        for node_id in sorted(fragility)
    }


def band_fragility(criticality: float, band_threshold: float) -> float | None:
    """The fragility at which this supplier's final_score reaches a band.

    None when criticality is too low for the band to be reachable at any
    fragility.  That is the honest answer for a genuinely replaceable supplier
    rather than a threshold of 1.4 dressed up as a trigger, and it is why the
    plan falls back to a lower band, or to the buyer, for its review point.
    """
    if criticality <= 0.0:
        return None
    threshold = band_threshold / criticality
    return None if threshold > 1.0 else threshold


def escalation_fragility(criticality: float) -> float | None:
    """The fragility at which this supplier crosses into the critical band."""
    return band_fragility(criticality, config.TRIAGE_ESCALATION_SCORE)


def _principal_buyer(graph: nx.DiGraph, node_id: str) -> dict[str, Any] | None:
    """The buyer this supplier most depends on for revenue.

    Ordered by exposure first, then value, then edge id — the same tiebreak the
    dependency path in the UI walks, so the plan names the buyer that appears
    on the chain rather than a different one.
    """
    edges = [
        {"buyer_id": buyer_id, **graph.edges[node_id, buyer_id]}
        for buyer_id in sorted(graph.successors(node_id))
    ]
    if not edges:
        return None
    edges.sort(key=lambda e: (-e["exposure_pct"], -e["annual_value_cr"], e["edge_id"]))
    return edges[0]


def _status_lines(
    fragile: bool, irreplaceable: bool, fragility: float, criticality: float, tier: int
) -> list[dict[str, Any]]:
    """The two readings, stated separately rather than collapsed into one word.

    This is the "High financial fragility, moderate replaceability" line —
    generated from the figures, not written by hand for one supplier.
    """
    return [
        {
            "kind": "fragility",
            "verdict": "fragile" if fragile else "holding",
            "detail": (
                f"Financially fragile — fragility {fragility:.2f}, at or above the "
                f"{config.TRIAGE_FRAGILE_MIN:.2f} watch threshold."
                if fragile
                else f"Not yet financially fragile — fragility {fragility:.2f}, below "
                f"the {config.TRIAGE_FRAGILE_MIN:.2f} watch threshold."
            ),
        },
        {
            "kind": "replaceability",
            "verdict": "irreplaceable" if irreplaceable else "replaceable",
            "detail": (
                f"Hard to replace — criticality {criticality:.2f} within tier {tier}, "
                f"in the top decile of this network."
                if irreplaceable
                else f"Relatively replaceable — criticality {criticality:.2f} within "
                f"tier {tier}, below the {config.TRIAGE_IRREPLACEABLE_MIN:.2f} "
                f"chokepoint threshold."
            ),
        },
    ]


def _review_triggers(
    fragility: float,
    criticality: float,
    escalate_at: float | None,
    alternatives: int | None,
    dependency: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """What would move this supplier into the funding queue, in order of nearness."""
    triggers: list[dict[str, Any]] = []

    if escalate_at is not None:
        triggers.append(
            {
                "metric": "fragility",
                "current": round(fragility, 4),
                "threshold": round(escalate_at, 4),
                "detail": (
                    f"Escalate to the funding queue if fragility reaches "
                    f"{escalate_at:.2f} — at this criticality that is where final_score "
                    f"crosses {config.TRIAGE_ESCALATION_SCORE:.2f} and the band turns "
                    f"critical."
                ),
            }
        )
    else:
        # It cannot reach the critical band on its own finances at any
        # fragility, so the review point is the band it CAN reach.  Stating the
        # unreachable threshold would be a trigger that never fires.
        high_at = band_fragility(criticality, config.BAND_HIGH)
        if high_at is not None:
            triggers.append(
                {
                    "metric": "fragility",
                    "current": round(fragility, 4),
                    "threshold": round(high_at, 4),
                    "detail": (
                        f"Re-review if fragility reaches {high_at:.2f} — that is where "
                        f"this supplier's band turns high. At criticality "
                        f"{criticality:.2f} it cannot reach critical on its own "
                        f"finances, however fragile it gets."
                    ),
                }
            )
        triggers.append(
            {
                "metric": "criticality",
                "current": round(criticality, 4),
                "threshold": round(config.TRIAGE_IRREPLACEABLE_MIN, 4),
                "detail": (
                    f"At criticality {criticality:.2f} this supplier cannot reach the "
                    f"critical band on its own finances alone. Escalate only if it "
                    f"becomes harder to replace — a lost second source, or volume "
                    f"concentrating onto it."
                ),
            }
        )

    if alternatives is not None:
        triggers.append(
            {
                "metric": "alternatives",
                "current": float(alternatives),
                "threshold": 0.0,
                "detail": (
                    f"{alternatives} alternative supplier(s) of the same part score as "
                    f"healthy enough to take the volume today. Escalate if that reaches "
                    f"zero — replaceability is the whole reason this is a watch and not "
                    f"a cheque."
                    if alternatives > 0
                    else "No alternative supplier of the same part was found in this "
                    "network. Replaceability here is a low criticality score, not a "
                    "second source you can call — treat the watch as provisional."
                ),
            }
        )

    if dependency is not None and dependency["buyer_is_stressed_origin"]:
        triggers.append(
            {
                "metric": "buyer_own_stress",
                "current": dependency["buyer_own_stress"],
                "threshold": round(min(1.0, dependency["buyer_own_stress"] + 0.1), 4),
                "detail": (
                    f"{dependency['buyer_name']} is an origin of this stress and takes "
                    f"{dependency['exposure_pct'] * 100:.0f}% of this supplier's "
                    f"revenue. Re-run the moment its payment behaviour worsens again."
                ),
            }
        )

    return triggers


def build_plan(
    graph: nx.DiGraph,
    network: dict[str, Any],
    score: dict[str, Any],
    scores_by_id: dict[str, dict[str, Any]],
    origins: set[str],
) -> dict[str, Any]:
    """The de-risking plan for one supplier.

    Reads only what the pipeline already computed — no scoring happens here, so
    a plan is a pure restatement of figures the caller can already see.  Every
    string is a template filled from those figures: AGENTS.md 1.2 rules an LLM
    out anywhere near this, and a plan that cannot be re-derived from the
    numbers on screen is a plan nobody can defend under questioning.
    """
    names = {n["node_id"]: n["name"] for n in network["nodes"]}
    tiers = {n["node_id"]: n["tier"] for n in network["nodes"]}

    node_id = score["node_id"]
    fragility = score["fragility"]
    criticality = score["criticality"]
    queue = score.get("triage_queue") or classify(
        fragility, criticality, node_id in origins
    )
    name = names.get(node_id, node_id)

    fragile = fragility >= config.TRIAGE_FRAGILE_MIN
    irreplaceable = criticality >= config.TRIAGE_IRREPLACEABLE_MIN

    buyer = _principal_buyer(graph, node_id)
    dependency: dict[str, Any] | None = None
    if buyer is not None:
        buyer_id = buyer["buyer_id"]
        buyer_score = scores_by_id.get(buyer_id, {})
        dependency = {
            "buyer_id": buyer_id,
            "buyer_name": names.get(buyer_id, buyer_id),
            "edge_id": buyer["edge_id"],
            "component": buyer["component"],
            "exposure_pct": round(buyer["exposure_pct"], 4),
            "annual_value_cr": round(buyer["annual_value_cr"], 2),
            "buyer_is_stressed_origin": buyer_id in origins,
            "buyer_own_stress": round(buyer_score.get("own_stress", 0.0), 4),
            "buyer_fragility": round(buyer_score.get("fragility", 0.0), 4),
        }

    inherited = score.get("inherited_stress", 0.0)
    inherited_share = round(inherited / fragility, 4) if fragility > 0.0 else 0.0

    # None means substitution was never considered for this node; [] means it
    # was considered and nobody qualified.  Carried through with the same
    # distinction the contract keeps everywhere else (SCHEMA.md 4.6).
    candidates = score.get("substitution_candidates")
    alternatives = None if candidates is None else len(candidates)

    escalate_at = escalation_fragility(criticality)
    # The fragility this supplier is actually reviewed at: the critical band if
    # it can reach it, the high band otherwise.
    review_at = escalate_at or band_fragility(criticality, config.BAND_HIGH)
    triggers = _review_triggers(
        fragility, criticality, escalate_at, alternatives, dependency
    )

    cost = score.get("intervention_cost_cr", 0.0)
    exposure = score.get("estimated_exposure_cr", 0.0)

    if queue == "fund_now":
        headline = (
            f"Fragile and hard to replace. {name} is a rescue candidate: ₹{cost:.2f} cr "
            f"stabilises it against ₹{exposure:.2f} cr of trade value at risk."
        )
        action = {"kind": "fund", "label": "Fund this supplier", "amount_cr": round(cost, 2)}
        actions = [
            (
                f"Commit ₹{cost:.2f} cr — one quarter of its receivables, scaled by "
                f"how stressed it is."
            ),
            (
                "Re-score the network with the funding applied and check the anchor's "
                "inbound supply at risk moves."
            ),
            "Hold it on the funded list until its band leaves critical.",
        ]
    elif queue == "derisk":
        headline = (
            f"High financial fragility, moderate replaceability. Immediate rescue is "
            f"not prioritised for {name} — watch it, and hold the money for a supplier "
            f"with no alternative."
        )
        action = {
            "kind": "derisk",
            "label": "Create de-risking plan",
            "amount_cr": round(cost, 2),
        }
        actions = [
            (
                "Flag for enhanced monitoring — re-read this filer's ageing table "
                "each quarter rather than each year."
            ),
            (
                f"Set the review trigger at fragility {escalate_at:.2f}; crossing it "
                f"moves this supplier into the funding queue."
                if escalate_at is not None
                else (
                    f"Set the review trigger at fragility {review_at:.2f}, where its "
                    f"band turns high — it cannot reach critical on its own finances "
                    f"at this criticality."
                    if review_at is not None
                    else "Set the review trigger on replaceability: escalate if the "
                    "alternatives disappear."
                )
            ),
            (
                f"Qualify a second source now, while there is time — {alternatives} "
                f"candidate(s) already score as able to take the volume."
                if alternatives
                else (
                    "Qualify a second source now, while there is time — the engine "
                    "looked and found no other supplier of this part in the network."
                    if alternatives == 0
                    else "Qualify a second source now, while there is time. "
                    "Replaceability here means this supplier is not a chokepoint, "
                    "not that a named alternative was found — substitution is only "
                    "searched below criticality "
                    f"{config.SUBSTITUTION_CRITICALITY_MAX:.2f}."
                )
            ),
            (
                f"Hold ₹{cost:.2f} cr contingent, not committed. It is what "
                f"stabilising this supplier would cost if the trigger fires."
            ),
        ]
    elif queue == "monitor":
        headline = (
            f"Stress has reached {name} but it is not yet fragile. Nothing to fund; "
            f"something to watch."
        )
        action = {"kind": "monitor", "label": "Add to watchlist", "amount_cr": None}
        actions = [
            (
                "Keep it on the watchlist and re-run when the upstream buyer's next "
                "filing lands."
            ),
            (
                f"It carries ₹{exposure:.2f} cr of trade value at risk — enough that a "
                f"deterioration here is worth catching early."
                if exposure > 0
                else "No trade value is currently at risk through this node."
            ),
        ]
    elif queue == "origin":
        headline = (
            f"{name} is where this stress starts — its own filings say it is paying "
            f"late. That is the diagnosis, not the rescue target."
        )
        action = {"kind": "none", "label": "Not a rescue target", "amount_cr": None}
        actions = [
            (
                "Funding the origin does not stabilise the suppliers it is "
                "stretching; the money has to reach them directly."
            ),
            (
                "Use the what-if control to see what its payment behaviour does to "
                "the tiers below it."
            ),
        ]
    else:
        headline = f"No meaningful stress reaches {name} in this scenario."
        action = {"kind": "none", "label": "No action", "amount_cr": None}
        actions = ["Nothing to do. It reappears here if the upstream stress rises."]

    return {
        "node_id": node_id,
        "name": name,
        "tier": tiers.get(node_id, 0),
        "queue": queue,
        "queue_label": QUEUE_LABEL[queue],
        "headline": headline,
        "fragility": round(fragility, 4),
        "criticality": round(criticality, 4),
        "final_score": round(score.get("final_score", 0.0), 4),
        "risk_band": score.get("risk_band", "stable"),
        "status": _status_lines(
            fragile, irreplaceable, fragility, criticality, tiers.get(node_id, 0)
        ),
        "exposure_at_risk_cr": round(exposure, 2),
        "stabilisation_cost_cr": round(cost, 2),
        "inherited_share": inherited_share,
        "alternatives_found": alternatives,
        "dependency": dependency,
        "review_triggers": triggers,
        "actions": actions,
        "recommended_action": action,
    }
