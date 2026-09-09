# PERSON_B.md — Backend, Simulation & Integration

**Person B / Person 2 — "Build the service and integration layer."**

Read `AGENTS.md` and `SCHEMA.md` before starting. This file assumes both.

---

## 1. What you own

| Path | Yours |
|---|---|
| `api/` | Everything |
| `tests/api/` | Everything |

Your reviewer for every PR is **Person A**.

You also **review every PR touching `engine/` and `data/`** — even when Person C wrote it.

You are the bridge:

```
Person A's engine  ──▶  your API  ──▶  Person C's frontend
```

Which means two responsibilities beyond writing endpoints:

1. **You own the seam.** When A's output doesn't fit what C needs, it surfaces in your layer first. Raise it rather than papering over it in a transform
2. **You own integration timing.** Phase 2 happens because you make it happen, not because the other two are ready

---

## 2. Stateless — the rule that shapes everything

The server holds **no** session state. See `AGENTS.md` §3.4.

- No scenario storage, no session IDs, no mutation between requests
- The client sends the full scenario with every call and gets a complete result
- A page refresh or a backend restart mid-demo loses nothing the client can't immediately re-send
- Caching only as a pure function of the request body

**Why:** a stateful server is slightly cleaner to write and has exactly one failure mode — losing state on stage. Not worth it.

---

## 3. The four endpoints

Full request and response shapes are in `SCHEMA.md` §5. Validate everything against `schema.json`.

### 3.1 `GET /api/network`

Raw network for initial render. No scoring — it should be fast, because C blocks on it before anything appears.

```python
@app.get("/api/network", response_model=NetworkResponse)
def get_network():
    net = load_network()          # cached at startup
    return {"meta": net["meta"], "nodes": net["nodes"], "edges": net["edges"]}
```

Loading `network.json` once at startup is fine — that is not session state.

### 3.2 `GET /api/at-risk?limit=10`

Baseline scoring, ranked nodes only. The default view.

Returns `scores` for the ranked nodes only, not all 412. C does not need 400 score objects to render a list of four.

Cache the baseline result at startup. It never changes for a given network file.

### 3.3 `POST /api/simulate`

Score under a scenario. Drives the what-if controls.

```python
@app.post("/api/simulate", response_model=ScoredNetwork)
def simulate(req: SimulateRequest):
    scenario = to_engine_scenario(req.scenario)
    return score_network(load_network(), scenario)
```

Full `ScoredNetwork` — C needs all node scores to recolour the graph.

### 3.4 `POST /api/intervene`

Before, after, and delta. This drives the closing demo beat, so it is the endpoint most worth getting right.

```python
@app.post("/api/intervene", response_model=InterveneResponse)
def intervene(req: InterveneRequest):
    net = load_network()
    baseline = req.baseline_scenario or Scenario()

    before = score_network(net, baseline)
    after  = score_network(net, baseline.with_interventions(req.interventions))

    return {"before": before, "after": after, "delta": compute_delta(before, after)}
```

`compute_delta` is yours, not the engine's — it is presentation logic. `per_node` includes only nodes whose `risk_band` changed.

**Two scoring calls per request is correct.** Do not optimise it into one. The comparison is the product.

---

## 4. Errors

| Status | When | Body |
|---|---|---|
| 400 | Unknown `node_id` in a scenario | `{"error": "unknown_node", "detail": "N999 not in network", "node_id": "N999"}` |
| 422 | Malformed body | pydantic output |
| 500 | Engine raised unexpectedly | `{"error": "engine_failure", "detail": "<message>"}` |

**Rules:**

- Never 500 for a bad request. A typo'd node ID is a 400
- Never 200 with an error inside
- Catch `UnknownNodeError` from the engine and map it to 400 with the offending ID named
- The `detail` field is read by a human under time pressure. `"N999 not in network"` is useful; `"KeyError"` is not

---

## 5. Config

```python
# api/config.py
NETWORK_PATH = os.getenv("FRAYFUSE_NETWORK", "data/mock/network.json")
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
```

**One environment variable is the entire real-data switch.** When A's transform produces `data/real/network.json`, you change a path. Nothing else in `api/` or `web/` moves.

If that turns out to be false, the contract was wrong — fix the contract, not the endpoint.

---

## 6. Tests — `tests/api/`

| Test | Asserts |
|---|---|
| `test_network_shape` | `/api/network` validates against `NetworkResponse` |
| `test_at_risk_shape` | `/api/at-risk` validates against `AtRiskResponse` |
| `test_simulate_shape` | `/api/simulate` validates against `ScoredNetwork` |
| `test_intervene_shape` | `/api/intervene` validates against `InterveneResponse` |
| `test_unknown_node_400` | Bad `node_id` returns 400, not 500, and names the ID |
| `test_malformed_422` | Garbage body returns 422 |
| `test_stateless` | Two identical requests return identical responses; an intervention does not affect a later baseline call |
| `test_demo_intervention` | `/api/intervene` on the fixture matches `expected_after_bands` |
| `test_empty_scenario` | An empty scenario returns the same result as `/api/at-risk` |

`test_stateless` is the one that catches the failure mode that would hurt most on stage.

---

## 7. Deployment

Local is enough. Do not build a pipeline.

```bash
uvicorn api.main:app --reload --port 8000
```

For the demo, run without `--reload` — the file watcher can restart mid-presentation.

Two things worth having:

- **`GET /health`** returning `{"status": "ok", "network": "<path>", "nodes": <count>}`. Ten seconds to write, tells you instantly whether the backend is up and which dataset it loaded
- **A `make demo` target** (or a shell script) that starts the API and the frontend together. Removes one class of stage error

---

## 8. Phases

**Phase 0 — Contract freeze**
- Agree `SCHEMA.md` and `schema.json` with A and C
- Write `api/models.py` — pydantic models mirroring the schema
- Stub all four endpoints returning static valid responses
- **Exit:** C can develop against your running API before A's engine exists

Stubbing early is the single most useful thing you do. It unblocks C immediately.

**Phase 1 — Independent build**
- Real endpoint logic against A's engine, or a stub scorer if the engine is mid-change
- Error handling
- **Exit:** all four endpoints return contract-valid responses

**Phase 2 — Integration**
- **You drive this.** Wire A's real engine and C's real frontend together
- Fix contract mismatches at the source, not with adapters
- **Exit:** one node flows end to end

**Phase 3 — Demo path**
- `test_demo_intervention` passes
- `/health` endpoint, `make demo` target
- Real dataset switched in if available
- **Exit:** the seven-step demo runs without a restart

**Phase 4 — Hardening**
- Error paths, response times, rehearsal

---

## 9. Traps specific to your track

- **Accidental state.** A module-level dict that caches scenario results is state. Cache only pure functions of the request body
- **Adapting around a contract mismatch.** If A's output doesn't fit C's need, fixing it in your layer hides the problem and leaves two people with different mental models. Change the contract instead
- **Optimising `/api/intervene` into one scoring call.** The before/after comparison is the product
- **Returning all 412 scores from `/api/at-risk`.** C needs four
- **Letting `--reload` run during the demo.** Restarts mid-presentation
- **Adding a database.** Explicitly out of scope — `AGENTS.md` §1.2
- **Waiting for A's engine before stubbing.** C is blocked on you, not on A
