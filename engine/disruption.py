"""Supply disruption — the second propagation, running WITH goods flow.

`contagion.py` answers "who runs out of cash when a buyer stops paying".  This
module answers the opposite question: "whose line stops when a supplier stops
delivering".  Both are needed, and they travel in opposite directions.

    contagion:   buyer -> supplier   (money that failed to arrive)
    disruption:  supplier -> buyer   (parts that failed to arrive)

DEMO_SCENARIO.md §6 needs this pass.  Payment stress alone can never reach the
anchor, because the anchor is the top buyer and nothing propagates into it.
What reaches the anchor is its supplier failing to deliver.

Why own payment stress does not seed a halt
-------------------------------------------
This is the one modelling decision that matters here, and it is the product's
own thesis stated backwards.

`own_stress` is measured from a company's *payment behaviour* — its MSMED
interest rose, its overdue share migrated, its payables outgrew its revenue.
Those signals say the company is paying its suppliers late.  A company
stretching its payables is **conserving cash, not stopping its line**; it is
exporting the problem downstream rather than absorbing it.  Seeding halt risk
from `own_stress` would say the opposite — that the visible tier-1 is the one
about to stop — which is exactly the belief FrayFuse exists to correct.

So halt risk is seeded by the part of a node's fragility it did *not* generate
itself: money owed to it that did not arrive.

    seed(n) = max(0.0, fragility(n) - own_stress(n))

For a funded node this is the *relieved* inherited stress, because
`intervention.py` pins fragility to `own_stress + relieved`.  Seeding from the
reported `inherited_stress` instead would ignore the funding entirely — the
intervention would change nothing downstream, which is the whole demo beat.

Where fragility is capped at 1.0 the subtraction understates the seed.  That is
conservative and deliberate: it can only make disruption smaller.

Why noisy-OR rather than a sum
------------------------------
A line stops if **any** input it cannot replace stops.  That is a disjunction,
not an addition:

    disruption(b) = 1 - Π over suppliers s of (1 - halt(s) x supply_impact(s->b))

Summing would let forty mildly-wobbly suppliers halt a healthy plant, and would
need a cap and a damping constant to stay in range.  Noisy-OR is bounded in
[0, 1] by construction, saturates gracefully, needs no invented constant, and
composes the same way when a halted node halts its own buyer:

    halt(n) = 1 - (1 - seed(n)) x (1 - disruption(n))

— two independent reasons to stop delivering: no cash, or no parts.

The iteration is monotone increasing and bounded above by 1.0, so it converges.
Cycles are fine, exactly as in contagion.

One sentence, out loud
----------------------
    Stress flows down the chain as invoices that were never paid; failure flows
    back up it as parts that never arrived.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from engine import config


@dataclass(frozen=True)
class DisruptionResult:
    """Converged supply-disruption state, with the detail ranking.py needs."""

    halt_risk: dict[str, float]  # chance this node stops delivering
    disruption: dict[str, float]  # chance this node's line stops for want of an input
    disrupted_inflow_cr: dict[str, float]  # expected inbound trade value that fails to arrive
    top_source: dict[str, str]  # buyer -> the supplier contributing most of its disruption
    iterations: int


def inbound_value(graph: nx.DiGraph, buyer_id: str) -> float:
    """Total annual value this buyer purchases across all its suppliers."""
    return sum(
        graph.edges[supplier_id, buyer_id]["annual_value_cr"]
        for supplier_id in sorted(graph.predecessors(buyer_id))
    )


def supply_impact(graph: nx.DiGraph, supplier_id: str, buyer_id: str, inbound: float) -> float:
    """How much of the buyer's ability to produce this one edge controls.

    A **confirmed sole source** scores 1.0 regardless of what the part costs.
    This is the same insight `criticality.py` applies to normalisation: rupee
    value is not importance.  A ₹19 crore seal kit stops a ₹1,241 crore brake
    assembly, because there is nobody else to buy it from.

    Everything else falls back to the supplier's share of the buyer's purchased
    value.  That is a **known understatement** — automotive supply is serial, so
    a cheap part missing stops the line just as dead as an expensive one — but
    it is the only replaceability proxy the data actually carries, and it never
    invents a constant.

    `is_single_source` of None (no filing stated sole-source status — all 37
    real edges) takes the same fallback.  That does implicitly assume the part
    is replaceable, which is a real limitation on real data: where sole-sourcing
    is undisclosed, this pass understates disruption.  Say so rather than
    hiding it.
    """
    if graph.edges[supplier_id, buyer_id]["is_single_source"] is True:
        return 1.0
    if inbound <= 0.0:
        return 0.0
    return graph.edges[supplier_id, buyer_id]["annual_value_cr"] / inbound


def propagate_disruption(
    graph: nx.DiGraph,
    fragility: dict[str, float],
    own_stress: dict[str, float],
) -> DisruptionResult:
    """Iterate supplier-to-buyer stoppage transmission until it converges.

    Args:
        graph:      the directed supply graph, edges supplier -> buyer
        fragility:  converged fragility from contagion, after any intervention
        own_stress: per-node stress from the node's own disclosures

    Synchronous update over sorted node ids, exactly as `contagion.propagate`,
    so the result is byte-identical across runs (AGENTS.md §3.1).
    """
    node_ids = sorted(graph.nodes)

    seed = {
        node_id: max(0.0, fragility.get(node_id, 0.0) - own_stress.get(node_id, 0.0))
        for node_id in node_ids
    }
    inbound = {node_id: inbound_value(graph, node_id) for node_id in node_ids}
    impact = {
        (supplier_id, buyer_id): supply_impact(graph, supplier_id, buyer_id, inbound[buyer_id])
        for supplier_id, buyer_id in sorted(graph.edges)
    }

    halt = dict(seed)
    disruption = dict.fromkeys(node_ids, 0.0)
    top_source: dict[str, str] = {}

    iterations = 0
    for iteration in range(1, config.MAX_ITERATIONS + 1):
        iterations = iteration
        next_disruption: dict[str, float] = {}
        next_top: dict[str, str] = {}

        for buyer_id in node_ids:
            survives = 1.0
            best_supplier, best_amount = "", 0.0

            for supplier_id in sorted(graph.predecessors(buyer_id)):
                contribution = halt[supplier_id] * impact[supplier_id, buyer_id]
                survives *= 1.0 - contribution
                if contribution > best_amount:
                    best_supplier, best_amount = supplier_id, contribution

            next_disruption[buyer_id] = 1.0 - survives
            if best_supplier:
                next_top[buyer_id] = best_supplier

        next_halt = {
            node_id: 1.0 - (1.0 - seed[node_id]) * (1.0 - next_disruption[node_id])
            for node_id in node_ids
        }

        delta = max(abs(next_halt[n] - halt[n]) for n in node_ids)
        halt, disruption, top_source = next_halt, next_disruption, next_top

        if delta < config.CONVERGENCE_THRESHOLD:
            break

    # Money, not probability: if a supplier stops, the whole of what it ships
    # stops arriving, not the replaceability-weighted fraction of it.  The
    # impact weight above answers "does the line stop"; this answers "how much
    # trade fails to arrive", and the two take different weights on purpose.
    # Seeded with 0.0 rather than sum()'s implicit int 0, so a node with no
    # suppliers serialises as 0.0 like every other monetary field instead of
    # as a bare 0 (AGENTS.md §3.1 on rounding consistently).
    disrupted_inflow_cr = {
        buyer_id: sum(
            (
                halt[supplier_id] * graph.edges[supplier_id, buyer_id]["annual_value_cr"]
                for supplier_id in sorted(graph.predecessors(buyer_id))
            ),
            0.0,
        )
        for buyer_id in node_ids
    }

    return DisruptionResult(
        halt_risk=halt,
        disruption=disruption,
        disrupted_inflow_cr=disrupted_inflow_cr,
        top_source=top_source,
        iterations=iterations,
    )
