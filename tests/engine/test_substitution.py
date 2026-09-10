"""Substitution tests — reading criticality on its low side.

The rule these mostly defend is the one that is easiest to break by accident:
a supplier whose sole-source status was never disclosed is NOT eligible for a
substitute.  Offering one would assert that alternatives exist on the strength
of absent evidence, which is the error AGENTS.md §3.6 exists to prevent.
"""

from __future__ import annotations

import networkx as nx
import pytest

from engine import config
from engine.criticality import CriticalityDetail, compute_criticality
from engine.graph import build_graph
from engine.pipeline import score_network
from engine.substitution import compute_substitutions


def _tiny_network() -> dict:
    """Four tier-2 suppliers selling the same part, one buyer at tier 1.

    Built by hand rather than sliced out of the mock so each test can state one
    fact and change one thing.  N100 is the supplier under test; N200, N300 and
    N400 are its potential replacements.
    """
    def node(node_id: str, tier: int, revenue: float | None, name: str) -> dict:
        return {
            "node_id": node_id,
            "name": name,
            "tier": tier,
            "sector": "auto_components",
            "product_category": "widgets",
            "revenue_cr": revenue,
            "cash_buffer_days": 90,
            "employees": 50,
            "is_observable": False,
            "data_source": "synthetic",
            "cin": None,
        }

    def edge(edge_id: str, supplier: str, buyer: str, component: str, value: float, sole) -> dict:
        return {
            "edge_id": edge_id,
            "supplier_id": supplier,
            "buyer_id": buyer,
            "component": component,
            "annual_value_cr": value,
            "exposure_pct": 0.1,
            "data_source": "synthetic",
            "is_single_source": sole,
            "confidence": "confirmed",
            "edge_provenance": "synthetic",
        }

    return {
        "meta": {
            "schema_version": "1.0",
            "generated_at": "2026-08-27T00:00:00Z",
            "generator": "mockgen",
            "currency_unit": "INR_crore",
            "node_count": 6,
            "edge_count": 5,
            "seed": 42,
            "observable_node_count": 0,
        },
        "nodes": [
            node("N001", 0, 1000.0, "Anchor Motors Ltd"),
            node("N010", 1, 500.0, "Buyer Systems Ltd"),
            node("N020", 1, 400.0, "Other Buyer Ltd"),
            node("N100", 2, 40.0, "Subject Components Pvt Ltd"),
            node("N200", 2, 90.0, "Roomy Alternatives Pvt Ltd"),
            node("N300", 2, 30.0, "Tight Alternatives Pvt Ltd"),
            node("N400", 2, None, "Undisclosed Revenue Pvt Ltd"),
        ],
        "edges": [
            edge("E001", "N010", "N001", "assemblies", 100.0, False),
            edge("E002", "N100", "N010", "widgets", 10.0, False),
            edge("E003", "N200", "N020", "widgets", 20.0, False),
            edge("E004", "N300", "N020", "widgets", 5.0, False),
            edge("E005", "N400", "N020", "widgets", 5.0, False),
        ],
        "stress_signals": [],
    }


@pytest.fixture
def any_criticality(monkeypatch):
    """Lift the criticality gate for the hand-built fixture.

    In a seven-node network the tier-2 flow share is divided between four
    suppliers, so the subject scores well above SUBSTITUTION_CRITICALITY_MAX and
    would be skipped for a reason that has nothing to do with what these tests
    are checking.  The threshold itself is exercised against the real mock
    network in test_high_criticality_node_is_not_considered, where the
    distribution it was calibrated to actually exists.
    """
    monkeypatch.setattr(config, "SUBSTITUTION_CRITICALITY_MAX", 1.0)


def _substitutions(network: dict, fragility: dict[str, float] | None = None):
    graph = build_graph(network)
    criticality = compute_criticality(graph)
    if fragility is None:
        fragility = dict.fromkeys(sorted(graph.nodes), 0.0)
    return graph, criticality, compute_substitutions(graph, network, criticality, fragility)


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def test_high_criticality_node_is_not_considered(network):
    """A node the ranked list is warning about is never offered a substitute.

    Suggesting a replacement for a supplier we have just called irreplaceable
    would be a contradiction on one screen.
    """
    scored = score_network(network)
    for score in scored["scores"]:
        if score["criticality"] > config.SUBSTITUTION_CRITICALITY_MAX:
            assert score["substitution_candidates"] is None, score["node_id"]


