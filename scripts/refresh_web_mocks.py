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

def build_sweep(trigger_node: str, network: dict | None = None) -> dict:
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
            body: dict = {"scenario": scenario}
            if network is not None:
                body["network"] = network
            result = client.post("/api/simulate", json=body).json()
            steps.append(
                {
                    "own_stress": level,
                    "scores": result["scores"],
                    "ranking": result["ranking"],
                    "summary": result["summary"],
                }
            )
    return {"trigger_node": trigger_node, "levels": list(SWEEP_LEVELS), "steps": steps}


def build_ingest_mock() -> dict:
    """POST the real collection directory to /api/ingest and keep the response.

    Uses data/real rather than data/mock deliberately: ingestion exists to build
    the graph from filings that were actually collected, and the demo uploads
    that folder.
    """
    import io
    import zipfile

    from api.main import app

    source = REPO_ROOT / "data" / "real"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.iterdir()):
            if path.is_file():
                archive.write(path, f"data/real/{path.name}")

    with TestClient(app) as client:
        response = client.post(
            "/api/ingest",
            files={"file": ("data_real.zip", buffer.getvalue(), "application/zip")},
        )
    if response.status_code != 200:
        raise SystemExit(f"ingest mock failed: {response.status_code} {response.text[:400]}")
    return response.json()


def build_ingest_intervention(ingested: dict) -> dict:
    """Fund the ingested network's top-ranked supplier, at the engine's own cost.

    Mirrors exactly what the console computes for an ingested network: the
    first entry in `ranking`, funded at the `intervention_cost_cr` the engine
    put on it. If that derivation changes on either side they will disagree,
    which is why both read the same two fields rather than a hardcoded id.
    """
    from api.main import app

    ranked = ingested["ranking"][0] if ingested["ranking"] else None
    if ranked is None:
        raise SystemExit("ingest mock produced an empty ranking; nothing to fund")
    cost = next(s["intervention_cost_cr"] for s in ingested["scores"] if s["node_id"] == ranked)

    network = {key: ingested[key] for key in ("meta", "nodes", "edges", "stress_signals")}
    with TestClient(app) as client:
        response = client.post(
            "/api/intervene",
            json={
                "baseline_scenario": {"stress_overrides": [], "interventions": []},
                "interventions": [{"node_id": ranked, "amount_cr": cost}],
                "network": network,
            },
        )
    if response.status_code != 200:
        raise SystemExit(f"ingest intervention mock failed: {response.status_code} {response.text[:400]}")
    return response.json()


def pick_trigger(ingested: dict) -> str:
    """The origin the ingested walkthrough tells its story about.

    MUST STAY IDENTICAL to `pickTrigger` in web/src/v2/lib/derive.ts — this
    script commits the sweep the slider reads offline, and a sweep built around
    a different trigger than the console names is a slider that moves a company
    the caption never mentions.

    The rule: walk the top-ranked supplier's dependency path upward and take the
    first stressed origin on it; failing that, the most-stressed origin that is
    not an anchor; failing that, whatever the engine listed first.
    """
    origins = list(ingested["summary"]["stressed_origin_nodes"])
    if not origins:
        raise SystemExit("ingest mock has no stressed origins; nothing to sweep")
    if len(origins) == 1:
        return origins[0]

    tier = {n["node_id"]: n["tier"] for n in ingested["nodes"]}
    own = {s["node_id"]: s["own_stress"] for s in ingested["scores"]}
    by_supplier: dict[str, list[dict]] = {}
    for edge in ingested["edges"]:
        by_supplier.setdefault(edge["supplier_id"], []).append(edge)

    ranking = ingested["ranking"]
    if ranking:
        current = ranking[0]
        seen = {current}
        for _ in range(8):
            if tier.get(current) == 0:
                break
            options = [e for e in by_supplier.get(current, []) if e["buyer_id"] not in seen]
            if not options:
                break
            options.sort(
                key=lambda e: (-e["exposure_pct"], -e["annual_value_cr"], e["edge_id"])
            )
            current = options[0]["buyer_id"]
            seen.add(current)
            if current in origins:
                return current

    suppliers = [n for n in origins if tier.get(n, 0) > 0]
    pool = suppliers or origins
    return min(pool, key=lambda n: (-own.get(n, 0.0), n))


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

    # The live-build page needs a response to replay with the backend off.
    # Built from the real collection CSVs, zipped exactly as a user would zip
    # that folder, and pushed through the real endpoint — so the committed mock
    # is the endpoint's own output rather than a description of it.
    ingest_payload = build_ingest_mock()
    payloads["ingest.json"] = ingest_payload

    # Funding the ingested network's own top-ranked supplier. Without this the
    # closing beat has nothing to show when the API is switched off and the
    # network came from an upload — there is no committed intervention for a
    # network that did not exist when the mocks were written.
    payloads["ingest-intervene.json"] = build_ingest_intervention(ingest_payload)

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

    # And the same sweep for the ingested network. Without it the what-if
    # slider simply vanished after an upload — the one control that proves the
    # numbers are being recomputed rather than replayed, missing on the path
    # that most needs to prove it. The trigger is derived exactly as the console
    # derives it, so the sweep and the caption name the same company.
    ingest_trigger = pick_trigger(ingest_payload)
    payloads["ingest-sweep.json"] = build_sweep(
        ingest_trigger,
        network={key: ingest_payload[key] for key in ("meta", "nodes", "edges", "stress_signals")},
    )

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
