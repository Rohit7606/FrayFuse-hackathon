"""Substitution candidates — reading the criticality model on its low side.

The ranked list answers "which suppliers are fragile AND irreplaceable".  This
module answers the opposite question for the other end of the same
distribution: where a supplier is replaceable, who could actually take the
volume.  It introduces no new signal.  Eligibility is decided entirely by
`criticality.CriticalityDetail`, which already measures irreplaceability, and
fitness is scored on `contagion.fragility`, which `ranking.py` already scores
on.

On undisclosed sole-source status.  `_single_source_status` returns three
different facts: 1.0 (confirmed sole source for something), 0.0 (every outgoing
edge explicitly says alternatives exist) and None (no outgoing edge disclosed
its status at all).  Only 0.0 makes a node eligible here.  Treating None as
permission to suggest replacements would assert that alternatives exist on the
strength of absent evidence — the same error AGENTS.md §3.6 exists to prevent,
and the mirror image of the mistake criticality.py already refuses to make when
it drops the sole-source term rather than defaulting it to false.

That rule has teeth on real data rather than being a formality.  On
data/real/network.json all 43 real companies carry undisclosed status, because
not one collected filing made a sole-sourcing statement, so not one of them is
offered a substitute.  Only the synthetic deep tier, where the generator states
the status explicitly, is eligible.  The suggestions are therefore confined to
the part of the network that actually disclosed enough to support them.

Capacity is normalised within tier for the reason documented at the top of
criticality.py: raw rupee headroom is size-correlated, so a network-wide
maximum hands it to the largest node and every deep-tier supplier scores near
zero against a tier-1 hub it was never competing with.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from engine import config
from engine.criticality import CriticalityDetail, _normalise_within_peer_group


@dataclass(frozen=True)
class SubstitutionCandidate:
    """One supplier who could take over one edge, with the arithmetic kept."""

    node_id: str
    name: str
    component: str
    replaces_edge_id: str
    fitness: float
    fragility: float
    # None where the candidate's revenue is undisclosed.  Not 0.0 — a company
    # that did not publish a revenue figure has unknown headroom, not none.
    capacity_headroom_cr: float | None
    reason_text: str


@dataclass(frozen=True)
class SubstitutionDetail:
    """Substitution result for one node.

    `eligible` and an empty `candidates` are different facts, and the schema
    keeps them apart: an ineligible node omits the field entirely ("we did not
    look"), an eligible node with nobody to suggest emits `[]` ("we looked and
    found nobody").
    """

    node_id: str
    eligible: bool
    candidates: tuple[SubstitutionCandidate, ...] = ()


def _committed_outflow(graph: nx.DiGraph, node_id: str) -> float:
    """Total annual value this node already ships to its buyers."""
    return sum(
        graph.edges[node_id, buyer_id]["annual_value_cr"]
        for buyer_id in sorted(graph.successors(node_id))
    )


def _headroom_cr(
    graph: nx.DiGraph, node_id: str, revenue: float | None
) -> float | None:
    """Revenue not already committed to existing customers.

    None where revenue is undisclosed, which is a different fact from zero
    headroom and must not be collapsed into it (AGENTS.md §3.6).  Clamped at
    zero below: a supplier shipping more than its disclosed revenue is a data
    quirk, not negative capacity.

    `revenue` is passed in from the NETWORK rather than read off the graph on
    purpose.  `build_graph` stores `node.get("revenue_cr") or 0.0`, so by the
    time a node reaches the graph an undisclosed revenue is indistinguishable
    from a disclosed zero — the exact collapse §3.6 forbids, and it would make
    every real company with an undisclosed revenue look like it had no capacity
    rather than unknown capacity.  Reading the input keeps the two apart.
    """
    if revenue is None:
        return None
    return max(0.0, revenue - _committed_outflow(graph, node_id))


def _makes_component(graph: nx.DiGraph, node_id: str, component: str) -> int:
    """How many buyers this node already supplies with `component`."""
    return sum(
        1
        for buyer_id in sorted(graph.successors(node_id))
        if graph.edges[node_id, buyer_id]["component"] == component
    )


def _is_eligible(
    graph: nx.DiGraph, node_id: str, detail: CriticalityDetail
) -> bool:
    """Whether this node is replaceable enough to warrant suggesting substitutes."""
    if detail.criticality > config.SUBSTITUTION_CRITICALITY_MAX:
        return False
    # Confirmed-not-sole-source only.  None is undisclosed, and undisclosed is
    # not permission — see the module docstring.
    if detail.single_source != 0.0:
        return False
    return graph.out_degree(node_id) > 0


def _compose_reason(
    component: str,
    other_buyers: int,
    headroom_cr: float | None,
    fragility: float,
) -> str:
    """Why this candidate could take the volume.  Template-generated, no LLM.

    Built the way `ranking._compose_reason` is: clauses assembled from the facts
    that are actually available, joined into one sentence, never empty.
    """
    buyers = "one other buyer" if other_buyers == 1 else f"{other_buyers} other buyers"
    clauses = [
        "Same tier",
        f"already supplies {component.replace('_', ' ')} to {buyers}",
    ]

    if headroom_cr is None:
        clauses.append("revenue undisclosed, so its spare capacity is unknown")
    else:
        clauses.append(f"₹{headroom_cr:.2f} cr of revenue not already committed")

    if fragility <= 0.0:
        clauses.append("no stress has reached it")
    else:
        # Three places, not two: fragility is a narrow quantity and 0.002
        # rounded to 0.00 would print a figure that contradicts its own clause.
        clauses.append(f"its own fragility is {fragility:.3f}")

    return ", ".join(clauses[:-1]) + ", and " + clauses[-1] + "."


def compute_substitutions(
    graph: nx.DiGraph,
    network: dict[str, Any],
    criticality: dict[str, CriticalityDetail],
    fragility: dict[str, float],
) -> dict[str, SubstitutionDetail]:
    """Substitution candidates for every replaceable supplier in the graph.

    `fragility` is the post-intervention value from `contagion`, the same one
    `ranking.py` scores on, so a supplier that has just been funded correctly
    becomes a better substitute rather than staying frozen at its baseline.

    Every loop iterates in sorted order and every tie breaks on `node_id`, so
    two runs over the same graph produce identical output (AGENTS.md §3.1).
    """
    names = {node["node_id"]: node["name"] for node in network["nodes"]}
    node_ids = sorted(graph.nodes)
    tier_of = {node_id: graph.nodes[node_id]["tier"] for node_id in node_ids}

    disclosed_revenue = {
        node["node_id"]: node.get("revenue_cr") for node in network["nodes"]
    }
    headroom = {
        node_id: _headroom_cr(graph, node_id, disclosed_revenue.get(node_id))
        for node_id in node_ids
    }

    # Pass 1 — enumerate every (candidate, edge-being-replaced) pairing and its
    # raw coverage.  Coverage has to be normalised across the whole population
    # before any of it can be scored, so the pairings are collected first.
    Pairing = tuple[str, str, str, str, str]  # supplier, edge_id, buyer, component, candidate
    pairings: list[Pairing] = []
    raw_coverage: dict[tuple[str, str], float] = {}
    coverage_tier: dict[tuple[str, str], int] = {}

    eligible_ids = [
        node_id for node_id in node_ids if _is_eligible(graph, node_id, criticality[node_id])
    ]

    for supplier_id in eligible_ids:
        tier = tier_of[supplier_id]
        for buyer_id in sorted(graph.successors(supplier_id)):
            edge = graph.edges[supplier_id, buyer_id]
            component = edge["component"]
            edge_value = edge["annual_value_cr"]

            for candidate_id in node_ids:
                if candidate_id == supplier_id:
                    continue
                if tier_of[candidate_id] != tier:
                    continue
                if _makes_component(graph, candidate_id, component) == 0:
                    continue
                # Already selling this buyer this part: not an alternative, the
                # same relationship.
                if graph.has_edge(candidate_id, buyer_id) and (
                    graph.edges[candidate_id, buyer_id]["component"] == component
                ):
                    continue

                pairings.append(
                    (supplier_id, edge["edge_id"], buyer_id, component, candidate_id)
                )

                candidate_headroom = headroom[candidate_id]
                if candidate_headroom is None:
                    continue
                key = (candidate_id, edge["edge_id"])
                # Coverage: how many times over the candidate's spare revenue
                # would cover the volume it is being asked to take on.  A
                # zero-value edge carries no volume to absorb, so any spare
                # capacity covers it.
                raw_coverage[key] = (
                    candidate_headroom / edge_value if edge_value > 0.0 else 1.0
                )
                coverage_tier[key] = tier_of[candidate_id]

    # Pass 2 — normalise coverage within tier, for the reason criticality.py
    # documents: rupee capacity is size-correlated and a network-wide maximum
    # would hand every capacity score to the largest tier.
    coverage_keys = {f"{node_id}|{edge_id}": value for (node_id, edge_id), value in raw_coverage.items()}
    coverage_groups = {
        f"{node_id}|{edge_id}": group for (node_id, edge_id), group in coverage_tier.items()
    }
    coverage_norm = _normalise_within_peer_group(coverage_keys, coverage_groups)

    # Pass 3 — score, rank and cap.
    by_supplier: dict[str, list[SubstitutionCandidate]] = {
        supplier_id: [] for supplier_id in eligible_ids
    }

    for supplier_id, edge_id, buyer_id, component, candidate_id in pairings:
        candidate_fragility = fragility[candidate_id]
        health = 1.0 - candidate_fragility

        terms: list[tuple[float, float]] = [(config.W_SUB_HEALTH, health)]
        candidate_headroom = headroom[candidate_id]
        if candidate_headroom is not None:
            terms.append(
                (config.W_SUB_CAPACITY, coverage_norm[f"{candidate_id}|{edge_id}"])
            )

        # An undisclosed revenue drops the capacity term and renormalises onto
        # health, exactly as compute_criticality drops the sole-source term
        # rather than substituting a default.
        weight_total = sum(weight for weight, _ in terms)
        fitness = sum(weight / weight_total * value for weight, value in terms)

        by_supplier[supplier_id].append(
            SubstitutionCandidate(
                node_id=candidate_id,
                name=names.get(candidate_id, candidate_id),
                component=component,
                replaces_edge_id=edge_id,
                fitness=round(min(max(fitness, 0.0), 1.0), 4),
                fragility=round(candidate_fragility, 4),
                capacity_headroom_cr=(
                    None if candidate_headroom is None else round(candidate_headroom, 2)
                ),
                reason_text=_compose_reason(
                    component,
                    _makes_component(graph, candidate_id, component),
                    candidate_headroom,
                    candidate_fragility,
                ),
            )
        )

    details: dict[str, SubstitutionDetail] = {}
    for node_id in node_ids:
        if node_id not in by_supplier:
            details[node_id] = SubstitutionDetail(node_id=node_id, eligible=False)
            continue

        ranked = sorted(
            by_supplier[node_id],
            key=lambda c: (-c.fitness, c.node_id, c.replaces_edge_id),
        )
        # One suggestion per candidate company: three ways to replace the same
        # firm are one alternative, not three.
        seen: set[str] = set()
        unique: list[SubstitutionCandidate] = []
        for candidate in ranked:
            if candidate.node_id in seen:
                continue
            seen.add(candidate.node_id)
            unique.append(candidate)
            if len(unique) == config.SUBSTITUTION_MAX_CANDIDATES:
                break

        details[node_id] = SubstitutionDetail(
            node_id=node_id, eligible=True, candidates=tuple(unique)
        )

    return details
