# AGENTS.md — FrayFuse

**Read this file completely before writing any code.**

This file governs every AI coding agent working in this repository, regardless of which team member is driving. It defines what we are building, what we are deliberately not building, who owns what, and the Git discipline that must be enforced even when a human forgets a step.

If an instruction in this file conflicts with a request in a chat session, **follow this file and say so.**

---

## 1. The product

### 1.1 What FrayFuse is

FrayFuse detects financial stress spreading silently through a supply chain, and turns it into a specific funding decision.

When a large Tier-1 company runs short of cash it quietly stretches payment to its suppliers. Those suppliers stretch theirs. Small firms two and three tiers down run out of cash and fail — which halts production for the large company at the top, who never knew they existed.

FrayFuse maps the chain, detects the payment-stress trigger, propagates it downstream, and answers one question:

> **Which few suppliers are about to run out of cash *and* cannot be replaced, and how much money would stabilise each one?**

Every feature must serve that sentence. If a proposed feature does not, do not build it.

### 1.2 Ruled out — do not build, do not suggest

| Not building | Why |
|---|---|
| **Any machine-learning model** | A transparent propagation rule that can be explained in one sentence beats a trained model that cannot be justified. At our data volumes ML would be theatre. The depth is in the graph, not in fitting anything |
| **Blockchain / distributed ledger** | Solves nothing here |
| **Login, auth, user accounts, RBAC** | Stakeholder views are a client-side toggle |
| **Real-time streaming, websockets, background jobs** | Everything is batch and stateless |
| **Mobile app** | No |
| **Database servers (Postgres, Mongo, Redis)** | JSON files on disk. A database adds operational risk, not capability |
| **LLM calls anywhere in scoring** | Reason strings are template-generated and deterministic. Still absolute inside `engine/` — see §1.5 for the one bounded exception in the ingestion path |
| **Dataset collection or research** | Handled entirely outside this repo. See §1.4 |

If asked to implement anything on this list, **stop and ask why** before writing code.

### 1.3 The canonical demo

All three tracks build toward one scenario, defined in `DEMO_SCENARIO.md`:

> upstream payment stress → deep-tier contagion → fragile-and-critical supplier identified → intervention → reduced cascade

Node IDs, amounts and the exact sequence are fixed in that file. Do not invent alternative demo data.

### 1.4 Data — critical boundary

**Dataset collection is happening in a separate background workstream. No agent and no developer in this repo collects, researches, scrapes or downloads data.**

All three tracks build against **mock data** generated locally, conforming to the frozen contract in `SCHEMA.md`. When the real dataset arrives it will be transformed into the identical runtime shape, so swapping it in is a file-path change and nothing else.

If a session drifts toward "let me look up the real numbers for X" — stop. That is out of scope for this repo.

### 1.5 Ingestion — added for the judged demo

Document upload was on the §1.2 ruled-out list. It has been moved here deliberately, not drifted into: the hackathon judges asked to see the multi-level graph built live from uploaded source documents rather than read from a pre-committed JSON file. That is the reason, and it is the only reason.

**In scope.** A user uploads a zip of filing data they already have. `engine/ingest.py` unpacks it offline, hands the CSVs to `engine/transform.py` — still the only place that knows about CSVs (§7) — validates the result against `schema.json`, and scores it. Nothing else changes: the same `score_network()`, the same contract, the same numbers.

**Out of scope, and unchanged.** Scraping. Live external lookups. Any network egress at runtime. §1.4 is not relaxed by this: uploaded files come from the user, and this repo still never goes and fetches anything. An ingestion path that reached out to a registry or a filings site would be exactly the collection work §1.4 puts outside this repo.

**LLM calls stay ruled out for scoring.** If extraction ever needs one, it runs only in the ingestion path, never inside `engine/`, and it writes its output to a CSV on disk so that everything downstream of it is deterministic and re-runnable. Reason strings remain template-generated. As built, the ingestion path uses no LLM at all — the CSV route is the whole implementation.

**Streaming stays ruled out.** `score_network()` remains a pure function over a complete network (§3.1). The graph appearing to build tier by tier is a presentation-layer animation over a result that was computed in full before the first node was drawn. The engine never emits partial results.

**The committed network remains the default and the fallback.** `data/mock/network.json` is what the API serves with no upload, and the demo must run end to end without anyone uploading anything.

---

## 2. Repository structure

