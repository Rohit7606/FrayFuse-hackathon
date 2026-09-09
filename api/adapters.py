"""Adapter layer between pydantic API models and the engine's frozen dataclasses.

to_engine_scenario:  pydantic Scenario  →  engine.pipeline.Scenario
compute_delta:       before/after ScoredNetwork  →  Delta for the response
"""

from __future__ import annotations

from api.models import (
    Delta,
    Intervention,
    PerNodeDelta,
    RiskBand,
    Scenario,
    ScoredNetwork,
)
from engine.pipeline import Intervention as EngineIntervention
from engine.pipeline import Scenario as EngineScenario
from engine.pipeline import StressOverride as EngineStressOverride

# Band severity, highest first — used to decide improved vs worsened
_BAND_SEVERITY: dict[RiskBand, int] = {
    "critical": 3,
    "high": 2,
    "watch": 1,
    "stable": 0,
}


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

    # Walk all nodes present in both snapshots
    for node_id in sorted(before_by_id.keys() & after_by_id.keys()):
        b = before_by_id[node_id]
        a = after_by_id[node_id]
        if b.risk_band == a.risk_band:
            continue
        sev_before = _BAND_SEVERITY[b.risk_band]
        sev_after = _BAND_SEVERITY[a.risk_band]
        if sev_after < sev_before:
            nodes_improved += 1
        else:
            nodes_worsened += 1
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
        total_exposure_reduced_cr=total_exposure_before - total_exposure_after,
        total_intervention_cost_cr=sum(i.amount_cr for i in interventions),
        per_node=per_node,
    )
