"""The single public entry point for the FrayFuse engine.

Person B calls exactly one function: score_network().
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from engine import criticality as criticality_mod
from engine import intervention as intervention_mod
from engine import ranking as ranking_mod
from engine import stress as stress_mod
from engine import substitution as substitution_mod
from engine import triage as triage_mod
from engine.contagion import propagate
from engine.disruption import propagate_disruption
from engine.graph import build_graph


class UnknownNodeError(Exception):
    """Raised when a scenario references a node_id not present in the network."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"{node_id} not in network")


@dataclass(frozen=True)
class StressOverride:
    """Override a node's own_stress value in a scenario."""

    node_id: str
    own_stress: float


@dataclass(frozen=True)
class Intervention:
    """Fund a node to reduce its inherited stress."""

    node_id: str
    amount_cr: float


@dataclass(frozen=True)
class Scenario:
    """An immutable scenario with stress overrides and interventions.

    Frozen and tuple-based so it cannot be mutated mid-scoring.
    """

    stress_overrides: tuple[StressOverride, ...] = ()
    interventions: tuple[Intervention, ...] = ()

    def with_interventions(
        self, interventions: Sequence[Intervention]
    ) -> Scenario:
        """Return a new Scenario with additional interventions appended."""
        return Scenario(
            stress_overrides=self.stress_overrides,
            interventions=self.interventions + tuple(interventions),
        )


def _validate_scenario(scenario: Scenario, node_ids: set[str]) -> None:
    """Reject a scenario naming a node the network does not contain.

    Raised as UnknownNodeError so the API can map it to a 400 that names the
    offending ID, rather than letting a typo surface as a 500.
    """
    for override in scenario.stress_overrides:
        if override.node_id not in node_ids:
            raise UnknownNodeError(override.node_id)
    for funding in scenario.interventions:
        if funding.node_id not in node_ids:
            raise UnknownNodeError(funding.node_id)


def score_network(
    network: dict,
    scenario: Scenario | None = None,
) -> dict:
    """Score a network under an optional scenario.

    Args:
        network:  NetworkInput dict, validated against schema.json
        scenario: stress overrides and interventions; None means baseline

    Returns:
        ScoredNetwork dict, validated against schema.json

    Pure. Deterministic. No I/O, no globals, no mutation of the input.
    """
    scenario = scenario or Scenario()
    network = copy.deepcopy(network)

    node_ids = {node["node_id"] for node in network["nodes"]}
    _validate_scenario(scenario, node_ids)

    graph = build_graph(network)

    stress_detail = stress_mod.compute_own_stress(network)
    own_stress = {node_id: detail.own_stress for node_id, detail in stress_detail.items()}
    for override in sorted(scenario.stress_overrides, key=lambda o: o.node_id):
        own_stress[override.node_id] = min(max(override.own_stress, 0.0), 1.0)

    baseline = propagate(graph, own_stress)

    funding = {
        node_id: sum(
            f.amount_cr for f in scenario.interventions if f.node_id == node_id
        )
        for node_id in sorted({f.node_id for f in scenario.interventions})
    }
    contagion = intervention_mod.apply_interventions(graph, own_stress, baseline, funding)

    criticality = criticality_mod.compute_criticality(graph)
    tier_of = {node["node_id"]: node["tier"] for node in network["nodes"]}

    # The second propagation, running WITH goods flow: whose line stops when a
    # supplier stops delivering.  Runs on the post-intervention fragility, so
    # funding a supplier is visible all the way up at the anchor.
    disruption = propagate_disruption(graph, contagion.fragility, own_stress)

    costs: dict[str, Any] = {}
    exposures: dict[str, Any] = {}
    for node_id in sorted(graph.nodes):
        costs[node_id] = intervention_mod.intervention_cost(
            graph, node_id, contagion.fragility[node_id]
        )
        exposures[node_id] = intervention_mod.estimated_exposure(
            graph,
            node_id,
            tier_of,
            contagion.fragility[node_id] * criticality[node_id].criticality,
        )

    # Substitution reads criticality on its low side and scores on the
    # post-intervention fragility, so a funded supplier correctly becomes a
    # better alternative.  Orchestrated here rather than from ranking.py, which
    # composes scores and must not reach for its own inputs.
    substitutions = substitution_mod.compute_substitutions(
        graph, network, criticality, contagion.fragility
    )

    # Which queue each supplier belongs in.  Reads the same two factors the
    # ranking multiplies together, but keeps them apart — fragile-and-
    # irreplaceable and fragile-but-replaceable are the same final_score and
    # opposite decisions (triage.py).
    triage = triage_mod.classify_all(
        contagion.fragility,
        {node_id: detail.criticality for node_id, detail in criticality.items()},
        set(contagion.origins),
    )

    scores = ranking_mod.build_scores(
        graph,
        network,
        stress_detail,
        contagion,
        criticality,
        costs,
        exposures,
        disruption,
        substitutions,
        triage,
    )

    return {
        "meta": network["meta"],
        "nodes": network["nodes"],
        "edges": network["edges"],
        "scores": scores,
        "ranking": ranking_mod.ranking_of(scores),
        "summary": ranking_mod.build_summary(scores, contagion, disruption, tier_of),
    }


