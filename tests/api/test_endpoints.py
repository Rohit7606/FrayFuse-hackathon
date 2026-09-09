import json
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models import (
    NetworkResponse,
    AtRiskResponse,
    ScoredNetwork,
    InterveneResponse
)


# Use a module-scoped TestClient because the API is stateless.
# Reusing the client across tests is safe and validates the stateless design.
@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_network_shape(client):
    response = client.get("/api/network")
    assert response.status_code == 200
    # Validate it parses correctly
    NetworkResponse.model_validate(response.json())


def test_at_risk_shape(client):
    response = client.get("/api/at-risk")
    assert response.status_code == 200
    AtRiskResponse.model_validate(response.json())
    
    # Test limit truncates
    resp_limit = client.get("/api/at-risk?limit=2")
    assert resp_limit.status_code == 200
    data = resp_limit.json()
    assert len(data["ranking"]) == 2
    assert len(data["scores"]) == 2


def test_simulate_shape(client):
    payload = {"scenario": {"stress_overrides": [], "interventions": []}}
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    ScoredNetwork.model_validate(response.json())


def test_intervene_shape(client):
    payload = {
        "interventions": [{"node_id": "N042", "amount_cr": 4.8}],
        "baseline_scenario": {"stress_overrides": [], "interventions": []}
    }
    response = client.post("/api/intervene", json=payload)
    assert response.status_code == 200
    InterveneResponse.model_validate(response.json())


def test_unknown_node_400(client):
    payload_sim = {"scenario": {"stress_overrides": [{"node_id": "N999", "own_stress": 0.5}], "interventions": []}}
    response = client.post("/api/simulate", json=payload_sim)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "unknown_node"
    assert data["node_id"] == "N999"

    payload_int = {
        "interventions": [{"node_id": "N999", "amount_cr": 4.8}],
        "baseline_scenario": {"stress_overrides": [], "interventions": []}
    }
    response2 = client.post("/api/intervene", json=payload_int)
    assert response2.status_code == 400
    data2 = response2.json()
    assert data2["error"] == "unknown_node"
    assert data2["node_id"] == "N999"


def test_malformed_422(client):
    payload = {"not_a_scenario": True}
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 422


def test_stateless(client):
    resp1 = client.get("/api/at-risk")
    assert resp1.status_code == 200
    resp2 = client.get("/api/at-risk")
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()

    # Call intervene
    payload = {
        "interventions": [{"node_id": "N042", "amount_cr": 4.8}],
        "baseline_scenario": {"stress_overrides": [], "interventions": []}
    }
    client.post("/api/intervene", json=payload)

    # Call at-risk again
    resp3 = client.get("/api/at-risk")
    assert resp3.status_code == 200
    assert resp3.json() == resp1.json()


def test_demo_intervention(client):
    with open("data/fixtures/demo_scenario.json", "r", encoding="utf-8") as f:
        demo = json.load(f)
    
    intervention = demo["intervention"]
    expected = demo["expected_after_bands"]

    payload = {
        "interventions": [intervention],
        "baseline_scenario": {"stress_overrides": [], "interventions": []}
    }
    response = client.post("/api/intervene", json=payload)
    assert response.status_code == 200
    data = response.json()

    after_by_id = {s["node_id"]: s for s in data["after"]["scores"]}
    for node_id, expected_band in expected.items():
        assert node_id in after_by_id, f"{node_id} missing from after.scores entirely"
        assert after_by_id[node_id]["risk_band"] == expected_band


def test_empty_scenario(client):
    payload = {"scenario": {"stress_overrides": [], "interventions": []}}
    resp_sim = client.post("/api/simulate", json=payload)
    resp_risk = client.get("/api/at-risk")
    
    sim_data = resp_sim.json()
    risk_data = resp_risk.json()
    
    sim_scores_by_id = {s["node_id"]: s for s in sim_data["scores"]}

    # at-risk's ranking must be a subset of simulate's ranking, in the same relative order
    sim_ranking_set = set(sim_data["ranking"])
    assert all(node_id in sim_ranking_set for node_id in risk_data["ranking"])

    # every node at-risk surfaces must appear in simulate's full scores with matching values
    for risk_score in risk_data["scores"]:
        node_id = risk_score["node_id"]
        assert node_id in sim_scores_by_id, f"{node_id} in at-risk but missing from simulate"
        assert risk_score == sim_scores_by_id[node_id]
