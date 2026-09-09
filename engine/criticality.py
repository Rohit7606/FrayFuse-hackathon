"""Criticality scoring — betweenness centrality, single-source flag, flow share.

Measures how irreplaceable a node is in the supply network.  This is the factor
that separates "fragile" from "fragile AND cannot be replaced", which is the
whole argument of the product.

On unknown sole-source status.  schema 1.1 made is_single_source nullable:
null means no filing stated sole-source status, and coercing it to false would
assert that alternatives exist.  All 37 real edges are null — not one filing in
the collected set made a sole-sourcing statement.  Treating that as 0.0 would
cap every real node at 0.65 criticality and rank them below every synthetic
chokepoint, which would encode our collection gap as a fact about the
companies.  So where a node's sole-source status is entirely unknown we drop
the term and renormalise the remaining weights, exactly as the stress ladder
drops an uncomputable rung.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from engine import config


@dataclass(frozen=True)
class CriticalityDetail:
    """Criticality for one node, with each component kept separate for reasons."""

    node_id: str
    criticality: float
    betweenness_norm: float
    flow_share_norm: float
    single_source: float | None  # None where no outgoing edge disclosed its status
    single_source_components: tuple[str, ...] = ()
    downstream_count: int = 0  # suppliers routing through this node, for the chokepoint reason


def _single_source_status(
    graph: nx.DiGraph, node_id: str
) -> tuple[float | None, tuple[str, ...]]:
    """Whether this node is a sole source for anything it sells.

    Returns (1.0, components) if any outgoing edge is a confirmed sole source,
    (0.0, ()) if every outgoing edge explicitly says alternatives exist, and
    (None, ()) where no outgoing edge disclosed its status at all.
    """
    components: list[str] = []
    any_known = False

    for buyer_id in sorted(graph.successors(node_id)):
        flag = graph.edges[node_id, buyer_id]["is_single_source"]
        if flag is None:
            continue
        any_known = True
        if flag:
            components.append(graph.edges[node_id, buyer_id]["component"])

    if components:
        return 1.0, tuple(sorted(set(components)))
    return (0.0, ()) if any_known else (None, ())


def compute_criticality(graph: nx.DiGraph) -> dict[str, CriticalityDetail]:
    """Criticality for every node in the graph.

    Betweenness on a few hundred nodes is fast enough to compute exactly.  If it
    ever needs k-sampling, seed it — an unseeded sample breaks determinism.
    """
    node_ids = sorted(graph.nodes)

    betweenness = nx.betweenness_centrality(graph, normalized=True)
    max_betweenness = max(betweenness.values(), default=0.0)

    outgoing_value = {
        node_id: sum(
            graph.edges[node_id, buyer_id]["annual_value_cr"]
            for buyer_id in sorted(graph.successors(node_id))
        )
        for node_id in node_ids
    }
    max_flow_share = max(outgoing_value.values(), default=0.0)

    details: dict[str, CriticalityDetail] = {}

    for node_id in node_ids:
        betweenness_norm = betweenness[node_id] / max_betweenness if max_betweenness > 0.0 else 0.0
        flow_share_norm = outgoing_value[node_id] / max_flow_share if max_flow_share > 0.0 else 0.0

        single_source, components = _single_source_status(graph, node_id)

        terms: list[tuple[float, float]] = [
            (config.W_BETWEENNESS, betweenness_norm),
            (config.W_FLOW_SHARE, flow_share_norm),
        ]
        if single_source is not None:
            terms.append((config.W_SINGLE_SOURCE, single_source))

        weight_total = sum(weight for weight, _ in terms)
        raw = sum(weight / weight_total * value for weight, value in terms)

        details[node_id] = CriticalityDetail(
            node_id=node_id,
            criticality=min(max(raw, 0.0), 1.0),
            betweenness_norm=betweenness_norm,
            flow_share_norm=flow_share_norm,
            single_source=single_source,
            single_source_components=components,
            downstream_count=len(list(graph.predecessors(node_id))),
        )

    return details
