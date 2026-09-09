"""FastAPI application — four endpoints, stateless, no session state.

Endpoints:
    GET  /api/network     — raw network for initial render
    GET  /api/at-risk     — baseline scoring, ranked list
    POST /api/simulate    — score under a scenario
    POST /api/intervene   — before/after/delta for funding decisions
    GET  /health          — liveness check
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.adapters import compute_delta, to_engine_scenario
from api.config import CORS_ORIGINS, NETWORK_PATH
from api.models import (
    AtRiskResponse,
    InterveneRequest,
    InterveneResponse,
    NetworkResponse,
    Scenario,
    ScoredNetwork,
    SimulateRequest,
)
from engine.pipeline import UnknownNodeError, score_network

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


_baseline_cache: dict | None = None


def baseline_result() -> dict:
    """The unscenario'd ScoredNetwork, computed once.

    This is a cache of a pure function of the network file, which AGENTS.md
    §3.4 permits: it never changes for a given dataset and holds no per-client
    state. Every scenario-bearing request is scored fresh.
    """
    global _baseline_cache
    if _baseline_cache is None:
        _baseline_cache = score_network(load_network())
    return _baseline_cache




# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.exception_handler(UnknownNodeError)
async def unknown_node_handler(request: Request, exc: UnknownNodeError) -> JSONResponse:
    """Map engine UnknownNodeError to a 400 with the offending node_id named."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "unknown_node",
            "detail": f"{exc.node_id} not in network",
            "node_id": exc.node_id,
        },
    )


@app.exception_handler(Exception)
async def catch_all_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions — structured 500, not a default error page."""
    # Let pydantic's RequestValidationError pass through as 422
    if isinstance(exc, RequestValidationError):
        raise exc
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "engine_failure",
            "detail": str(exc),
        },
    )


def validate_node_ids(scenario: Scenario, net: dict) -> None:
    """Raise UnknownNodeError if any referenced node_id isn't in the network."""
    known_ids = {n["node_id"] for n in net["nodes"]}
    for override in scenario.stress_overrides:
        if override.node_id not in known_ids:
            raise UnknownNodeError(override.node_id)
    for intervention in scenario.interventions:
        if intervention.node_id not in known_ids:
            raise UnknownNodeError(intervention.node_id)


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
    """Raw network for initial render. No scoring."""
    net = load_network()
    return {"meta": net["meta"], "nodes": net["nodes"], "edges": net["edges"]}


@app.get("/api/at-risk", response_model=AtRiskResponse)
def get_at_risk(limit: int = Query(default=10, ge=1, le=1000)):
    """Baseline scoring, ranked list only. The default view.

    Returns `scores` for the ranked nodes only, not all 412 — the UI renders a
    list of four and does not need four hundred score objects to do it.

    `limit` is bounded below at 1 because it indexes a slice: a negative limit
    read as `ranking[:-5]` silently returned the list minus its last five
    entries with a 200, which is a wrong answer rather than an error.
    """
    result = baseline_result()
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
    """Score the network under a scenario. Drives the what-if controls."""
    net = load_network()
    validate_node_ids(req.scenario, net)
    return ScoredNetwork.model_validate(score_network(net, to_engine_scenario(req.scenario)))


@app.post("/api/intervene", response_model=InterveneResponse)
def intervene(req: InterveneRequest):
    """Apply funding and return before, after, and the delta.

    Two scoring calls per request is correct and deliberate — the comparison is
    the product. Do not optimise it into one.
    """
    net = load_network()

    baseline = req.baseline_scenario or Scenario()
    validate_node_ids(baseline, net)
    validate_node_ids(Scenario(interventions=req.interventions), net)

    engine_baseline = to_engine_scenario(baseline)
    engine_after = engine_baseline.with_interventions(
        to_engine_scenario(Scenario(interventions=req.interventions)).interventions
    )

    before = ScoredNetwork.model_validate(score_network(net, engine_baseline))
    after = ScoredNetwork.model_validate(score_network(net, engine_after))

    return InterveneResponse(
        before=before,
        after=after,
        delta=compute_delta(before, after, interventions=req.interventions),
    )
