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

    for name, payload in payloads.items():
        path = OUT / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
