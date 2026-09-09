"""Engine tests — the ten assertions specified in docs/PERSON_A.md §6.

test_demo_scenario is the safety net.  If a tuning change breaks it, that is the
system working: retune, or update the fixture deliberately with both other team
members named on the PR (DEMO_SCENARIO.md §7).
"""

from __future__ import annotations

import copy
import json

import pytest

from engine import config
from engine.contagion import propagate
from engine.criticality import compute_criticality
from engine.graph import build_graph
from engine.pipeline import (
    Intervention,
    Scenario,
    StressOverride,
    UnknownNodeError,
    score_network,
)
from engine.stress import compute_node_stress, compute_own_stress
from tests.engine.conftest import validator_for

# ---------------------------------------------------------------------------
# Determinism and purity
# ---------------------------------------------------------------------------


def test_determinism(network):
    """Two runs on the same input give byte-identical JSON (AGENTS.md §3.1)."""
    first = json.dumps(score_network(network), sort_keys=True)
    second = json.dumps(score_network(network), sort_keys=True)
    assert first == second


def test_no_input_mutation(network):
    """score_network never mutates the network it was handed."""
    before = copy.deepcopy(network)
    score_network(network)
    assert network == before


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


def test_schema_valid(network, schema):
    """mockgen output validates as NetworkInput; pipeline output as ScoredNetwork."""
    input_errors = sorted(
        validator_for(schema, "NetworkInput").iter_errors(network),
        key=lambda e: list(e.path),
    )
    assert input_errors == [], [f"{list(e.path)}: {e.message}" for e in input_errors[:5]]

    result = score_network(network)
    output_errors = sorted(
        validator_for(schema, "ScoredNetwork").iter_errors(result),
        key=lambda e: list(e.path),
    )
    assert output_errors == [], [f"{list(e.path)}: {e.message}" for e in output_errors[:5]]


def test_fragility_bounds(network):
    """No score falls outside [0, 1] on any node."""
    for score in score_network(network)["scores"]:
        for field in ("own_stress", "inherited_stress", "fragility", "criticality", "final_score"):
            assert 0.0 <= score[field] <= 1.0, f"{score['node_id']}.{field} = {score[field]}"


def test_reasons_present(network):
    """Every score carries a non-empty reason and factors summing to 1.0."""
    for score in score_network(network)["scores"]:
        assert score["reason_text"].strip(), score["node_id"]
        assert len(score["reason_text"]) >= 10, score["node_id"]
        assert score["reason_factors"], score["node_id"]
        total = sum(f["weight"] for f in score["reason_factors"])
        assert abs(total - 1.0) < 1e-9, f"{score['node_id']} factors sum to {total}"


def test_ranking_is_ordered_and_tie_broken(network):
    """Ranking is final_score descending, ties broken by node_id ascending."""
    result = score_network(network)
    by_id = {s["node_id"]: s for s in result["scores"]}
    keys = [(-by_id[n]["final_score"], n) for n in result["ranking"]]
    assert keys == sorted(keys)
    assert all(by_id[n]["risk_band"] != "stable" for n in result["ranking"])
    assert all(
        s["rank"] is None for s in result["scores"] if s["risk_band"] == "stable"
    )

    # Stressed origins keep their band but are never ranked — SCHEMA.md §4.3.
    origins = set(result["summary"]["stressed_origin_nodes"])
    assert origins, "the demo network must have at least one stressed origin"
    assert not (origins & set(result["ranking"]))
    assert all(by_id[n]["rank"] is None for n in origins)


# ---------------------------------------------------------------------------
# Propagation behaviour
# ---------------------------------------------------------------------------


def test_convergence(network):
    """Contagion terminates under MAX_ITERATIONS on the demo network."""
    summary = score_network(network)["summary"]
    assert summary["iterations_to_converge"] <= config.MAX_ITERATIONS


