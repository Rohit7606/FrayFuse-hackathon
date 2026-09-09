"""Supply-disruption tests — the second propagation, running with goods flow.

The counterfactual beat in DEMO_SCENARIO.md §6 rests on these: the anchor
carries real supply risk at baseline, and funding the deep-tier chokepoint
visibly reduces it.  If a tuning change breaks that, the demo's closing step
stops working — retune, or update §6 deliberately with both other team members
named on the PR.
"""

from __future__ import annotations

import networkx as nx
import pytest

from engine import config
from engine.disruption import propagate_disruption, supply_impact
from engine.graph import build_graph
from engine.pipeline import Intervention, Scenario, score_network


@pytest.fixture
def scored(network):
    return score_network(network)


def _by_id(result):
    return {s["node_id"]: s for s in result["scores"]}


# ---------------------------------------------------------------------------
# Bounds, determinism, convergence
# ---------------------------------------------------------------------------


def test_disruption_within_bounds(scored):
    """Both propagated quantities stay in [0, 1] on every node."""
    for score in scored["scores"]:
        assert 0.0 <= score["halt_risk"] <= 1.0, score["node_id"]
        assert 0.0 <= score["supply_disruption"] <= 1.0, score["node_id"]
        assert score["disrupted_inflow_cr"] >= 0.0, score["node_id"]


def test_disruption_converges(scored):
    """Terminates well inside MAX_ITERATIONS, like contagion."""
    assert scored["summary"]["disruption_iterations_to_converge"] < config.MAX_ITERATIONS


def test_disruption_deterministic(network):
    """Same input, same numbers — noisy-OR is a product, so order would show."""
    first = _by_id(score_network(network))
    second = _by_id(score_network(network))
    for node_id, score in first.items():
        assert score["halt_risk"] == second[node_id]["halt_risk"]
        assert score["supply_disruption"] == second[node_id]["supply_disruption"]


def test_every_score_has_a_disruption_reason(scored):
    """Never empty, exactly like reason_text (SCHEMA.md §4.1)."""
    for score in scored["scores"]:
        assert score["disruption_reason"].strip()
        assert len(score["disruption_reason"]) >= 10


def test_disruption_converges_on_a_cycle():
    """A cycle must converge rather than ratchet to 1.0.

    Noisy-OR is monotone increasing and bounded, so it settles; this pins that
    behaviour rather than trusting the argument.
    """
    graph = nx.DiGraph()
    for node_id in ("N001", "N002", "N003"):
        graph.add_node(node_id, tier=1, cash_buffer_days=10)
    for supplier, buyer in (("N001", "N002"), ("N002", "N003"), ("N003", "N001")):
        graph.add_edge(
            supplier,
            buyer,
            exposure_pct=0.5,
            annual_value_cr=10.0,
            is_single_source=True,
            component="widget",
        )

    fragility = {"N001": 0.4, "N002": 0.0, "N003": 0.0}
    result = propagate_disruption(graph, fragility, dict.fromkeys(fragility, 0.0))

    assert result.iterations <= config.MAX_ITERATIONS
    for node_id, value in result.halt_risk.items():
        assert 0.0 <= value <= 1.0, node_id


# ---------------------------------------------------------------------------
# The modelling decisions, pinned
# ---------------------------------------------------------------------------


def test_own_payment_stress_does_not_seed_a_halt(network, scored):
    """A company stretching its payables is conserving cash, not stopping.

    N007 is stressed entirely by its own disclosures (own_stress == fragility),
    so every bit of its halt risk must come from its own suppliers failing —
    not from its payment behaviour.  This is the product's thesis stated
    backwards; if it inverts, the demo argues against itself.
    """
    n007 = _by_id(scored)["N007"]
    assert n007["own_stress"] == n007["fragility"]
    assert n007["halt_risk"] == pytest.approx(n007["supply_disruption"])


def test_sole_source_impact_ignores_rupee_value(network):
    """A confirmed sole source scores 1.0 whatever the part costs.

    N042 ships N007 a ₹19.2 cr seal kit out of ₹212 cr of inbound purchases —
    9% by value, 100% by replaceability.
    """
    graph = build_graph(network)
    inbound = sum(
        graph.edges[s, "N007"]["annual_value_cr"] for s in graph.predecessors("N007")
    )
    assert supply_impact(graph, "N042", "N007", inbound) == 1.0

    # A non-sole-source edge falls back to its share of purchased value.
    assert supply_impact(graph, "N203", "N007", inbound) < 0.5


def test_disruption_reaches_the_anchor(scored):
    """The beat payment stress structurally cannot produce.

    N001 is the top buyer, so nothing propagates *into* it and its fragility is
    0.0 by construction.  Supply disruption travels the other way and does
    reach it — that is the entire reason this pass exists.
    """
    n001 = _by_id(scored)["N001"]
    assert n001["fragility"] == 0.0
    assert n001["supply_disruption"] > 0.0
    assert n001["disruption_band"] != "stable"
    assert n001["disrupted_inflow_cr"] > 0.0


def test_anchor_disruption_summary_is_ordered(scored):
    """summary.anchor_disruption lists tier-0 nodes, worst first."""
    anchors = scored["summary"]["anchor_disruption"]
    assert anchors, "the mock network has three tier-0 anchors"
    keys = [(-a["supply_disruption"], a["node_id"]) for a in anchors]
    assert keys == sorted(keys)
    assert anchors[0]["node_id"] == "N001"
    assert anchors[0]["stopped_by"] == "N007"


# ---------------------------------------------------------------------------
# The counterfactual — DEMO_SCENARIO.md §6
# ---------------------------------------------------------------------------


def test_intervention_reduces_anchor_disruption(network, demo, scored):
    """Funding N042 must visibly drain supply risk out of the anchor.

    This is step 7's second half.  Without it the toggle has nothing to show.
    """
    after = _by_id(
        score_network(
            network,
            Scenario(
                interventions=(
                    Intervention(
                        demo["intervention"]["node_id"], demo["intervention"]["amount_cr"]
                    ),
                )
            ),
        )
    )
    before = _by_id(scored)
    anchor = demo["counterfactual_anchor"]

    assert after[anchor]["supply_disruption"] < before[anchor]["supply_disruption"]
    assert after[anchor]["disrupted_inflow_cr"] < before[anchor]["disrupted_inflow_cr"]
    # The trigger's own line risk clears too: its sole-source input is funded.
    assert after["N007"]["supply_disruption"] < before["N007"]["supply_disruption"] / 2


def test_intervention_never_worsens_disruption(network, demo):
    """Funding a node must not raise supply disruption anywhere.

    The monotonicity twin of test_intervention_monotonic: money can only remove
    stoppage risk from the network, never add it.
    """
    before = _by_id(score_network(network))
    after = _by_id(
        score_network(
            network,
            Scenario(
                interventions=(
                    Intervention(
                        demo["intervention"]["node_id"], demo["intervention"]["amount_cr"]
                    ),
                )
            ),
        )
    )
    for node_id, score in before.items():
        assert after[node_id]["supply_disruption"] <= score["supply_disruption"] + 1e-9, node_id