def main() -> None:
    """Score a network file and print the ranked list.

    Usage: python -m engine.pipeline data/mock/network.json
    """
    import argparse
    import json
    import sys
    from pathlib import Path

    # Reason strings carry ₹, and Windows consoles default to cp1252, which
    # cannot encode it — the determinism check in AGENTS.md §5.2 redirects this
    # output to a file and died on it.  Force UTF-8 rather than dropping the
    # currency symbol, since every displayed number must carry its unit.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Score a FrayFuse network.")
    parser.add_argument("network", type=Path, help="path to a NetworkInput json file")
    parser.add_argument("--json", action="store_true", help="print the full ScoredNetwork")
    parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="also spread this many ₹ cr across the ranked suppliers",
    )
    args = parser.parse_args()

    network = json.loads(args.network.read_text(encoding="utf-8"))
    result = score_network(network)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    names = {n["node_id"]: n["name"] for n in result["nodes"]}
    by_id = {s["node_id"]: s for s in result["scores"]}
    summary = result["summary"]

    print(
        f"{summary['total_nodes']} nodes, "
        f"{summary['at_risk_count']} at risk, "
        f"converged in {summary['iterations_to_converge']} iterations"
    )
    print(f"bands: {summary['band_counts']}")

    # What to DO about them, which the bands deliberately do not say.
    queues: dict[str, int] = {}
    for score in result["scores"]:
        queue = score.get("triage_queue") or "clear"
        queues[queue] = queues.get(queue, 0) + 1
    print(f"queues: {queues}")
    print(
        f"intervention ₹{summary['total_intervention_cost_cr']} cr "
        f"vs exposure ₹{summary['total_estimated_exposure_cr']} cr\n"
    )
    for node_id in result["ranking"]:
        score = by_id[node_id]
        print(
            f"{score['rank']:>3}. {node_id} {names[node_id]}  "
            f"[{score['risk_band']}] [{score.get('triage_queue', '?')}] "
            f"score {score['final_score']:.4f} "
            f"= fragility {score['fragility']:.4f} x criticality {score['criticality']:.4f}"
        )
        print(f"     {score['reason_text']}")
        print(
            f"     stabilise ₹{score['intervention_cost_cr']} cr | "
            f"exposure ₹{score['estimated_exposure_cr']} cr | depth {score['propagation_depth']}"
        )

    # The counterfactual beat, DEMO_SCENARIO.md §6.  Printed here so the demo's
    # closing line can be rehearsed from the CLI without the API or the UI.
    anchors = [a for a in summary["anchor_disruption"] if a["supply_disruption"] > 0.0]
    if anchors:
        print("\nanchors at risk from a supplier that stops delivering:")
        for anchor in anchors:
            stopped_by = anchor["stopped_by"]
            through = f" via {stopped_by} {names[stopped_by]}" if stopped_by else ""
            print(
                f"     {anchor['node_id']} {names[anchor['node_id']]}  "
                f"[{anchor['disruption_band']}] disruption "
                f"{anchor['supply_disruption']:.4f}{through}"
            )
            print(f"     ₹{anchor['disrupted_inflow_cr']} cr of inbound supply at risk")

    # The budget beat, rehearsable from the CLI for the same reason the
    # counterfactual above is.  Imported here rather than at module scope
    # because allocation.py imports this module.
    if args.budget is not None:
        from engine.allocation import allocate_budget

        allocation = allocate_budget(network, args.budget)
        objective = allocation["objective"]
        print(
            f"\n₹{allocation['budget_cr']} cr budget: "
            f"₹{allocation['allocated_cr']} cr committed, "
            f"₹{allocation['unallocated_cr']} cr unallocated "
            f"({allocation['scoring_runs']} scoring runs)"
        )
        print(
            f"     anchor inflow at risk ₹{objective['before_cr']} cr → "
            f"₹{objective['after_cr']} cr  (−₹{objective['reduced_cr']} cr)"
        )
        for row in allocation["allocations"]:
            print(
                f"     ₹{row['amount_cr']:>6.2f} cr → {row['node_id']} {row['name']}  "
                f"{row['coverage'] * 100:.0f}% of need · "
                f"{row['band_before']} → {row['band_after']}"
            )


if __name__ == "__main__":
    main()
