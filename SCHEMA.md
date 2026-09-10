# SCHEMA.md — FrayFuse Data Contract

**Schema version: 1.3**

This file is the boundary between all three tracks. It has **no single owner** — changes require both other team members to be named on the PR. See `AGENTS.md` §4.3.

---

## 1. The three layers

Data exists in three distinct shapes. Confusing them is the most likely way this project goes wrong, so they are named explicitly.

| Layer | Shape | Produced by | Consumed by | Lives in |
|---|---|---|---|---|
| **Collection** | 5 CSV files | Background workstream, outside this repo | `engine/transform.py` only | `data/real/` |
| **Runtime input** | `network.json` | `engine/mockgen.py` or `engine/transform.py` | `engine/pipeline.py` | `data/mock/`, `data/real/` |
| **Runtime output** | `ScoredNetwork` | `engine/pipeline.py` | `api/`, then `web/` | in memory, over HTTP |

**Developers only ever see the runtime layers.** The collection CSVs are an upstream concern and are documented in §7 for reference only.

```
   CSVs  ──transform.py──▶  network.json  ──pipeline.py──▶  ScoredNetwork  ──API──▶  UI
 (external)                  (runtime in)                    (runtime out)
                                  ▲
                                  │
                             mockgen.py
                          (the day-one path)
```

Both `mockgen.py` and `transform.py` emit the **identical shape**. That is what makes swapping in the real dataset a one-line change.

---

## 2. Conventions that apply everywhere

### 2.1 Currency

**All monetary values are ₹ crore, expressed as floats.** Field names carry a `_cr` suffix. There are no exceptions and no other units anywhere in the runtime layer.

Conversion from source units happens exactly once, in `transform.py`.

### 2.2 Edge direction — read this carefully

Edges are **not** `from`/`to`. Those words caused confusion in early drafts, so the fields are named explicitly:

```json
{ "supplier_id": "N042", "buyer_id": "N007" }
```

- **Goods** flow supplier → buyer
- **Money** flows buyer → supplier
- **Stress propagates buyer → supplier** — that is, *against* the direction of goods, following the money that failed to arrive

`exposure_pct` is always expressed as a fraction of the **supplier's** revenue. This is the single most important number in the model.

### 2.3 Missing versus zero

- `null` — the source did not disclose this figure
- `0` or `0.0` — the source explicitly stated nil or zero

Never conflate them. A company that discloses nil overdue payables is not the same as one that omits the disclosure.

### 2.4 Rounding

Applied at serialisation only, never mid-calculation:

- Monetary fields: 2 decimal places
- Score fields (0–1 range): 4 decimal places
- Percentage fields stored as fractions (`0.78`), not as `78`

### 2.5 Identifiers

- `node_id` — format `N###`, zero-padded to three digits, e.g. `N001`
- `edge_id` — format `E###`
- IDs are stable across regenerations of the mock data given the same seed
- IDs are sorted lexicographically wherever iteration order could affect output

---

## 3. Runtime input — `network.json`

The complete file:

```json
{
  "meta": { ... },
  "nodes": [ ... ],
  "edges": [ ... ],
  "stress_signals": [ ... ]
}
```

