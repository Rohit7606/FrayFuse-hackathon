"""Tests for API hardening — /health, startup loading, and catch-all 500."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api import errors
from api.main import app


# Safe to reuse — API is stateless, no state to reset between tests.
@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_shape(client):
    """GET /health returns status, network path, and nodes count matching meta."""
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert "network" in health
    assert "nodes" in health

    net = client.get("/api/network").json()
    assert health["nodes"] == net["meta"]["node_count"]


def test_startup_loads_network():
    """Network cache is populated by the startup event itself, before any request."""
    import api.main as main_module

    # Force a clean state so a pre-existing cache from other tests can't
    # make this test pass for the wrong reason.
    main_module._network_cache = None

    with TestClient(main_module.app):
        # Entering the `with` block runs FastAPI's startup event.
        # Assert the cache is populated *before* making any HTTP request.
        assert main_module._network_cache is not None
        assert "nodes" in main_module._network_cache
        assert len(main_module._network_cache["nodes"]) > 0


def test_engine_failure_500():
    """An unexpected exception returns a structured 500, not FastAPI's default."""
    # Use raise_server_exceptions=False so TestClient returns the 500
    # response instead of re-raising the exception through the test.
    error_client = TestClient(app, raise_server_exceptions=False)

    def _boom() -> dict:
        raise RuntimeError("something broke unexpectedly")

    with patch("api.main.load_network", side_effect=_boom):
        response = error_client.get("/api/network")

    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "engine_failure"
    assert "something broke unexpectedly" in data["detail"]


# ---------------------------------------------------------------------------
# Bad input must be 4xx, never 5xx — SCHEMA.md §5.6
# ---------------------------------------------------------------------------


def test_negative_intervention_is_422(client):
    """A negative funding amount is a bad request, not an engine failure.

    Unbounded, it passed request validation and only failed against Delta's own
    ge=0 constraint when the *response* was built, which the catch-all handler
    turned into a 500.
    """
    response = client.post(
        "/api/intervene",
        json={
            "baseline_scenario": {"stress_overrides": [], "interventions": []},
            "interventions": [{"node_id": "N042", "amount_cr": -100.0}],
        },
    )
    assert response.status_code == 422
    assert "amount_cr" in response.text


def test_out_of_range_own_stress_is_422(client):
    """own_stress is a 0-1 float. Out of range is an error, not a silent clamp."""
    response = client.post(
        "/api/simulate",
        json={
            "scenario": {
                "stress_overrides": [{"node_id": "N042", "own_stress": 5.0}],
                "interventions": [],
            }
        },
    )
    assert response.status_code == 422
    assert "own_stress" in response.text


@pytest.mark.parametrize("limit", [-5, 0])
def test_non_positive_limit_is_422(client, limit):
    """`limit` indexes a slice, so a negative value silently returned a wrong list.

    `ranking[:-5]` is the ranked list minus its last five entries, served with a
    200. Bounded below at 1, it is now a readable 422.
    """
    assert client.get(f"/api/at-risk?limit={limit}").status_code == 422


def test_valid_limit_still_works(client):
    """The guard must not break the ordinary case."""
    response = client.get("/api/at-risk?limit=4")
    assert response.status_code == 200
    assert len(response.json()["ranking"]) <= 4


# ---------------------------------------------------------------------------
# Error bodies must match schema.json ErrorResponse — SCHEMA.md §5.6
# ---------------------------------------------------------------------------


def _error_validator():
    import json
    from pathlib import Path

    import jsonschema

    schema = json.loads(
        (Path(__file__).resolve().parents[2] / "schema.json").read_text(encoding="utf-8")
    )
    return jsonschema.Draft7Validator(
        {
            "$schema": schema["$schema"],
            "definitions": schema["definitions"],
            "$ref": "#/definitions/ErrorResponse",
        }
    )


def test_unknown_node_body_matches_schema(client):
    """The 400 body validates, and its code is in the closed enum."""
    response = client.post(
        "/api/simulate",
        json={
            "scenario": {
                "stress_overrides": [{"node_id": "N999", "own_stress": 0.5}],
                "interventions": [],
            }
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert list(_error_validator().iter_errors(body)) == []
    assert body["error"] == errors.UNKNOWN_NODE
    assert body["node_id"] == "N999"


def test_engine_failure_body_matches_schema():
    """The 500 body validates too — the one legitimate 500."""
    error_client = TestClient(app, raise_server_exceptions=False)

    def _boom() -> dict:
        raise RuntimeError("something broke unexpectedly")

    with patch("api.main.load_network", side_effect=_boom):
        response = error_client.get("/api/network")

    assert response.status_code == 500
    body = response.json()
    assert list(_error_validator().iter_errors(body)) == []
    assert body["error"] == errors.ENGINE_FAILURE
