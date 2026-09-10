# Implementation brief: substitution candidates + live network build from uploaded filings

You are working in the FrayFuse repository (supply-chain financial stress detection, hackathon
project). Read `AGENTS.md` **completely** before writing any code, then read `SCHEMA.md`,
`docs/PERSON_A.md`, `docs/PERSON_B.md` and `docs/PERSON_C.md`. This brief assumes you have.

You are implementing two features. They are independent — build them on separate branches and
open separate PRs. Do not bundle them.

---

## 0. Governance — read this first, it overrides your default reflex

### 0.1 A deliberate scope change to AGENTS.md is part of this work

`AGENTS.md` §1.2 currently lists as ruled-out:

- "Document upload, OCR, PDF parsing at runtime"
- "LLM calls at runtime"
- "Real-time streaming, websockets, background jobs"

Feature 2 requires the first, optionally the second, and touches the third. §4.3 tells you to stop
and ask why before implementing anything on that list. **You are being told why now, in advance:**
the hackathon judges asked to see the multi-level graph constructed live from uploaded source
documents rather than from a pre-committed JSON file. That is a deliberate, sanctioned scope
change, not drift.

Therefore, as the **first commit of the feature-2 branch**, amend `AGENTS.md`:

- Move "Document upload, OCR, PDF parsing at runtime" out of the §1.2 ruled-out table and into a
  new subsection §1.5 "Ingestion — added for the judged demo", stating precisely what is now in
  scope (offline zip upload of pre-collected filing CSVs/PDFs → schema → scored network) and what
  remains out of scope (scraping, live external lookups, any network egress at runtime).
- Keep "LLM calls at runtime" ruled out **for scoring**. If you use an LLM for extraction, it runs
  only in the ingestion path and never inside `engine/`. Reason strings stay template-generated and
  deterministic. Say this explicitly in §1.5.
- Add a changelog row in §9.
- Do **not** relax §1.4 (no data collection/scraping in this repo). Uploaded files come from the
  user; the repo still never goes and fetches anything.

If you find yourself about to violate any other AGENTS.md rule, stop and surface it instead of
quietly proceeding.

### 0.2 Commit and PR discipline

- Follow the git loop in `AGENTS.md` §4.2 exactly. Never commit to `main`.
- Branch names: feature 1 → `a/substitution-candidates`. Feature 2 → `ab/live-ingestion`
  (it spans `engine/` and `api/`, which is a pairing branch per §4.1).
- Commit messages follow §4.4 (`feat:`, `fix:`, `test:`, `docs:`, `data:`, `chore:`).
- **Do not add any `Co-Authored-By` trailer to any commit. Do not add any "Generated with" line to
  commit messages or PR descriptions. No AI attribution anywhere in git history.**
- Work in small commits. One logical change each.
- Before opening each PR, walk the §4.5 checklist that applies to the folders you touched and state
  in the PR description that you did, including the two-run byte-identical determinism check if you
  touched `engine/`.
- Name the required reviewer per the §2.1 ownership table.

### 0.3 Non-negotiable engineering rules that will bite you

- **Determinism (§3.1).** No `random`, `datetime.now()`, `uuid4()` in any scoring path. Sort by
  `node_id` before every loop whose order could affect output. Round monetary values to 2 places
  and scores to 4, at serialisation only. No parallelism in scoring.
- **null vs zero (§3.6).** `null` means undisclosed; `0.0` means disclosed as nil. Never coerce one
  to the other. This matters enormously in both features — see how `engine/criticality.py`
  `_single_source_status` returns `None` versus `0.0` and renormalises weights around the missing
  term. Mirror that discipline.
- **Currency (§3.5).** All money is ₹ crore as floats. Conversion happens once, at transform time.
- **Schema changes (§3.2, §4.3).** Additive only. Bump `meta.schema_version`, add a `SCHEMA.md`
  changelog line, update `schema.json`, update `web/src/v2/types.ts`, and regenerate the frontend
  mocks in `web/src/mocks/` via `scripts/refresh_web_mocks.py`.
- **Stateless API (§3.4).** No session state, no server-side scenario storage.
- Type hints on every public function. Constants go in `engine/config.py` with a one-line comment
  explaining what the value means and why it has that value — no magic numbers inline.
- Comments explain *why*, not *what*.

---

## FEATURE 1 — Intra-graph substitution candidates

Branch: `a/substitution-candidates`

### 1.1 The product question

The ranked list currently answers "which suppliers are fragile AND irreplaceable." For nodes at the
*other* end of the criticality distribution — replaceable ones — the useful answer is different:
"you could switch away from this one, and here is who could take the volume."

This is not a new concept bolted on. `engine/criticality.py` already computes exactly the signal
that decides eligibility. You are reading the existing model on its low side.

### 1.2 Where the logic lives

