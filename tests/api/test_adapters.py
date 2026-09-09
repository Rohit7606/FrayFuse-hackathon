"""Unit tests for api.adapters — no server needed, just function calls."""

from __future__ import annotations

from api.adapters import compute_delta, to_engine_scenario
from api.models import (
    BandCounts,
    Delta,
    Intervention,
    Meta,
    PerNodeDelta,
    ReasonFactor,
    Scenario,
    Score,
    ScoredNetwork,
    StressOverride,
    Summary,
)
from engine.pipeline import Intervention as EngineIntervention
from engine.pipeline import Scenario as EngineScenario
from engine.pipeline import StressOverride as EngineStressOverride


# ---------------------------------------------------------------------------
# Shared helpers — build minimal valid objects for testing
# ---------------------------------------------------------------------------

_META = Meta(
    schema_version="1.0",
    generated_at="2026-08-27T00:00:00Z",
    generator="mockgen",
    currency_unit="INR_crore",
    node_count=4,
    edge_count=0,
    seed=42,
)

_SUMMARY = Summary(
    total_nodes=4,
    at_risk_count=2,
    band_counts=BandCounts(critical=1, high=1, watch=0, stable=2),
    total_intervention_cost_cr=4.8,
    total_estimated_exposure_cr=160.0,
    iterations_to_converge=3,
)


def _make_score(
    node_id: str,
    risk_band: str,
    fragility: float,
    estimated_exposure_cr: float = 10.0,
) -> Score:
    """Build a minimal Score with reasonable defaults for the fields we don't test."""
    return Score(
        node_id=node_id,
        own_stress=0.0,
        inherited_stress=fragility,
        fragility=fragility,
        criticality=0.5,
        final_score=fragility * 0.5,
        risk_band=risk_band,
        reason_text=f"Test score for {node_id}",
        reason_factors=[],
        intervention_cost_cr=4.8,
        estimated_exposure_cr=estimated_exposure_cr,
        propagation_depth=1,
    )


def _make_scored_network(scores: list[Score]) -> ScoredNetwork:
    """Wrap a list of scores into a minimal ScoredNetwork."""
    return ScoredNetwork(
        meta=_META,
        nodes=[],
        edges=[],
        scores=scores,
        ranking=[s.node_id for s in scores if s.risk_band != "stable"],
        summary=_SUMMARY,
    )


# ---------------------------------------------------------------------------
# to_engine_scenario tests
# ---------------------------------------------------------------------------


def test_empty_scenario_roundtrips():
    """An empty pydantic Scenario converts to an empty engine Scenario."""
    pydantic_scenario = Scenario()
    engine_scenario = to_engine_scenario(pydantic_scenario)

    assert engine_scenario == EngineScenario()
    assert engine_scenario.stress_overrides == ()
    assert engine_scenario.interventions == ()


def test_scenario_with_overrides_and_interventions():
    """A scenario with both stress_overrides and interventions converts correctly."""
    pydantic_scenario = Scenario(
        stress_overrides=[
            StressOverride(node_id="N007", own_stress=0.85),
            StressOverride(node_id="N001", own_stress=0.50),
        ],
        interventions=[
            Intervention(node_id="N042", amount_cr=4.80),
        ],
    )
    engine_scenario = to_engine_scenario(pydantic_scenario)

    assert engine_scenario == EngineScenario(
        stress_overrides=(
            EngineStressOverride(node_id="N007", own_stress=0.85),
            EngineStressOverride(node_id="N001", own_stress=0.50),
        ),
        interventions=(
            EngineIntervention(node_id="N042", amount_cr=4.80),
        ),
    )
    # Engine types are tuples, not lists
    assert isinstance(engine_scenario.stress_overrides, tuple)
    assert isinstance(engine_scenario.interventions, tuple)


# ---------------------------------------------------------------------------
# compute_delta tests
# ---------------------------------------------------------------------------


def test_compute_delta_excludes_unchanged_nodes():
    """Nodes whose risk_band didn't change must not appear in per_node."""
    before = _make_scored_network([
        _make_score("N042", "critical", 0.63),
        _make_score("N087", "high", 0.40),
    ])
    # N042 improves, N087 stays the same
    after = _make_scored_network([
        _make_score("N042", "stable", 0.10),
        _make_score("N087", "high", 0.40),
    ])

    delta = compute_delta(before, after, interventions=[])

    per_node_ids = [p.node_id for p in delta.per_node]
    assert "N042" in per_node_ids
    assert "N087" not in per_node_ids


def test_compute_delta_demo_case():
    """The demo's N042 critical→stable and N118 high→watch case."""
    before = _make_scored_network([
        _make_score("N042", "critical", 0.63, estimated_exposure_cr=148.3),
        _make_score("N203", "high", 0.44, estimated_exposure_cr=20.0),
        _make_score("N087", "high", 0.40, estimated_exposure_cr=10.0),
        _make_score("N118", "high", 0.30, estimated_exposure_cr=11.3),
    ])
    after = _make_scored_network([
        _make_score("N042", "stable", 0.10, estimated_exposure_cr=0.0),
        _make_score("N203", "high", 0.44, estimated_exposure_cr=20.0),
        _make_score("N087", "high", 0.40, estimated_exposure_cr=10.0),
        _make_score("N118", "watch", 0.10, estimated_exposure_cr=11.3),
    ])

    interventions = [Intervention(node_id="N042", amount_cr=4.80)]
    delta = compute_delta(before, after, interventions=interventions)

    # N042: critical→stable (improved), N118: high→watch (improved)
    assert delta.nodes_improved == 2
    assert delta.nodes_worsened == 0

    # Intervention cost comes from the interventions list, not scores
    assert delta.total_intervention_cost_cr == 4.80

    # Exposure reduced: before sum 189.6 - after sum 41.3 = 148.3
    assert round(delta.total_exposure_reduced_cr, 2) == 148.3

    # per_node has exactly the two changed nodes, sorted by node_id
    assert len(delta.per_node) == 2
    changed_ids = {p.node_id for p in delta.per_node}
    assert changed_ids == {"N042", "N118"}

    n042 = next(p for p in delta.per_node if p.node_id == "N042")
    assert n042.band_before == "critical"
    assert n042.band_after == "stable"

    n118 = next(p for p in delta.per_node if p.node_id == "N118")
    assert n118.band_before == "high"
    assert n118.band_after == "watch"
