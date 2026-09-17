# FrayFuse — Supply-Chain Financial Contagion Intelligence 🔗

<img width="1920" height="1440" alt="FrayFuse Hero Banner" src="PLACEHOLDER_HERO_IMAGE" />

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Stateless_API-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![NetworkX](https://img.shields.io/badge/NetworkX-Graph_Engine-FF6F00?style=for-the-badge)](https://networkx.org)
[![React](https://img.shields.io/badge/React-19.2-61DAFB?style=for-the-badge&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?style=for-the-badge&logo=typescript)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-8.2-646CFF?style=for-the-badge&logo=vite)](https://vite.dev)
[![Tests](https://img.shields.io/badge/Tests-204_passing-2EA043?style=for-the-badge&logo=pytest&logoColor=white)](#-project-status)
[![Determinism](https://img.shields.io/badge/Output-Byte_Identical-8B5CF6?style=for-the-badge)](#determinism-is-a-hard-requirement)
[![No ML](https://img.shields.io/badge/Machine_Learning-Deliberately_None-DC2626?style=for-the-badge)](#️-scoring-engine-methodology)

> **Which few suppliers are about to run out of cash *and* cannot be replaced, and how much money would stabilise each one?**
>
> Every feature in this repository exists to answer that one sentence. Built as a hackathon submission on a frozen three-track contract (`engine` / `api` / `web`), scored end to end with **zero machine learning** — the depth is in the graph, not in fitting anything.

---

## Problem Statement

- **Invisible Sub-Tier Exposure:** A large Tier-1 manufacturer can name its direct suppliers and almost nobody beneath them. On our mock network only **8 of 412 companies** publish anything at all; on the real collection it is **14 of 298**. The firms whose failure actually stops the line are the ones nobody is looking at.

- **Payment Stress Is Contagious and Silent:** When a buyer runs short of cash it does not announce it — it quietly stretches payment to its suppliers. Those suppliers stretch theirs. The distress travels downstream as invoices that were never paid, two and three tiers deep, long before any rating agency reacts.

- **The Ageing Table Is Built to Look Clean:** A statutory trade-payables ageing table is a snapshot of one day — 31 March — and it is the one day a company can prepare for. The MSMED disclosures in the *same filing* describe the whole year, and they frequently contradict the snapshot. Nobody reads them side by side.

- **Centrality Is Mistaken for Criticality:** Conventional supply-chain analytics rank suppliers by size, spend, or graph centrality — all of which are size-correlated. Measured on our own network, network-wide normalisation handed betweenness **0.875** and flow share **1.000** to the Tier-1 hub while a genuine sole-source Tier-2 chokepoint scored **0.137** and **0.012**. The method buries exactly the supplier it was built to find.

- **Risk Dashboards Stop Short of a Decision:** Existing tools produce a heat map and end there. A treasury team cannot act on a colour. They need a name, a rupee figure, and the counterfactual: *what happens if we do nothing.*

There is a critical need for a system that reads **published filings**, propagates stress along real trade relationships, and converts the result into a **specific, costed funding decision** that can be defended line by line.

---

## Project Objective

**FrayFuse** is a deterministic supply-chain contagion engine that maps a multi-tier supplier network, detects the payment-stress trigger from published statutory filings, propagates it downstream against goods flow, and turns the result into a ranked, costed intervention plan.

The platform aims to:

- **Detect Stress From Disclosure, Not Inference:** Score a company's payment behaviour from a four-rung signal ladder read out of its own MSMED and trade-payables ageing disclosures — where a rise in MSMED interest is a *statutory admission* of late payment, not an analyst's opinion.
- **Propagate Contagion Along the Money:** Transmit fragility **buyer → supplier**, against the direction goods travel, scaled by revenue dependency and damped per hop, iterated to convergence on a graph that is allowed to contain cycles.
- **Rank by Fragile × Irreplaceable:** Multiply fragility by a within-tier criticality score so that a robust chokepoint and a fragile commodity supplier both fall away, and only the intersection survives — `final_score = fragility × criticality`.
- **Run the Chain Backwards:** Propagate *supply disruption* the other way, supplier → buyer, using a noisy-OR composition, so a failure four tiers down can be traced to a halted production line at the anchor.
- **Cost the Rescue and Prove the Counterfactual:** Quantify what stabilising each supplier costs, re-score the entire network with that supplier funded, and show the same figures with the intervention removed.
- **Spread a Finite Budget:** Given a real number — ₹1 cr, ₹5 cr, ₹25 cr — allocate it across several suppliers by rupees-of-anchor-exposure-removed per rupee committed, then re-score the committed set jointly so nothing reported is double-counted.
- **Never Fabricate a Fact:** Enforce, in code and in tests, that no sole-source claim and no generated rupee figure is ever attached to a real company's name.

---

## Sustainable Development Goals (SDGs)

This project aligns with the following United Nations Sustainable Development Goals:

### SDG 8: Decent Work and Economic Growth
- **Target 8.3:** Small manufacturing suppliers fail from working-capital starvation, not from lack of demand. FrayFuse identifies which of them are days away from that failure and prices the bridge — a ₹2.04 cr payment that prevents a firm from collapsing preserves the jobs inside it.
- **Target 8.10:** The engine reads **MSMED Act** disclosures, India's statutory late-payment regime for micro and small enterprises, and treats a rise in accrued MSMED interest as the leading stress signal — turning a compliance footnote into an early-warning instrument for the smallest firms in the chain.

### SDG 9: Industry, Innovation and Infrastructure
- **Target 9.3:** Increases access of small-scale industrial enterprises to financial services by giving a Tier-1 anchor or a lender a defensible, evidence-backed reason to extend credit to a Tier-2 or Tier-3 supplier it has never heard of.
- **Target 9.4:** Preventing a cascading supply-chain halt avoids the waste of an entire production line stopping and restarting — the emissions-heaviest failure mode in discrete manufacturing.

### SDG 12: Responsible Consumption and Production
- **Target 12.6:** Every node and edge carries a row-level `data_source` and a visible `substituted` list, so the difference between a disclosed fact and a modelling assumption is never lost. The system makes corporate disclosure quality legible rather than laundering it into a score.

---

## Proposed Solution

FrayFuse uses a **'Two-Direction Propagation' Architecture**. Conventional supply-chain risk tools model one flow. FrayFuse models two, in opposite directions, because the failure mechanism genuinely runs both ways:

> **Stress flows down the chain as invoices that were never paid; failure flows back up it as parts that never arrived.**

There is no machine learning anywhere in the scoring path — a transparent propagation rule that can be explained in one sentence beats a trained model that cannot be justified, and at these data volumes ML would be theatre. Every constant lives in `engine/config.py` beside the evidence for its value, and the ones that are stated assumptions rather than measurements say so in the file.

### Architecture & Workflow:

<img width="2752" height="1536" alt="FrayFuse Architecture Diagram" src="PLACEHOLDER_ARCHITECTURE_DIAGRAM" />

*Three-track architecture: the pure-Python `engine` scoring a NetworkX DiGraph, a stateless FastAPI layer exposing seven endpoints, and a React 19 console rendering a force-directed canvas — communicating only through the frozen `SCHEMA.md` contract.*

1. **Collection & Transform (offline):** 43 real Indian manufacturing companies, 30 disclosed trade relationships, and 46 company-years of financials are collected into CSVs under `data/real/`. `engine/transform.py` converts them to a runtime `network.json`, synthesising a generated Tier-2/Tier-3 layer beneath the real companies (the collected cohort bottoms out at 3-node chains, so nothing would propagate without it). `TRANSFORM_GENERATED_AT` is fixed rather than `now()`, so the same CSVs always produce a byte-identical file.

2. **Graph Construction:** `engine/graph.py` builds a `networkx.DiGraph` with edges oriented **supplier → buyer**. Only edges at `confidence: "confirmed"` may carry stress — inference from a third party is never given the standing of a company's own disclosure. A supplier's outgoing `exposure_pct` may exceed 1.0 only by rounding tolerance.

3. **Stress Detection:** `engine/stress.py` evaluates a four-rung signal ladder against the two most recent *comparable* financial years. Weights are renormalised over whichever rungs a filer actually discloses — a company with only rung 1 available scores on rung 1 at full weight. A rung whose inputs are absent is **dropped, never defaulted**.

4. **Contagion Propagation:** `engine/contagion.py` transmits fragility buyer → supplier, scaled by revenue dependency, damped at `DAMPING = 0.75` per hop and absorbed by the receiving node's cash buffer. Iterated to convergence (`CONVERGENCE_THRESHOLD = 0.001`, typically 4–5 iterations, capped at 10). Cycles are expected and handled — no topological sort is attempted.

5. **Criticality Scoring:** `engine/criticality.py` combines betweenness (0.45), sole-source status (0.35) and flow share (0.20), normalised **within tier** rather than across the network. A node whose sole-source status is undisclosed drops that term and renormalises, exactly as the stress ladder does.

6. **Ranking & Triage:** `engine/ranking.py` computes `final_score = fragility × criticality`, bands it, and generates a deterministic template-composed reason string. `engine/triage.py` then splits the same population on the two factors *separately* — because `0.35 × 0.20` and `0.10 × 0.70` are the same product and the opposite decision — into `fund_now`, `derisk`, `monitor`, and `clear` queues.

7. **Supply Disruption (reverse pass):** `engine/disruption.py` propagates the other way, supplier → buyer, seeded by the part of a node's fragility it did *not* generate itself. A company stretching its own payables is conserving cash, not stopping its line. Composition is noisy-OR: `disruption(b) = 1 − Π(1 − halt(s) × supply_impact(s→b))`.

8. **Intervention & Allocation:** `engine/intervention.py` prices the rescue and re-scores the whole network with the funded node's fragility pinned, producing the counterfactual. `engine/allocation.py` probes each candidate independently, ranks by efficiency (₹ of anchor exposure removed per ₹ committed), commits greedily to the budget, then re-scores the committed set **jointly** — so every headline figure reported comes from the joint run.

9. **API & Console:** `api/main.py` serves seven stateless endpoints. `web/src/v2/` renders an eight-step walkthrough over a single force-directed canvas. **Nothing in the frontend computes a risk figure** — every number on screen arrived from an engine call, including every stop on the what-if slider.

10. **Live Ingestion:** `POST /api/ingest` accepts a zip of collection CSVs and returns a fully scored network in one server-side pass, guarded against zip bombs by caps on member count and declared uncompressed size checked *before* anything is written to disk.

---

## 🛠️ Technologies Used

### Engine Stack (Pure Python — `engine/`)

- **Python 3.12:** The entire scoring path. No notebooks, no runtime document parsing, no external service calls during scoring.
- **NetworkX:** Directed-graph primitives and betweenness centrality over the supplier network. Chosen over a graph database because a 412-node network fits in memory and a database would add operational risk without adding capability.
- **NumPy:** Vector arithmetic in the propagation loops and the z-score fallback statistics in the stress ladder.
- **pandas:** CSV ingestion and reshaping inside `engine/transform.py` and `engine/ingest.py` only — deliberately absent from the scoring path, which operates on plain dicts so its output is trivially serialisable and diffable.
- **`engine/config.py`:** Every tunable constant in one file, each with the evidence for its value written beside it. No magic numbers exist anywhere else in the codebase, and every threshold documents the distribution it was calibrated against.
- **`engine/mockgen.py`:** Seeded generator producing the canonical 412-node / 1,339-edge network at `MOCK_SEED = 42`, with a fixed `MOCK_GENERATED_AT` so the same seed yields a byte-identical file.

### API Stack (`api/`)

- **FastAPI:** Seven endpoints, entirely stateless. `score_network()` is a pure function over a whole network and stays that way — there is no session, no job queue, and no partial result.
- **Pydantic:** Request and response models mirroring the frozen `SCHEMA.md` contract, with `tests/api/test_schema_contract.py` asserting that the API response validates against `schema.json` rather than against the models that produced it.
- **Uvicorn:** ASGI server. Run without `--reload` during a demo, for the obvious reason.
- **python-multipart:** `multipart/form-data` parsing for `POST /api/ingest`. FastAPI requires it for `UploadFile` and there is no stdlib path.
- **Custom middleware:** A per-request timing line at `INFO`, and a catch-all exception handler that returns a schema-shaped error rather than an HTML traceback — because a stack trace on a projector ends a demo.

### Frontend Stack (`web/`)

- **React 19.2:** The v2 console. Function components throughout; the walkthrough's step state is a single discriminated union, not a pile of booleans.
- **TypeScript 6.0:** `web/src/v2/types.ts` mirrors the same schema the API validates against, so a contract change breaks the build rather than the demo.
- **Vite 8.2:** Dev server and build. Two modes — `dev` reads committed mock responses with the backend off, `dev:live` hits the real API. `scripts/refresh_web_mocks.py` exists to guarantee the two return identical figures.
- **react-force-graph-2d:** Canvas force-directed rendering of the network. One canvas, four reading modes — the *mode* changes, never the data.
- **Ajv:** Runtime JSON-schema validation of the committed mocks in `web/tests/mocks.test.ts`, so an out-of-date mock fails CI instead of silently diverging from the engine.
- **Vitest + oxlint:** 30 web tests and a lint pass, both wired into the same check the Python side runs.
- **Hand-written CSS (`console.css`):** No UI framework. Bands are never shown as colour alone — every chip prints its name — and `prefers-reduced-motion` resolves the cascade animation straight to its completed state.

### Data Layer (`data/`)

- **`data/real/`:** Five collection CSVs — `companies.csv` (43 real Indian manufacturers with CIN and NSE symbols), `edges.csv` (37 rows, 30 of which survive into the built network), `financials.csv` (46 company-years), `distress_events.csv` (rating actions with source URLs), and `entity_pool.csv` (the fictional-name pool for the generated tier).
- **`data/real/DATA_DICTIONARY.md`:** The field-level contract and, in §3b, the two integrity rules that are enforced in code with tests rather than left to care.
- **`data/mock/network.json`:** The canonical 412-node / 1,339-edge demo network at seed 42, with complete rupee values throughout — the dataset to quote for rupee-for-rupee figures.
- **`data/fixtures/`:** The pinned demo fixture with fixed node IDs guaranteed by `DEMO_SCENARIO.md`.
- **JSON files on disk — no database server.** Postgres, Mongo and Redis are all on the explicit do-not-build list in `AGENTS.md` §1.2.

### Testing & Tooling

- **pytest:** 174 Python tests across `tests/engine/`, `tests/api/` and `tests/web/`, including determinism assertions, schema-contract validation, ingestion hardening against hostile archives, and the real-vs-synthetic integrity rules.
- **Ruff:** Lint and format for the entire Python tree, clean on every commit.
- **`scripts/determinism_check.py`:** Runs the pipeline twice and diffs the output byte for byte.
- **`scripts/latency_check.py`:** Times the endpoints, because a judge waiting three seconds for a slider is a judge who has stopped listening.
- **`scripts/preflight.py`:** One command that verifies the demo machine is actually ready.
- **`scripts/demo.ps1`:** Starts the API, waits on `/health` before starting the frontend, and stops both on Ctrl+C. A `Makefile` wraps the same commands for anyone who has `make`.

### Governance Documents

- **`AGENTS.md`:** The rules every contributor follows — determinism, per-directory ownership, git discipline, and the explicit do-not-build list with a reason for each entry.
- **`SCHEMA.md` + `schema.json`:** The frozen contract between the three tracks. Additive changes only, versioned, with a changelog.
- **`DEMO_SCENARIO.md`:** The canonical demo with fixed node IDs, the exact figures expected on each screen, and a written recovery procedure for when the live build fails on stage.

---

## 📸 System Visuals

### 1. The Network Canvas — 412 Companies, Four Tiers Deep
*The opening view: the full supplier network rendered as a force-directed canvas with the anchor at centre, four tiers radiating outward, and every node neutral. The story rail on the left doubles as the legend, because colour is carrying data on this screen and never gets to do that without its name beside it.*
<img width="100%" alt="FrayFuse Network Canvas" src="PLACEHOLDER_SCREENSHOT_01_NETWORK" />
<!-- Add screenshot: Step 01 "The chain" — full graph, all nodes neutral, story rail visible, node/edge/tier counts in the caption bar -->

### 2. Ageing vs Reality — The Evidence Sheet
*The single most persuasive screen in the product. The trigger's statutory trade-payables ageing table — a snapshot of 31 March, the one day a company can prepare for — printed beside its MSMED lines, which describe the whole year. Both come from the same public filing and they contradict each other. This panel answers "how do you know?" with the company's own disclosures rather than with a score.*
<img width="100%" alt="Ageing vs Reality Evidence Sheet" src="PLACEHOLDER_SCREENSHOT_02_EVIDENCE" />
<!-- Add screenshot: Step 03 "Ageing vs reality" — EvidenceSheet open showing the ageing snapshot on the left and the MSMED payment-reality lines on the right, with the FY labels -->

### 3. The Cascade — Stress Propagating One Hop at a Time
*Stress revealed in the order the engine actually assigned it, using the `propagation_depth` returned by `POST /api/simulate`. It is not a fixed sequence on a timer — the animation is driven by engine output, hop by hop, amber then red, outward from the trigger against the direction goods travel.*
<img width="100%" alt="Contagion Cascade Animation" src="PLACEHOLDER_SCREENSHOT_03_CASCADE" />
<!-- Add screenshot: Step 04 "Stress propagates" — mid-cascade, with some tiers lit amber/red and the outer tiers still neutral -->

### 4. Fragile × Irreplaceable — The Ranked List
*15 suppliers out of 412, each with a plain-English template-generated reason, a rupee stabilisation cost, and the exposure carried through it. The headline finding sits at `final_score` **0.204** against the next node's **0.090** — a 2.3× gap — and the list explains in one line why the supplier that started the cascade is not the one to rescue.*
<img width="100%" alt="Ranked At-Risk Supplier List" src="PLACEHOLDER_SCREENSHOT_04_RANKING" />
<!-- Add screenshot: Step 05 "Fragile × irreplaceable" — SidePanel showing the ranked list with band chips, scores, reasons and cost/exposure figures -->

### 5. Fund It, Then Undo It — The Counterfactual
*The closing beat. ₹2.04 cr into `N042` takes it `critical → stable`, carries `N118` `high → stable` with it, and drains the anchor's supply risk from **₹848.96 cr to ₹308.36 cr**. Toggle the intervention off and the cascade completes — the anchor's own line stops. Both states are real engine runs, and re-running it on stage produces byte-identical numbers.*
<img width="100%" alt="Intervention Counterfactual" src="PLACEHOLDER_SCREENSHOT_05_INTERVENE" />
<!-- Add screenshot: Step 07 "Fund it, then undo it" — before/after comparison with the counterfactual toggle, showing both the funded and unfunded anchor state -->

<details>
<summary>🗺️ The Eight-Step Walkthrough — Full Gallery</summary>

### 01 — The Chain
*The whole network, ~400 nodes, four tiers, anchor at centre. Nothing is coloured yet.*
<img width="100%" alt="Step 01 The Chain" src="PLACEHOLDER_SCREENSHOT_STEP_01" />
<!-- Add screenshot: Step 01, full neutral graph with node_count / edge_count / tier count in the caption -->

### 02 — What the Anchor Sees
*Observable nodes highlighted, everything else dimmed. 8 of 412 companies publish anything at all. The dark region is not carelessness — the data does not exist.*
<img width="100%" alt="Step 02 What the Anchor Sees" src="PLACEHOLDER_SCREENSHOT_STEP_02" />
<!-- Add screenshot: Step 02, observable nodes lit, the rest dimmed, with the "N of these companies publish anything" caption -->

### 03 — Ageing vs Reality
*The trigger's own filing, opened. Two disclosures, same document, opposite stories.*
<img width="100%" alt="Step 03 Ageing vs Reality" src="PLACEHOLDER_SCREENSHOT_STEP_03" />
<!-- Add screenshot: Step 03, EvidenceSheet fully expanded with both disclosure blocks and the FY comparison -->

### 04 — Stress Propagates
*The cascade, revealed by engine-assigned propagation depth rather than by timer.*
<img width="100%" alt="Step 04 Stress Propagates" src="PLACEHOLDER_SCREENSHOT_STEP_04" />
<!-- Add screenshot: Step 04, completed cascade with all bands resolved across the canvas -->

### 05 — Fragile × Irreplaceable
*The ranked list, and the argument for why the origin of the stress is not the rescue.*
<img width="100%" alt="Step 05 Fragile x Irreplaceable" src="PLACEHOLDER_SCREENSHOT_STEP_05" />
<!-- Add screenshot: Step 05, ranked list panel beside the graph with the top-ranked node selected -->

### 06 — Why This One Matters
*Path focus: the dependency chain from a deep-tier supplier up to the anchor, walked over `edges` by `exposure_pct`, with the component name and dependency percentage on each hop.*
<img width="100%" alt="Step 06 Path Focus" src="PLACEHOLDER_SCREENSHOT_STEP_06" />
<!-- Add screenshot: Step 06, single dependency path highlighted on the canvas with the rest of the graph dimmed, hop tooltips visible -->

### 07 — Fund It, Then Undo It
*Before, after, and the counterfactual, side by side.*
<img width="100%" alt="Step 07 Fund It Then Undo It" src="PLACEHOLDER_SCREENSHOT_STEP_07" />
<!-- Add screenshot: Step 07, the funded state with the counterfactual toggle control visible -->

### 08 — Spread a Budget
*A fixed sum split across several suppliers, best efficiency ratio first, with the unallocated remainder reported honestly rather than sprinkled.*
<img width="100%" alt="Step 08 Spread a Budget" src="PLACEHOLDER_SCREENSHOT_STEP_08" />
<!-- Add screenshot: Step 08, allocation result showing committed amounts per supplier, total allocated, and unallocated balance -->

</details>

<details>
<summary>🧭 The Decision Layer — Panels & Controls</summary>

### Decision Panel — Which Queue, and Why
*Selecting any supplier opens its decision panel: its triage queue, the exposure through it, its stabilisation cost, and the review triggers that would escalate it. Every figure arrives from `POST /api/derisk`; the panel computes nothing.*
<img width="100%" alt="Supplier Decision Panel" src="PLACEHOLDER_SCREENSHOT_DECISION_1" />
<!-- Add screenshot: DecisionPanel open on a fund_now supplier, showing queue label, exposure, cost, and escalation triggers -->

### Queue Board — Fund Now vs Watch and Second-Source
*The network split on the two factors separately: 6 suppliers to fund (fragile and hard to replace) and 11 to watch and second-source (fragile but not chokepoints) — 6 of which never reach the ranked list at all, because `final_score` multiplies their replaceability away.*
<img width="100%" alt="Triage Queue Board" src="PLACEHOLDER_SCREENSHOT_DECISION_2" />
<!-- Add screenshot: QueueBoard showing the fund_now and derisk columns with counts and supplier names -->

### Watch List — Capital Held Contingent
*A supplier in the watch queue can be moved into a session watch list: capital held **contingent**, not committed. A supplier in the funding queue can be funded straight from the panel, running the same counterfactual the closing beat does.*
<img width="100%" alt="Session Watch List" src="PLACEHOLDER_SCREENSHOT_DECISION_3" />
<!-- Add screenshot: the watch list populated with two or three suppliers and the contingent-capital total -->

### Substitution Candidates — The Other End of the Distribution
*Where a supplier is replaceable, the engine suggests up to three alternatives scored on health (0.60) and spare capacity (0.40). Eligibility requires an edge that **explicitly states** alternatives exist — undisclosed status is never read as permission, which is why not one of the 43 real companies is offered a substitute.*
<img width="100%" alt="Substitution Candidates Panel" src="PLACEHOLDER_SCREENSHOT_DECISION_4" />
<!-- Add screenshot: substitution candidates list for a replaceable supplier showing fitness scores and the eligibility note -->

### What-If Slider — Re-Scoring the Trigger Live
*Drag the trigger's `own_stress` and the whole network re-scores. Live it posts to `/api/simulate`; offline it reads `web/src/mocks/simulate-sweep.json`, where every stop was produced by that same engine call ahead of time. A native `<input type="range">` on purpose — keyboard, screen reader and touch all work without a line of code.*
<img width="100%" alt="What-If Simulation Slider" src="PLACEHOLDER_SCREENSHOT_DECISION_5" />
<!-- Add screenshot: WhatIfBar at a mid-range position with the re-scored band counts and the anchor figure updating -->

</details>

<details>
<summary>📥 The Live Build — Filings to a Scored Chain</summary>

### Upload — A Zip of Collection CSVs
*The judges asked to see the graph constructed from uploaded source documents rather than read from a committed JSON file, so the build is its own page rather than a step inside the console. Guarded at 16 MB on the wire, 64 MB expanded, 200 members maximum — checked before anything is written.*
<img width="100%" alt="Ingestion Upload Screen" src="PLACEHOLDER_SCREENSHOT_BUILD_1" />
<!-- Add screenshot: BuildPage upload state with the drop target and the stated size caps -->

### Assembly — Structure First, Colour Second
*The archive is processed in a single server-side pass and comes back complete; what the page animates is the **reveal** of a finished result, in the order the work actually happened. The page says so on screen rather than dressing a completed job up as a progress bar. The skeleton assembles in ink; risk only resolves once the graph is whole.*
<img width="100%" alt="Live Graph Assembly" src="PLACEHOLDER_SCREENSHOT_BUILD_2" />
<!-- Add screenshot: BuildPage mid-assembly, tiers appearing in sequence in monochrome with the ingest log beside the canvas -->

### Ingest Report — What Was Read, and What Was Rejected
*The completed build with its report: nodes and edges accepted, rows rejected with reasons, and the substitutions the engine had to make — each one named, so a runtime fill stays a visible modelling decision rather than a fabricated fact.*
<img width="100%" alt="Ingestion Report" src="PLACEHOLDER_SCREENSHOT_BUILD_3" />
<!-- Add screenshot: BuildPage completed state showing the IngestReport counts, rejections and substitution list -->

</details>

---

## 🚀 Running FrayFuse

#### Engine only — no API, no frontend

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m engine.pipeline data/mock/network.json
```

That prints the ranked list and the anchor counterfactual with nothing else running.

#### The whole demo — API and UI together

```powershell
./scripts/demo.ps1
./scripts/demo.ps1 -Network data/real/network.json    # the real dataset
```

The script waits on `/health` before starting the frontend and stops both on Ctrl+C. A `Makefile` wraps the same commands for anyone who has `make`; it is not installed on the demo machine, so `demo.ps1` is the working path.

#### Every command

```bash
python -m engine.pipeline data/mock/network.json      # score and print
python -m engine.mockgen --seed 42 --out data/mock/network.json
python -m engine.transform --in data/real/ --out data/real/network.json
uvicorn api.main:app --port 8000                      # no --reload during a demo
pytest tests/ -q                                      # 174 tests
ruff check .
cd web && npm install && npm run dev                  # mocks; dev:live for the API
```

#### Environment configuration

```bash
# API
FRAYFUSE_NETWORK=data/mock/network.json    # the dataset the API serves — the entire real-data switch
FRAYFUSE_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000
FRAYFUSE_LOG_LEVEL=INFO                    # DEBUG for more, WARNING to quieten per-request timing

# web
VITE_API_BASE=http://127.0.0.1:8000        # a backend on another host or port
```

> CORS permits `localhost` **and** `127.0.0.1` on ports 5173 and 3000 — both spellings, because a browser treats them as different origins and Vite prints both when started with `--host`. Clicking the wrong one used to fail the whole app with nothing on screen to explain why.

#### Determinism is a hard requirement

The same input must produce byte-identical output, because a judge will re-run the counterfactual on stage:

```bash
python -m engine.pipeline data/mock/network.json --json > run1.json
python -m engine.pipeline data/mock/network.json --json > run2.json
diff run1.json run2.json && echo DETERMINISTIC
```

#### The API surface

| Endpoint | Method | What it returns |
|---|---|---|
| `/health` | GET | Liveness, used by `demo.ps1` before it starts the frontend |
| `/api/network` | GET | The raw network plus optional `stress_signals`, so the evidence panel prints a filer's own ageing and MSMED rows rather than restating them |
| `/api/at-risk?limit=N` | GET | The ranked list and the summary |
| `/api/simulate` | POST | A full re-score under a scenario — every what-if slider stop |
| `/api/intervene` | POST | The counterfactual: the network re-scored with a supplier funded |
| `/api/derisk` | POST | One supplier's plan — queue, stabilisation cost, exposure, escalation thresholds |
| `/api/allocate` | POST | A budget spread across several suppliers, best ratio first |
| `/api/ingest` | POST | A zip of collection CSVs in, a fully scored network out |

---

## 📊 Project Status

| Domain | Status | Notes |
|:-------|:-------|:------|
| **Scoring Engine** | ✅ **Complete** | All five stages plus triage, substitution and allocation; every constant evidenced in `config.py` |
| **Contagion Propagation** | ✅ **Stable** | Converges in 4–5 iterations on 412 nodes; cycles handled without a topological sort |
| **Supply-Disruption Pass** | ✅ **Complete** | Noisy-OR composition running supplier → buyer, seeded by non-self-generated fragility |
| **API (FastAPI)** | ✅ **Complete** | 7 stateless endpoints, schema-contract tested against `schema.json` |
| **Frontend (React 19 v2 console)** | ✅ **Complete** | Eight-step walkthrough, decision panel, what-if bar, live build page |
| **Real Dataset** | ✅ **Active** | 43 real Indian manufacturers, 30 disclosed edges, 46 company-years, 255 generated deep-tier nodes |
| **Live Ingestion** | ✅ **Complete** | Zip upload hardened against zip bombs; caps checked before any write |
| **Determinism** | ✅ **Verified** | Byte-identical for scoring, mock generation and the CSV transform |
| **Test Suite** | ✅ **Passing** | 174 Python + 30 web = **204 tests**, `ruff` clean |
| **Public Deployment** | ⏳ **Local only** | Runs locally by design — no auth, no database, no hosted state. Deployment was never in scope |
| **Real-Data Rupee Coverage** | 🔄 **Partial** | 13 of the 30 real edges carry no disclosed `annual_value_cr`, so exposure understates on real data — the deliberate cost of never inventing a figure |

---

## ⚙️ Scoring Engine Methodology

Eight stages, no machine learning, no model weights. Every constant below lives in `engine/config.py` with its evidence beside it.

| # | Stage | Module | Formula |
|:--|:---|:---|:---|
| 1 | Stress detection | `stress.py` | `own_stress = Σ (wᵢ / Σw_available) × rungᵢ` |
| 2 | Contagion (buyer → supplier) | `contagion.py` | `fragility(s) = min(1, own_stress(s) + received(s))` |
| 3 | Criticality (within tier) | `criticality.py` | `0.45·betweenness + 0.35·sole_source + 0.20·flow_share` |
| 4 | Ranking | `ranking.py` | `final_score = fragility × criticality` |
| 5 | Disruption (supplier → buyer) | `disruption.py` | `1 − Π(1 − halt(s) × supply_impact(s→b))` |
| 6 | Intervention | `intervention.py` | `cost = (Σ annual_value / 4) × fragility` |
| 7 | Triage | `triage.py` | split on fragility **and** criticality separately |
| 8 | Allocation | `allocation.py` | greedy on `Δ anchor_inflow_at_risk / ₹ committed` |

---

### 1. Stress — four rungs, renormalised over what a filer actually disclosed

| Rung | Weight | Fires when | Measured |
|:---|:---|:---|:---|
| MSMED interest direction | `0.45` | Accrued MSMED interest rose YoY | pre-event **6/8**, controls **0/7** |
| Not Due → overdue migration | `0.25` | Overdue share rose **> +20 pp** | 18 no-event transitions top out at **+15.5 pp** |
| Payables ÷ revenue | `0.20` | Ratio rose YoY | distress **+4.0/+5.2 pp**, controls **−1.8/−2.2 pp** |
| Non-MSME ageing growth | `0.10` | Aged non-MSME buckets grew | fallback where the MSME book is immaterial |

```python
weight_total = sum(RUNG_WEIGHTS[rung] for rung in values)
raw = sum(RUNG_WEIGHTS[rung] / weight_total * value for rung, value in sorted(values.items()))
```

A rung whose inputs are absent is dropped from the denominator, never defaulted — so a filer disclosing only rung 1 scores on rung 1 at full weight (`0.45/0.45 = 1.0`). Fewer than two comparable years gives `0.0`.

**Retired:** MSME balance growth. Control Bharat Gears posted **+629%** in a year CARE *upgraded* it, against distress case Nectar's **+583%**. Does not discriminate.

### 2. Contagion — stress travels against goods flow

```
received(s)  = 0.75 × (1 − buffer_strength(s)) × Σ_buyers fragility(b) × exposure_pct(s→b)
fragility(s) = min(1.0, own_stress(s) + received(s))
buffer_strength(days) = min(days / 90, 0.35)
```

`DAMPING = 0.75` per hop. Converges at `Δ < 0.001`, typically 4–5 iterations, capped at 10. Cycles are expected — damping guarantees convergence, so no topological sort.

The buffer cap was `0.9`, a **10× per-hop swing**. Collection measured `cash_buffer_days` across 44 company-years and got **AUC 0.569** against a 0.500 coin flip — so it was cut to `0.35`, a **1.54× swing**. It nudges; it does not decide.

### 3. Criticality — the normalisation is the argument

|  | Tier-1 hub | Sole-source Tier-2 chokepoint |
|:---|:---|:---|
| Betweenness, network-wide | **0.875** | 0.137 |
| Flow share, network-wide | **1.000** | 0.012 |
| Criticality, **within tier** | — | **0.475** vs a replaceable peer's **0.178** |

Network-wide normalisation makes `0.65` of criticality a proxy for revenue and buries the supplier the product exists to find. Within tier: **2.7× separation**. Undisclosed sole-source status drops the term and renormalises.

### 4. Ranking — fragile × irreplaceable

`critical ≥ 0.20` · `high 0.06–0.20` · `watch 0.012–0.06` · `stable < 0.012`

Thresholds are calibrated to the distribution this model produces at seed 42, not to a claim about the world. What carries meaning is the ordering: **0.204 against 0.090, a 2.3× gap.**

|  | `N042` Sealsworks | `N203` Kalyani Fastener |
|:---|:---|:---|
| Dependency on the trigger | 78% | 61% |
| Cash buffer | 18 days | 34 days |
| Suppliers routing through it | 6 | **12 — better connected** |
| Sole source? | **Yes** | No |
| Fragility × Criticality | 0.3498 × **0.5838** | 0.2230 × 0.4034 |
| **Final score** | **0.2042** | **0.0900** |

`N203` is the more central node and still ranks second. Well connected is not the same as irreplaceable.

### 5. Disruption — the chain, backwards

```
seed(n)       = max(0.0, fragility(n) − own_stress(n))
disruption(b) = 1 − Π_suppliers (1 − halt(s) × supply_impact(s→b))
halt(n)       = 1 − (1 − seed(n)) × (1 − disruption(n))
```

Halt risk is seeded by the fragility a node did **not** generate itself — a company stretching its own payables is conserving cash, not stopping its line. Noisy-OR because a line stops if *any* unreplaceable input stops; it is bounded in `[0,1]` by construction and needs no invented cap. Own bands: `0.20 / 0.06 / 0.012`.

### 6. Intervention — the counterfactual

```
cost(n)     = (Σ annual_value_cr(n → buyers) / 4) × fragility(n)
exposure(n) = value_through(n) × (3 / 12) × final_score(n)
```

`value_through` counts each edge on a path to an anchor **exactly once** — enumerating paths would double-count shared edges and is unbounded on a cyclic graph. `DISRUPTION_MONTHS = 3` is a stated assumption.

**Mock network, seed 42:** 15 ranked at risk · **₹16.54 cr** to stabilise all · **₹738.18 cr** exposed if nobody moves. Funding `N042` with **₹2.04 cr** takes it `critical → stable`, carries `N118` `high → stable`, and drains anchor supply risk from **₹848.96 cr to ₹308.36 cr**.

### 7. Triage — because `0.35 × 0.20` and `0.10 × 0.70` are the opposite decision

| Queue | Condition | Response |
|:---|:---|:---|
| `fund_now` | `fragility ≥ 0.10` **and** `criticality ≥ 0.30` | Commit capital |
| `derisk` | `fragility ≥ 0.10`, `criticality < 0.30` | Watch, second-source, hold the money |
| `monitor` | `fragility ≥ 0.02` | Watchlist until the next filing |
| `clear` | below both | No response |

`0.10` is the top ~4% of network fragility (p90 0.0465, p99 0.2083); `0.30` is the top decile of within-tier criticality (p90 0.2974). Splits the at-risk population **6 to fund / 11 to watch** — 6 of which never reach the ranked list, because `final_score` multiplies their replaceability away.

### 8. Allocation — where ₹5 crore actually goes

The objective is the anchor's own exposure, `Σ disrupted_inflow_cr` across tier-0. Each of the top 8 candidates is probed independently, ranked by **₹ of anchor exposure removed per ₹ committed**, committed greedily, then re-scored **jointly** — independent probes double-count shared chains, so every reported figure comes from the joint run.

| Budget | Committed | Suppliers | Anchor exposure removed |
|:---|:---|:---|:---|
| ₹1 cr | ₹1.00 cr | 2 | ₹359 cr |
| ₹5 cr | ₹5.00 cr | 5 | ₹914 cr |
| ₹25 cr | ₹14.44 cr | 8 | ₹1,224 cr |

Past ₹14.44 cr nobody in the pool is worth funding; the rest is reported **unallocated** rather than sprinkled.

---

### The line we do not cross

Two rules, enforced by tests rather than by care:

- **No sole-source claim against a real company.** Chokepoints are confined to synthetic buyers. All 43 real companies carry undisclosed status — not one filing made a sole-sourcing statement — so not one is offered a substitute either.
- **No generated rupee figure beside a real name.** Undisclosed fields carry `null` and name themselves in `substituted`, keeping the runtime fill a visible modelling decision.

> **Quote the mock network for rupee-for-rupee figures, and the real network for the mechanism.** 13 of the 30 real edges carry no disclosed `annual_value_cr`, so exposure understates on real data — the deliberate cost of the rule above.

**Real dataset (298 nodes, 43 real filers):** Hero MotoCorp Limited, a real tier-0 anchor, reaches `critical` supply disruption at **0.2089**, **₹37.94 cr** of inbound supply at risk, stopped by Shivam Autotech Limited — whose stress comes from its own MSMED disclosures.

---

## 🎯 Key Features

- ✅ **Four-Rung Stress Ladder Over Statutory Filings:** Detects payment stress from MSMED interest direction, Not Due → overdue migration, payables-to-revenue drift and non-MSME ageing growth, with weights renormalised over whatever a filer actually disclosed — and no rung ever substituted with a default.
- ✅ **Bidirectional Contagion Model:** Two propagation passes in opposite directions — cash stress travelling buyer → supplier, supply disruption travelling supplier → buyer — because that is genuinely how the failure mechanism works.
- ✅ **Within-Tier Criticality Normalisation:** The single change that makes the product work. Comparing a supplier against its own tier instead of against the whole network produces a **2.7× separation** between a genuine sole-source chokepoint and a comparably stressed replaceable peer.
- ✅ **Fragile × Irreplaceable Ranking:** A multiplicative score that discards robust chokepoints and replaceable weaklings alike, surfacing only the intersection — 15 names out of 412, each with a template-generated plain-English reason.
- ✅ **Costed Counterfactual:** Re-scores the entire network with a supplier funded and with the funding removed, both as real engine runs. ₹2.04 cr into one Tier-2 supplier drains the anchor's supply risk from ₹848.96 cr to ₹308.36 cr.
- ✅ **Two-Factor Triage:** Splits at-risk suppliers into `fund_now` and `derisk` on fragility and criticality *separately*, because the product of the two destroys the distinction between "commit capital" and "hold capital contingent and second-source".
- ✅ **Budget Allocation Optimiser:** Spreads a finite sum by rupees-of-anchor-exposure-removed per rupee committed, re-scores the committed set jointly, and reports what it could not spend rather than sprinkling it.
- ✅ **Substitution Candidates:** Reads the criticality model on its low side to suggest up to three replacements scored on health (0.60) and spare within-tier capacity (0.40) — and refuses to suggest any where sole-source status is merely *undisclosed*.
- ✅ **Live Document Ingestion:** A zip of collection CSVs becomes a scored multi-tier graph in one server-side pass, hardened against zip bombs by caps checked before anything is written to disk.
- ✅ **Engine-Driven Cascade Animation:** Replays the `propagation_depth` the engine actually assigned to each node, in order. It does not stage a fixed sequence on a timer, and the frontend computes no risk figure anywhere.
- ✅ **Byte-Identical Determinism:** Fixed seeds, fixed generation timestamps, sorted iteration throughout, and no floating-point comparison without a named threshold — verified by script for scoring, mock generation and the CSV transform.
- ✅ **Row-Level Provenance:** Every node and edge names its `data_source`, every runtime fill is listed in `substituted`, and two integrity rules about real companies are enforced by tests rather than by good intentions.
- ✅ **Offline-Identical Frontend:** `npm run dev` (committed mocks, backend off) and `npm run dev:live` (live API) return identical figures, guaranteed by `scripts/refresh_web_mocks.py` — so a dead network on demo day costs nothing.

---

## 🚫 Deliberately Not Built

Machine learning, blockchain, authentication, runtime document parsing inside the scoring path, streaming, mobile, database servers, and LLM calls at runtime. A reason for each is recorded in `AGENTS.md` §1.2, and reason strings throughout the product are template-generated and deterministic.

The one exception is documented as an exception: document upload was on the ruled-out list and was moved off it deliberately, not drifted into, because the hackathon judges asked to see the multi-level graph built live from uploaded source documents. That is the reason, and it is the only reason.

---

## 📁 Repository Layout

```
engine/     the model — graph, stress, contagion, criticality, ranking,
            intervention, disruption, triage, substitution, allocation,
            plus mockgen, ingest and the CSV transform
api/        FastAPI, seven endpoints, stateless
web/        React + TypeScript console, force-directed canvas, live build page
data/       mock network, demo fixture, real collection CSVs + data dictionary
scripts/    demo runner, determinism check, latency check, preflight, mock refresh
tests/      204 tests across all three tracks
```

| Contract | What it governs |
|:---|:---|
| `AGENTS.md` | Rules every contributor follows — determinism, ownership, git discipline, the do-not-build list |
| `SCHEMA.md` + `schema.json` | The frozen contract between the three tracks |
| `DEMO_SCENARIO.md` | The canonical demo, with fixed node IDs and a written stage-failure recovery |
| `data/real/DATA_DICTIONARY.md` | Field-level definitions and the real-versus-synthetic integrity rules |
| `docs/PERSON_A/B/C.md` | Per-track briefs |

---

<p align="center">
  <strong>Stress flows down the chain as invoices that were never paid.<br>Failure flows back up it as parts that never arrived.</strong><br>
  Built with ⚡ by Team TechNix
</p>
