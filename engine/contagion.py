"""Contagion propagation — the core of FrayFuse.

Stress propagates from buyers to suppliers (against goods flow), scaled by
exposure_pct and damped by cash_buffer_days.  Synchronous update with sorted
iteration for determinism.

Why synchronous: the whole new fragility vector is computed from the previous
one and then swapped.  Updating in place would make the result depend on
iteration order, which breaks the byte-identical guarantee in AGENTS.md §3.1.

Why damping: without it a long chain accumulates stress without limit and
everything ends up at 1.0.  Each hop transmits DAMPING of what reached it,
which produces sensible three-to-four-hop decay.

Cycles are expected — supply chains contain them.  Synchronous iteration with
damping handles them; do not attempt a topological sort.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import networkx as nx

from engine import config


@dataclass(frozen=True)
class ContagionResult:
    """Converged fragility across the network, with the detail needed to explain it."""

    fragility: dict[str, float]
    inherited: dict[str, float]
    own_stress: dict[str, float]
    depth: dict[str, int]
    iterations: int
    origins: tuple[str, ...]
    top_contributor: dict[str, str]  # node_id -> the buyer that sent it the most stress


def buffer_strength(cash_buffer_days: int) -> float:
    """How much of an incoming shock a node's cash buffer absorbs.

    Capped at MAX_BUFFER_STRENGTH because nobody is fully immune, and because
    collection measured this field across 44 verified company-years and found it
    does not separate distress from control (AUC 0.569).  It is a shock
    absorption term, not a predictive signal, so it must nudge rather than
    decide — see config.MAX_BUFFER_STRENGTH for the full evidence.
    """
    return min(max(cash_buffer_days / config.BUFFER_REF_DAYS, 0.0), config.MAX_BUFFER_STRENGTH)


def _propagation_depth(graph: nx.DiGraph, origins: list[str]) -> dict[str, int]:
    """Hops from the nearest originating stress node, following buyer to supplier.

    Stress travels against goods flow, so the BFS walks predecessors.  Nodes no
    stress can reach are given 0 — the schema requires a non-negative integer
    and there is no "unreachable" value in the contract.  Their fragility is
    0.0, so the UI never animates them anyway.
    """
    depth = {node_id: 0 for node_id in graph.nodes}
    if not origins:
        return depth

    seen = set(origins)
    queue = deque((node_id, 0) for node_id in sorted(origins))
    while queue:
        node_id, hops = queue.popleft()
        depth[node_id] = hops
        for supplier_id in sorted(graph.predecessors(node_id)):
            if supplier_id not in seen:
                seen.add(supplier_id)
                queue.append((supplier_id, hops + 1))
    return depth


def propagate(
    graph: nx.DiGraph,
    own_stress: dict[str, float],
    pinned: dict[str, float] | None = None,
) -> ContagionResult:
    """Iterate buyer-to-supplier stress transmission until it converges.

    Args:
        graph:      the directed supply graph, edges supplier -> buyer
        own_stress: per-node stress from the node's own disclosures
        pinned:     nodes whose fragility is held fixed, used by intervention.py
                    to re-run propagation with a funded node's stress clamped

    Returns the converged vector plus the detail ranking.py needs for reasons.
    """
    pinned = pinned or {}
    node_ids = sorted(graph.nodes)

    fragility = {
        node_id: pinned.get(node_id, own_stress.get(node_id, 0.0)) for node_id in node_ids
    }
    inherited = {node_id: 0.0 for node_id in node_ids}
    top_contributor: dict[str, str] = {}

    iterations = 0
    for iteration in range(1, config.MAX_ITERATIONS + 1):
        iterations = iteration
        next_fragility: dict[str, float] = {}
        next_inherited: dict[str, float] = {}
        next_top: dict[str, str] = {}

        for supplier_id in node_ids:
            received = 0.0
            best_buyer, best_amount = "", 0.0

            for buyer_id in sorted(graph.successors(supplier_id)):
                exposure = graph.edges[supplier_id, buyer_id]["exposure_pct"]
                contribution = fragility[buyer_id] * exposure
                received += contribution
                if contribution > best_amount:
                    best_buyer, best_amount = buyer_id, contribution

            received *= config.DAMPING
            received *= 1.0 - buffer_strength(graph.nodes[supplier_id]["cash_buffer_days"])

            next_inherited[supplier_id] = received
            if best_buyer:
                next_top[supplier_id] = best_buyer

            if supplier_id in pinned:
                next_fragility[supplier_id] = pinned[supplier_id]
            else:
                next_fragility[supplier_id] = min(
                    1.0, own_stress.get(supplier_id, 0.0) + received
                )

        delta = max((abs(next_fragility[n] - fragility[n]) for n in node_ids), default=0.0)
        fragility, inherited, top_contributor = next_fragility, next_inherited, next_top

        if delta < config.CONVERGENCE_THRESHOLD:
            break

    origins = [n for n in node_ids if own_stress.get(n, 0.0) > 0.0]

    return ContagionResult(
        fragility=fragility,
        inherited=inherited,
        own_stress={n: own_stress.get(n, 0.0) for n in node_ids},
        depth=_propagation_depth(graph, origins),
        iterations=iterations,
        origins=tuple(origins),
        top_contributor=top_contributor,
    )
