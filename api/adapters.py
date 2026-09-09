"""Adapter layer between pydantic API models and the engine's frozen dataclasses.

to_engine_scenario:  pydantic Scenario  →  engine.pipeline.Scenario
compute_delta:       before/after ScoredNetwork  →  Delta for the response
"""

from __future__ import annotations

from api.models import (
    Delta,
    Intervention,
    PerNodeDelta,
    Scenario,
    ScoredNetwork,
)
from engine.pipeline import Intervention as EngineIntervention
from engine.pipeline import Scenario as EngineScenario
from engine.pipeline import StressOverride as EngineStressOverride

# Below this, a fragility change is floating-point noise rather than an effect.
_FRAGILITY_EPSILON = 1e-9


def to_engine_scenario(scenario: Scenario) -> EngineScenario:
    """Convert a pydantic Scenario into the engine's frozen dataclass."""
    return EngineScenario(
        stress_overrides=tuple(
            EngineStressOverride(node_id=o.node_id, own_stress=o.own_stress)
            for o in scenario.stress_overrides
        ),
        interventions=tuple(
            EngineIntervention(node_id=i.node_id, amount_cr=i.amount_cr)
            for i in scenario.interventions
        ),
    )


def compute_delta(
    before: ScoredNetwork,
    after: ScoredNetwork,
    interventions: list[Intervention],
) -> Delta:
    """Compute the delta between two scored networks.

    Only nodes whose risk_band changed appear in per_node.
    total_intervention_cost_cr is the sum of the interventions applied,
    not derived from score differences.
    """
    before_by_id = {s.node_id: s for s in before.scores}
    after_by_id = {s.node_id: s for s in after.scores}

    nodes_improved = 0
    nodes_worsened = 0
    per_node: list[PerNodeDelta] = []

    for node_id in sorted(before_by_id.keys() & after_by_id.keys()):
        b = before_by_id[node_id]
        a = after_by_id[node_id]

        # Counted on FRAGILITY, not on band. Funding relieves stress
        # continuously, but a band is a coarse bucket, so counting band flips
        # undercounts the reach of an intervention badly: on the demo network
        # 8 nodes get materially less fragile and only 2 cross a boundary.
        # "8 suppliers improved" is the honest number and the one that shows
        # the cascade receding. SCHEMA.md §5.5 constrains only `per_node`.
        if a.fragility < b.fragility - _FRAGILITY_EPSILON:
            nodes_improved += 1
        elif a.fragility > b.fragility + _FRAGILITY_EPSILON:
            nodes_worsened += 1

        # per_node stays band-based: it drives the "critical -> stable" chips,
        # and a row saying a node moved from 0.3498 to 0.3497 is noise.
        if b.risk_band != a.risk_band:
            per_node.append(
                PerNodeDelta(
                    node_id=node_id,
                    fragility_before=b.fragility,
                    fragility_after=a.fragility,
                    band_before=b.risk_band,
                    band_after=a.risk_band,
                )
            )

    total_exposure_before = sum(s.estimated_exposure_cr for s in before.scores)
    total_exposure_after = sum(s.estimated_exposure_cr for s in after.scores)

    return Delta(
        nodes_improved=nodes_improved,
        nodes_worsened=nodes_worsened,
        # Rounded here, at serialisation. Summing several hundred 2-decimal
        # floats and subtracting leaves binary noise that would otherwise reach
        # the UI as 148.29999999999998.
        total_exposure_reduced_cr=round(total_exposure_before - total_exposure_after, 2),
        total_intervention_cost_cr=round(sum(i.amount_cr for i in interventions), 2),
        per_node=per_node,
    )
