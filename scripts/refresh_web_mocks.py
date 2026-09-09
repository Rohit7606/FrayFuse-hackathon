"""Regenerate web/src/mocks/ from the live API.

The mocks must be the real contract, not hand-written guesses. Run this after
any change to the engine, the schema, or the mock network — and commit the
result, so Person C can develop with the backend switched off entirely.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Run from anywhere: scripts/ is not a package and the repo root is not
# necessarily on sys.path when invoked as `python scripts/...`.
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

OUT = REPO_ROOT / "web" / "src" / "mocks"


# The slider's stops. 0.75 is the trigger's own baseline stress on the mock
# network — the step the slider opens on — so the sweep must contain it exactly
# rather than round to 0.7 and open on a figure the baseline view never showed.
SWEEP_LEVELS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0)

def build_sweep(trigger_node: str) -> dict:
    """Score the network once per slider stop, keeping scores and summary only.

    Scores are kept WHOLE. An earlier version carried a whitelist of the fields
    the UI was known to read, which quietly dropped `reason_text` and
    `reason_factors` — so in mock mode the what-if panel lost every explanation
    the live API would have shown, and the two modes stopped agreeing. Only
    `nodes` and `edges` are dropped, because those genuinely do not vary with
    the scenario and repeating them twelve times would put megabytes of
    duplicate network in the bundle.
    """
    from api.main import app

    steps = []
    with TestClient(app) as client:
        for level in SWEEP_LEVELS:
            scenario = {
                "stress_overrides": [{"node_id": trigger_node, "own_stress": level}],
                "interventions": [],
            }
            result = client.post("/api/simulate", json={"scenario": scenario}).json()
            steps.append(
                {
                    "own_stress": level,
                    "scores": result["scores"],
                    "ranking": result["ranking"],
                    "summary": result["summary"],
                }
            )
    return {"trigger_node": trigger_node, "levels": list(SWEEP_LEVELS), "steps": steps}


def main() -> None:
    from api.main import app

    demo = json.loads(
        (REPO_ROOT / "data" / "fixtures" / "demo_scenario.json").read_text(encoding="utf-8")
    )
    empty = {"stress_overrides": [], "interventions": []}

    OUT.mkdir(parents=True, exist_ok=True)
    with TestClient(app) as client:
        payloads = {
            "network.json": client.get("/api/network").json(),
            "at-risk.json": client.get("/api/at-risk?limit=10").json(),
            "simulate.json": client.post("/api/simulate", json={"scenario": empty}).json(),
            "intervene.json": client.post(
                "/api/intervene",
                json={"baseline_scenario": empty, "interventions": [demo["intervention"]]},
            ).json(),
        }

    # The what-if slider sweeps the trigger node's own_stress. Mock mode has no
    # backend to sweep against, so every step is scored here and committed —
    # real engine output at each level, not an interpolation of two endpoints.
    #
    # Only `scores` and `summary` are kept per step. `nodes` and `edges` do not
    # change with the scenario, and repeating a 600 KB network eleven times
    # would put 7 MB of duplicate data in the bundle. The UI merges scores onto
    # the network it already holds, which is what it does with a live response
    # too, so both paths take the same code path.
    payloads["simulate-sweep.json"] = build_sweep(demo["trigger_node"])

    # DEMO_SCENARIO.md §8: "Never hardcode these IDs in application logic. Read
    # them from the fixture." The frontend cannot reach data/fixtures/ from
    # inside web/, so the fixture ships alongside the mocks and the components
    # import it like any other payload.
    payloads["demo-scenario.json"] = demo

    for name, payload in payloads.items():
        path = OUT / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
