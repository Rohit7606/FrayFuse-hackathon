"""Budget allocation tests.

Two properties matter more than any figure these produce: the allocator must
never commit more than it was given, and the same budget must always produce the
same plan.  A judge re-running the optimiser on stage and seeing a different
split would sink the demo faster than a wrong number would.
"""

from __future__ import annotations

import pytest

from engine import config
from engine.allocation import allocate_budget, anchor_inflow_at_risk
from engine.pipeline import Intervention, Scenario, StressOverride, score_network

# The allocator scores once per probed candidate, so a small pool keeps the
# suite quick without changing what is being tested.
POOL = 4
BUDGET = 5.0


@pytest.fixture(scope="module")
def mock_network():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "mock" / "network.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result(mock_network):
    return allocate_budget(mock_network, BUDGET, pool_size=POOL)


def test_never_commits_more_than_the_budget(result):
    assert result["allocated_cr"] <= BUDGET + 1e-9
    assert result["allocated_cr"] + result["unallocated_cr"] == pytest.approx(BUDGET)


def test_no_supplier_is_given_more_than_it_needs(result):
    for row in result["allocations"]:
        assert row["amount_cr"] <= row["cost_cr"] + 1e-9
        assert 0.0 <= row["coverage"] <= 1.0


def test_dust_is_reported_unallocated_rather_than_sprinkled(result):
    for row in result["allocations"]:
        assert row["coverage"] >= config.ALLOCATION_MIN_COVERAGE


def test_each_supplier_appears_once(result):
    ids = [row["node_id"] for row in result["allocations"]]
    assert len(ids) == len(set(ids))


def test_deterministic(mock_network):
    first = allocate_budget(mock_network, BUDGET, pool_size=POOL)
    second = allocate_budget(mock_network, BUDGET, pool_size=POOL)
    assert first["allocations"] == second["allocations"]
    assert first["objective"] == second["objective"]


def test_it_actually_reduces_the_thing_it_optimises(result):
    assert result["objective"]["reduced_cr"] > 0.0
    assert result["objective"]["after_cr"] < result["objective"]["before_cr"]


def test_the_reported_objective_is_the_joint_re_score_not_a_sum_of_probes(result):
    """The figure to quote comes from scoring the whole allocation together.

    Independent probes double-count suppliers that share a chain, so their sum
    is an upper bound and must never be what gets reported.
    """
    assert result["objective"]["after_cr"] == pytest.approx(
        anchor_inflow_at_risk(result["after"])
    )
    assert result["objective"]["reduced_cr"] == pytest.approx(
        result["objective"]["before_cr"] - result["objective"]["after_cr"], abs=0.01
    )


def test_ordering_is_by_efficiency(result):
    efficiencies = [row["efficiency"] for row in result["allocations"]]
    assert efficiencies == sorted(efficiencies, reverse=True)


def test_zero_budget_allocates_nothing_and_changes_nothing(mock_network):
    result = allocate_budget(mock_network, 0.0, pool_size=POOL)
    assert result["allocations"] == []
    assert result["allocated_cr"] == 0.0
    assert result["objective"]["reduced_cr"] == 0.0
    # No funding means no second scoring pass to make: before IS after.
    assert result["after"] is result["before"]


def test_a_budget_larger_than_the_pool_needs_reports_the_remainder(mock_network):
    result = allocate_budget(mock_network, 10_000.0, pool_size=POOL)
    assert result["unallocated_cr"] > 0.0
    for row in result["allocations"]:
        assert row["coverage"] == pytest.approx(1.0)


def test_no_stressed_origin_is_ever_funded(mock_network, result):
    """Funding the company doing the stretching does not stabilise its suppliers.

    `ranking` already excludes origins and the allocator draws from `ranking`;
    this asserts the property directly so a future change of candidate source
    cannot quietly reintroduce them.
    """
    origins = set(result["before"]["summary"]["stressed_origin_nodes"])
    assert origins
    assert not {row["node_id"] for row in result["allocations"]} & origins


def test_it_respects_a_baseline_scenario(mock_network):
    """An allocation made under a what-if is an allocation for that network."""
    trigger = score_network(mock_network)["summary"]["stressed_origin_nodes"][0]
    calm = Scenario(
        stress_overrides=(StressOverride(node_id=trigger, own_stress=0.0),)
    )
    result = allocate_budget(mock_network, BUDGET, base_scenario=calm, pool_size=POOL)
    # With the origin paying on time there is nothing left to rescue, so the
    # money stays in the account rather than being spent to prove a point.
    assert result["allocated_cr"] == 0.0
    assert result["unallocated_cr"] == pytest.approx(BUDGET)


def test_interventions_already_in_the_scenario_are_kept(mock_network):
    """The budget is committed on top of funding that has already happened."""
    baseline = score_network(mock_network)
    top = baseline["ranking"][0]
    cost = next(
        row["intervention_cost_cr"] for row in baseline["scores"] if row["node_id"] == top
    )
    funded = Scenario(interventions=(Intervention(node_id=top, amount_cr=cost),))

    result = allocate_budget(mock_network, BUDGET, base_scenario=funded, pool_size=POOL)
    # Already stabilised, so it is not re-funded out of the new budget.
    assert top not in {row["node_id"] for row in result["allocations"]}
