"""FastAPI application — four endpoints, stateless, no session state.

Endpoints:
    GET  /api/network     — raw network for initial render
    GET  /api/at-risk     — baseline scoring, ranked list
    POST /api/simulate    — score under a scenario
    POST /api/intervene   — before/after/delta for funding decisions
    POST /api/ingest      — build and score a network from an uploaded zip
    GET  /health          — liveness check
"""

from __future__ import annotations

import json
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import errors, scoring
from api.adapters import compute_delta
from api.config import CORS_ORIGINS, NETWORK_PATH
from api.models import (
    AtRiskResponse,
    IngestResponse,
    InterveneRequest,
    InterveneResponse,
    NetworkResponse,
    Scenario,
    ScoredNetwork,
    SimulateRequest,
)
from engine import config as engine_config
from engine.ingest import IngestError, ingest_zip
from engine.pipeline import UnknownNodeError

logger = logging.getLogger("frayfuse")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load the network eagerly, so a missing file fails at boot, not on stage.

    Uses the lifespan protocol rather than the deprecated on_event hook.
    """
    try:
        net = load_network()
        logger.info("Loaded network from %s (%d nodes)", NETWORK_PATH, len(net["nodes"]))
    except FileNotFoundError:
        raise SystemExit(f"FATAL: network file not found: {NETWORK_PATH}") from None
    except (json.JSONDecodeError, KeyError) as exc:
        raise SystemExit(f"FATAL: malformed network file {NETWORK_PATH}: {exc}") from exc
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FrayFuse",
    description="Supply-chain financial stress detection and intervention API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Network loading — cached at startup, not session state
# ---------------------------------------------------------------------------

_network_cache: dict | None = None


def load_network() -> dict:
    """Load and cache the network file. Called once at startup."""
    global _network_cache
    if _network_cache is None:
        with open(NETWORK_PATH, "r", encoding="utf-8") as f:
            _network_cache = json.load(f)
    return _network_cache




# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.exception_handler(UnknownNodeError)
async def unknown_node_handler(request: Request, exc: UnknownNodeError) -> JSONResponse:
    """Map engine UnknownNodeError to a 400 with the offending node_id named."""
    return errors.unknown_node(exc.node_id)


@app.exception_handler(Exception)
async def catch_all_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions — structured 500, not a default error page."""
    # Let pydantic's RequestValidationError pass through as 422
    if isinstance(exc, RequestValidationError):
        raise exc
    logger.exception("Unhandled exception: %s", exc)
    return errors.engine_failure(str(exc))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness check — is the backend up and which dataset did it load?"""
    net = load_network()
    return {"status": "ok", "network": NETWORK_PATH, "nodes": len(net["nodes"])}


@app.get("/api/network", response_model=NetworkResponse)
def get_network():
    """Raw network for initial render. No scoring.

    Carries `stress_signals` through verbatim so the UI can show the published
    ageing and MSMED lines behind a stress score instead of restating them.
    A network file without signals serves an empty list rather than failing.
    """
    net = load_network()
    return {
        "meta": net["meta"],
        "nodes": net["nodes"],
        "edges": net["edges"],
        "stress_signals": net.get("stress_signals", []),
    }


@app.get("/api/at-risk", response_model=AtRiskResponse)
def get_at_risk(limit: int = Query(default=10, ge=1, le=1000)):
    """Baseline scoring, ranked list only. The default view.

    Returns `scores` for the ranked nodes only, not all 412 — the UI renders a
    list of four and does not need four hundred score objects to do it.

    `limit` is bounded below at 1 because it indexes a slice: a negative limit
    read as `ranking[:-5]` silently returned the list minus its last five
    entries with a 200, which is a wrong answer rather than an error.
    """
    result = scoring.baseline(load_network())
    ranking = result["ranking"][:limit]
    wanted = set(ranking)
    scores = [s for s in result["scores"] if s["node_id"] in wanted]

    return AtRiskResponse(
        meta=result["meta"],
        ranking=ranking,
        scores=scores,
        summary=result["summary"],
    )


@app.post("/api/simulate", response_model=ScoredNetwork)
def simulate(req: SimulateRequest):
    """Score the network under a scenario. Drives the what-if controls.

    Scores `req.network` when the client sent one — the network it ingested —
    and the server's default otherwise. The server keeps nothing either way, so
    this stays a pure function of the request body (AGENTS.md §3.4).
    """
    network = req.network.model_dump(mode="json") if req.network else load_network()
    return ScoredNetwork.model_validate(scoring.simulate(network, req.scenario))


@app.post("/api/intervene", response_model=InterveneResponse)
def intervene(req: InterveneRequest):
    """Apply funding and return before, after, and the delta.

    Two scoring calls per request is correct and deliberate — the comparison is
    the product. Do not optimise it into one.
    """
    network = req.network.model_dump(mode="json") if req.network else load_network()
    before_raw, after_raw = scoring.intervene(
        network, req.baseline_scenario or Scenario(), req.interventions
    )
    before = ScoredNetwork.model_validate(before_raw)
    after = ScoredNetwork.model_validate(after_raw)

    return InterveneResponse(
        before=before,
        after=after,
        delta=compute_delta(before, after, interventions=req.interventions),
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(file: Annotated[UploadFile, File()]):
    """Build and score a network from an uploaded zip of collection CSVs.

    AGENTS.md §1.5. Offline only: the archive is unpacked into a temporary
    directory the request owns, handed to the existing transform, validated
    against schema.json and scored by the existing `score_network()`. Nothing
    is fetched, nothing is written into the repo, and no LLM is involved.

    Stateless (§3.4). The scored network and the NetworkInput it came from both
    go back to the client, which sends the network with any scenario request
    that follows. The server keeps no copy and the default network it loaded at
    startup is untouched, so the demo still runs end to end with no upload.

    Every failure a user can cause is a 422 naming the file. A 500 here would
    be a bug, not a bad upload (SCHEMA.md §5.6).
    """
    # Read with a ceiling rather than into memory unbounded. UploadFile is a
    # spooled temp file, so this is a guard against a large body, not a defence
    # against the archive expanding — that check is inside ingest_zip, on the
    # declared sizes, before anything is written.
    data = await file.read(engine_config.INGEST_MAX_UPLOAD_BYTES + 1)
    if len(data) > engine_config.INGEST_MAX_UPLOAD_BYTES:
        return errors.invalid_upload(
            f"upload exceeds the {engine_config.INGEST_MAX_UPLOAD_BYTES // 1_048_576} MB limit"
        )
    if not data:
        return errors.invalid_upload("the uploaded file is empty")

    with tempfile.TemporaryDirectory(prefix="frayfuse-ingest-") as workdir:
        try:
            network, report = ingest_zip(data, Path(workdir))
        except IngestError as exc:
            return errors.invalid_upload(str(exc))

        scored = scoring.simulate(network, Scenario())

    return IngestResponse.model_validate(
        {
            **scored,
            "stress_signals": network.get("stress_signals", []),
            "ingest_report": report.as_dict(),
        }
    )