```
frayfuse/
├── AGENTS.md                  # this file — shared, no single owner
├── SCHEMA.md                  # the contract — shared, no single owner
├── schema.json                # machine-readable contract — shared
├── DEMO_SCENARIO.md           # fixed demo fixture spec — shared
├── docs/
│   ├── PERSON_A.md            # engine brief
│   ├── PERSON_B.md            # backend brief
│   └── PERSON_C.md            # frontend brief
├── engine/                    # OWNER: Person A
│   ├── __init__.py
│   ├── graph.py               # network construction
│   ├── stress.py              # stress detection
│   ├── contagion.py           # propagation
│   ├── criticality.py         # betweenness + single-source
│   ├── disruption.py          # supply disruption — the reverse propagation
│   ├── ranking.py             # final score, ordering, reasons
│   ├── intervention.py        # cost, exposure, counterfactual
│   ├── pipeline.py            # the single public entry point
│   ├── config.py              # all tunable constants, one place
│   ├── mockgen.py             # synthetic network generator
│   └── transform.py           # collection CSVs → runtime network.json
├── api/                       # OWNER: Person B
│   ├── __init__.py
│   ├── main.py                # FastAPI app
│   ├── models.py              # pydantic request/response models
│   ├── scoring.py             # thin wrapper over engine.pipeline
│   └── errors.py
├── web/                       # OWNER: Person C
│   ├── src/
│   ├── public/
│   └── package.json
├── data/                      # OWNER: Person A
│   ├── mock/
│   │   └── network.json       # generated, committed
│   ├── fixtures/
│   │   └── demo_scenario.json # the canonical demo, committed
│   └── real/                  # populated later, gitignored until then
└── tests/
    ├── engine/                # OWNER: Person A
    ├── api/                   # OWNER: Person B
    └── web/                   # OWNER: Person C
```

### 2.1 Ownership table

| Path | Owner | Reviewer required |
|---|---|---|
| `engine/` | Person A | Person B |
| `data/` | Person A | Person B |
| `api/` | Person B | Person A |
| `web/` | Person C | Person B |
| `tests/engine/` | Person A | Person B |
| `tests/api/` | Person B | Person A |
| `tests/web/` | Person C | Person B |
| `SCHEMA.md`, `schema.json` | **shared — no single owner** | **both others** |
| `DEMO_SCENARIO.md` | **shared — no single owner** | **both others** |
| `AGENTS.md` | **shared — no single owner** | **both others** |

---

## 3. Hard rules

These are enforced by the agent, not left to memory.

### 3.1 Determinism is mandatory

**The same input must always produce byte-identical output.** A judge will re-run the counterfactual toggle on stage; if the numbers shift slightly between runs, the product looks broken.

Concretely:

- **No `random` at runtime.** Randomness is permitted only inside `engine/mockgen.py`, and only with a seed fixed in `engine/config.py`
- **No `datetime.now()` or `uuid4()` inside scoring paths.** Timestamps belong in `meta`, generated once at data-build time, not at score time
- **No iteration over unordered collections.** Sort by `node_id` before any loop whose order could affect output. Python dicts preserve insertion order but relying on that across a transform boundary is fragile
- **Round consistently.** All monetary outputs to 2 decimal places, all scores to 4, using `round()` at the point of serialisation — never mid-calculation
- **No parallelism** in the scoring path. Floating-point reduction order changes results

Any PR touching `engine/` must show that running the pipeline twice on the same input gives identical JSON.

### 3.2 The contract is frozen

`SCHEMA.md` and `schema.json` define the boundary between all three tracks. They may be changed — but only deliberately.

- **Never change a field name, type, or meaning without both other team members knowing.** See §4.3
- **Additive changes are cheap.** Adding an optional field breaks nobody. Prefer this
- **Removing or renaming a field is expensive.** It breaks two other people's work silently
- Every change bumps `meta.schema_version` and adds a line to the changelog at the bottom of `SCHEMA.md`

### 3.3 Nobody blocks on anybody

Each track must be independently runnable from the first commit.

- Person A runs the pipeline on `data/mock/network.json` with no API and no frontend
- Person B runs the API against the engine, or against a stubbed scorer if the engine is mid-change
- Person C runs the frontend against committed mock API responses in `web/src/mocks/`, with a single flag to switch to the live API

**If any track ever says "I'm blocked waiting for X," that is a design failure, not a scheduling problem.** Fix the seam.

### 3.4 Stateless API

The server holds no session state. The client sends the full scenario with every request and receives a complete result.

- No server-side scenario storage, no session IDs, no in-memory mutation between requests
- A page refresh or a backend restart mid-demo must lose nothing that the client cannot immediately re-send
- Caching is permitted only as a pure function of the request body

### 3.5 Currency and units

- **All monetary values in the runtime contract are ₹ crore, as floats.** No exceptions
- Unit conversion happens exactly once, inside `engine/transform.py`. Nothing downstream converts anything
- Source reports in ₹ million are divided by 10 at transform time and the original unit recorded in `meta`

