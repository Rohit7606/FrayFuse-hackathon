"""Ingestion endpoint tests.

Two things these are really defending:

  1. **No 500 on user input.** Everything a person can do to a zip file — hand
     over the wrong one, a corrupt one, a hostile one, an enormous one — comes
     back as a 422 naming the file. A 500 here is a bug, not a bad upload
     (SCHEMA.md §5.6).
  2. **The default network is untouched.** The demo has to run end to end with
     nobody uploading anything, so ingestion must never mutate what the server
     loaded at startup.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DIR = REPO_ROOT / "data" / "real"
SCHEMA = json.loads((REPO_ROOT / "schema.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(members.items()):
            archive.writestr(name, payload)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def real_zip() -> bytes:
    """The whole data/real directory, which is the archive the demo uploads.

    Deliberately includes the markdown, the committed network.json and
    backtest_panel.csv — a realistic upload is a folder, not a curated set of
    exactly five files, and none of that extra content may derail it.
    """
    return _zip_bytes(
        {
            f"data/real/{path.name}": path.read_bytes()
            for path in sorted(REAL_DIR.iterdir())
            if path.is_file()
        }
    )


def _post(client: TestClient, payload: bytes, name: str = "upload.zip"):
    return client.post("/api/ingest", files={"file": (name, payload, "application/zip")})


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_valid_csv_zip_succeeds(client, real_zip):
    response = _post(client, real_zip)
    assert response.status_code == 200, response.text

    body = response.json()
    assert len(body["nodes"]) == len(body["scores"])
    assert body["summary"]["total_nodes"] == len(body["nodes"])
    assert body["stress_signals"], "the evidence panel needs the filed rows back"


def test_response_validates_against_the_schema(client, real_zip):
    """The ingested payload is a ScoredNetwork like any other."""
    body = _post(client, real_zip).json()
    validator = jsonschema.Draft7Validator(
        {
            "$schema": SCHEMA["$schema"],
            "definitions": SCHEMA["definitions"],
            "$ref": "#/definitions/ScoredNetwork",
        }
    )
    scored = {key: body[key] for key in ("meta", "nodes", "edges", "scores", "ranking", "summary")}
    errors = sorted(validator.iter_errors(scored), key=lambda e: list(e.path))
    assert errors == [], [f"{list(e.path)}: {e.message}" for e in errors[:5]]


def test_report_counts_what_the_filings_did_not_say(client, real_zip):
    """The null count is the product's thesis as a number, not a diagnostic."""
    report = _post(client, real_zip).json()["ingest_report"]

    assert report["companies_read"] > 0
    assert report["nodes_built"] > report["companies_read"], "a deep tier was generated"
    assert report["generated_nodes"] > 0
    assert report["fields_null"] > 0, "real filings leave fields blank; that is the point"
    assert report["observable_nodes"] < report["nodes_built"]

    # The extra members rode along and were ignored rather than refused.
    ignored = " ".join(report["files_ignored"])
    assert "DATA_DICTIONARY.md" in ignored
    assert set(report["files_used"]) >= {"companies.csv", "financials.csv", "edges.csv"}


def test_same_zip_twice_gives_identical_results(client, real_zip):
    """Byte-identical, because a judge will upload it again on stage."""
    first = _post(client, real_zip).json()
    second = _post(client, real_zip).json()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_renamed_files_are_matched_by_header(client, real_zip):
    """A judge's slightly-renamed file still lands correctly."""
    renamed = {
        "co.csv": (REAL_DIR / "companies.csv").read_bytes(),
        "fin_2024.csv": (REAL_DIR / "financials.csv").read_bytes(),
        "relationships.csv": (REAL_DIR / "edges.csv").read_bytes(),
        "pool.csv": (REAL_DIR / "entity_pool.csv").read_bytes(),
    }
    response = _post(client, _zip_bytes(renamed))
    assert response.status_code == 200, response.text
    assert set(response.json()["ingest_report"]["files_used"]) >= {
        "companies.csv",
        "financials.csv",
        "edges.csv",
    }


# ---------------------------------------------------------------------------
# Everything a user can get wrong
# ---------------------------------------------------------------------------


