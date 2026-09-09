"""Validate live endpoint responses against schema.json itself.

SCHEMA.md §6 requires this and it is not the same check as the pydantic
response_model. The models are a *second* transcription of the contract, so
they can drift from it silently — and did: they pinned schema_version to "1.0",
typed is_single_source as a bare bool and omitted the required `confidence`
field, so with extra="forbid" every endpoint serving the committed mock network
returned a 500. Pydantic validated the responses happily against its own stale
idea of the contract.

These tests check the responses against the file all three tracks share, so the
models cannot drift away from it again without a failure.
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


def test_network_matches_schema(client):
    assert_valid(client.get("/api/network").json(), "NetworkResponse")


def test_at_risk_matches_schema(client):
    assert_valid(client.get("/api/at-risk?limit=10").json(), "AtRiskResponse")


def test_simulate_matches_schema(client):
    response = client.post(
        "/api/simulate",
        json={"scenario": {"stress_overrides": [{"node_id": "N007", "own_stress": 0.9}],
                           "interventions": []}},
    )
    assert_valid(response.json(), "ScoredNetwork")


def test_intervene_matches_schema(client):
    response = client.post(
        "/api/intervene",
        json={
            "baseline_scenario": {"stress_overrides": [], "interventions": []},
            "interventions": [DEMO["intervention"]],
        },
    )
    assert_valid(response.json(), "InterveneResponse")


def test_unknown_node_error_matches_schema(client):
    response = client.post(
        "/api/simulate",
        json={"scenario": {"stress_overrides": [{"node_id": "N999", "own_stress": 0.5}],
                           "interventions": []}},
    )
    assert response.status_code == 400
    assert_valid(response.json(), "ErrorResponse")
    assert response.json()["node_id"] == "N999"


def test_at_risk_returns_only_ranked_scores(client):
    """PERSON_B.md §3.2: C needs four score objects, not four hundred."""
    payload = client.get("/api/at-risk?limit=4").json()
    assert len(payload["scores"]) == len(payload["ranking"]) <= 4
    assert {s["node_id"] for s in payload["scores"]} == set(payload["ranking"])


def test_at_risk_reproduces_the_demo_fixture(client):
    """The default view is the demo's step 5."""
    payload = client.get("/api/at-risk?limit=4").json()
    assert payload["ranking"] == DEMO["expected_ranking"]
    bands = {s["node_id"]: s["risk_band"] for s in payload["scores"]}
    assert bands == DEMO["expected_bands"]