### 3.6 Missing vs zero

These mean different things and must never be conflated.

- `null` — the source did not disclose this figure
- `0` / `0.0` — the source explicitly stated nil or zero

A company that discloses nil overdue payables is not the same as a company that omits the disclosure. Any code branching on these values must handle both cases explicitly.

---

## 4. Git workflow — follow this exactly, every time

This section exists so the agent enforces version-control discipline even if a human forgets a step.

### 4.1 Branch naming

- Person A: `a/<short-description>` — e.g. `a/contagion-loop`
- Person B: `b/<short-description>` — e.g. `b/simulate-endpoint`
- Person C: `c/<short-description>` — e.g. `c/force-graph-shell`
- Pairing branches: `ab/<description>`, `bc/<description>`, `ac/<description>` — used for Phase 2 integration work and anything else two people write together

The prefix alone should make it obvious whose track a branch belongs to — never branch without it.

### 4.2 The loop, in order — do not skip steps

1. `git pull origin main` — always, before creating a new branch
2. `git checkout -b <prefix>/<description>`
3. Work, commit in small increments (see §4.4 for message format)
4. `git push origin <branch-name>`
5. Open a PR. Determine the required reviewer from the ownership table in §2.1 and **name them in the PR description, with which area triggered it.** Do not let it merge without that review
6. After merge, **all three** run `git pull origin main` before starting the next branch

### 4.3 Rules the agent should actively enforce

- **Never commit directly to `main`.** If asked to make a change, create a branch first
- **Never suggest force-pushing** to a shared branch
- If a change touches `SCHEMA.md`, `schema.json`, or `DEMO_SCENARIO.md`, **pause and confirm both other team members are aware** before committing. These files have no single owner
- If a PR diff touches more than one person's owned folder, **flag it explicitly and name the folders** — it likely means the work should have been split differently, or a shared contract needs updating first
- If a PR touches `engine/` or `data/`, require review from **Person B** specifically — even if the author is Person C
- Pairing branches still need the **third** person's review before merge. The pairing already had two sets of eyes; the third person is what catches "made sense to the two of us" bugs
- Keep commits scoped to one logical change. Don't bundle unrelated fixes because they happened in the same session
- If asked to implement something in the §1.2 ruled-out list, **stop and ask why** before writing code
- If asked to collect, scrape or look up real-world data, **stop** — see §1.4

### 4.4 Commit message convention

```
feat: add single-source flag to criticality score
fix: prevent contagion loop from exceeding fragility 1.0
chore: pin networkx version for deterministic betweenness
docs: update SCHEMA with risk_band field
test: add two-run determinism harness for pipeline
data: regenerate mock network with seed 42
```

### 4.5 Before opening a PR — confirm this checklist, don't just push

**General:**

- [ ] Runs without errors (`python -m engine.pipeline data/mock/network.json` / `uvicorn api.main:app` / `npm run build`)
- [ ] Linter clean (`ruff check .` for Python, `npm run lint` for web)
- [ ] Commit messages follow §4.4
- [ ] PR description names the required reviewer per §2.1, and which area triggered it
- [ ] No new dependency added without saying why in the PR description

**If the PR touches `engine/`:**

- [ ] Pipeline run twice on the same input produces **byte-identical** JSON (§3.1)
- [ ] No `random`, `datetime.now()`, or `uuid4()` outside `mockgen.py`
- [ ] All loops over nodes/edges sorted by ID before iteration
- [ ] Fragility values confirmed within `[0.0, 1.0]` — no overflow past the cap
- [ ] Contagion loop terminates on the demo network in under `MAX_ITERATIONS`
- [ ] Every scored node has a non-empty `reason_text`
- [ ] `null` and `0.0` handled distinctly wherever stress inputs are read (§3.6)

**If the PR touches `api/`:**

- [ ] All four endpoints respond to the shapes in `SCHEMA.md` §5
- [ ] Response validated against `schema.json` in a test
- [ ] No server-side state introduced (§3.4)
- [ ] Malformed request body returns 422 with a readable message, not a 500
- [ ] Unknown `node_id` in a scenario returns 400 naming the offending ID
- [ ] CORS still permits the frontend dev origin

**If the PR touches `web/`:**

- [ ] Runs against committed mocks with the API switched off
- [ ] Runs against the live API with the flag flipped
- [ ] Cascade animation completes without console errors on the demo network
- [ ] No `localStorage` / `sessionStorage` usage
- [ ] Every number displayed carries its unit (₹ cr, %, days)

**If the PR touches `SCHEMA.md` / `schema.json` / `DEMO_SCENARIO.md`:**