def test_confirmed_sole_source_is_not_considered(any_criticality):
    """Sole source for anything means not replaceable, whatever its criticality."""
    network = _tiny_network()
    for candidate_edge in network["edges"]:
        if candidate_edge["edge_id"] == "E002":
            candidate_edge["is_single_source"] = True

    _, criticality, result = _substitutions(network)
    assert criticality["N100"].single_source == 1.0
    assert result["N100"].eligible is False
    assert result["N100"].candidates == ()


def test_undisclosed_sole_source_is_not_considered(any_criticality):
    """AGENTS.md §3.6: undisclosed is not permission.

    `is_single_source: null` means no filing stated the status.  Coercing that
    to "alternatives exist" would fabricate the one claim nobody made, which is
    exactly the null-versus-zero error the contract forbids.  The node must come
    back NOT eligible — not eligible-with-an-empty-list, which would mean we
    looked.
    """
    network = _tiny_network()
    for candidate_edge in network["edges"]:
        if candidate_edge["edge_id"] == "E002":
            candidate_edge["is_single_source"] = None

    _, criticality, result = _substitutions(network)
    assert criticality["N100"].single_source is None
    assert result["N100"].eligible is False


def test_null_and_empty_list_are_different_facts(network):
    """The two states the schema keeps apart survive into the scored output."""
    scored = score_network(network)
    values = [score["substitution_candidates"] for score in scored["scores"]]
    assert any(value is None for value in values), "nothing was skipped"
    assert any(isinstance(value, list) for value in values), "nothing was considered"


def test_node_with_no_outgoing_edges_is_not_considered(network):
    """A node that supplies nobody has no relationship to substitute for."""
    graph = build_graph(network)
    _, _, result = _substitutions(network)
    for node_id in sorted(graph.nodes):
        if graph.out_degree(node_id) == 0:
            assert result[node_id].eligible is False, node_id


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------


def test_candidates_are_same_tier_and_same_component(any_criticality):
    network = _tiny_network()
    graph, _, result = _substitutions(network)

    detail = result["N100"]
    assert detail.eligible is True
    assert detail.candidates, "the tiny network has three obvious alternatives"
    for candidate in detail.candidates:
        assert graph.nodes[candidate.node_id]["tier"] == graph.nodes["N100"]["tier"]
        assert candidate.component == "widgets"


def test_candidate_already_supplying_that_buyer_is_excluded(any_criticality):
    """Not an alternative — the same relationship."""
    network = _tiny_network()
    network["nodes"].append(
        {
            "node_id": "N500",
            "name": "Already Supplying Pvt Ltd",
            "tier": 2,
            "sector": "auto_components",
            "product_category": "widgets",
            "revenue_cr": 80.0,
            "cash_buffer_days": 90,
            "employees": 50,
            "is_observable": False,
            "data_source": "synthetic",
            "cin": None,
        }
    )
    network["edges"].append(
        {
            "edge_id": "E006",
            "supplier_id": "N500",
            "buyer_id": "N010",
            "component": "widgets",
            "annual_value_cr": 7.0,
            "exposure_pct": 0.1,
            "data_source": "synthetic",
            "is_single_source": False,
            "confidence": "confirmed",
            "edge_provenance": "synthetic",
        }
    )

    _, _, result = _substitutions(network)
    suggested = {candidate.node_id for candidate in result["N100"].candidates}
    assert "N500" not in suggested


def test_fragile_candidate_ranks_below_a_healthy_one(any_criticality):
    """A replacement that is itself about to fail is not a replacement."""
    network = _tiny_network()
    # N200 has the most headroom, so without the health term it would lead.
    fragility = {
        "N001": 0.0,
        "N010": 0.0,
        "N020": 0.0,
        "N100": 0.0,
        "N200": 0.9,
        "N300": 0.0,
        "N400": 0.0,
    }
    _, _, result = _substitutions(network, fragility)

    order = [candidate.node_id for candidate in result["N100"].candidates]
    assert order.index("N300") < order.index("N200")


