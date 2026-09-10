"""Thin wrapper over engine.pipeline — keeps endpoint handlers clean.

Every scoring path the API has goes through here, so `main.py` is routing,
validation and serialisation only, and the engine is called from exactly one
module.

**Statelessness.** `AGENTS.md` §3.4 permits caching only as a pure function of
the request. The baseline is cached because it is a pure function of the loaded
network file and never changes for a given dataset; every scenario-bearing
request is scored fresh, and nothing is retained between calls.
"""

from __future__ import annotations

from typing import Any

from api.adapters import to_engine_scenario
from api.models import Intervention, Scenario
from engine import allocation as allocation_mod
from engine import config as engine_config
from engine import triage as triage_mod
from engine.graph import build_graph
from engine.pipeline import UnknownNodeError, score_network

_baseline_cache: dict[str, Any] | None = None


def reset_baseline_cache() -> None:
    """Drop the cached baseline.

    Only for tests and for a process that swaps the network file underneath
    itself. Nothing in a request path should call this.
    """
    global _baseline_cache
    _baseline_cache = None


def validate_node_ids(scenario: Scenario, network: dict[str, Any]) -> None:
    """Raise UnknownNodeError if the scenario names a node the network lacks.

    The engine validates this too. Doing it here as well means the API can
    answer a typo with a 400 without paying for a full scoring run first, and
    the error names the same ID either way.
    """
    known = {node["node_id"] for node in network["nodes"]}
    for override in scenario.stress_overrides:
        if override.node_id not in known:
            raise UnknownNodeError(override.node_id)
    for funding in scenario.interventions:
        if funding.node_id not in known:
            raise UnknownNodeError(funding.node_id)


def baseline(network: dict[str, Any]) -> dict[str, Any]:
    """The unscenario'd ScoredNetwork, computed once per process."""
    global _baseline_cache
    if _baseline_cache is None:
        _baseline_cache = score_network(network)
    return _baseline_cache


def simulate(network: dict[str, Any], scenario: Scenario) -> dict[str, Any]:
    """Score the network under one scenario. Never cached — the input varies."""
    validate_node_ids(scenario, network)
    return score_network(network, to_engine_scenario(scenario))


def intervene(
    network: dict[str, Any],
    baseline_scenario: Scenario,
    interventions: list[Intervention],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Score the same network with and without a set of interventions.

    Returns `(before, after)`. Two full scoring runs per request is correct and
    deliberate — the comparison *is* the product, and patching the first result
    in place would hide exactly the downstream improvements the closing demo
    beat exists to show. Do not optimise it into one.
    """
    funded = Scenario(interventions=interventions)
    validate_node_ids(baseline_scenario, network)
    validate_node_ids(funded, network)

    engine_baseline = to_engine_scenario(baseline_scenario)
    engine_after = engine_baseline.with_interventions(
        to_engine_scenario(funded).interventions
    )

    return score_network(network, engine_baseline), score_network(network, engine_after)


def derisk(
    network: dict[str, Any],
    node_id: str,
    scenario: Scenario,
) -> dict[str, Any]:
    """The de-risking plan for one supplier under one scenario.

    One scoring run, then a restatement of what it produced — the plan reads
    figures, it does not compute new ones. The scenario is honoured so that a
    plan built while the what-if slider is off its baseline describes the
    network the caller is actually looking at.
    """
    if node_id not in {node["node_id"] for node in network["nodes"]}:
        raise UnknownNodeError(node_id)
    validate_node_ids(scenario, network)

    scored = score_network(network, to_engine_scenario(scenario))
    scores_by_id = {row["node_id"]: row for row in scored["scores"]}

    return triage_mod.build_plan(
        build_graph(network),
        network,
        scores_by_id[node_id],
        scores_by_id,
        set(scored["summary"]["stressed_origin_nodes"]),
    )


def allocate(
    network: dict[str, Any],
    budget_cr: float,
    baseline_scenario: Scenario,
    max_candidates: int | None = None,
) -> dict[str, Any]:
    """Spread a budget across the ranked suppliers.

    Never cached: the budget varies, and a cached allocation would be a plan for
    somebody else's money. Costs one scoring run per probed candidate plus a
    baseline and a joint re-score — see engine/allocation.py.
    """
    validate_node_ids(baseline_scenario, network)
    return allocation_mod.allocate_budget(
        network,
        budget_cr,
        to_engine_scenario(baseline_scenario),
        pool_size=max_candidates or engine_config.ALLOCATION_CANDIDATE_POOL,
    )
