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

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.adapters import compute_delta, to_engine_scenario
from api.config import CORS_ORIGINS, NETWORK_PATH
from api.models import (
    AtRiskResponse,
    BandCounts,
    Delta,
    InterveneRequest,
    InterveneResponse,
    NetworkResponse,
    PerNodeDelta,
    ReasonFactor,
    Scenario,
    Score,
    ScoredNetwork,
    SimulateRequest,
    Summary,
)
from engine.pipeline import UnknownNodeError, score_network

logger = logging.getLogger("frayfuse")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FrayFuse",
    description="Supply-chain financial stress detection and intervention API",
    version="0.1.0",
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


@app.on_event("startup")
def startup_load_network() -> None:
    """Eagerly load the network at startup — fail fast if the file is missing or malformed."""
    try:
        load_network()
        logger.info("Loaded network from %s (%d nodes)", NETWORK_PATH, len(_network_cache["nodes"]))
    except FileNotFoundError:
        logger.error("Network file not found: %s", NETWORK_PATH)
        raise SystemExit(f"FATAL: network file not found: {NETWORK_PATH}")
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("Malformed network file %s: %s", NETWORK_PATH, exc)
        raise SystemExit(f"FATAL: malformed network file {NETWORK_PATH}: {exc}")


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
# Endpoints — stubbed for Phase 0
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
def get_at_risk(limit: int = 10):
    """Baseline scoring, ranked list only."""
    net = load_network()
    
    scores = [
        Score(
            node_id="N042",
            own_stress=0.0,
            inherited_stress=0.63,
            fragility=0.63,
            criticality=0.88,
            final_score=0.56,
            risk_band="critical",
            reason_text="Fragile and single-source",
            reason_factors=[ReasonFactor(kind="single_source", detail="Sole supplier", weight=1.0)],
            intervention_cost_cr=4.8,
            estimated_exposure_cr=148.3,
            propagation_depth=3,
            rank=1
        ),
        Score(
            node_id="N203",
            own_stress=0.0,
            inherited_stress=0.44,
            fragility=0.44,
            criticality=0.31,
            final_score=0.14,
            risk_band="high",
            reason_text="Fragile but not single-source",
            reason_factors=[],
            intervention_cost_cr=2.0,
            estimated_exposure_cr=20.0,
            propagation_depth=2,
            rank=2
        ),
        Score(
            node_id="N087",
            own_stress=0.0,
            inherited_stress=0.40,
            fragility=0.40,
            criticality=0.30,
            final_score=0.12,
            risk_band="high",
            reason_text="Moderate risk",
            reason_factors=[],
            intervention_cost_cr=3.0,
            estimated_exposure_cr=10.0,
            propagation_depth=2,
            rank=3
        ),
        Score(
            node_id="N118",
            own_stress=0.0,
            inherited_stress=0.30,
            fragility=0.30,
            criticality=0.20,
            final_score=0.06,
            risk_band="high",
            reason_text="Second-order casualty",
            reason_factors=[],
            intervention_cost_cr=4.4,
            estimated_exposure_cr=11.3,
            propagation_depth=4,
            rank=4
        )
    ]
    
    ranking = ["N042", "N203", "N087", "N118"]
    
    summary = Summary(
        total_nodes=412,
        at_risk_count=4,
        band_counts=BandCounts(critical=1, high=3, watch=11, stable=397),
        total_intervention_cost_cr=14.2,
        total_estimated_exposure_cr=189.6,
        iterations_to_converge=4,
        stressed_origin_nodes=["N007"],
        max_propagation_depth=4
    )
    
    return AtRiskResponse(
        meta=net["meta"],
        ranking=ranking[:limit],
        scores=scores[:limit],
        summary=summary
    )


@app.post("/api/simulate", response_model=ScoredNetwork)
def simulate(req: SimulateRequest):
    """Score the network under a scenario."""
    net = load_network()
    validate_node_ids(req.scenario, net)

    try:
        engine_scenario = to_engine_scenario(req.scenario)
        result = score_network(net, engine_scenario)
        return ScoredNetwork.model_validate(result)
    except NotImplementedError:
        # Engine not yet implemented — Phase 0 static fallback
        at_risk = get_at_risk(limit=4)
        return ScoredNetwork(
            meta=at_risk.meta,
            nodes=net["nodes"],
            edges=net["edges"],
            scores=at_risk.scores,
            ranking=at_risk.ranking,
            summary=at_risk.summary,
        )


@app.post("/api/intervene", response_model=InterveneResponse)
def intervene(req: InterveneRequest):
    """Apply funding and return before, after, and delta."""
    net = load_network()

    if req.baseline_scenario is not None:
        validate_node_ids(req.baseline_scenario, net)
    validate_node_ids(Scenario(interventions=req.interventions), net)

    try:
        baseline = req.baseline_scenario or Scenario()
        engine_baseline = to_engine_scenario(baseline)
        engine_after = engine_baseline.with_interventions(
            to_engine_scenario(Scenario(interventions=req.interventions)).interventions
        )

        before_dict = score_network(net, engine_baseline)
        after_dict = score_network(net, engine_after)

        before = ScoredNetwork.model_validate(before_dict)
        after = ScoredNetwork.model_validate(after_dict)
        delta = compute_delta(before, after, interventions=req.interventions)

        return InterveneResponse(before=before, after=after, delta=delta)
    except NotImplementedError:
        # Engine not yet implemented — Phase 0 static fallback
        before_at_risk = get_at_risk(limit=4)
        before = ScoredNetwork(
            meta=before_at_risk.meta,
            nodes=net["nodes"],
            edges=net["edges"],
            scores=before_at_risk.scores,
            ranking=before_at_risk.ranking,
            summary=before_at_risk.summary,
        )

        after_scores = []
        for s in before.scores:
            s_copy = s.model_copy()
            if s_copy.node_id == "N042":
                s_copy.risk_band = "stable"
                s_copy.final_score = 0.0
                s_copy.rank = None
            elif s_copy.node_id == "N118":
                s_copy.risk_band = "watch"
                s_copy.final_score = 0.02
            after_scores.append(s_copy)

        after_scores.sort(key=lambda x: x.final_score, reverse=True)
        after_ranking = []
        current_rank = 1
        for s in after_scores:
            if s.risk_band != "stable":
                s.rank = current_rank
                after_ranking.append(s.node_id)
                current_rank += 1
            else:
                s.rank = None

        after_summary = before.summary.model_copy()
        after_summary.total_intervention_cost_cr = 14.2 - 4.8
        after_summary.total_estimated_exposure_cr = 189.6 - 148.3
        after_summary.band_counts = BandCounts(
            critical=0, high=2, watch=12, stable=398
        )

        after = ScoredNetwork(
            meta=before.meta,
            nodes=net["nodes"],
            edges=net["edges"],
            scores=after_scores,
            ranking=after_ranking,
            summary=after_summary,
        )

        delta = Delta(
            nodes_improved=7,
            nodes_worsened=0,
            total_exposure_reduced_cr=148.3,
            total_intervention_cost_cr=4.8,
            per_node=[
                PerNodeDelta(
                    node_id="N042",
                    fragility_before=0.63,
                    fragility_after=0.10,
                    band_before="critical",
                    band_after="stable",
                ),
                PerNodeDelta(
                    node_id="N118",
                    fragility_before=0.30,
                    fragility_after=0.10,
                    band_before="high",
                    band_after="watch",
                ),
            ],
        )

        return InterveneResponse(before=before, after=after, delta=delta)
