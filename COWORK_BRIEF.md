# FrayFuse — Data Collection & Restructuring Brief (for Claude Cowork)

You are extending an existing, carefully-built financial evidence dataset. **It is already good. Your
job is to fill specific gaps and add specific structure — not to redesign it, not to re-derive it, and
above all not to guess at any number.**

Read `DATA_DICTIONARY.md` and `findings.md` in full before touching anything. They encode traps that
have already caused, or nearly caused, wrong numbers. Everything below assumes you have read them.

---

## 0. Context — what this data feeds, and why the gaps matter

FrayFuse is a supply-chain contagion risk engine. It builds a directed graph of Indian manufacturers,
detects payment stress from public disclosures, propagates that stress **buyer → supplier** through
the graph, and ranks nodes by `fragility × criticality`.

The score is **multiplicative**. `criticality` is derived entirely from graph structure —
betweenness (0.45), sole-source status (0.35), flow share (0.20). Right now the dataset has almost no
graph, so criticality ≈ 0 for every company, so **every score is zero regardless of how good the
stress signals are.**

That is the single most important fact in this brief. The signal work is ~80% done. The network is
~5% done. Prioritise accordingly.

Current state:

| File | Rows | Assessment |
|---|---|---|
| `companies.csv` | 16 | Good. Missing CINs, 5 unknown tiers, one duplicate identity |
| `financials.csv` | 46 | Strong provenance. Real gaps in revenue, cost base, interest lines |
| `edges.csv` | 21 | **The critical gap.** No values, no components, one tier, one inbound edge |
| `distress_events.csv` | 10 | Good. The most credible asset in the set |
| `entity_pool.csv` | — | **Does not exist.** Specified in the schema as a required file |

---

## 1. Real vs synthetic — the boundary, and how to decide

The finished network will be roughly 400 nodes. **Most of it is synthetic and always was going to be** —
the schema anticipates this explicitly (real companies at tiers 0–1, generated companies at tiers 2–3).
That is not a compromise. Public filings simply do not disclose tier-2 and tier-3 supply relationships,
and no amount of collection effort will change that.

The failure mode is not "too much synthetic data." It is **blurring which is which**, or attaching a
fabricated fact to a real, named company.

### 1.1 The test

Ask one question of every field:

> **If this number were wrong, would we be making a false claim about a real, identifiable company —
> or merely making the demo less plausible?**

- False claim about a real company → **must be real, or empty. Never modelled.**
- Merely less plausible → **synthetic is fine, if labelled.**

### 1.2 Must be real — the product's claims rest on these

| What | Why |
|---|---|
| Every field in `financials.csv` | This is the back-test. It is the one genuinely novel claim FrayFuse makes: *payment stress is visible in public filings months before rating agencies act.* A single fabricated figure here destroys the whole claim, and it is the figure a judge or an investor will check |
| `distress_events.csv` in full — event dates, agency, rating transitions, `days_between_ar_and_event` | The temporal-leakage proof. Worthless if any date is approximate |
| `report_filing_date`, `report_url`, `source_page` on every row | Provenance *is* the product here. An unverifiable claim about a real company is worse than no claim |
| `has_not_due_column`, `ageing_basis`, `basis`, `msme_book_material`, `cost_base_type` | Comparability flags. Defaulting any of them silently corrupts a real company's score — this is documented in `DATA_DICTIONARY.md` §5 as the main source of confidently wrong answers |
| `cash_buffer_days` **for real, named companies** | It scales that company's contagion damping, so a modelled value is a fabricated assertion that a named firm is more or less able to survive non-payment. It is also cheaply derivable from filings you are already opening. See §4.1 |
| Identity: `name`, `cin`, `sector`, `product_category`, `tier_role` for real companies | Basic factual accuracy |
| Edges **between two real named companies** — existence, direction, `confidence` | "Shivam supplies Hero MotoCorp" is a factual assertion about two real firms. Real or absent |
| `is_single_source = true` on any real edge | The strongest claim in the product and the easiest to fabricate. See §5.5 |