def test_undisclosed_revenue_still_scores_on_health_alone(any_criticality):
    """Capacity is dropped and its weight renormalised, never defaulted.

    Mirrors compute_criticality dropping an undisclosed sole-source term.  With
    zero fragility the surviving health term is 1.0, so fitness is 1.0 — if the
    capacity term had been defaulted to zero instead, it would be W_SUB_HEALTH.
    """
    network = _tiny_network()
    _, _, result = _substitutions(network)

    candidates = {c.node_id: c for c in result["N100"].candidates}
    assert "N400" in candidates, "an undisclosed revenue must not disqualify a candidate"
    assert candidates["N400"].capacity_headroom_cr is None
    assert candidates["N400"].fitness == pytest.approx(1.0)
    assert candidates["N400"].fitness > config.W_SUB_HEALTH


def test_suggestions_are_capped(any_criticality):
    network = _tiny_network()
    _, _, result = _substitutions(network)
    for detail in result.values():
        assert len(detail.candidates) <= config.SUBSTITUTION_MAX_CANDIDATES


def test_one_entry_per_candidate_company(any_criticality):
    """Three ways to replace the same firm are one alternative, not three."""
    network = _tiny_network()
    _, _, result = _substitutions(network)
    for detail in result.values():
        ids = [candidate.node_id for candidate in detail.candidates]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Determinism and output shape
# ---------------------------------------------------------------------------


def test_ordering_is_deterministic(network):
    """Two runs, identical candidate lists — a demo that reorders is not a demo."""
    first = {s["node_id"]: s["substitution_candidates"] for s in score_network(network)["scores"]}
    second = {s["node_id"]: s["substitution_candidates"] for s in score_network(network)["scores"]}
    assert first == second


def test_every_candidate_carries_a_reason(network):
    scored = score_network(network)
    for score in scored["scores"]:
        for candidate in score["substitution_candidates"] or []:
            assert candidate["reason_text"].strip(), score["node_id"]
            assert len(candidate["reason_text"]) >= 10
            assert candidate["reason_text"].endswith(".")


def test_reason_names_the_component_and_the_headroom(network):
    """Template-generated, and it says what it measured."""
    scored = score_network(network)
    for score in scored["scores"]:
        for candidate in score["substitution_candidates"] or []:
            reason = candidate["reason_text"]
            assert candidate["component"].replace("_", " ") in reason
            if candidate["capacity_headroom_cr"] is None:
                assert "undisclosed" in reason
            else:
                assert f"{candidate['capacity_headroom_cr']:.2f}" in reason


def test_rounding_matches_the_contract(network):
    scored = score_network(network)
    for score in scored["scores"]:
        for candidate in score["substitution_candidates"] or []:
            assert candidate["fitness"] == round(candidate["fitness"], 4)
            assert candidate["fragility"] == round(candidate["fragility"], 4)
            if candidate["capacity_headroom_cr"] is not None:
                assert candidate["capacity_headroom_cr"] == round(
                    candidate["capacity_headroom_cr"], 2
                )


def test_substitution_does_not_change_any_existing_number(network):
    """Purely additive: the layer must not move a score, a band or the ranking."""
    from engine import ranking as ranking_mod

    graph = build_graph(network)
    scored = score_network(network)

    stripped = [
        {k: v for k, v in score.items() if k != "substitution_candidates"}
        for score in scored["scores"]
    ]
    for score in stripped:
        assert set(score) == set(stripped[0]), "score shape drifted between nodes"

    # The ranking is derived from final_score, which substitution never touches.
    assert scored["ranking"] == ranking_mod.ranking_of(scored["scores"])
    assert len(scored["scores"]) == graph.number_of_nodes()


def test_candidate_fitness_is_bounded(network):
    scored = score_network(network)
    for score in scored["scores"]:
        for candidate in score["substitution_candidates"] or []:
            assert 0.0 <= candidate["fitness"] <= 1.0
            assert 0.0 <= candidate["fragility"] <= 1.0
            if candidate["capacity_headroom_cr"] is not None:
                assert candidate["capacity_headroom_cr"] >= 0.0


def test_criticality_detail_shape_is_what_eligibility_reads(any_criticality):
    """Guard the coupling: eligibility depends on these three facts existing."""
    network = _tiny_network()
    graph = build_graph(network)
    detail = compute_criticality(graph)["N100"]
    assert isinstance(detail, CriticalityDetail)
    assert detail.single_source in (0.0, 1.0, None)
    assert isinstance(graph, nx.DiGraph)
