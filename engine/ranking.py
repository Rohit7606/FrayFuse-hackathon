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
from engine.stress import StressDetail

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


def build_scores(
    graph: nx.DiGraph,
    network: dict[str, Any],
    stress: dict[str, StressDetail],
    contagion: ContagionResult,
    criticality: dict[str, CriticalityDetail],
    costs: dict[str, float],
    exposures: dict[str, float],
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
            }
        )

    ranked = sorted(
        (s for s in scores if s["risk_band"] != "stable"),
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
) -> dict[str, Any]:
    """Network-level totals for the header panel."""
    band_counts = {band: 0 for band in BAND_ORDER}
    for score in scores:
        band_counts[score["risk_band"]] += 1

    at_risk = [s for s in scores if s["rank"] is not None]

    return {
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
