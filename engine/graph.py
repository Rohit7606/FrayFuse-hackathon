"""Network construction from runtime input.

Edge direction convention:
    Edges are added as G.add_edge(supplier_id, buyer_id, ...) — matching
    the direction of goods flow.  Stress propagates AGAINST this direction,
    from buyer to supplier, following the money that failed to arrive.

Note on multi-row edge collapse.  PERSON_A.md §3.2 specifies grouping repeated
(supplier_id, buyer_id) rows by financial year and dropping terminated
relationships.  That logic cannot live here: the runtime Edge contract carries
neither `fy` nor a termination field, so the information only exists in the
collection CSVs.  Collapse therefore belongs to transform.py, and this module
treats a duplicate pair as a contract violation and raises.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from engine import config


class DanglingEdgeError(ValueError):
    """An edge references a node_id that is not in the network."""


class DuplicateEdgeError(ValueError):
    """Two edges share a (supplier_id, buyer_id) pair.

    DiGraph.add_edge would silently overwrite the first edge's attributes.
    Collapse belongs upstream in transform.py — see the module docstring.
    """


class ExposureOverflowError(ValueError):
    """A supplier's outgoing exposure_pct sums to more than the whole of its revenue."""


def propagating_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the edges evidenced well enough to carry stress, sorted by edge_id.

    An edge whose `confidence` is not in PROPAGATING_EDGE_CONFIDENCE is real
    context but not a claim the company made — see schema_change_request.md §1.
    A missing `confidence` is treated as the strongest level, because the field
    was only added in schema 1.1 and pre-1.1 files predate the distinction.
    """
    return sorted(
        (
            edge
            for edge in edges
            if edge.get("confidence", "confirmed") in config.PROPAGATING_EDGE_CONFIDENCE
        ),
        key=lambda e: e["edge_id"],
    )


def build_graph(network: dict[str, Any]) -> nx.DiGraph:
    """Build the directed supply graph from a NetworkInput dict.

    Nodes and edges are inserted in sorted-ID order.  NetworkX preserves
    insertion order, and betweenness centrality can differ on ties otherwise
    (AGENTS.md §3.1).
    """
    graph = nx.DiGraph()

    for node in sorted(network["nodes"], key=lambda n: n["node_id"]):
        graph.add_node(
            node["node_id"],
            tier=node["tier"],
            revenue_cr=node["revenue_cr"],
            cash_buffer_days=node["cash_buffer_days"],
            name=node["name"],
            sector=node["sector"],
            product_category=node["product_category"],
            is_observable=node["is_observable"],
            data_source=node["data_source"],
        )

    seen: dict[tuple[str, str], str] = {}
    exposure_sum: dict[str, float] = {}

    for edge in propagating_edges(network["edges"]):
        supplier_id, buyer_id = edge["supplier_id"], edge["buyer_id"]

        for role, node_id in (("supplier_id", supplier_id), ("buyer_id", buyer_id)):
            if node_id not in graph:
                raise DanglingEdgeError(
                    f"{edge['edge_id']} has dangling {role} {node_id}"
                )

        pair = (supplier_id, buyer_id)
        if pair in seen:
            raise DuplicateEdgeError(
                f"{edge['edge_id']} repeats the pair {supplier_id}->{buyer_id} "
                f"already added by {seen[pair]}; collapse it in transform.py"
            )
        seen[pair] = edge["edge_id"]

        exposure_sum[supplier_id] = exposure_sum.get(supplier_id, 0.0) + edge["exposure_pct"]

        graph.add_edge(
            supplier_id,
            buyer_id,
            edge_id=edge["edge_id"],
            exposure_pct=edge["exposure_pct"],
            annual_value_cr=edge["annual_value_cr"],
            is_single_source=edge.get("is_single_source"),
            component=edge["component"],
            data_source=edge["data_source"],
        )

    for supplier_id, total in sorted(exposure_sum.items()):
        if total > config.MAX_EXPOSURE_SUM_TOLERANCE:
            raise ExposureOverflowError(
                f"{supplier_id} outgoing exposure_pct sums to {total:.4f} > "
                f"{config.MAX_EXPOSURE_SUM_TOLERANCE}"
            )

    return graph


def buyers_of(graph: nx.DiGraph, supplier_id: str) -> list[str]:
    """Buyers a supplier sells to, sorted.  Stress arrives from these."""
    return sorted(graph.successors(supplier_id))


def suppliers_of(graph: nx.DiGraph, buyer_id: str) -> list[str]:
    """Suppliers a buyer buys from, sorted.  Stress travels on to these."""
    return sorted(graph.predecessors(buyer_id))