New module: `engine/substitution.py`. Owner is Person A (`engine/`), reviewer Person B.

Do **not** put this logic in `ranking.py`. `ranking.py` composes scores and reasons; substitution is
a distinct question with its own inputs. Follow the existing module shape — a frozen dataclass for
the per-node detail, one public `compute_*` function taking the graph, returning a dict keyed by
`node_id`, sorted iteration throughout.

### 1.3 Eligibility

A node is eligible for substitution suggestions when **all** of:

1. Its `criticality` is at or below a new threshold constant, `SUBSTITUTION_CRITICALITY_MAX`, added
   to `engine/config.py` under the Criticality section with a comment justifying the value from the
   observed distribution (read the existing comments around `BAND_CRITICAL` for the tone — calibrate
   to what the model actually produces on `data/mock/network.json` at seed 42, and *say* that it is a
   calibration to an observed distribution, not a claim about the world). Start by actually measuring
   the criticality distribution before picking the number.
2. It is **not** a confirmed sole source for anything — i.e. `CriticalityDetail.single_source` is
   `0.0`. Note the null case carefully: `single_source is None` means *undisclosed*, which is not
   permission to declare the supplier replaceable. Treat `None` as **not eligible** and explain in
   the module docstring that asserting replaceability on absent evidence would be the same error
   §3.6 exists to prevent.
3. It has at least one outgoing edge (it actually supplies something).

### 1.4 Finding candidates

For each eligible supplier `S` and each of its outgoing edges `S -> B` carrying `component` `C`:

Candidate pool = other nodes `X` where:
- `X != S`
- `X` sits at the **same tier** as `S` (`graph.nodes[X]["tier"] == graph.nodes[S]["tier"]`)
- `X` has at least one outgoing edge whose `component == C` (it demonstrably makes this part)
- `X` does not already supply `B` with `C` (no duplicate relationship — check existing edges)

Rank candidates by a **substitution fitness** score, composed of two terms with weights in
`config.py` (`W_SUB_HEALTH`, `W_SUB_CAPACITY`, summing to 1.0):

- **Health term** = `1.0 - fragility[X]`. A replacement that is itself about to fail is not a
  replacement. Use the post-intervention `contagion.fragility`, the same values `ranking.py` scores
  on, so a funded supplier correctly becomes a better substitution candidate.
- **Capacity term** = a normalised measure of `X`'s headroom to absorb the volume on edge `S -> B`.
  Compute it from data you already have: `X`'s total outgoing `annual_value_cr` relative to its
  `revenue_cr`, giving remaining revenue headroom, then compare that headroom against the
  `annual_value_cr` of the edge being replaced. Normalise **within tier**, for exactly the reason
  documented at the top of `engine/criticality.py` — raw value is size-correlated and a network-wide
  max hands it to the largest node. Reuse or mirror `_normalise_within_peer_group`.

Handle `revenue_cr is None` explicitly (real nodes often lack it): drop the capacity term for that
candidate and renormalise the remaining weight onto the health term, exactly as
`compute_criticality` drops the sole-source term. Do not substitute a default revenue.

Cap the number of suggestions per node at `SUBSTITUTION_MAX_CANDIDATES` (config constant, suggest 3).
Ties break by `node_id` ascending. Deterministic ordering is mandatory.

### 1.5 Output shape — additive schema change

Add an optional field to each `Score` object:

```json
"substitution_candidates": [
  {
    "node_id": "N214",
    "name": "Rathi Precision Components Pvt Ltd",
    "component": "sheet_metal",
    "replaces_edge_id": "E0912",
    "fitness": 0.7431,
    "fragility": 0.0210,
    "capacity_headroom_cr": 18.40,
    "reason_text": "Same tier, supplies sheet metal to two other buyers, ₹18.40 cr of unused revenue headroom, and carries no inherited stress."
  }
]
```

Rules:
- The field is **absent or an empty list** for non-eligible nodes. Absent means "we did not look";
  empty list means "we looked and found nobody." Pick one convention, document it in `SCHEMA.md`,
  and be consistent — this is a §3.6-shaped distinction and reviewers will check it.
- `reason_text` is **template-generated and deterministic**, like `_compose_reason` in `ranking.py`.
  No LLM. Read `_compose_reason` and `_compose_disruption_reason` and match their construction style
  and tone.
- `capacity_headroom_cr` rounds to 2, `fitness` and `fragility` to 4.

Wire it in `engine/pipeline.py` inside `score_network()`, after criticality and contagion are
computed, and attach to the score objects in `ranking.build_scores` (pass the substitution result in
as a parameter — do not have `ranking.py` import and call `substitution.py` itself; keep the
orchestration in `pipeline.py` where it already lives).