### 1.3 Can and should be synthetic — label it and move on

| What | Notes |
|---|---|
| **All tier-2 and tier-3 nodes** — names, revenue, buffers, employees, sector | Generated. This is the layer the product argues is invisible; generating it is the honest demonstration of *why* it matters |
| **All edges below tier-1** | Same reasoning. Structure, fan-out and depth should be plausible, not real |
| `component` strings on synthetic edges | |
| `is_single_source` on synthetic edges | 3–5 genuine chokepoints so criticality has something to find |
| `annual_value_cr` on synthetic edges | |
| `employees` anywhere | Display only |
| The 400-node scale itself | The real cohort will be ~25–30 nodes. The rest is generated |

### 1.4 The grey zone — a real company with a field you cannot find

This is where the damage happens, so decide it once and apply it everywhere:

**Leave it empty. Do not model it. Do not carry it across from a peer.**

Then, if the engine needs a value to run, the *engine* substitutes one at runtime and flags the node —
that is a modelling decision made visibly in code, not a fabricated fact frozen into a data file that
outlives everyone's memory of where it came from.

The one exception: `annual_value_cr` derived from a **disclosed percentage** × that company's **real
revenue** is a legitimate derivation, not a fabrication — the schema anticipates it. Record it as
`value_basis = derived_from_disclosed_pct` so it is never mistaken for a disclosed amount.

### 1.5 Must never be synthetic, under any circumstances

- The `data_source` flag itself. It is the honesty mechanism; if it is ever wrong, nothing else in the
  dataset can be trusted.
- Any rupee figure the UI displays next to a real company's name.
- Any distress event, rating action, or date.
- Any statement that a real company is a sole source.

### 1.6 What to tell the developers

Every node and edge carries `data_source: "real" | "synthetic"`. Fill it honestly at row level, never
at file level. A real company with a synthetic buffer is **not** a real node — if that situation ever
arises, it needs a third value (`mixed`), and you should raise it rather than pick one. Note it in the
schema change request (§8.5).

---

## 2. Non-negotiable rules

These are carried over from `DATA_DICTIONARY.md` §2. Violating any of them silently corrupts the
model. If you cannot satisfy a rule, **leave the cell empty and say so in your report.** An empty cell
is a fact about disclosure. A guessed number is a defect that will be discovered at the worst
possible moment.

**Rule 1 — Read each financial year from its own annual report.**
Never take a year's figure from a later report's comparative column. Companies restate. Shivam
Autotech's FY24 "Not Due" was ₹0.04 lakh in the FY24 report and ₹639.06 lakh in the FY25 comparative —
the same year, moved by ~16,000× on the exact line that carries the signal. If you *must* use a
comparative column, say so explicitly in `source_page`.

**Rule 2 — Empty, `nil`, and a number are three different things.**
- empty cell = the source did not disclose this line at all
- `nil` = the source explicitly printed a zero or a dash
- a number = the source printed that number

Never infer. Never estimate. Never carry a figure across from a related entity, a subsidiary, or a
peer.

**Rule 3 — Every monetary figure is ₹ crore.** Record the source unit in `units_as_reported`
(`lakh` ÷ 100, `million` ÷ 10, `crore` ÷ 1). Where rounding to 2 decimals would turn a real non-zero
figure into `0.00`, keep more decimals (Shivam FY24 `msme_not_due` = `0.0004`). Do not re-round.

**Rule 4 — Never compare an ageing bucket across companies without checking `has_not_due_column`
and `ageing_basis`.** Both change what "under 1 year" means.

**Rule 5 — Never mix `basis` within a row.** `standalone` and `consolidated` are different entities.

**Rule 6 (new, for you) — Every single new number needs three things:** a `report_url` (or
`source_url`), a `report_filing_date`, and a `source_page` naming the note or page number. A number
without provenance is not accepted. If you find a figure via a web search snippet, a screener site,
a summary table, or an AI-generated summary, **do not record it** — go to the primary filing or leave
it empty.