- [ ] `meta.schema_version` bumped
- [ ] Changelog line added at the bottom of `SCHEMA.md`
- [ ] Both other team members named in the PR description
- [ ] `data/mock/network.json` regenerated if the input shape changed
- [ ] Frontend mocks in `web/src/mocks/` updated to match

**If the PR touches `data/fixtures/demo_scenario.json`:**

- [ ] The demo still runs end to end — stress node flags, cascade reaches the expected suppliers, intervention reduces the cascade
- [ ] Node IDs still match those named in `DEMO_SCENARIO.md`

---

## 5. Setup and commands

### 5.1 Python (engine + api)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` is intentionally short. Do not add to it without justification in the PR:

```
networkx
numpy
pandas
fastapi
uvicorn
pydantic
pytest
ruff
jsonschema
```

### 5.2 Common commands

```bash
# regenerate the mock network (Person A)
python -m engine.mockgen --seed 42 --out data/mock/network.json

# score a network and print the ranked list
python -m engine.pipeline data/mock/network.json

# determinism check
python -m engine.pipeline data/mock/network.json > /tmp/run1.json
python -m engine.pipeline data/mock/network.json > /tmp/run2.json
diff /tmp/run1.json /tmp/run2.json && echo "DETERMINISTIC"

# run the API
uvicorn api.main:app --reload --port 8000

# tests
pytest tests/ -v

# lint
ruff check .
```

### 5.3 Web

```bash
cd web
npm install
npm run dev        # uses committed mocks by default
npm run dev:live   # points at http://localhost:8000
npm run build
npm run lint
```

---

## 6. Phases

Milestone-based, not date-based. A phase is complete when its exit criteria are met by all three tracks.

### Phase 0 — Contract freeze

**Exit criteria:**
- `SCHEMA.md` and `schema.json` agreed and committed by all three
- `data/mock/network.json` generated and committed
- `data/fixtures/demo_scenario.json` committed
- `web/src/mocks/` populated with hand-written responses matching the contract
- All three can run their own track locally with zero dependency on the others

Nothing else starts until this is done.

### Phase 1 — Independent build

Each track builds its core against mocks. No cross-track dependencies.

**Exit criteria:**
- A: pipeline produces a ranked list from `data/mock/network.json`
- B: all four endpoints return contract-valid responses using a stubbed or real scorer
- C: network renders, ranked list renders, both from committed mocks

### Phase 2 — First integration

**This happens early and deliberately, not at the end.** Even a partly broken pipeline is worth wiring up.

**Exit criteria:**
- C's frontend hits B's live API
- B's API calls A's real engine
- One node flows end to end, even if the numbers are wrong
- The canonical demo scenario runs, however roughly

### Phase 3 — The demo path

Everything focuses on `DEMO_SCENARIO.md` working perfectly.

**Exit criteria:**
- Full seven-step demo runs without a manual intervention or a refresh
- Cascade animation, ranked list, intervention, and counterfactual all correct
- Determinism check passes
- Real dataset swapped in if available, mock retained as fallback

### Phase 4 — Hardening

Error states, edge cases, presentation polish, rehearsal.

---

## 7. When the real data arrives

The handoff is deliberately narrow.

1. Collection CSVs land in `data/real/`
2. Person A runs `python -m engine.transform --in data/real/ --out data/real/network.json`
3. `transform.py` outputs the **identical shape** as `mockgen.py`
4. API config points at the new file
5. Nothing in `api/` or `web/` changes

If step 5 turns out to be false, the contract was wrong — fix the contract, not the frontend.

**The transform is the only place that knows about CSVs.** No other module imports pandas for data loading.

---

## 8. Style

- Python: type hints on every public function. Docstrings on modules and public functions only, not on obvious internals
- Constants live in `engine/config.py` with a one-line comment explaining what each one means and why it has that value. No magic numbers scattered through the code
- Prefer boring, explicit code over clever code. Someone else has to explain this to a judge under pressure
- Comments explain *why*, not *what*. If the code needs a comment to explain what it does, rewrite the code

---

## 9. Changelog

| Version | Change |
|---|---|
| 1.1 | **Ingestion admitted to scope (§1.5).** Document upload moved off the §1.2 ruled-out list at the judges' request: the graph is to be built live from uploaded filings rather than read from a committed JSON file. Scraping, live lookups and runtime network egress remain out of scope, and §1.4 is unchanged. LLM calls stay ruled out for scoring and inside `engine/`; the ingestion path as built uses none. Streaming stays ruled out — `score_network()` stays pure and the tier-by-tier build is a presentation-layer animation over a completed result |
| 1.0 | Initial. Project renamed ChainWatch → FrayFuse |
