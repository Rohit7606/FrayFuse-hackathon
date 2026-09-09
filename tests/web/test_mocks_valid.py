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