def test_cycles(network):
    """A network containing a cycle converges rather than diverging."""
    graph = build_graph(network)
    # A -> B -> C -> A, every edge carrying the whole of the supplier's revenue.
    graph.add_edge("CYC_A", "CYC_B", exposure_pct=1.0, annual_value_cr=1.0)
    graph.add_edge("CYC_B", "CYC_C", exposure_pct=1.0, annual_value_cr=1.0)
    graph.add_edge("CYC_C", "CYC_A", exposure_pct=1.0, annual_value_cr=1.0)
    for node_id in ("CYC_A", "CYC_B", "CYC_C"):
        graph.nodes[node_id]["cash_buffer_days"] = 0

    own_stress = {n: 0.0 for n in graph.nodes}
    own_stress["CYC_A"] = 1.0

    result = propagate(graph, own_stress)
    assert result.iterations <= config.MAX_ITERATIONS
    assert all(0.0 <= v <= 1.0 for v in result.fragility.values())


def test_intervention_monotonic(network, demo):
    """Funding a node never increases fragility anywhere in the network."""
    before = score_network(network)
    after = score_network(
        network,
        Scenario(
            interventions=(
                Intervention(demo["intervention"]["node_id"], demo["intervention"]["amount_cr"]),
            )
        ),
    )

    before_by_id = {s["node_id"]: s["fragility"] for s in before["scores"]}
    for score in after["scores"]:
        assert score["fragility"] <= before_by_id[score["node_id"]] + 1e-9, score["node_id"]


def test_stress_override_applies(network):
    """A scenario override replaces a node's own_stress and propagates."""
    baseline = score_network(network)
    raised = score_network(network, Scenario(stress_overrides=(StressOverride("N007", 1.0),)))

    baseline_by_id = {s["node_id"]: s for s in baseline["scores"]}
    raised_by_id = {s["node_id"]: s for s in raised["scores"]}

    assert raised_by_id["N007"]["own_stress"] == 1.0
    assert raised_by_id["N042"]["fragility"] > baseline_by_id["N042"]["fragility"]


def test_unknown_node_raises(network):
    """A scenario naming a node not in the network raises UnknownNodeError."""
    with pytest.raises(UnknownNodeError) as excinfo:
        score_network(network, Scenario(stress_overrides=(StressOverride("N999", 0.5),)))
    assert excinfo.value.node_id == "N999"

    with pytest.raises(UnknownNodeError):
        score_network(network, Scenario(interventions=(Intervention("N999", 1.0),)))


# ---------------------------------------------------------------------------
# Null versus zero — AGENTS.md §3.6
# ---------------------------------------------------------------------------


def _signal_row(fy: str, **overrides) -> dict:
    row = {
        "node_id": "N001",
        "fy": fy,
        "msme_not_due_cr": 100.0,
        "msme_under_1yr_cr": 5.0,
        "total_trade_payables_cr": 200.0,
        "revenue_cr": 1000.0,
        "has_not_due_column": True,
        "ageing_basis": "due_date",
        "basis": "standalone",
        "data_source": "real",
    }
    row.update(overrides)
    return row


def test_null_vs_zero(network):
    """An undisclosed figure and a disclosed nil produce different behaviour.

    Interest null in both years means the rung cannot be computed and is dropped
    from the renormalisation.  Interest 0.0 rising to 0.5 is a disclosed nil
    becoming a disclosed positive — the strongest form of the primary signal.
    """
    undisclosed = compute_node_stress(
        "N001",
        [
            _signal_row("FY23", msmed_interest_accrued_unpaid_cr=None),
            _signal_row("FY24", msmed_interest_accrued_unpaid_cr=None),
        ],
    )
    disclosed_nil_then_positive = compute_node_stress(
        "N001",
        [
            _signal_row("FY23", msmed_interest_accrued_unpaid_cr=0.0),
            _signal_row("FY24", msmed_interest_accrued_unpaid_cr=0.5),
        ],
    )

    assert "interest_direction" not in undisclosed.rungs_available
    assert "interest_direction" in disclosed_nil_then_positive.rungs_fired
    assert disclosed_nil_then_positive.own_stress > undisclosed.own_stress


def test_missing_not_due_column_drops_migration_rung():
    """has_not_due_column false makes the migration rung unavailable, not zero."""
    detail = compute_node_stress(
        "N001",
        [
            _signal_row("FY23", has_not_due_column=False),
            _signal_row("FY24", has_not_due_column=False),
        ],
    )
    assert "not_due_migration" not in detail.rungs_available


def test_series_break_skips_the_transition():
    """A year flagged series_break is not differenced against the year before it."""
    detail = compute_node_stress(
        "N001",
        [
            _signal_row("FY23", msmed_interest_accrued_unpaid_cr=0.1),
            _signal_row(
                "FY24",
                msmed_interest_accrued_unpaid_cr=9.0,
                series_break="ind_as_transition",
            ),
        ],
    )
    assert detail.own_stress == 0.0
    assert detail.rungs_fired == ()


