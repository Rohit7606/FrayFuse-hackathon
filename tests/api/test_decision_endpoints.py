"""Endpoint tests for /api/derisk and /api/allocate.

Two rules from SCHEMA.md §5.8 do most of the work here: never a 500 for a bad
request, and never a 200 with an error inside.  The rest asserts that both
endpoints stay stateless — the same body must always come back with the same
answer, and neither may leave anything behind that changes the next call.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from api.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO_ROOT / "schema.json").read_text(encoding="utf-8"))
DEMO = json.loads(
    (REPO_ROOT / "data" / "fixtures" / "demo_scenario.json").read_text(encoding="utf-8")
)

# Keeps the suite quick: each extra candidate is a full scoring run.
POOL = 4


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def assert_valid(instance: object, definition: str) -> None:
    validator = jsonschema.Draft7Validator(
        {
            "$schema": SCHEMA["$schema"],
            "definitions": SCHEMA["definitions"],
            "$ref": f"#/definitions/{definition}",
        }
    )
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    assert errors == [], [f"{list(e.path)}: {e.message}" for e in errors[:5]]


# ---------------------------------------------------------------------------
# /api/derisk
# ---------------------------------------------------------------------------


def test_derisk_matches_schema(client):
    response = client.post("/api/derisk", json={"node_id": DEMO["intervention"]["node_id"]})
    assert response.status_code == 200
    assert_valid(response.json(), "DeriskPlan")


def test_derisk_puts_the_headline_finding_in_the_funding_queue(client):
    plan = client.post(
        "/api/derisk", json={"node_id": DEMO["intervention"]["node_id"]}
    ).json()
    assert plan["queue"] == "fund_now"
    assert plan["recommended_action"]["kind"] == "fund"
    assert plan["recommended_action"]["amount_cr"] == plan["stabilisation_cost_cr"]


def test_derisk_refuses_to_rescue_the_origin(client):
    plan = client.post("/api/derisk", json={"node_id": DEMO["trigger_node"]}).json()
    assert plan["queue"] == "origin"
    assert plan["recommended_action"]["amount_cr"] is None


def test_derisk_unknown_node_is_400_naming_the_id(client):
    response = client.post("/api/derisk", json={"node_id": "N999"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "unknown_node"
    assert body["node_id"] == "N999"


def test_derisk_malformed_node_id_is_422_not_500(client):
    assert client.post("/api/derisk", json={"node_id": "banana"}).status_code == 422
    assert client.post("/api/derisk", json={}).status_code == 422


def test_derisk_honours_the_scenario(client):
    """A plan built under a what-if describes the network the caller can see."""
    node_id = DEMO["intervention"]["node_id"]
    calm = {
        "stress_overrides": [{"node_id": DEMO["trigger_node"], "own_stress": 0.0}],
        "interventions": [],
    }
    baseline = client.post("/api/derisk", json={"node_id": node_id}).json()
    relieved = client.post(
        "/api/derisk", json={"node_id": node_id, "scenario": calm}
    ).json()

    assert relieved["fragility"] < baseline["fragility"]
    assert relieved["queue"] != "fund_now"


def test_derisk_is_stateless(client):
    node_id = DEMO["intervention"]["node_id"]
    first = client.post("/api/derisk", json={"node_id": node_id}).json()
    client.post(
        "/api/derisk",
        json={
            "node_id": node_id,
            "scenario": {
                "stress_overrides": [{"node_id": DEMO["trigger_node"], "own_stress": 0.0}],
                "interventions": [],
            },
        },
    )
    assert client.post("/api/derisk", json={"node_id": node_id}).json() == first


# ---------------------------------------------------------------------------
# /api/allocate
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def allocation(client):
    response = client.post(
        "/api/allocate", json={"budget_cr": 5.0, "max_candidates": POOL}
    )
    assert response.status_code == 200
    return response.json()


def test_allocate_matches_schema(allocation):
    assert_valid(allocation, "AllocateResponse")


def test_allocate_never_overspends(allocation):
    assert allocation["allocated_cr"] <= allocation["budget_cr"]
    assert allocation["allocated_cr"] + allocation["unallocated_cr"] == pytest.approx(
        allocation["budget_cr"]
    )
    assert allocation["delta"]["total_intervention_cost_cr"] == pytest.approx(
        allocation["allocated_cr"]
    )


def test_allocate_protects_the_anchors(allocation):
    assert allocation["objective"]["metric"] == "anchor_inflow_at_risk_cr"
    assert allocation["objective"]["after_cr"] < allocation["objective"]["before_cr"]
    assert allocation["delta"]["nodes_improved"] > 0
    assert allocation["delta"]["nodes_worsened"] == 0


def test_allocate_summaries_bracket_the_same_run(allocation):
    """summary_before and summary_after must describe one comparison.

    They replace the before/after ScoredNetwork pair, so if they ever came from
    different runs the whole response would be quietly incomparable.
    """
    before = allocation["summary_before"]
    after = allocation["summary_after"]
    assert before["total_nodes"] == after["total_nodes"]
    assert after["at_risk_count"] <= before["at_risk_count"]


def test_allocate_zero_budget_is_a_200_that_spends_nothing(client):
    response = client.post("/api/allocate", json={"budget_cr": 0.0, "max_candidates": POOL})
    assert response.status_code == 200
    body = response.json()
    assert body["allocations"] == []
    assert body["objective"]["reduced_cr"] == 0.0
    assert_valid(body, "AllocateResponse")


def test_allocate_rejects_a_negative_budget_with_422(client):
    assert client.post("/api/allocate", json={"budget_cr": -1.0}).status_code == 422


def test_allocate_bounds_the_probe_count(client):
    """max_candidates is the cost of the request, so it cannot be unbounded."""
    assert client.post(
        "/api/allocate", json={"budget_cr": 1.0, "max_candidates": 500}
    ).status_code == 422
    assert client.post(
        "/api/allocate", json={"budget_cr": 1.0, "max_candidates": 0}
    ).status_code == 422


def test_allocate_reports_what_it_cost_to_compute(allocation):
    assert allocation["scoring_runs"] >= 1
    assert len(allocation["candidates_considered"]) <= POOL


def test_allocate_unknown_node_in_the_baseline_scenario_is_400(client):
    response = client.post(
        "/api/allocate",
        json={
            "budget_cr": 1.0,
            "baseline_scenario": {
                "stress_overrides": [{"node_id": "N999", "own_stress": 0.5}],
                "interventions": [],
            },
        },
    )
    assert response.status_code == 400
    assert response.json()["node_id"] == "N999"


def test_allocate_is_deterministic(client):
    body = {"budget_cr": 5.0, "max_candidates": POOL}
    first = client.post("/api/allocate", json=body).json()
    second = client.post("/api/allocate", json=body).json()
    assert first == second