def test_zip_slip_is_rejected(client):
    """A member resolving outside the extraction directory is refused.

    The classic archive attack: a relative path that climbs out and overwrites
    something. It must never be written, and the refusal must be a 422.
    """
    hostile = _zip_bytes(
        {
            "../../escaped.csv": b"company_id,name,tier_role\nC1,Escaped Ltd,tier1\n",
            "companies.csv": (REAL_DIR / "companies.csv").read_bytes(),
        }
    )
    response = _post(client, hostile)
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_upload"
    assert "outside" in response.json()["detail"]
    assert not (REPO_ROOT / "escaped.csv").exists()


def test_too_many_members_is_rejected(client):
    payload = _zip_bytes(
        {f"file_{index:04d}.txt": b"x" for index in range(config.INGEST_MAX_MEMBERS + 5)}
    )
    response = _post(client, payload)
    assert response.status_code == 422
    assert "members" in response.json()["detail"]


def test_zip_bomb_is_rejected_on_declared_size(client):
    """Refused before a byte is written, on the declared uncompressed size."""
    oversized = config.INGEST_MAX_UNCOMPRESSED_BYTES + 1
    payload = _zip_bytes({"huge.csv": b"\0" * oversized})
    response = _post(client, payload)
    assert response.status_code == 422
    assert "expands to" in response.json()["detail"]


def test_unrecognisable_archive_names_what_it_wanted(client):
    """No recognisable CSVs — a 422 that tells the user what was expected."""
    payload = _zip_bytes({"notes.txt": b"hello", "photo.png": b"\x89PNG"})
    response = _post(client, payload)
    assert response.status_code == 422

    detail = response.json()["detail"]
    assert "companies.csv" in detail
    assert "DATA_DICTIONARY" in detail


def test_corrupt_archive_is_not_a_500(client):
    response = _post(client, b"this is definitely not a zip file")
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_upload"


def test_empty_upload_is_rejected(client):
    response = _post(client, b"")
    assert response.status_code == 422


def test_partial_collection_names_the_missing_file(client):
    """companies.csv alone cannot build a network, and the message says which."""
    payload = _zip_bytes({"companies.csv": (REAL_DIR / "companies.csv").read_bytes()})
    response = _post(client, payload)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "financials.csv" in detail and "edges.csv" in detail


# ---------------------------------------------------------------------------
# Statelessness
# ---------------------------------------------------------------------------


def test_ingestion_does_not_replace_the_default_network(client, real_zip):
    """The demo must still run with no upload at all (AGENTS.md §1.5)."""
    before = client.get("/health").json()
    _post(client, real_zip)
    after = client.get("/health").json()

    assert before == after
    assert client.get("/api/at-risk?limit=3").status_code == 200


def test_scenarios_run_against_a_client_supplied_network(client, real_zip):
    """The client holds the ingested network and sends it back (§3.4).

    No session id, no server-side handle: the request carries everything it
    needs, so two clients can hold two different networks at once.
    """
    body = _post(client, real_zip).json()
    network = {key: body[key] for key in ("meta", "nodes", "edges", "stress_signals")}

    response = client.post(
        "/api/simulate",
        json={"scenario": {"stress_overrides": [], "interventions": []}, "network": network},
    )
    assert response.status_code == 200
    assert len(response.json()["scores"]) == len(body["nodes"])

    # Same request without the network scores the default, which is a
    # different size — proof the override is what did the work.
    default = client.post(
        "/api/simulate",
        json={"scenario": {"stress_overrides": [], "interventions": []}},
    )
    assert len(default.json()["scores"]) != len(body["nodes"])


def test_intervene_accepts_a_client_supplied_network(client, real_zip):
    body = _post(client, real_zip).json()
    network = {key: body[key] for key in ("meta", "nodes", "edges", "stress_signals")}
    ranked = body["ranking"][0]

    response = client.post(
        "/api/intervene",
        json={
            "baseline_scenario": {"stress_overrides": [], "interventions": []},
            "interventions": [{"node_id": ranked, "amount_cr": 1.0}],
            "network": network,
        },
    )
    assert response.status_code == 200
    assert response.json()["delta"]["total_intervention_cost_cr"] == 1.0