Then propagate the contract change: `schema.json`, `SCHEMA.md` (+ changelog + version bump),
`api/models.py`, `web/src/v2/types.ts`, and regenerate `web/src/mocks/` with
`scripts/refresh_web_mocks.py`.

### 1.6 Tests

New file `tests/engine/test_substitution.py`, matching the style of the existing engine tests:

- A high-criticality node yields no candidates.
- A confirmed sole-source node yields no candidates even if criticality is low.
- A node whose `single_source` is `None` (undisclosed) yields no candidates — assert this explicitly
  with a comment naming AGENTS.md §3.6.
- Candidates are same-tier and same-component only.
- A candidate already supplying that buyer is excluded.
- A fragile candidate ranks below a healthy one.
- A candidate with `revenue_cr is None` still scores, on the health term alone.
- Ordering is deterministic across two runs.
- Every candidate carries a non-empty `reason_text`.

Also extend the determinism harness in `tests/engine/test_pipeline.py` if it enumerates score fields.

### 1.7 Frontend surface

Owner Person C (`web/`). Surface candidates in `web/src/v2/components/SidePanel.tsx` (or
`EvidenceSheet.tsx` — read both, pick whichever already owns per-node detail) as a clearly separated
"Replaceable — alternatives exist" block, visually distinct from the risk narrative so it never reads
as another warning.

**Use the `animate` skill** when building the reveal of this block. It is a disclosure, not a state
change, so it wants a short, quiet entrance — not the cascade treatment. Respect
`prefers-reduced-motion`. No `localStorage`. Every number carries its unit (₹ cr, %, days) per §4.5.

---

## FEATURE 2 — Upload a zip of financial docs → schema → live graph build

Branch: `ab/live-ingestion`. This spans `engine/` and `api/` and `web/`; flag that explicitly in the
PR description per §4.3.

**Amend AGENTS.md first (see §0.1 above), as commit 1, before writing any ingestion code.**

### 2.1 Split the problem — this is the single most important instruction here

There are two entirely separate problems and conflating them is how this fails on stage:

- **(A) Ingestion:** uploaded zip → validated `NetworkInput` JSON. Genuinely hard, failure-prone.
- **(B) Live build visual:** the graph drawing itself in tier by tier from the anchor outward.
  Easy, and it is a **presentation-layer animation over an already-computed result**.

**Do not make the engine stream partial results.** `score_network()` is fast and deterministic on a
few hundred nodes and must stay a pure function (§3.1). Compute the whole scored network the moment
ingestion completes, hand the finished payload to the frontend, and let the frontend *reveal* it
progressively. Anything else destroys determinism and buys nothing the audience can see.

### 2.2 Part A — ingestion

New module: `engine/ingest.py`. It sits alongside `engine/transform.py` and **reuses it** — do not
write a second CSV→network path. `transform.py` is already "the only place that knows about CSVs"
(§7). `ingest.py` unpacks and normalises an upload into the directory shape `transform.py` expects,
then calls it.

Pipeline:

1. **Unpack safely.** Use `zipfile`, and defend against path traversal (`../`, absolute paths,
   symlinks) — reject any member whose resolved path escapes the extraction root. Enforce a total
   uncompressed size cap and a member-count cap, both as `config.py` constants, to refuse zip bombs.
   Extract to a caller-supplied temp directory. Never extract into the repo tree.
2. **Classify members.** Identify which extracted files map to the collection CSVs
   `transform.py` already consumes — read `data/real/` (`companies.csv`, `edges.csv`,
   `financials.csv`, `entity_pool.csv`, `distress_events.csv`) and `data/real/DATA_DICTIONARY.md`
   to learn the exact expected columns. Match by filename first, then by header signature, so a
   judge's slightly-renamed file still lands correctly.
3. **The happy path is CSVs.** If the zip contains the expected CSVs, you are done — hand off to
   `transform.py`. This must work with zero LLM involvement and is the path you rehearse.
4. **The PDF path is a documented, bounded fallback.** If the zip contains PDFs/filings rather than
   CSVs, extract structured fields into the `financials.csv` shape. If you use an LLM for this, it
   runs **only here**, never in `engine/` scoring, and the extraction output is written to disk as a
   CSV so the run downstream of it is fully deterministic and re-runnable. Record extraction
   provenance per field.
5. **Never invent a number.** Any field you cannot extract with confidence is `null`, never a
   guessed value (§3.6). A node whose filings yielded nothing stays in the graph with
   `is_observable: false` and `data_source` set accordingly — the schema already models this and it
   is *narratively perfect*: "most of this network is dark" is the product's own thesis. Lean on it
   rather than papering over gaps.
6. **Validate before returning.** Run the produced network against `schema.json` with `jsonschema`.
   A failure returns a readable error naming the offending file and field — never a 500.
