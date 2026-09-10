"""Triage tests — the decision layer on top of the ranking.

The rule these defend is the one the ranking cannot express: fragile-and-
irreplaceable and fragile-but-replaceable are the same `final_score` and the
opposite response.  If triage ever becomes a function of `final_score` alone,
`test_same_score_opposite_queue` is what fails.
"""

from __future__ import annotations

import pytest

from engine import config, triage
from engine.graph import build_graph
from engine.pipeline import score_network

# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------


def test_same_score_opposite_queue():
    """The whole reason this module exists, as one assertion."""
    fragile_replaceable = 0.35 * 0.20
    solvent_chokepoint = 0.10 * 0.70
    assert fragile_replaceable == pytest.approx(solvent_chokepoint)

    assert triage.classify(0.35, 0.20, is_origin=False) == "derisk"
    assert triage.classify(0.10, 0.70, is_origin=False) == "fund_now"


def test_thresholds_are_inclusive_at_the_boundary():
    """At the threshold is inside it — config states ">= ", so must the code."""
    frag = config.TRIAGE_FRAGILE_MIN
    crit = config.TRIAGE_IRREPLACEABLE_MIN
    assert triage.classify(frag, crit, is_origin=False) == "fund_now"
    assert triage.classify(frag, crit - 1e-9, is_origin=False) == "derisk"
    assert triage.classify(frag - 1e-9, crit, is_origin=False) == "monitor"


def test_origin_beats_every_other_reading():
    """An origin is a diagnosis, never a rescue target — ranking.py agrees."""
    assert triage.classify(1.0, 1.0, is_origin=True) == "origin"
    assert triage.classify(0.0, 0.0, is_origin=True) == "origin"


def test_untouched_nodes_are_clear():
    assert triage.classify(config.TRIAGE_MONITOR_MIN - 1e-9, 0.9, False) == "clear"


def test_every_queue_is_one_the_contract_allows():
    for fragility in (0.0, 0.05, 0.5, 1.0):
        for criticality in (0.0, 0.2, 0.9):
            for origin in (True, False):
                assert (
                    triage.classify(fragility, criticality, origin) in triage.QUEUE_ORDER
                )


# ---------------------------------------------------------------------------
# escalation thresholds
# ---------------------------------------------------------------------------


def test_unreachable_thresholds_are_none_not_a_number_above_one():
    """A trigger that can never fire must not be printed as if it could."""
    assert triage.escalation_fragility(0.0) is None
    # Criticality this low cannot reach the critical band at fragility 1.0.
    assert triage.escalation_fragility(config.BAND_CRITICAL / 2) is None
    assert triage.escalation_fragility(1.0) == pytest.approx(config.BAND_CRITICAL)


def test_no_emitted_trigger_is_out_of_range(network):
    scored = score_network(network)
    graph = build_graph(network)
    scores = {row["node_id"]: row for row in scored["scores"]}
    origins = set(scored["summary"]["stressed_origin_nodes"])

    for node_id in sorted(scores):
        plan = triage.build_plan(graph, network, scores[node_id], scores, origins)
        for trigger in plan["review_triggers"]:
            if trigger["metric"] in ("fragility", "criticality", "buyer_own_stress"):
                assert 0.0 <= trigger["threshold"] <= 1.0, (node_id, trigger)


# ---------------------------------------------------------------------------
# plans over the real mock network
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scored_mock():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "mock" / "network.json"
    net = json.loads(path.read_text(encoding="utf-8"))
    return net, score_network(net)


def _plans(scored_mock):
    net, scored = scored_mock
    graph = build_graph(net)
    scores = {row["node_id"]: row for row in scored["scores"]}
    origins = set(scored["summary"]["stressed_origin_nodes"])
    return [
        triage.build_plan(graph, net, scores[node_id], scores, origins)
        for node_id in sorted(scores)
    ]


def test_every_node_gets_a_queue_and_a_non_empty_plan(scored_mock):
    plans = _plans(scored_mock)
    assert len(plans) == len(scored_mock[1]["scores"])
    for plan in plans:
        assert plan["queue"] in triage.QUEUE_ORDER
        assert plan["headline"]
        assert plan["actions"]
        assert plan["review_triggers"]
        assert len(plan["status"]) == 2


def test_plan_agrees_with_the_score_it_was_built_from(scored_mock):
    _, scored = scored_mock
    scores = {row["node_id"]: row for row in scored["scores"]}
    for plan in _plans(scored_mock):
        row = scores[plan["node_id"]]
        assert plan["queue"] == row["triage_queue"]
        assert plan["fragility"] == row["fragility"]
        assert plan["stabilisation_cost_cr"] == row["intervention_cost_cr"]
        assert plan["exposure_at_risk_cr"] == row["estimated_exposure_cr"]


def test_alternatives_not_considered_is_null_not_zero(scored_mock):
    """The §4.6 distinction, which a count would silently collapse."""
    _, scored = scored_mock
    scores = {row["node_id"]: row for row in scored["scores"]}
    for plan in _plans(scored_mock):
        candidates = scores[plan["node_id"]]["substitution_candidates"]
        if candidates is None:
            assert plan["alternatives_found"] is None
        else:
            assert plan["alternatives_found"] == len(candidates)


def test_money_is_only_recommended_where_money_is_the_answer(scored_mock):
    for plan in _plans(scored_mock):
        action = plan["recommended_action"]
        if plan["queue"] == "fund_now":
            assert action["kind"] == "fund"
            assert action["amount_cr"] == plan["stabilisation_cost_cr"]
        elif plan["queue"] in ("monitor", "clear", "origin"):
            # null, not 0.0 — money is not the answer here, which is a
            # different fact from a zero-rupee requirement.
            assert action["amount_cr"] is None


def test_plans_are_deterministic(scored_mock):
    assert _plans(scored_mock) == _plans(scored_mock)


def test_the_demo_trigger_is_an_origin_and_the_headline_finding_is_fundable(
    scored_mock, demo
):
    _, scored = scored_mock
    scores = {row["node_id"]: row for row in scored["scores"]}
    assert scores[demo["trigger_node"]]["triage_queue"] == "origin"
    assert scores[demo["intervention"]["node_id"]]["triage_queue"] == "fund_now"


def test_the_watch_queue_reaches_beyond_the_ranked_list(scored_mock):
    """`derisk` is not a subset of `ranking` — SCHEMA.md §4.7 says so.

    A fragile but genuinely replaceable supplier has its low criticality
    multiplied away by final_score and never ranks. Surfacing that population is
    the point of the queue, so if this ever becomes an empty set the queue has
    quietly turned into a filter over `ranking`.
    """
    _, scored = scored_mock
    ranked = set(scored["ranking"])
    watched = {
        row["node_id"] for row in scored["scores"] if row["triage_queue"] == "derisk"
    }
    assert watched - ranked
