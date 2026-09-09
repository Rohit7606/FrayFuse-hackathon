"""Shared fixtures for the engine tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MOCK_NETWORK = REPO_ROOT / "data" / "mock" / "network.json"
DEMO_FIXTURE = REPO_ROOT / "data" / "fixtures" / "demo_scenario.json"
SCHEMA_PATH = REPO_ROOT / "schema.json"


@pytest.fixture(scope="session")
def schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def demo() -> dict[str, Any]:
    return json.loads(DEMO_FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def network() -> dict[str, Any]:
    """A fresh copy of the mock network for every test.

    Deliberately function-scoped: test_no_input_mutation would be meaningless if
    tests shared one dict, and a mutation bug would leak between tests.
    """
    return json.loads(MOCK_NETWORK.read_text(encoding="utf-8"))


def validator_for(schema: dict[str, Any], definition: str):
    """A jsonschema validator bound to one definition in schema.json."""
    import jsonschema

    return jsonschema.Draft7Validator(
        {
            "$schema": schema["$schema"],
            "definitions": schema["definitions"],
            "$ref": f"#/definitions/{definition}",
        }
    )