7. **Reuse the synthetic deep tier.** A real cohort bottoms out too shallow to propagate — this is
   already documented at `config.py` `DEEP_TIER_SEED`. `transform.py` already calls
   `synthesise_deep_tier`. Keep that behaviour and make sure the UI can tell the audience which
   layer is generated (nodes already carry `data_source` and `substituted`).

Determinism: the same zip must produce a byte-identical `network.json`. That means fixed
`TRANSFORM_GENERATED_AT` (already in config), seeded deep-tier generation (already), sorted
iteration over zip members (`sorted(zf.namelist())` — zip order is not guaranteed), and no
`datetime.now()` anywhere in the output.

### 2.3 Part A — the endpoint

Add to `api/main.py`: `POST /api/ingest`, accepting a `multipart/form-data` file upload.

- Add `python-multipart` to `requirements.txt` and justify it in the PR description (§4.5 requires
  this for any new dependency).
- Enforce an upload size limit before reading the body into memory.
- Returns the **full scored network** — the same `ScoredNetwork` shape `/api/simulate` returns — plus
  a small `ingest_report` object: files seen, files used, rows parsed, fields extracted, fields left
  null, warnings. The report is a demo asset, not debug output: it is what lets you say "we read 43
  filings and 37 of them disclosed nothing usable" on stage.
- **Statelessness (§3.4).** The server must not hold the ingested network as mutable global state.
  Return the whole payload to the client and let the client send it back with subsequent scenario
  requests, **or** — if that payload is too heavy for the demo — key a bounded, purely-functional
  cache on a content hash of the uploaded bytes. If you take the cache route, document it in the PR
  as a deliberate reading of §3.4 and keep it a pure function of the request body, exactly as §3.4
  permits. Do not invent session IDs.
- Malformed zip → 422 with a readable message. Unknown/unparseable content → 422 naming the file.
  Never a 500 on user input.
- Preserve the existing startup behaviour: the committed `data/mock/network.json` remains the default
  network and the fallback. **The demo must still run end to end with no upload at all.** Never make
  the pre-existing demo path depend on ingestion succeeding.

New tests in `tests/api/test_ingest.py`: valid CSV zip succeeds; zip-slip path traversal is rejected;
oversized zip is rejected; zip with no recognisable files returns 422 with a useful message; response
validates against `schema.json`; two uploads of the same zip return identical results.

### 2.4 Part B — the live build visual

Owner Person C (`web/`). This is where the judges' actual request lives, so give it real care.

Add an upload affordance to the v2 console (read `web/src/v2/Console.tsx`, `api.ts`, `GraphStage.tsx`
and `StoryRail.tsx` first — the console already has a step/mode state machine and you must extend it
rather than bolt a parallel flow beside it).

Sequence after the response lands:

1. Anchors (tier 0) appear first.
2. Then tier 1, then tier 2, then tier 3 — each tier's nodes fading/scaling in, with the edges
   connecting them to the already-present tier drawing after their endpoints exist.
3. Counters tick up as it builds (nodes placed, edges drawn, ₹ cr of trade mapped).
4. The existing risk colouring and the ranked list only resolve **after** the structure is complete —
   build the skeleton, then light it up. Two beats, not one.

**Use the `animate` skill for this.** This is the centrepiece animation of the demo and it needs the
real treatment: purpose, property choice, easing and duration, stagger within a tier, interruption
behaviour if the user clicks mid-build, and a reduced-motion path that jumps straight to the
completed graph. `GraphStage.tsx` renders to canvas, so the tier reveal is driven by animating an
alpha/scale per node inside the existing draw loop, not by CSS transitions — read how the existing
cascade and `observability` mode already gate node rendering (there is prior art there: it dims 404
of 412 nodes to make a point) and extend that mechanism rather than inventing a second one.

Constraints: no console errors on the demo network (§4.5); no `localStorage`; every number carries
its unit; must still run against committed mocks with the API switched off — so mock the ingest
response in `web/src/mocks/` too, and make the build animation replayable from the mock without a
backend.

### 2.5 Rehearsal safety

Add a documented fallback: if ingestion fails live, one action returns the console to the committed
network with the full build animation still playing. Do not let a failed upload leave a blank stage.
Write this into `DEMO_SCENARIO.md` as an explicit recovery step (that file is shared-ownership —
follow §4.3 and note it in the PR).

---

## Order of work

1. Feature 1 end to end (engine → schema → api → tests → web), PR, merge.
2. `git pull origin main`.
3. Feature 2, AGENTS.md amendment as commit 1, then ingestion, then endpoint, then the build visual.

Verify at each step with the §5.2 commands: `python -m engine.pipeline data/mock/network.json`, the
two-run determinism diff, `pytest tests/ -v`, `ruff check .`, `npm run build`, `npm run lint`.

If anything in this brief contradicts `AGENTS.md` in a way §0.1 does not explicitly sanction, stop
and say so rather than proceeding.
