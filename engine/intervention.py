"""Intervention cost, exposure estimation, and counterfactual scoring.

Both cost and exposure are stated assumptions (see config.py), not measurements.
Be ready to say so: "we assume a three-month disruption window" is a defensible
answer to a judge; pretending it was measured is not.
"""

from __future__ import annotations

from collections import deque

import networkx as nx

from engine import config
from engine.contagion import ContagionResult, propagate


def quarterly_receivable(graph: nx.DiGraph, node_id: str) -> float:
    """One quarter of what this node invoices its buyers annually."""
    annual = sum(
        graph.edges[node_id, buyer_id]["annual_value_cr"]
        for buyer_id in sorted(graph.successors(node_id))
    )
    return annual / 4.0


def intervention_cost(graph: nx.DiGraph, node_id: str, fragility: float) -> float:
    """Money needed to stabilise this supplier.

    One quarter of receivables, scaled by how stressed the node is.  A node
    under no stress needs nothing; a node at fragility 1.0 needs the whole
    quarter bridged.
    """
    return quarterly_receivable(graph, node_id) * fragility


def value_through(graph: nx.DiGraph, node_id: str, tier_of: dict[str, int]) -> float:
    """Annual trade value on the paths from this node down to any anchor.

    PERSON_A.md §3.7 says "sum of annual_value_cr on all paths from n to any
    tier-0 node".  Enumerating paths would double-count every shared edge and is
    combinatorially unbounded on a cyclic graph, so we sum the value of each
    edge that lies on at least one such path, counting every edge exactly once.
    That is a stated modelling choice, and it is the conservative reading: it
    never inflates exposure by counting the same rupee twice.
    """
    anchors = {n for n, tier in tier_of.items() if tier == 0}
    if not anchors:
        return 0.0

    # Nodes from which an anchor is reachable, walking supplier -> buyer.
    reaches_anchor: set[str] = set()
    queue = deque(sorted(anchors))
    seen = set(anchors)
    while queue:
        current = queue.popleft()
        reaches_anchor.add(current)
        for supplier_id in sorted(graph.predecessors(current)):
            if supplier_id not in seen:
                seen.add(supplier_id)
                queue.append(supplier_id)

    if node_id not in reaches_anchor:
        return 0.0

    # Edges downstream of node_id that also lead to an anchor lie on a path.
    total = 0.0
    visited = {node_id}
    queue = deque([node_id])
    while queue:
        current = queue.popleft()
        for buyer_id in sorted(graph.successors(current)):
            if buyer_id not in reaches_anchor:
                continue
            total += graph.edges[current, buyer_id]["annual_value_cr"]
            if buyer_id not in visited:
                visited.add(buyer_id)
                queue.append(buyer_id)
    return total


def estimated_exposure(
    graph: nx.DiGraph, node_id: str, tier_of: dict[str, int], final_score: float
) -> float:
    """Trade value at risk if this supplier fails.

    Scaled by DISRUPTION_MONTHS out of twelve — how long we assume production is
    interrupted before an alternative is qualified — and by final_score, so a
    node unlikely to fail carries proportionally less expected exposure.
    """
    months = config.DISRUPTION_MONTHS / 12.0
    return value_through(graph, node_id, tier_of) * months * final_score


def coverage_for(amount_cr: float, cost_cr: float) -> float:
    """What fraction of a node's stabilisation cost a given amount covers."""
    if cost_cr <= 0.0:
        return 1.0 if amount_cr > 0.0 else 0.0
    return min(max(amount_cr / cost_cr, 0.0), 1.0)


def apply_interventions(
    graph: nx.DiGraph,
    own_stress: dict[str, float],
    baseline: ContagionResult,
    interventions: dict[str, float],
) -> ContagionResult:
    """Re-run propagation with funded nodes' fragility pinned.

    Funding reduces the node's inherited stress in proportion to coverage; its
    own stress is untouched, because cash does not undo a company's own late
    payments.  Propagation is then re-run from scratch rather than patched in
    place — a full re-run is what makes downstream suppliers improve, which is
    the entire point of the closing demo beat.
    """
    if not interventions:
        return baseline

    pinned: dict[str, float] = {}
    for node_id in sorted(interventions):
        amount = interventions[node_id]
        cost = intervention_cost(graph, node_id, baseline.fragility[node_id])
        coverage = coverage_for(amount, cost)
        relieved = baseline.inherited[node_id] * (1.0 - coverage)
        pinned[node_id] = min(1.0, own_stress.get(node_id, 0.0) + relieved)

    return propagate(graph, own_stress, pinned=pinned)
