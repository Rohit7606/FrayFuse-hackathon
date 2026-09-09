"""Structured error responses for the FrayFuse API.

Error shapes match the `ErrorResponse` definition in `schema.json`: an `error`
code from a closed enum, a human-readable `detail`, and `node_id` where one
offending node can be named.

Two rules from `SCHEMA.md` §5.6 that these exist to enforce:

    Never return 500 for a bad request. Never return 200 with an error inside.

The codes live here as constants rather than as string literals scattered
through `main.py`, so a typo in one handler cannot silently emit a code the
schema does not allow and the frontend does not recognise.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

# The closed enum from schema.json ErrorResponse. Adding a member here without
# adding it there produces a response the contract rejects.
UNKNOWN_NODE = "unknown_node"
INVALID_SCENARIO = "invalid_scenario"
ENGINE_FAILURE = "engine_failure"


def unknown_node(node_id: str) -> JSONResponse:
    """400 — a scenario named a node the loaded network does not contain.

    Names the offending ID, because "unknown node" alone sends the caller
    hunting through a four-hundred-node payload for their own typo.
    """
    return JSONResponse(
        status_code=400,
        content={
            "error": UNKNOWN_NODE,
            "detail": f"{node_id} not in network",
            "node_id": node_id,
        },
    )


def invalid_scenario(detail: str) -> JSONResponse:
    """400 — a scenario that is well-formed but cannot be scored.

    Distinct from the 422 pydantic returns for a malformed body: that is a
    shape problem, this is a meaning problem.
    """
    return JSONResponse(
        status_code=400,
        content={"error": INVALID_SCENARIO, "detail": detail},
    )


def engine_failure(detail: str) -> JSONResponse:
    """500 — the engine raised something we did not anticipate.

    This is the only legitimate 500. If a caller can trigger it with a bad
    request, that is a missing validation rule, not an engine failure.
    """
    return JSONResponse(
        status_code=500,
        content={"error": ENGINE_FAILURE, "detail": detail},
    )