**Rule 7 (new) — Temporal leakage.** For any company with a distress event, only figures **published
before the event date** may be used for back-testing. Publication date, not board-approval date.
Record `report_filing_date` accurately; it is what makes the prediction claim defensible.

---

## 3. Retrieval routes — already solved, do not rediscover

From `findings.md` §7:

**Working:**
1. **BSE annual-report index API** —
   `api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w?scripcode=<bse_code>`
   Returns every annual report with a PDF URL **and `Fld_AuthoriseDate`** — the exact date BSE received
   it. This gives you report discovery and the temporal-leakage date in one call. Use it first for
   every company that has a `bse_code`.
2. **In-browser PDF parsing** — load pdf.js from cdnjs inside a `bseindia.com` page, fetch the report,
   scan for a keyword, return only the 2–3 pages needed. A few hundred tokens instead of a 369-page
   report. This is the primary extraction method.
3. **CRISIL works through a real browser** (it returns HTTP 406 to automated access), including the
   three-year rating history table.
4. Chrome automatic-downloads permission is already granted for `bseindia.com` and `[*.]crisil.com`.
   Route everything through BSE-hosted copies.
5. **~1 report in 6 is a scan** and needs OCR at 350–400 dpi. When you OCR, verify the result against
   another disclosure of the same figure and record that you did.

