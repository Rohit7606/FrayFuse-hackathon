"""Criticality scoring — betweenness centrality, single-source flag, flow share.

Measures how irreplaceable a node is in the supply network.  This is the factor
that separates "fragile" from "fragile AND cannot be replaced", which is the
whole argument of the product.

Why betweenness and flow share are normalised within tier.  Both quantities are
size-correlated by construction: a deep-tier supplier is a small company, so it
carries little trade value, and it sits near the edge of the graph, so few paths
run through it.  Dividing by the network-wide maximum hands both maxima to the
tier-1 hub and crushes everything below it — measured on the mock, the tier-1
hub took betweenness 0.875 and flow share 1.000 while a genuine sole-source
tier-2 chokepoint scored 0.137 and 0.012.  That makes 0.65 of criticality a
proxy for revenue, so the ranked list fills with big stressed companies rather
than the small irreplaceable ones the product exists to find.

Normalising within tier asks the question that actually matters — how
irreplaceable is this node compared with the others at its level — and mirrors
the rule the collection workstream already applies to companies: compare within
a peer group, and across groups compare direction and relative position, never
levels (DATA_DICTIONARY.md §5).  A tier whose nodes all score zero, such as the
anchors and the leaf suppliers, normalises to zero rather than dividing by it.

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


def _normalise_within_peer_group(
    values: dict[str, float], peer_group: dict[str, int]
) -> dict[str, float]:
    """Scale each value by the largest in its peer group.

    A group whose values are all zero normalises to zero rather than dividing by
    it — the anchors and the leaf suppliers have no paths running through them,
    and that is a fact about them, not a missing measurement.
    """
    maxima: dict[int, float] = {}
    for node_id, value in values.items():
        group = peer_group[node_id]
        maxima[group] = max(maxima.get(group, 0.0), value)

    normalised: dict[str, float] = {}
    for node_id, value in values.items():
        group_max = maxima[peer_group[node_id]]
        normalised[node_id] = value / group_max if group_max > 0.0 else 0.0
    return normalised


def compute_criticality(graph: nx.DiGraph) -> dict[str, CriticalityDetail]:
    """Criticality for every node in the graph.

    Betweenness on a few hundred nodes is fast enough to compute exactly.  If it
    ever needs k-sampling, seed it — an unseeded sample breaks determinism.
    """
    node_ids = sorted(graph.nodes)
    tier_of = {node_id: graph.nodes[node_id]["tier"] for node_id in node_ids}

    betweenness = nx.betweenness_centrality(graph, normalized=True)
    outgoing_value = {
        node_id: sum(
            graph.edges[node_id, buyer_id]["annual_value_cr"]
            for buyer_id in sorted(graph.successors(node_id))
        )
        for node_id in node_ids
    }

    if config.NORMALISE_CRITICALITY_WITHIN_TIER:
        betweenness_scaled = _normalise_within_peer_group(betweenness, tier_of)
        flow_scaled = _normalise_within_peer_group(outgoing_value, tier_of)
    else:
        whole_network = dict.fromkeys(node_ids, 0)
        betweenness_scaled = _normalise_within_peer_group(betweenness, whole_network)
        flow_scaled = _normalise_within_peer_group(outgoing_value, whole_network)

    details: dict[str, CriticalityDetail] = {}

    for node_id in node_ids:
        betweenness_norm = betweenness_scaled[node_id]
        flow_share_norm = flow_scaled[node_id]

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
