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
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from engine.pipeline import UnknownNodeError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NETWORK_PATH = os.getenv("FRAYFUSE_NETWORK", "data/mock/network.json")
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

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


# ---------------------------------------------------------------------------
# Endpoints — stubs, returning 501 until wired to the engine
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness check — is the backend up and which dataset did it load?"""
    return {"status": "ok", "network": NETWORK_PATH}


@app.get("/api/network")
def get_network():
    """Raw network for initial render. No scoring."""
    raise HTTPException(status_code=501, detail="Not yet implemented — Phase 1 work")


@app.get("/api/at-risk")
def get_at_risk(limit: int = 10):
    """Baseline scoring, ranked list only."""
    raise HTTPException(status_code=501, detail="Not yet implemented — Phase 1 work")


@app.post("/api/simulate")
def simulate():
    """Score the network under a scenario."""
    raise HTTPException(status_code=501, detail="Not yet implemented — Phase 1 work")


@app.post("/api/intervene")
def intervene():
    """Apply funding and return before, after, and delta."""
    raise HTTPException(status_code=501, detail="Not yet implemented — Phase 1 work")