### 3.1 `meta`

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-27T00:00:00Z",
  "generator": "mockgen",
  "seed": 42,
  "currency_unit": "INR_crore",
  "node_count": 412,
  "edge_count": 1183,
  "observable_node_count": 6
}
```

| Field | Type | Notes |
|---|---|---|
| `schema_version` | string | Must match the version this file declares |
| `generated_at` | ISO 8601 string | Set once at build time. **Never** at score time |
| `generator` | `"mockgen"` \| `"transform"` | Which path produced this file |
| `seed` | integer \| null | Present for `mockgen`, null for `transform` |
| `currency_unit` | string | Always `"INR_crore"` |

### 3.2 `nodes`

One entry per company.

```json
{
  "node_id": "N042",
  "name": "Sealsworks Rubber Industries Pvt Ltd",
  "tier": 2,
  "sector": "auto_components",
  "product_category": "sealing_systems",
  "revenue_cr": 24.70,
  "cash_buffer_days": 18,
  "employees": 42,
  "is_observable": false,
  "data_source": "synthetic",
  "cin": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `node_id` | string | yes | `N###` |
| `name` | string | yes | Must be plausible. Never `Company_47` |
| `tier` | integer | yes | `0` = OEM/anchor, `1`, `2`, `3` |
| `sector` | string | yes | snake_case |
| `product_category` | string | yes | snake_case |
| `revenue_cr` | float | yes | Annual, ₹ crore |
| `cash_buffer_days` | integer | yes | Days of operating cost the firm can survive unpaid. Drives shock damping |
| `employees` | integer | no | Display only |
| `is_observable` | boolean | yes | `true` if real financial disclosures exist for this node |
| `data_source` | `"real"` \| `"synthetic"` | yes | Drives honest UI labelling. **Never blur this** |
| `cin` | string \| null | no | Corporate identity number where known |

### 3.3 `edges`

One entry per supply relationship.

```json
{
  "edge_id": "E317",
  "supplier_id": "N042",
  "buyer_id": "N007",
  "component": "hydraulic_seal_kit",
  "annual_value_cr": 19.20,
  "exposure_pct": 0.7773,
  "is_single_source": true,
  "data_source": "synthetic"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `edge_id` | string | yes | `E###` |
| `supplier_id` | string | yes | Must exist in `nodes` |
| `buyer_id` | string | yes | Must exist in `nodes` |
| `component` | string | yes | snake_case |
| `annual_value_cr` | float | yes | Annual trade value along this edge |
| `exposure_pct` | float | yes | Fraction of the **supplier's** revenue. Range `0.0`–`1.0` |
| `is_single_source` | boolean | yes | `true` if the buyer has no alternative supplier for this component |
| `data_source` | `"real"` \| `"synthetic"` | yes | |

**Validation rule:** for any supplier, the sum of `exposure_pct` across its outgoing edges must not exceed `1.0` (allow `1.02` tolerance for rounding). `transform.py` and `mockgen.py` must both enforce this.

### 3.4 `stress_signals`

One entry per observable company-year. Nodes with `is_observable: false` have no entries here — their stress is inferred entirely by propagation.

```json
{
  "node_id": "N007",
  "fy": "FY24",
  "msme_unbilled_cr": null,
  "msme_not_due_cr": 53.42,
  "msme_under_1yr_cr": 3.08,
  "msme_1_2yr_cr": 0.12,
  "msme_2_3yr_cr": 0.02,
  "msme_over_3yr_cr": 0.05,
  "msme_total_cr": 56.69,
  "nonmsme_total_cr": 360.20,
  "total_trade_payables_cr": 489.18,
  "msmed_principal_unpaid_year_end_cr": 50.63,
  "msmed_principal_paid_beyond_appointed_day_cr": 386.11,
  "msmed_interest_accrued_unpaid_cr": 2.02,
  "revenue_cr": 2969.08,
  "cost_of_materials_cr": 1904.55,
  "trade_payables_turnover_ratio": 5.41,
  "has_not_due_column": true,
  "basis": "standalone",
  "data_source": "real"
}
```

| Field | Type | Notes |
|---|---|---|
| `fy` | string | `"FY22"` … `"FY25"` |
| `msme_*_cr` | float \| null | Schedule III ageing buckets. `null` where not disclosed |
| `msmed_principal_paid_beyond_appointed_day_cr` | float \| null | Whole-year flow figure. **Was designated the primary signal; it is not.** Collection found it disclosed in 3 of 46 verified company-years, all in one company. Keep the field — it is genuinely strong where it exists — but it cannot carry the model. See `docs/PERSON_A.md` §3.1 |
| `msmed_interest_due_unpaid_cr` | float \| null | MSMED interest lines. **The largest of these three drives the primary signal** — a YoY rise is a statutory admission of late payment, and it needs no Not Due column, so it is available for every filer |
| `msmed_interest_due_on_payments_beyond_appointed_day_cr` | float \| null | See above |
| `ageing_basis` | `"due_date"` \| `"transaction_date"` | **Critical.** Schedule III says buckets run from the due date; some filers age from the transaction date instead. Two companies with different values here have incomparable buckets under the same column names |
| `msme_book_material` | boolean | `false` where MSME dues are a rounding error and every MSMED line reads nil. Gates whether a *level* is comparable — never use it to suppress a growth signal |
| `series_break` | string \| null | Set where a year is not comparable with the previous one (restatement, discontinued operations, GAAP transition). The stress ladder must skip that transition rather than compute a meaningless delta |
| `liquidity_quality` | string \| null | Set where a liquidity component was excluded or is not what it appears. One collected company's ₹770 cr of "current investments" was unquoted equity pledged against loans |
| `msmed_principal_unpaid_year_end_cr` | float \| null | Point-in-time snapshot |
| `cost_of_materials_cr` | float \| null | Denominator for late-payment intensity |
| `has_not_due_column` | boolean | **Critical.** `false` means the filer omitted the Not Due column, so `msme_under_1yr_cr` silently includes amounts not yet due and is **not comparable** with other companies. Code must branch on this |
| `basis` | `"standalone"` \| `"consolidated"` | Never mix within one node's series |

#### Why two signals

Indian annual reports disclose payment behaviour in two places that can tell opposite stories.

The **ageing table** is a photograph taken on 31 March and can be tidied up beforehand. The **MSMED note** reports whole-year flows and cannot.

A real observed example: one listed company's ageing table showed every rupee in "Not Due" for two consecutive years, while its MSMED note showed principal paid beyond the appointed day nearly doubling.

**Therefore the model prefers whole-year flow figures over the ageing snapshot.**

**Amended after collection.** The specific flow figure this section was built around —
`msmed_principal_paid_beyond_appointed_day_cr` — is disclosed by almost nobody: 3 of 46 verified
company-years, all belonging to one company. The reasoning above survives; the field does not. The
signal that carries it is the **MSMED interest lines**, which rise only past the appointed day and are
therefore also a whole-year statutory admission — and which every filer discloses. See
`docs/PERSON_A.md` §3.1 for the full ladder and the control-tested evidence behind each rung.

---

## 4. Runtime output — `ScoredNetwork`

Produced by `engine.pipeline.score_network()`. This is what the API serves and the UI renders.

```json
{
  "meta": { ... },
  "nodes": [ ... ],
  "edges": [ ... ],
  "scores": [ ... ],
  "ranking": [ ... ],
  "summary": { ... }
}
```

`nodes` and `edges` are passed through unchanged from the input. `scores`, `ranking` and `summary` are new.

### 4.1 `scores`

One entry per node — **every** node, including unstressed ones.

```json
{
  "node_id": "N042",
  "own_stress": 0.0,
  "inherited_stress": 0.6314,
  "fragility": 0.6314,
  "criticality": 0.8820,
  "final_score": 0.5569,
  "risk_band": "critical",
  "rank": 1,
  "reason_text": "78% of revenue depends on Brakecraft Components, whose late supplier payments rose sharply in FY24. Sole source for hydraulic seal kit.",
  "reason_factors": [
    { "kind": "exposure",       "detail": "78% revenue dependency on Brakecraft Components", "weight": 0.42 },
    { "kind": "upstream_stress","detail": "Brakecraft late payments rose 2.1x in FY24",      "weight": 0.36 },
    { "kind": "single_source",  "detail": "Sole source for hydraulic seal kit",              "weight": 0.22 }
  ],
  "intervention_cost_cr": 4.80,
  "estimated_exposure_cr": 61.40,
  "propagation_depth": 2,
  "halt_risk": 0.5132,
  "supply_disruption": 0.2514,
  "disruption_band": "critical",
  "disrupted_inflow_cr": 4.68,
  "disruption_reason": "Precision Polymer Works Pvt Ltd is at risk of halting polymer compound deliveries — sole source, nothing else to buy it from. ₹4.68 cr of inbound supply at risk."
}
```

| Field | Type | Notes |
|---|---|---|
| `own_stress` | float 0–1 | From this node's own disclosures. `0.0` for non-observable nodes |
| `inherited_stress` | float 0–1 | Received through propagation |
| `fragility` | float 0–1 | `min(1.0, own_stress + inherited_stress)` |
| `criticality` | float 0–1 | Graph position — how irreplaceable |
| `final_score` | float 0–1 | `fragility × criticality` |
| `risk_band` | enum | `"critical"` \| `"high"` \| `"watch"` \| `"stable"`. Thresholds in §4.4 |
| `rank` | integer \| null | 1 = highest `final_score`. `null` where `risk_band` is `"stable"` |
| `reason_text` | string | **Mandatory, never empty.** Template-generated, deterministic |
| `reason_factors` | array | Structured breakdown for the UI. `weight` values sum to `1.0` |
| `intervention_cost_cr` | float | Money needed to stabilise this supplier |
| `estimated_exposure_cr` | float | Value at risk if this supplier fails |
| `propagation_depth` | integer | Hops from the nearest originating stress node. `0` if self-stressed |
| `halt_risk` | float 0–1 | Chance this node stops delivering — no cash, or no parts |
| `supply_disruption` | float 0–1 | Chance this node's own line stops for want of an input it cannot replace |
| `disruption_band` | enum | Same four values as `risk_band`, **separate thresholds** — §4.4 |
| `disrupted_inflow_cr` | float | Expected inbound trade value that fails to arrive |
| `disruption_reason` | string | **Mandatory, never empty.** Template-generated, deterministic |
| `substitution_candidates` | array \| null | Who else could take this supplier's volume — §4.6. Added in 1.3 |

The five before the last are the **supply-disruption layer**, added in 1.2. They
are a second propagation running in the opposite direction to the first, and
they do not enter `final_score`, `risk_band` or `ranking` — those are unchanged.

### 4.2 How the numbers are produced

Full algorithm specification lives in `docs/PERSON_A.md` §3. Summarised here so B and C understand what they are serving and rendering.

**Own stress** combines two year-on-year changes, compared against sector norms:

- *Migration ratio* — `under_1yr / (not_due + under_1yr)`. Unavailable when `has_not_due_column` is `false`
- *Late-payment intensity* — `msmed_principal_paid_beyond_appointed_day_cr / cost_of_materials_cr`

The second is weighted more heavily because it cannot be window-dressed.

**Inherited stress** propagates from buyers to suppliers, scaled by `exposure_pct` and damped by the supplier's `cash_buffer_days`, iterating until convergence.

**Criticality** blends normalised betweenness centrality, the single-source flag, and the node's share of total network flow.

**Supply disruption** runs the other way — supplier to buyer, following the parts rather than
the money. A node's halt risk is seeded by the part of its fragility it did *not* generate
itself (`fragility − own_stress`), because a company stretching its own payables is conserving
cash rather than stopping its line. Buyers combine their suppliers' halt risks by noisy-OR
weighted by replaceability, so a confirmed sole source counts fully regardless of what the part
costs. Full specification in `docs/PERSON_A.md` §3.8.

> **In one sentence:** stress flows down the chain as invoices that were never paid; failure
> flows back up it as parts that never arrived.

### 4.3 `ranking`

Just the ordered `node_id` list, so the UI does not re-sort:

```json
["N042", "N118", "N203", "N087"]
```

Contains nodes whose `risk_band` is not `"stable"`, ordered by `final_score` descending. Ties broken by `node_id` ascending — **this tiebreak is required for determinism.**

**Stressed origins are excluded.** A node whose stress comes from its own published
disclosures is listed in `summary.stressed_origin_nodes` and keeps its `risk_band` and
`final_score`, but carries `rank: null` and does not appear here. The ranked list answers
"which suppliers are about to run out of cash *that you could not already see*" — an origin
is the thing you already knew. The worked example above does exactly this: `N007` is the
trigger and is absent from `ranking`.

### 4.4 `summary`

```json
{
  "total_nodes": 412,
  "stressed_origin_nodes": ["N007"],
  "at_risk_count": 4,
  "band_counts": { "critical": 1, "high": 3, "watch": 11, "stable": 397 },
  "total_intervention_cost_cr": 14.20,
  "total_estimated_exposure_cr": 189.60,
  "max_propagation_depth": 3,
  "iterations_to_converge": 4,
  "disruption_iterations_to_converge": 4,
  "anchor_disruption": [
    { "node_id": "N001", "supply_disruption": 0.1076, "disruption_band": "high", "disrupted_inflow_cr": 848.96, "stopped_by": "N007" }
  ]
}
```

`anchor_disruption` lists every tier-0 node, worst first, ties by `node_id`. It exists so the UI
can drive `DEMO_SCENARIO.md` §6 without scanning four hundred score objects for the three
anchors. `stopped_by` is the supplier contributing most of that anchor's disruption, or `null`
where none does.

**Risk band thresholds** — defined once, in `engine/config.py`:

| Band | `final_score` |
|---|---|
| `critical` | ≥ 0.20 |
| `high` | 0.06 – 0.20 |
| `watch` | 0.012 – 0.06 |
| `stable` | < 0.012 |

Recalibrated in 1.1. `final_score` is the product of two sub-1 factors and fragility is
damped twice on the way down the chain, so the realistic range is far narrower than the
original thresholds assumed — the whole non-origin population fits under 0.21. At 0.50 every
deep-tier supplier banded `stable`, including the sole-source chokepoint the demo is built
around. **These are a calibration to an observed distribution, not a measured threshold for
corporate distress.** What carries meaning is the ordering and the separation between bands.

**Disruption band thresholds** are separate constants (`DISRUPTION_BAND_*`) and currently hold
the same values. That is an observation about the two distributions, not a shortcut — and they
are free to diverge. They are deliberately **not** calibrated to put the demo's anchor in the
top band: at these thresholds `N001` bands `high` at baseline and drops to `watch` once `N042`
is funded.

---


### 4.6 `substitution_candidates`

The ranked list answers "fragile **and** irreplaceable". This field answers the
opposite question at the other end of the same distribution: where a supplier is
replaceable, who could actually take the volume. It introduces no new signal —
eligibility is read off `criticality`, fitness is scored on the same
`contagion.fragility` that `final_score` uses.

**`null` and `[]` are different facts and must never be collapsed.**

| Value | Meaning |
|---|---|
| `null` | Substitution was **not considered**. The node is above `SUBSTITUTION_CRITICALITY_MAX`, or is a confirmed sole source, or its sole-source status is **undisclosed**, or it supplies nothing |
| `[]` | It **was** considered, and no same-tier supplier of the same component qualified |
| non-empty | Up to `SUBSTITUTION_MAX_CANDIDATES` alternatives, best fitness first, ties broken on `node_id` |

This is the same distinction as `null` versus `0.0` everywhere else in this
contract (AGENTS.md §3.6), and it carries real weight here. A node whose
`is_single_source` is undisclosed gets `null`, **not** `[]` — offering a
replacement on the strength of absent evidence would assert that alternatives
exist, which is precisely the claim nobody filed. On `data/real/network.json`
that rule excludes all 43 real companies, because not one collected filing made
a sole-sourcing statement.

Per candidate:

| Field | Type | Notes |
|---|---|---|
| `node_id` | NodeId | The alternative supplier |
| `name` | string | Its name, so the UI need not join back to `nodes` |
| `component` | string | The part it already makes and would take over |
| `replaces_edge_id` | EdgeId | The specific relationship being replaced |
| `fitness` | float 0–1 | `W_SUB_HEALTH x (1 - fragility)` + `W_SUB_CAPACITY x` capacity, normalised within tier |
| `fragility` | float 0–1 | The candidate's own fragility — a replacement that is failing is not a replacement |
| `capacity_headroom_cr` | float \| null | Revenue not already committed. **`null` means revenue undisclosed**, which is unknown headroom, not zero. The capacity term is dropped and its weight renormalised onto health, exactly as criticality drops an undisclosed sole-source term |
| `reason_text` | string | **Mandatory, never empty.** Template-generated and deterministic. Never an LLM |

Candidates are same-tier and same-component only, exclude anyone already
supplying that buyer that part, and are capped at one entry per candidate
company — three ways to replace the same firm are one alternative, not three.


## 5. API contract

Base URL: `http://localhost:8000`. All responses `application/json`. The API is **stateless** — see `AGENTS.md` §3.4.

### 5.1 The `Scenario` object

Sent by the client on every mutating request. The server holds nothing between calls.

```json
{
  "stress_overrides": [
    { "node_id": "N007", "own_stress": 0.85 }
  ],
  "interventions": [
    { "node_id": "N042", "amount_cr": 4.80 }
  ]
}
```

Both arrays default to empty. An empty scenario means "score the baseline."

### 5.2 `GET /api/network`

Returns the raw network for initial render. No scoring.

**Response:** `{ "meta": {...}, "nodes": [...], "edges": [...], "stress_signals": [...] }`

`stress_signals` is **optional and additive in 1.2**, and carries the published
ageing and MSMED rows verbatim — the same rows `engine/stress.py` reads. It is
there so a client can show *where a stress score came from* rather than
restating the figures: the year-end ageing snapshot beside the whole-year MSMED
payment lines. A network file without signals serves `[]`, and no client may
require the field to render.

### 5.3 `GET /api/at-risk?limit=10`

Baseline scoring, ranked list only. The default view.

**Response:**

```json
{
  "meta": {...},
  "ranking": ["N042", "N118"],
  "scores": [ ... ],
  "summary": {...}
}
```

`scores` contains only the ranked nodes, not all 412.

### 5.4 `POST /api/simulate`

Score the network under a scenario. Used by the what-if controls.

**Request:** `{ "scenario": { ...Scenario... } }`

**Response:** full `ScoredNetwork`.

### 5.5 `POST /api/ingest`

Build and score a network from an uploaded zip of collection CSVs. Added with
ingestion (AGENTS.md §1.5); offline only, and no LLM.

**Request:** `multipart/form-data` with one `file` field holding a zip.

**Response:** a full `ScoredNetwork`, plus `stress_signals` and an
`ingest_report`:

```json
{
  "meta": {...}, "nodes": [...], "edges": [...],
  "scores": [...], "ranking": [...], "summary": {...},
  "stress_signals": [...],
  "ingest_report": {
    "files_seen": [...], "files_used": {"companies.csv": "data/real/companies.csv"},
    "files_ignored": [...], "rows_parsed": {"companies.csv": 43},
    "companies_read": 43, "nodes_built": 298, "edges_built": 302,
    "generated_nodes": 255, "observable_nodes": 14,
    "fields_present": 618, "fields_null": 440, "warnings": [...]
  }
}
```

`stress_signals` comes back because the client needs the whole `NetworkInput`:
to render the evidence panel, and to send with the scenario requests that
follow.

**Errors are always 422 `invalid_upload`, never 500.** An unreadable zip, a
member resolving outside the extraction directory, an archive over the size or
member caps, or no recognisable collection CSVs — each names the file.

**Statelessness.** The server keeps nothing. The network it loaded at startup is
untouched and remains the default, so the demo runs end to end with no upload.

### 5.6 Scoring a client-supplied network

`POST /api/simulate` and `POST /api/intervene` both accept an optional
`network` field holding a full `NetworkInput`. Present, it is scored instead of
the server's default; absent, nothing changes.

This is what keeps ingestion stateless (AGENTS.md §3.4). The client holds the
network it ingested and sends it with each scenario, so every request stays a
pure function of its own body and two clients can hold two different networks
without knowing about each other. There is no session id and no server-side
handle.

### 5.7 `POST /api/intervene`

Apply funding and return before, after, and the delta. This drives the closing demo beat.

**Request:**

```json
{
  "baseline_scenario": { "stress_overrides": [...], "interventions": [] },
  "interventions": [ { "node_id": "N042", "amount_cr": 4.80 } ]
}
```

**Response:**

```json
{
  "before": { ...ScoredNetwork... },
  "after":  { ...ScoredNetwork... },
  "delta": {
    "nodes_improved": 7,
    "nodes_worsened": 0,
    "total_exposure_reduced_cr": 148.30,
    "total_intervention_cost_cr": 4.80,
    "per_node": [
      { "node_id": "N042", "fragility_before": 0.6314, "fragility_after": 0.1102, "band_before": "critical", "band_after": "stable" }
    ]
  }
}
```

`per_node` includes only nodes whose `risk_band` changed.

### 5.8 Errors

| Status | When | Body |
|---|---|---|
| 400 | Unknown `node_id` in a scenario | `{ "error": "unknown_node", "detail": "N999 not in network", "node_id": "N999" }` |
| 422 | Malformed body | pydantic validation output |
| 500 | Engine raised | `{ "error": "engine_failure", "detail": "<message>" }` |

Never return 500 for a bad request. Never return 200 with an error inside.

---

## 6. Validation

`schema.json` holds JSON Schema definitions for every object above.

```python
import json, jsonschema

schema = json.load(open("schema.json"))
jsonschema.validate(instance=network, schema=schema["definitions"]["NetworkInput"])
```

**Required in tests:**

- A: `mockgen` and `transform` output validates against `NetworkInput`
- B: every endpoint response validates against its definition
- C: committed mocks in `web/src/mocks/` validate against the same definitions

If a mock does not validate, it is not a mock — it is a future integration bug.

---

## 7. Collection layer — reference only

**No developer in this repo reads these files.** Documented so `transform.py` has a spec to work from.

Five CSVs land in `data/real/`:

| File | Grain | Key fields |
|---|---|---|
| `companies.csv` | One row per company | `company_id`, `name`, `cin`, `sector`, `product_category`, `cohort`, `tier_role`, `graph_connectable` |
| `financials.csv` | One row per company-year | ageing buckets, MSMED flow figures, `revenue`, `cost_of_materials_consumed`, `has_not_due_column`, `units_as_reported`, `basis` |
| `edges.csv` | One row per disclosed relationship | `from_company`, `to_company`, `relationship_type`, `weight_pct`, `name_confidence` |
| `distress_events.csv` | One row per stress event | `company_id`, `event_date`, `event_type`, `agency`, `mentions_payables_stretch` |
| `entity_pool.csv` | Real company names for the synthetic layer | `name`, `source`, `location`, `product_category` |

### 7.1 What `transform.py` must do

1. **Normalise units** — divide by 10 where `units_as_reported` is `million`. Record the original in `meta`
2. **Map IDs** — `company_id` → `node_id` in `N###` format, deterministically ordered
3. **Assign tiers** — from `tier_role`, defaulting to `1` for listed manufacturers
4. **Compute `exposure_pct`** — from `edges.csv` `weight_pct` where disclosed; otherwise from `annual_value / supplier_revenue`
5. **Stitch the synthetic layer** — real nodes at tier 0–1, generated nodes at tier 2–3, using names from `entity_pool.csv`. **Implemented.** The generator lives in `mockgen.py` (AGENTS.md §3.1 confines `random` to it) and is seeded from `config.DEEP_TIER_SEED`. Two invariants are enforced in code: no `is_single_source` edge may point at a real buyer, and no generated figure may be written onto a real node — both from `DATA_DICTIONARY.md` §3b
6. **Set `data_source` honestly** — `"real"` only where the figure came from a filing
7. **Preserve `has_not_due_column`** — do not silently default it to `true`
8. **Validate the output** against `NetworkInput` before writing

---

## 8. Changelog

| Version | Change |
|---|---|
| 1.0 | Initial contract. Edge fields named `supplier_id`/`buyer_id` rather than `from`/`to`. MSMED flow figure designated primary signal. `has_not_due_column` added as a required comparability flag |
| 1.1 | Carries the comparability flags the collection workstream measured: `ageing_basis`, `msme_book_material`, `series_break`, `liquidity_quality` on stress signals; `confidence`, `edge_provenance` and a nullable `is_single_source` on edges; `observation_completeness` on nodes. Risk-band thresholds recalibrated to the score distribution the engine actually produces (§4.4). Stressed origins excluded from `ranking` (§4.3). This entry also records the version bump that `schema.json` had already taken but which was never written up here — agreed with Person B and Person C |
| 1.3 | **Ingestion endpoint and client-supplied networks.** `POST /api/ingest` (§5.5) builds and scores a network from an uploaded zip of collection CSVs; `simulate` and `intervene` take an optional `network` (§5.6) so the result can be scored without the server holding it. New error code `invalid_upload`, always 422. Additive throughout: every existing request and response is unchanged, and the default network still serves with no upload. Needs Person B and Person C review |
| 1.3 | **`substitution_candidates` on `Score`.** Optional, additive and output-only — `NetworkInput` is untouched, no data file's `meta.schema_version` moves, and `mockgen`/`transform` are unchanged. `final_score`, `risk_band` and `ranking` are unchanged; nothing that was correct before returns a different number. `null` means not considered and `[]` means considered-and-empty (§4.6). New engine module `engine/substitution.py`, orchestrated from `pipeline.py`. Needs Person B review |
| 1.2 | **`stress_signals` on `GET /api/network`.** Optional, additive, pass-through — the endpoint already had the rows in memory and was dropping them. Required so the UI can display a filer's own disclosure beside the score derived from it; the alternative was hardcoding rupee figures in the frontend, which AGENTS.md §3.6 forbids. No engine, no scoring and no data file changes; an older client is unaffected because the field is optional. Needs Person B review |
| 1.2 | **Supply-disruption layer.** Adds `halt_risk`, `supply_disruption`, `disruption_band`, `disrupted_inflow_cr` and `disruption_reason` to `Score`, and `anchor_disruption` plus `disruption_iterations_to_converge` to `Summary`. Purely additive and **output-only** — `NetworkInput` is untouched, so no data file's `meta.schema_version` moves and `mockgen`/`transform` are unchanged. `final_score`, `risk_band` and `ranking` are unchanged; nothing that was correct before returns a different number. Closes the `DEMO_SCENARIO.md` §6 counterfactual, which payment-stress propagation structurally could not reach. Needs Person B and Person C review |
