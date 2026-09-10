"""Validate the committed frontend mocks against schema.json.

PERSON_C.md §7 calls this the test that pays for itself: a mock that does not
validate is not a mock, it is a future integration bug hidden from yourself.
It catches contract drift before Phase 2 rather than during it.

Written in Python so it runs in the same `pytest tests/` pass as everything
else, and needs no JS toolchain to be installed to be useful.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MOCKS = REPO_ROOT / "web" / "src" / "mocks"
SCHEMA = json.loads((REPO_ROOT / "schema.json").read_text(encoding="utf-8"))
DEMO = json.loads(
    (REPO_ROOT / "data" / "fixtures" / "demo_scenario.json").read_text(encoding="utf-8")
)

# Every endpoint the client can call, and the definition its payload must match.
MOCK_DEFINITIONS = {
    "network.json": "NetworkResponse",
    "at-risk.json": "AtRiskResponse",
    "simulate.json": "ScoredNetwork",
    "intervene.json": "InterveneResponse",
}


@pytest.mark.parametrize(("filename", "definition"), sorted(MOCK_DEFINITIONS.items()))
def test_mock_validates(filename, definition):
    path = MOCKS / filename
    assert path.exists(), f"{filename} missing — the frontend cannot run offline without it"

    validator = jsonschema.Draft7Validator(
        {
            "$schema": SCHEMA["$schema"],
            "definitions": SCHEMA["definitions"],
            "$ref": f"#/definitions/{definition}",
        }
    )
    instance = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    assert errors == [], [f"{list(e.path)}: {e.message}" for e in errors[:5]]


def test_mocks_carry_the_demo_scenario():
    """The offline mocks must tell the same story as the live API.

    Person C reads node IDs from the fixture rather than hardcoding them, so a
    mock that ranks different nodes would make the demo behave differently with
    the backend switched off than with it on — and that difference would only
    surface during a rehearsal.
    """
    at_risk = json.loads((MOCKS / "at-risk.json").read_text(encoding="utf-8"))
    assert at_risk["ranking"][: len(DEMO["expected_ranking"])] == DEMO["expected_ranking"]

    bands = {s["node_id"]: s["risk_band"] for s in at_risk["scores"]}
    for node_id, expected in DEMO["expected_bands"].items():
        assert bands[node_id] == expected, node_id


def test_intervene_mock_shows_the_cascade_receding():
    """Step 7's payload: funding one node must improve others and worsen none."""
    payload = json.loads((MOCKS / "intervene.json").read_text(encoding="utf-8"))
    delta = payload["delta"]
    assert delta["nodes_improved"] > 0
    assert delta["nodes_worsened"] == 0
    assert delta["total_exposure_reduced_cr"] > delta["total_intervention_cost_cr"]

    after = {s["node_id"]: s["risk_band"] for s in payload["after"]["scores"]}
    for node_id, expected in DEMO["expected_after_bands"].items():
        assert after[node_id] == expected, node_id


def test_every_node_declares_its_data_source():
    """A judge must never mistake a generated node for a real company."""
    network = json.loads((MOCKS / "network.json").read_text(encoding="utf-8"))
    for node in network["nodes"]:
        assert node["data_source"] in {"real", "synthetic"}


# ---------------------------------------------------------------------------
# Decision-layer mocks (schema 1.4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["derisk.json", "ingest-derisk.json"])
def test_every_committed_plan_validates(filename):
    """One plan per node, so any supplier the graph can select has a real one."""
    path = MOCKS / filename
    assert path.exists(), f"{filename} missing — the plan panel cannot run offline"

    validator = jsonschema.Draft7Validator(
        {
            "$schema": SCHEMA["$schema"],
            "definitions": SCHEMA["definitions"],
            "$ref": "#/definitions/DeriskPlan",
        }
    )
    plans = json.loads(path.read_text(encoding="utf-8"))
    assert plans
    for node_id, plan in plans.items():
        assert plan["node_id"] == node_id
        errors = sorted(validator.iter_errors(plan), key=lambda e: list(e.path))
        assert errors == [], [f"{node_id} {list(e.path)}: {e.message}" for e in errors[:3]]


@pytest.mark.parametrize("filename", ["allocate.json", "ingest-allocate.json"])
def test_every_committed_allocation_validates(filename):
    path = MOCKS / filename
    assert path.exists(), f"{filename} missing — the optimiser cannot run offline"

    validator = jsonschema.Draft7Validator(
        {
            "$schema": SCHEMA["$schema"],
            "definitions": SCHEMA["definitions"],
            "$ref": "#/definitions/AllocateResponse",
        }
    )
    runs = json.loads(path.read_text(encoding="utf-8"))
    assert runs
    for run in runs:
        errors = sorted(validator.iter_errors(run), key=lambda e: list(e.path))
        assert errors == [], [f"{list(e.path)}: {e.message}" for e in errors[:3]]
        assert run["allocated_cr"] <= run["budget_cr"] + 1e-9


def test_committed_budget_stops_match_the_client():
    """A stop the client offers but the mocks do not carry is a dead control.

    web/src/v2/api.ts throws rather than approximating an unlisted budget, so
    the two lists have to be the same list.
    """
    import re

    source = (REPO_ROOT / "web" / "src" / "v2" / "api.ts").read_text(encoding="utf-8")
    declared = re.search(r"BUDGET_LEVELS = \[([^\]]+)\]", source)
    assert declared, "BUDGET_LEVELS not found in web/src/v2/api.ts"
    client_stops = [float(value) for value in declared.group(1).split(",")]

    for filename in ("allocate.json", "ingest-allocate.json"):
        runs = json.loads((MOCKS / filename).read_text(encoding="utf-8"))
        assert [run["budget_cr"] for run in runs] == client_stops, filename


def test_derisk_mock_matches_the_endpoint():
    """The plans are built from the engine, not by calling the endpoint 412 times.

    That is only legitimate while the two produce the same object, so this
    checks it against the live endpoint rather than assuming it.
    """
    from fastapi.testclient import TestClient

    from api.main import app

    plans = json.loads((MOCKS / "derisk.json").read_text(encoding="utf-8"))
    with TestClient(app) as client:
        for node_id in (DEMO["trigger_node"], DEMO["intervention"]["node_id"]):
            response = client.post("/api/derisk", json={"node_id": node_id})
            assert response.status_code == 200
            assert response.json() == plans[node_id], node_id


def test_the_committed_allocation_beats_its_own_budget():
    """The optimiser mock has to make the point it exists to make."""
    runs = json.loads((MOCKS / "allocate.json").read_text(encoding="utf-8"))
    for run in runs:
        if run["allocations"]:
            assert run["objective"]["reduced_cr"] > run["allocated_cr"]
            assert run["delta"]["nodes_worsened"] == 0

    # Diminishing returns must be visible: more money never removes less
    # exposure, and the largest budget cannot spend itself out.
    reduced = [run["objective"]["reduced_cr"] for run in runs]
    assert reduced == sorted(reduced)