def test_single_year_gives_no_stress(network):
    """One year of data cannot produce a change, so own_stress is 0.0."""
    detail = compute_node_stress("N001", [_signal_row("FY24")])
    assert detail.own_stress == 0.0
    assert "insufficient_history" in detail.notes


def test_non_observable_nodes_have_no_own_stress(network):
    """Nodes with no disclosures get 0.0 — their stress comes from propagation."""
    details = compute_own_stress(network)
    observable = {n["node_id"] for n in network["nodes"] if n["is_observable"]}
    for node_id, detail in details.items():
        if node_id not in observable:
            assert detail.own_stress == 0.0


# ---------------------------------------------------------------------------
# The demo fixture
# ---------------------------------------------------------------------------


def test_demo_nodes_present(network, demo):
    """The six fixed DEMO_SCENARIO.md IDs survive any regeneration."""
    node_ids = {n["node_id"] for n in network["nodes"]}
    expected = set(demo["expected_ranking"]) | {demo["trigger_node"], demo["counterfactual_anchor"]}
    assert expected <= node_ids


def test_sole_source_outranks_equally_fragile_peer(network):
    """N042 must outrank N203 on criticality — DEMO_SCENARIO.md §3.

    Both are tier-2 and comparably stressed; only N042 is irreplaceable. This is
    the contrast the whole ranking argument rests on ("fragility alone is not
    enough — we rank by fragile x irreplaceable"), so it gets a test of its own
    rather than riding on the fixture's exact band values.
    """
    graph = build_graph(network)
    criticality = compute_criticality(graph)
    by_id = {s["node_id"]: s for s in score_network(network)["scores"]}

    # N203 is deliberately the BETTER-connected node: more suppliers route
    # through it, so it wins on betweenness. It must still lose overall.
    assert criticality["N203"].betweenness_norm > criticality["N042"].betweenness_norm
    assert criticality["N042"].single_source == 1.0
    assert criticality["N203"].single_source == 0.0
    assert by_id["N042"]["criticality"] > by_id["N203"]["criticality"]
    assert by_id["N042"]["final_score"] > 2.0 * by_id["N203"]["final_score"]


def test_deep_tier_criticality_is_not_crushed_by_the_hub(network):
    """A deep-tier chokepoint must be able to out-score the tier-1 hub on criticality.

    Betweenness and flow share are size-correlated, so normalising them across
    the whole network makes criticality a proxy for revenue and buries exactly
    the suppliers the product exists to find. Guards config.NORMALISE_CRITICALITY_WITHIN_TIER.
    """
    graph = build_graph(network)
    criticality = compute_criticality(graph)
    assert criticality["N042"].criticality > 0.4
    assert criticality["N118"].criticality > criticality["N203"].criticality


def test_demo_anchor_pays_on_time(network):
    """N001 is the anchor: DEMO_SCENARIO.md §2 says it pays on time.

    The counterfactual only lands if the anchor starts the demo green, so its
    own disclosures must show no deterioration.
    """
    assert compute_own_stress(network)["N001"].own_stress == 0.0


def test_demo_scenario(network, demo):
    """Ranking and bands match data/fixtures/demo_scenario.json."""
    result = score_network(network)
    by_id = {s["node_id"]: s for s in result["scores"]}

    assert result["ranking"][: len(demo["expected_ranking"])] == demo["expected_ranking"]
    assert demo["trigger_node"] in result["summary"]["stressed_origin_nodes"]
    for node_id, expected_band in demo["expected_bands"].items():
        assert by_id[node_id]["risk_band"] == expected_band, node_id


def test_demo_intervention_bands(network, demo):
    """Funding N042 moves it and N118 into the fixture's expected after-bands."""
    result = score_network(
        network,
        Scenario(
            interventions=(
                Intervention(demo["intervention"]["node_id"], demo["intervention"]["amount_cr"]),
            )
        ),
    )
    by_id = {s["node_id"]: s for s in result["scores"]}
    for node_id, expected_band in demo["expected_after_bands"].items():
        assert by_id[node_id]["risk_band"] == expected_band, node_id
