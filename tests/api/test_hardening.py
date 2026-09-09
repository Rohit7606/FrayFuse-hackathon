"""Tests for API hardening — /health, startup loading, and catch-all 500."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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
