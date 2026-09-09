# FrayFuse — Session 3: Close the Data Set

**This is intended to be the last collection session.** Two jobs: a cheap backfill that makes the
existing data reproducible, and a bounded attempt at the graph. Then the data workstream stops and the
engine becomes the critical path.

Read `data/real/DATA_DICTIONARY.md` §2 first. The seven rules still apply in full.

Note the repo layout changed: the dataset now lives at **`data/real/`** in the `FrayFuse-hackathon`
repo, and it is under version control. Work against that copy.

---

## 0. Where things stand

Your last session's negative result on `cash_buffer_days` has been accepted and acted on. The engine's
`MAX_BUFFER_STRENGTH` dropped from 0.9 to 0.35, mockgen's tier-1 band was corrected from 60–100 days
to 3–45, and `docs/PERSON_A.md` §3.1 has been rewritten around the four-rung ladder with the
`msmed_principal_paid_beyond_appointed_day` weighting removed. The signal work is done and it holds up.

What is not done is the graph, and that is the whole of Part B below.

---

## Part A — Backfill (cheap, no new documents)

### A1. `total_expenses_includes_dep_fin` is blank on 15 rows

Every buffer value recomputes correctly, but the CSV cannot be recomputed from itself without this
flag, which breaks the "reproducible from `financials.csv`" requirement.

Blank on: SHIVAM FY2022–25, LOKESH FY2023–25, SETCO FY2022/23/25, BGL FY2023/24/25, RICO_C FY2023/24.

On five of them the flag is load-bearing — SHIVAM FY2023, LOKESH FY2025, SETCO FY2022/23/25 give 8–25%
different answers depending on the reading, and all five reproduce the recorded value **with**
subtraction, so the intended value is `true`. Confirm from the source rather than assuming, and fill
all 15.

### A2. `msmed_note_verbatim` — 16 of 46 filled

Finish the remaining 30. These are documents you have already located.

Your partial pass already produced a result worth extending: PreCam and Shivam both *print* the
"beyond the appointed day" caption across 8 rows while reporting no value against it. So the caption is
commoner than the figure — which sharpens `findings.md` §4 rather than contradicting it. Completing
this tells us whether that pattern is general.

### A3. `undrawn_credit_facilities_cr` — 0 of 46

Not collected at all last session. It was marked secondary, so that was within spec, but it is the
field that would explain your own headline finding: how Balrampur Chini operates at 0 days of cash
buffer while holding an investment-grade rating.

Take it from rating rationales ("unutilised working capital limits", "average utilisation of X%") and
liquidity notes. **Prioritise the companies at the extremes of the buffer distribution** — Balrampur
(0 days), Shivam and BHS (1 day), Gensol (351 days), PreCam (266 days). If undrawn facilities explain
the low-buffer survivors, that converts a negative result into a positive one about *liquidity
quality*, which is a considerably stronger finding.

### A4. CINs — 5 of 28 companies

On the cover or corporate-information page of every annual report. Low urgency, but it is the join key
to MCA data and it is nearly free while the documents are open.

---

## Part B — The graph, bounded

**Read this framing before starting, because the success criterion is unusual.**

The graph is the half of the product that does not yet exist. Measured on the current data: 20 nodes,
16 resolvable edges, five disconnected star fragments, longest chain 3 nodes, and **exactly one node
in the entire network has non-zero betweenness centrality** (Setco, 0.0117, and only because of the
single Lava Cast supplier edge).

Since `criticality = 0.45×betweenness + 0.35×single_source + 0.20×flow_share`, and `final_score =
fragility × criticality`, this means **almost every real node currently scores zero no matter how
stressed it is.**

### B1. Supplier edges — target 3–5 per automotive company

Companies: SHIVAM, SETCO, BGL, RICO_C, PRECAM_C, AUTOIND, LOKESH. `findings.md` §6 established that
automotive is the only viable graph cohort — do not spend time outside it.

Seams that have already produced supplier edges here:
- **Auditor going-concern references and emphasis-of-matter paragraphs** — this is how Lava Cast was found
- **Related-party transaction notes** — group suppliers, with exact amounts
- **MSMED disputes, litigation and contingent-liability notes** — suppliers who sued
- **Capital commitments** — named vendors
- **ACMA member directory** — in scope
- Supplier-recognition and awards pages, in both directions

### B2. The success criterion is an honest ceiling, not a target number

**Your product's core premise is that deep-tier supply relationships are not publicly disclosed.** If
that premise is true, this search should mostly fail — and establishing *how* mostly, deliberately, is
a more valuable result than a list of edges.

So: report the ceiling. "We searched seven companies across six seam types and recovered nine supplier
edges, of which four are confirmed and five probable" is a finding the project can build on and defend
in front of a judge. A larger number reached by relaxing evidence standards is worth less than nothing,
because it silently converts the product's central claim into a lie.

**Specifically do not:**
- Infer an edge from two companies operating in the same sector or cluster
- Promote a `probable` edge to `confirmed` to improve connectivity
- Set `is_single_source = true` from the sparsity of our own data. It carries 0.35 of criticality and
  it is the field most likely to be filled by accident. Only an explicit primary-source statement
  qualifies — quote it in `single_source_evidence`. Empty means unknown; `false` is itself a claim
- Add edges to counterparties that have no `companies.csv` row

### B3. Edge values

Only 2 of 21 edges carry `annual_value_cr`. Same preference order as before: disclosed amount >
disclosed percentage × that supplier's real revenue > rating-agency percentage > leave empty with
`value_basis = not_available`. Do not estimate.

---

## Explicitly out of scope this session

- `entity_pool.csv` — still blocked on the project owner's naming decision
- New distress companies. `findings.md` §10 costs this at ~40 candidates for n=5 events; the return no
  longer justifies it
- New industries
- P2 items (third control pair, Shivam FY24 resolution, s.43B(h) confirmation) unless Part A and Part B
  finish early — in which case take them in that order

---

## Report back

- Part A completion counts per item
- **The supplier-edge ceiling**: seams searched per company, edges found, confidence breakdown, and
  your honest assessment of whether more searching would yield more
- Any company where undrawn facilities materially change how its buffer should be read
- Whether the "beyond the appointed day" caption pattern generalises beyond PreCam and Shivam
- Anything in `findings.md` your new data overturns

Update `DATA_DICTIONARY.md` (version bump, change-log entry) and append a dated section to
`findings.md`. Do not rewrite existing narrative in either.

## Delivery

Return **all eight files**, including ones you did not change:
`companies.csv`, `financials.csv`, `edges.csv`, `distress_events.csv`, `backtest_panel.csv`,
`DATA_DICTIONARY.md`, `findings.md`, `schema_change_request.md`.

`distress_events.csv` has gone missing from two of the last two handoffs and had to be recovered from
older copies both times. Files also arrived once as `-1` duplicates that overwrote the originals.
Return the full set, correctly named, every time.
