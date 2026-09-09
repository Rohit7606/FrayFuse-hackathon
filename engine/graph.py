"""Network construction from runtime input.

Edge direction convention:
    Edges are added as G.add_edge(supplier_id, buyer_id, ...) — matching
    the direction of goods flow.  Stress propagates AGAINST this direction,
    from buyer to supplier, following the money that failed to arrive.
"""