**Blocked — do not waste time:**
- container/device `curl` (proxy 403)
- WebFetch on large PDFs (truncates ~page 45; 413 above 30 MB)
- Google Drive (`ROBOTS_DISALLOWED`)
- BSE announcements API for downgrade discovery — headlines are generic ("Revision in credit rating
  of…"), so identifying downgrades needs reading each attachment. Keyword web search runs ~50%
  precision.

**Useful notes for the new work below:**
- Customer/supplier rupee amounts most often live in the **related-party transactions note** (for
  group entities) and in the **Ind AS 115 major-customer disclosure** ("revenue from one customer
  exceeding 10% of total revenue" — usually unnamed, but gives a percentage).
- Rating rationales (CARE, ICRA, CRISIL) routinely state customer concentration percentages and
  sometimes name the customers. These are already a proven source in this dataset.
- Cash, bank balances, current investments, total expenses and depreciation are all on the face of
  the balance sheet and P&L — the same pages you already open for the ageing table.

---

## 4. P0 — the engine cannot run on real data without these

### 4.1 Collect `cash_buffer_days` inputs — highest value per hour in this brief

This field is **required and non-nullable** in the runtime schema, and it drives the damping term in
the contagion loop — the term that stops every long chain converging to 1.0. It currently exists for
**zero** companies. Per §1.2 it must be real for every real company.

Add these columns to `financials.csv` (raw components — do **not** only store the derived figure):

| New column | Source | Notes |
|---|---|---|
| `cash_and_cash_equivalents_cr` | Balance sheet, current assets | As printed |
| `bank_balances_other_cr` | Balance sheet | Other bank balances line, if separate |
| `current_investments_cr` | Balance sheet, current assets | |
| `total_expenses_cr` | P&L | Total expenses line |
| `depreciation_amortisation_cr` | P&L | |
| `finance_costs_cr` | P&L | |
| `cash_buffer_days` | derived | `(cash + bank_other + current_inv) / ((total_expenses − depreciation − finance_costs) / 365)`, rounded to integer |

Store the raws so the formula can be revised without re-collecting. If any component is not
separately disclosed, leave it empty and leave `cash_buffer_days` empty too — do not partially
compute.

**Scope:** all 14 companies that have `financials.csv` rows, every year present. ~46 rows.

### 4.2 Fill the missing revenue figures — 20 rows, and it silently disables a signal

Signal 3 in the ladder is "payables ÷ revenue rising." **All four years of all three automotive
controls (BGL_C, RICO_C, PRECAM_C) have no revenue at all**, so the signal cannot be tested on the
cohort it matters most for.

Fill `revenue_standalone` (or `revenue_consolidated`, matching the row's `basis`) for exactly these
company-years:

```
BHS FY2022
SHIVAM FY2022
SETCO FY2022
BGL_C FY2022, FY2023, FY2024, FY2025
RICO_C FY2022, FY2023, FY2024, FY2025
PRECAM_C FY2022, FY2023, FY2024, FY2025
NEULAND_C FY2025
BALRAMPUR_C FY2022, FY2025
NECTAR FY2025
DHANUKA_C FY2025
```

### 4.3 Fill the missing cost base — 23 rows

`cost_of_materials_consumed` is the denominator for late-payment intensity. Missing for exactly the
20 rows above, plus `GENSOL FY2022`, `BESTAGRO FY2023`, `BESTAGRO FY2024`.

**Special case:** Best Agrolife reports "Purchase of stock-in-trade" rather than cost of materials
(it is a trading-heavy model). Add a new column `purchases_stock_in_trade_cr` and record it there,
leaving `cost_of_materials_consumed` empty. Do the same for any other company with a trading cost
base. Record which one applies in a new column `cost_base_type` with values
`materials_consumed` | `stock_in_trade` | `both`.

### 4.4 Record which MSMED interest line each company actually discloses

`findings.md` §5 establishes **MSMED interest direction as the strongest signal** — it rose ahead of
6 of 8 events and in 0 of 7 control transitions, and it needs no Not Due column, so it works for
every company. But the metric is defined as "the largest of three disclosed lines," and the dataset
does not record which lines a company actually files.

Add to `financials.csv`:

| New column | Values |
|---|---|
| `msmed_interest_lines_disclosed` | pipe-separated from `accrued_unpaid` \| `due_unpaid` \| `due_on_payments_beyond_appointed_day` \| `none` |
| `msmed_note_format` | `tabular` \| `narrative` \| `absent` |
| `msmed_note_verbatim` | the exact sentence or line label as printed, quoted |

`msmed_note_verbatim` matters because of `findings.md` §4: the "primary signal"
(`msmed_principal_paid_beyond_appointed_day`) was assumed extinct after seven companies, then found
in Bharat Gears — which discloses it as its own named line. **Check the exact note wording company
by company; do not assume absence.**

Then fill the 12 company-years where all three interest columns are blank:

```
SHIVAM FY2022
BGL_C FY2022
RICO_C FY2022, FY2023, FY2024, FY2025
PRECAM_C FY2022, FY2023, FY2024, FY2025
BALRAMPUR_C FY2022, FY2025
```

Where the company genuinely does not disclose the line, write `nil` if it printed a zero/dash, or
leave empty if the line is absent entirely. The distinction is load-bearing.

### 4.5 Fix two identity problems in `companies.csv`

1. **`BGL` and `BGL_C` are the same company** — Bharat Gears Limited, NSE symbol `BHARATGEAR` on both
   rows. One is recorded as an abandoned distress candidate, one as the control. Resolve this: keep a
   single company row, and if the dual role needs recording, add a `role_history` note rather than a
   duplicate identity. Update every `company_id` reference in the other three files.
2. **14 of 16 companies have no CIN.** The runtime schema carries `cin` per node and it is the join
   key to MCA data later. Collect it for all companies — it is on the cover or the corporate-
   information page of every annual report.
3. **5 companies have `tier_role = unknown`** (GENSOL, BESTAGRO, BHS, JPA, DHANUKA_C). Assign a tier
   from their actual position (`tier0` OEM/anchor, `tier1` direct supplier to OEM, `tier2`, `tier3`),
   or record `not_applicable` with a one-line reason if the company genuinely sits outside a
   manufacturing chain.

---

## 5. P1 — the graph. This is the half of the product that currently does not exist

Read this section carefully. The current `edges.csv` has 21 rows and cannot produce a single non-zero
criticality score, for four separate reasons.

Per §1, everything in this section concerns **real** edges between **real** companies. The synthetic
tier-2/3 layer is generated later by the engine team and is not your responsibility — except for the
name pool in §5.6.

### 5.1 Restructure `edges.csv`

Current columns: `from_company, to_company, relationship_type, confidence, evidence_source, fy,
weight_pct, weight_amount_cr, source_url`.

Keep all of them. `to_company` stays as the **as-disclosed name string** — that is provenance, do not
overwrite it. Add:

| New column | Type | Notes |
|---|---|---|
| `edge_id` | string | `E001`… stable once assigned |
| `from_company_id` | string | resolved id of the supplier |
| `to_company_id` | string | **resolved id** of the buyer — requires §5.3 below |
| `component` | snake_case string | What actually flows along this edge. `unknown` is permitted and honest |
| `annual_value_cr` | float | ₹ crore of annual trade along this edge |
| `value_basis` | enum | `disclosed_amount` \| `derived_from_disclosed_pct` \| `rating_agency_stated_pct` \| `not_available` |
| `is_single_source` | boolean | **See §5.5 — read before filling** |
| `single_source_evidence` | text | Required whenever `is_single_source` is true. The quoted sentence and its source |
| `direction_normalised` | enum | `supplier_to_buyer` — normalise every row so `from_company_id` is always the supplier and `to_company_id` always the buyer |

**`direction_normalised` is critical.** The engine propagates stress buyer → supplier and the
`supplied_by` rows currently point the other way. Normalise every row so the columns mean one thing.
Verify each flip against the source before applying it.

### 5.2 Fill edge values — no edge currently has one

**0 of 21 rows have `annual_value_cr`.** Only 5 have `weight_pct`. Without these, `flow_share` (0.20
of criticality), `intervention_cost_cr` and `estimated_exposure_cr` are all uncomputable — which
means the product's cost-vs-exposure screen has no real-data path at all.

For every edge, in this order of preference:

1. **A disclosed rupee amount** → `value_basis = disclosed_amount`. Look in related-party transaction
   notes, segment notes, and MD&A.
2. **A disclosed percentage** of the supplier's revenue → compute
   `annual_value_cr = weight_pct / 100 × supplier's revenue_cr for that FY`, set
   `value_basis = derived_from_disclosed_pct`. Sources: Ind AS 115 major-customer disclosure, MD&A
   customer-concentration statements.
3. **A rating-agency stated percentage** → same computation, `value_basis = rating_agency_stated_pct`.
   Rating rationales in this dataset already carry these (Shivam/Hero at 40% FY25 and 60% FY22 came
   from exactly this route).
4. **Nothing** → leave `annual_value_cr` empty, `value_basis = not_available`. Do not estimate.
   Per §1.4, an empty cell on a real edge is correct; a modelled rupee figure next to two real company
   names is not.

### 5.3 Add tier-0 anchor company rows

13 counterparties currently exist **only as free-text name strings** in `edges.csv`. They have no
company row, no id, no financials, no tier. These are the graph's anchors — the demo's centre node.

Create `companies.csv` rows (and, for the priority five, `financials.csv` rows) with
`cohort = counterparty` and `tier_role = tier0`:

**Priority — listed, large, well-disclosed, cheap to collect:**
`Hero MotoCorp`, `Tata Motors`, `Ashok Leyland`, `Mahindra & Mahindra`, `Eicher Motors`

**Secondary — id and classification row only, financials optional:**
`Kirloskar Oil Engines`, `International Tractors (Sonalika)`, `Deere & Company`, `Hilti`, `Mando`,
`GlaxoSmithKline`, `BluSmart Mobility`, `Lava Cast Private Limited`

Note that the anchors are *buyers*, so their own payment behaviour is directly relevant — an OEM
stretching its suppliers is the origin of the cascade the product models. Collecting their ageing
tables and MSMED notes is high value, not just scaffolding.

### 5.4 Inbound supplier edges — you have exactly one

20 of 21 edges are `supplies_to` (company → its buyer). Contagion propagates **buyer → supplier**, so
what the engine most needs is each company's *suppliers*, and the dataset has one: Lava Cast → Setco.

**Target: 3–5 named suppliers for each of the automotive companies** (SHIVAM, SETCO, BGL, RICO_C,
PRECAM_C, AUTOIND, LOKESH). `findings.md` §6 is explicit that automotive is the only viable graph
cohort — do not spend time hunting supplier edges outside it.

Seams that have already produced supplier edges in this dataset:
- **Auditor going-concern references and emphasis-of-matter paragraphs** (this is how Lava Cast was
  found)
- **Related-party transaction notes** — names group suppliers with exact amounts
- **MSMED disputes and litigation/contingent-liability notes** — name suppliers who sued
- **Contingent liabilities and commitments** — capital commitments name vendors
- **The ACMA member directory** (listed as out of scope previously — it is in scope now)
- Awards and supplier-recognition pages, in both directions

Expect a low yield. Report honestly how many you found; a small number of real supplier edges plus a
clearly-labelled synthetic layer is a defensible product. Inventing edges to reach a target is not.

### 5.5 `is_single_source` — read this before you fill a single cell

`is_single_source` carries **0.35 of the criticality score**, and it is the field most likely to be
filled by accident.

**Do not infer sole-source status from the structure of this dataset.** The fact that a company has
only one edge in `edges.csv` means only that we found one edge. It is evidence about our collection,
not about the world. Treating it as sole-source would manufacture the product's headline finding out
of our own ignorance, and it is exactly the kind of thing that ends a risk product's credibility.

Set `is_single_source = true` **only** with an explicit statement in a primary source — MD&A language
("the sole supplier of…", "the only approved vendor for…"), a rating rationale, a customer's own
disclosure, or a qualification note. Quote it verbatim in `single_source_evidence` with its URL.

Otherwise leave it **empty**, not `false`. Empty means unknown; `false` is a claim that alternatives
exist, and that is also a claim requiring evidence.

Realistically you may find very few. That is an acceptable and honest outcome — report the count. The
demo's chokepoints can and should live in the synthetic layer, where inventing them is legitimate.

### 5.6 Create `entity_pool.csv`

Specified in the schema as one of the five collection files. Does not exist. It supplies plausible
names for the synthetic tier-2/tier-3 layer that gets stitched under the real companies.

Columns: `name, source, source_url, location, product_category, tier_hint, entity_type, use_verbatim`

Target 300–500 Indian auto-component manufacturers. Sources: ACMA member directory, Auto Expo /
Automechanika exhibitor lists, MSME Samadhaan registrations, state auto-cluster directories.

> **⚠ Raise this with the project owner before using these names verbatim.** These are real,
> identifiable companies. Attaching a real firm's name to a synthetic node that the UI then renders
> as "fragile, 18 days of cash, at risk of failure" is a reputational and potentially legal problem
> even with a `data_source: synthetic` label attached — labels do not travel with screenshots.
>
> **Safer alternative, recommended:** decompose the collected names into components (place or surname
> element + product element + suffix — e.g. "Kalyani" / "Sealsworks" / "Precision Polymer" +
> "Industries" / "Components" / "Works" + "Pvt Ltd") and recombine them into names that are plausible
> but not real. Collect the pool either way — the recombination needs a real corpus to sound right.
> Set `use_verbatim = false` by default on every row.

---

## 6. P2 — strengthens the claim, do after P0 and P1

### 6.1 A third automotive control pair

`findings.md` §8.7 names this as its own top recommendation: the +20 pp migration threshold rests on
2 pre-event transitions against 18 no-event ones, and it is the weakest quantitative claim in the set.

Best candidates — already checked and disqualified as distress cases, which is exactly what makes
them free verified controls: **Autoline Industries, Automotive Stampings, Omax Autos**. Prefer one
that discloses a Not Due column, since that is what the threshold needs.

### 6.2 Resolve the Shivam FY24 discrepancy

Converts a qualified event observation into a clean one — n=1 → n=2 on the event side of the migration
threshold, at near-zero cost. The state of play: the FY24 report says Not Due ₹0.04 lakh; the FY25
comparative says ₹639.06 lakh; the BSE-hosted FY24 copy is identical to the separately-sourced one and
was never resubmitted; and the 16-09-2024 corrigendum corrects eleven pages to one-paisa precision but
**not** page 117, which carries the ageing table.

Remaining routes: investor-relations contact, the FY26 report's comparatives when published, the
company secretary, or a stock-exchange clarification request.

### 6.3 Confirm the Section 43B(h) hypothesis

`findings.md` §5 retires the MSME-balance-growth signal after control Bharat Gears posted +629%
against distress case Nectar's +583%. The working hypothesis is that s.43B(h) of the Income Tax Act,
effective FY2024, pushed balances from "Others" into "MSME" with no change in payment behaviour.

**This is currently unverified and sits underneath several observations in the dataset.** Confirm the
statutory cause and effective date from the Act, CBDT circulars, and ICAI guidance. If confirmed, the
whole FY23→FY24 MSME *level* step is an artefact and must be excluded from every level comparison.

### 6.4 Test the `msme_book_material` threshold

The 5% threshold is untested in the 3–8% band; Neuland sits at 4.91% and Nectar at 2.59% while showing
the clearest signal in its cohort. Compute `msme_pct_of_trade_payables` for every company-year (not
just per-company) and report the distribution.

---

## 7. New deliverable — `backtest_panel.csv`

The strongest asset in this dataset is the temporally clean prediction claim, and there is currently
no file that states it. Build one. **Entirely real data — no synthetic rows, ever.** One row per
company-year **transition**:

```
company_id, from_fy, to_fy, cohort, industry_group, distress_mechanism,
is_pre_event, event_date, days_between_ar_and_event,
has_not_due_column, msme_book_material, ageing_basis,
interest_direction,            # up | down | flat | unavailable
interest_from_cr, interest_to_cr, interest_line_used,
migration_pp,                  # change in share of MSME dues past due, pp
payables_over_revenue_pp,      # change in payables ÷ revenue, pp
nonmsme_aged_growth_pct,
signal_fired,                  # which ladder rung fired, or none_fired
notes
```

Every derived figure must be reproducible from `financials.csv` — do not enter anything here that
cannot be recomputed from the raw columns. This file is the evidence for the product's headline
claim, so it must be checkable end to end.

---

## 8. Documentation you must update

1. **`DATA_DICTIONARY.md`** — add every new column with its definition, permitted values, and any
   comparability trap. Bump the version and add a change-log entry under §9 describing what changed
   and why. Follow the existing style exactly.
2. **A new `DATA_DICTIONARY.md` section on the real/synthetic boundary** — transcribe §1 of this brief
   into the dictionary so the rule outlives this session.
3. **§5b industry-specific rules** — before adding any company from a new `industry_group`, write its
   subsection first. `findings.md` §8.6 is explicit that skipping this would have produced a
   confidently wrong "no deterioration" result for sugar.
4. **§8 per-company caveat register** — a row for every company you add or materially change.
5. **`findings.md`** — append a new dated session section. Do not rewrite the existing narrative;
   it is a session log and its history is part of the evidence. If a new finding overturns an old
   conclusion, say so explicitly and leave the old text with a pointer, exactly as the Shivam and
   MSME-balance-growth entries already do.
6. **`schema_change_request.md`** (new file) — the engine repo's contract has gaps your new data
   exposes. Write them up for the developers; do not try to change their code. At minimum:
   - the runtime edge schema has only `data_source: real | synthetic`, with no way to carry
     `confidence` (`confirmed` / `probable` / `concentration_only`). 6 of 21 edges are `probable` —
     inference, not disclosure — and there is currently no honest place to say so
   - the same schema has no way to express a **real company with an unavailable field**. A `mixed`
     value, or per-field provenance, is needed — see §1.6
   - the runtime stress schema weights `msmed_principal_paid_beyond_appointed_day` at 0.65, and that
     field has a value in 3 of 46 company-years, all belonging to one control company. The validated
     ladder in `DATA_DICTIONARY.md` §6 is not represented in the schema at all
   - there is no slot anywhere in the runtime output for the back-test result

---

## 9. Definition of done

Run a full consistency pass over every row, in the style of `findings.md` §9, and report results:

- [ ] MSME bucket sums reconcile to stated MSME totals (±₹0.05 cr)
- [ ] MSME + non-MSME + disputed reconciles to total trade payables where components are present
- [ ] No duplicate company-years; no duplicate company identities
- [ ] Every row has `report_url`, `report_filing_date`, `source_page`, `units_as_reported`, `basis`
- [ ] Every new number traces to a primary filing, not a summary or a search snippet
- [ ] Every `company_id` in `financials.csv`, `edges.csv` and `distress_events.csv` exists in
      `companies.csv`
- [ ] Every `to_company_id` in `edges.csv` resolves to a `companies.csv` row
- [ ] No edge has `is_single_source = true` without `single_source_evidence`
- [ ] Every `annual_value_cr` has a `value_basis`
- [ ] No modelled or estimated value appears anywhere against a real company (§1)
- [ ] `backtest_panel.csv` recomputes exactly from `financials.csv`
- [ ] `cash_buffer_days` is either fully computed from present components or empty — never partial
- [ ] Every `days_between_ar_and_event` is positive for rows marked `backtest_valid = true`

**Report separately and prominently:**
- every cell you left empty and why
- every figure you found that is wrong in the source document itself (the dataset already contains
  two — Neuland's FY24 ageing footings — recorded from their components with the discrepancy noted)
- every restatement you find between reports
- any conclusion in `findings.md` that your new data overturns
- the final count of `is_single_source = true` edges, and of edges with a real `annual_value_cr`
- the real-node count and real-edge count, so the engine team knows how much synthetic layer to
  generate

---

## 10. What not to do

- **Do not estimate, interpolate, or fill a gap with a peer's figure.** Empty is a valid answer and
  is always better than a plausible-looking wrong number.
- **Do not take figures from screener sites, summary tables, aggregators, or search snippets.**
  Primary filings only.
- **Do not take a year from a later report's comparative column** without saying so in `source_page`.
- **Do not infer `is_single_source` from the sparsity of our own edge data.**
- **Do not generate the synthetic tier-2/3 layer.** That belongs to the engine team, who generate it
  deterministically from a seed. Your job is the real layer plus the name pool.
- **Do not delete or rewrite existing rows** to fit a new structure. Add columns; if a value must
  change, record the old value and the reason in the caveat register.
- **Do not rewrite `findings.md`'s existing narrative.** Append.
- **Do not modify anything outside the data folder.** The engine, API and web code are owned by
  another workstream and explicitly forbid data collection.
- **Do not expand the distress cohort before finishing P0 and P1.** `findings.md` §10 costs it out:
  roughly one candidate in eight yields a usable migration observation, so reaching n=5 events means
  checking ~40 more companies. The graph work is cheaper and unblocks more.

---

## 11. Suggested order of work

1. §4.5 identity fixes (fast, and everything else joins on these keys)
2. §4.1 cash buffer components — one pass per report, same pages as the ageing table
3. §4.2 + §4.3 revenue and cost base — same pass, do them together
4. §4.4 MSMED note wording and the 12 missing interest rows
5. §5.3 anchor company rows
6. §5.1 edge restructure, then §5.2 values, then §5.4 supplier edges
7. §7 `backtest_panel.csv`
8. §8 documentation
9. §5.6 entity pool — **but raise the naming flag first**
10. P2 items

Steps 2–4 are one pass over reports you have already located. Do them in a single sweep per company
rather than three separate ones.
