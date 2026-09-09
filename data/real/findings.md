# FrayFuse — Stage 1B: Distress Evidence Set

**Session date 2026-09-08.** Read `DATA_DICTIONARY.md` before using any figure here — it holds the
field definitions, the comparability traps, and the per-industry rules.

---

## 1. Headline

**8 distress companies and 6 industry-matched controls, across 7 industries; 33 company-years; all
back-testable.**

**The controls changed two conclusions, and that is the most valuable thing in this session.**

*Does payment-stress deterioration appear before documented financial distress?* Where the model
claims to apply, yes:

| `distress_mechanism` | Companies | Signal fired? |
|---|---|---|
| `trading_stress` / `external_shock` — **what FrayFuse models** | Setco, Shivam, Lokesh, Best Agrolife, Nectar | **5 of 5** |
| `financial_structure` — default driven by debt structure, not operations | Bajaj Hindusthan, Jaiprakash | 0 clean, 1 partial |
| `governance` — fraud / fund diversion | Gensol | 0 of 1 |

Scoring all eight gives 62%; scoring the five the model claims gives 100%. Tag the mechanism or the
result is meaningless.

**But two of the signals do not survive contact with the controls** — see §5. One is retired outright.
The signal that survives best is **MSMED interest direction: it rose ahead of 6 of 8 events and in
0 of 7 control transitions**, and it needs no Not Due column, so it works for every company.

Lead times: **177 to 350 days**, plus Setco's year-plus.

---

## 2. Cohort

| Company | Industry | Event | Lead | Mechanism | Signal |
|---|---|---|---|---|---|
| **Setco Automotive** | automotive | ICRA → [ICRA]D, 03-Sep-2025 | 1 yr+ | trading_stress | Not Due → overdue |
| **Shivam Autotech** | automotive | CARE outlook → Negative, 22-Jul-2025 | 344 d | trading_stress | Not Due → overdue |
| **Lokesh Machines** | industrial_machinery | CARE outlook → Negative, 24-Feb-2025 | 194 d | external_shock | MSMED interest nil → + |
| **Nectar Lifesciences** | pharma | CARE → BB-/A4 (RWN), 16-Jul-2025 | 336 d | trading_stress | payables ÷ revenue ↑ |
| **Best Agrolife** | chemicals | Crisil → BBB/Stable, 22-Aug-2025 | 350 d | trading_stress | payables ÷ revenue ↑ |
| **Gensol Engineering** | energy_infrastructure | CARE → CARE D, 03-Mar-2025 | 177 d | governance | none fired |
| **Bajaj Hindusthan Sugar** | food_agri | CARE → CARE D, 29-Mar-2025 | 302 d | financial_structure | none fired |
| **Jaiprakash Associates** | cement | NCLT CIRP admission, 03-Jun-2024 | 269 d | financial_structure | mixed / partial |

**Controls** (industry-matched, same years, comparable size): Bharat Gears → Shivam · Rico Auto →
Setco · Precision Camshafts → Setco · Neuland Laboratories → Nectar · Dhanuka Agritech → Best
Agrolife · Balrampur Chini Mills → Bajaj Hindusthan.

Four of the six were companies I had already *disqualified* as distress candidates — they were
rejected precisely because their rating actions showed them healthy, which made them free, verified
controls.

---

## 3. What the deterioration looks like

In all three automotive cases the total payables number was flat or falling and the payables turnover
ratio *improved*, while the bucket split deteriorated.

**Setco Automotive** (consolidated, ₹ crore) — FY23 → FY24, published ~13 months ahead:

| | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| MSME — Not Due | 11.26 | 7.03 | 23.27 |
| MSME — overdue under 1 yr | **4.33** | **8.52** | **11.71** |
| MSME total | 16.05 | **15.65 (−2%)** | 34.99 |
| Non-MSME total | 77.70 | 80.73 | 61.96 |
| Payables turnover ratio | 3.49 | **3.53 (better)** | 3.54 |

Share of MSME dues past due **29.8% → 55.1%**. In FY25 — published 22 days before the downgrade —
MSME payables rose 124% while non-MSME payables *fell* 23%.

**Shivam Autotech** — MSME total *fell* 2%, turnover ratio *improved* 17.5%, Not Due collapsed from
₹3.42 crore to ₹4,000, overdue share **77.9% → 100.0%**, non-MSME payables fell 32%.

**Lokesh Machines** — MSMED interest due went **nil → ₹1.80 lakh**. Interest accrues only past the
appointed day, so nil-to-positive is a statutory admission of late payment.

**Nectar** — payables ÷ revenue 20.9% → 24.9%. **Best Agrolife** — 14.9% → 20.1%, with non-MSME aged
buckets ×4 and ×17, and an MSME book so small (₹0.15 crore) that every MSMED line is nil.

### Two restatements, both on the line that carries the signal

Shivam's FY25 report restates FY24's Not Due from ₹0.04 lakh to ₹639.06 lakh — the same year, moved by
~16,000× across the boundary that matters — and restates FY24 accrued interest to a figure identical
to FY23's, which looks like a carry-forward error. Setco restated FY24 revenue between reports.
**Hence Rule 1: read each year from its own report.** Bajaj Hindusthan was cross-checked and showed no
restatement, so it is not universal — but it is common enough to be the default assumption.

---

## 4. The primary signal exists after all — in exactly one company

`msmed_principal_paid_beyond_appointed_day` is empty or nil in **32 of 33 company-years**. The
exception is **Bharat Gears — a control** — which discloses "The amount of principal paid beyond the
appointed day" as its own line: **₹9.21 crore in FY23 falling to ₹3.20 crore in FY24**, a 65%
improvement in a company CARE upgraded.

The contrast inside that one company is the finding. Its **stock** figures rose sharply and look like
distress (MSE balance 7.3×, overdue share 20.5% → 36.1%); its **flow** figure fell sharply and
correctly says healthy. That is precisely the argument the original brief made for preferring the flow
figure — now demonstrated, from the healthy side.

So the primary signal is not extinct, only rare. It is worth checking the exact MSMED note wording for
every new company rather than assuming absence.

---

## 5. What the controls overturned

### Retired: MSME balance growth

**Bharat Gears, upgraded by CARE, posted MSME payables growth of +629% — higher than distress case
Nectar's +583%.** The signal does not discriminate and has been retired.

Four companies across four industries show large FY24 MSME jumps, including a healthy control:

| Company | Cohort | FY24 MSME growth |
|---|---|---|
| Lokesh Machines | distress | +3,544% |
| Bajaj Hindusthan | distress | +1,560% |
| **Bharat Gears** | **control** | **+629%** |
| Nectar Lifesciences | distress | +583% |
| Dhanuka Agritech | control | +37% |
| Rico Auto | control | +23% |

**Working hypothesis, not verified:** Section 43B(h) of the Income Tax Act took effect for FY2024 and
gave buyers a strong incentive to identify and register MSME vendors properly, shifting balances from
"Others" into "MSME" with no change in payment behaviour. Bharat Gears fits — MSME up 7.3× while
*total* trade payables **fell** 8%. Someone should confirm the statutory cause. Until then, treat any
FY23→FY24 MSME *level* change as uninterpretable, and Nectar's signal_path has been changed from
`msme_balance_growth` to `payables_outgrowing_revenue`, which does hold up.

### Quantified: Not Due → overdue migration

Every company with a Not Due column was extended to a full FY22–FY25 panel, so each acts as its own
control and the "no-event" distribution can be measured rather than assumed.

| | FY22 | FY23 | FY24 | FY25 | YoY changes (pp) |
|---|---|---|---|---|---|
| **Setco** *(distress)* | 22.9 | 29.8 | **55.1** | 33.5 | +6.9 · **+25.2 ←event** · −21.6 |
| **Shivam** *(distress)* | 85.2 | 77.9 | **100.0** | 67.8 | −7.3 · **+22.1 ←event** · −32.2 |
| Bharat Gears *(control)* | 49.2 | 20.5 | 36.1 | 19.3 | −28.7 · +15.5 · −16.8 |
| Rico Auto *(control)* | 70.9 | 26.2 | 32.8 | 29.6 | −44.7 · +6.6 · −3.2 |
| Precision Camshafts *(control)* | 5.4 | 3.1 | 1.8 | 1.9 | −2.4 · −1.2 · +0.0 |
| Balrampur Chini *(control)* | 62.9 | 0.0 | 0.0 | 0.0 | −62.9 · 0.0 · 0.0 |
| Neuland *(control)* | — | 0.0 | 0.0 | 8.5 | +0.0 · +8.5 |

**18 no-event transitions: maximum +15.5 pp. 2 pre-event transitions: +25.2 and +22.1 pp.**
Complete separation, with a 6.6 pp margin.

The shape of the null distribution is the useful part. Healthy companies swing *violently downward*
— as far as −62.9 pp — but rarely upward: only one of eighteen exceeded +10 pp. A **sustained rise
above +20 pp** is genuinely rare, and that is now a measured claim rather than an assumption.

**Two honest caveats.** First, n = 2 on the event side. Second, Shivam's +22.1 pp depends on which
report is used: its FY25 report restates FY24 Not Due from ₹0.04 lakh to ₹639.06 lakh, which turns
+22.1 pp into **−20.0 pp** and moves it into the no-event range. Shivam's own Not Due share runs 34.2%
(FY22), 24.4% (FY23), then either 1.1% or 46.7% (FY24), then 47.3% (FY25) — the restated version fits
that series and the original looks like a reporting error. **Update after further verification.** Shivam filed a Corrigendum to its FY24 annual report with BSE
on 16-09-2024 correcting errors on eleven pages — including differences as small as ₹0.01 lakh and a
misspelling of "Gurugram" — but it does **not** correct page 117, which carries the trade payables
ageing table. The company therefore reviewed that report to one-paisa precision and did not treat the
Not Due figure as an error. That shifts the balance toward the as-filed FY24 figure being intentional
and the FY25 comparative being a regrouping (the FY25 report carries only a generic "previous year
figures have been regrouped/restated" note).

Shivam is accordingly upgraded from disputed to a **qualified** event observation
(`msme_not_due_migration_qualified`). Report the threshold both ways: **conservatively n = 1 event
(Setco alone), or n = 2 including Shivam**, against 18 non-events either way. The company has still
not explained the difference.

### Now the strongest signal: MSMED interest direction

Panels extended across cohorts. The metric is the largest of the three MSMED interest lines disclosed
(accrued and unpaid / due on unpaid principal / interest due on payments made beyond the appointed
day), in ₹ crore.

| | FY22 | FY23 | FY24 | FY25 | direction (* = pre-event) |
|---|---|---|---|---|---|
| **Shivam** *(distress)* | | 0.73 | 0.79 | 1.33 | **UP\*** · UP |
| **Setco** *(distress)* | 0.07 | 0.07 | 0.06 | 0.19 | = · dn · **UP\*** |
| **Lokesh** *(distress)* | | nil | 0.02 | 0.03 | **UP\*** · UP |
| **Gensol** *(distress)* | nil | 0.02 | 0.05 | | UP · **UP\*** |
| **Bajaj Hindusthan** *(distress)* | nil | nil | 0.16 | | = · **UP\*** |
| **Jaiprakash** *(distress)* | 3.58 | 5.93 | | | **UP\*** |
| Nectar *(distress)* | | 0.14 | 0.10 | 0.22 | **dn\*** · UP |
| Best Agrolife *(distress)* | | nil | nil | | **=\*** |
| Bharat Gears *(control)* | | 0.02 | 0.02 | 0.02 | = · = |
| Dhanuka *(control)* | | 0.14 | 0.14 | 0.14 | = · = |
| Neuland *(control)* | | 1.11 | 0.27 | 0.14 | dn · dn |
| Balrampur *(control)* | | nil | nil | | = |

**Pre-event: rose in 6 of 8. Controls: rose in 0 of 7 transitions.**

On this sample that is 75% sensitivity at 100% specificity — better discrimination than the migration
signal, and available for **every** company because it needs no Not Due column. The two misses are
explicable: Nectar's fell in the pre-event year (though it rose sharply afterwards), and Best Agrolife
has essentially no MSME book, so every MSMED line is nil.

**One caveat that cuts against over-reading the controls.** In two of the four controls the accrued
figure is *frozen* — Bharat Gears reports 2.37 in FY23, FY24 and FY25; Dhanuka reports 13.65 three
years running. These look like legacy provisions carried forward rather than live measurements, so
"control never rises" partly reflects a static number. Neuland's, which does move, moves **down** in
both years. The signal to trust is a *rise*, not the absence of movement.

**And the primary signal is volatile too.** Bharat Gears' "principal paid beyond the appointed day"
runs 9.21 → 3.20 → 8.32 over FY23–FY25 in a company that was upgraded. A single-year rise in that flow
figure is therefore not diagnostic on its own either — the useful reading is its direction alongside
the interest lines.

### Confirmed: payables ÷ revenue

Distress +4.0 to +5.2 pp (Nectar, Best Agrolife); all three tested controls **fell**, −1.8 to −2.2 pp.

### The sugar caveat, refined

Balrampur Chini carries trade payables of **5.0% of revenue against Bajaj Hindusthan's 59.0%**, on
comparable scale (₹5,594 cr vs ₹6,077 cr revenue) — a ten-fold gap within one industry and the single
strongest discriminator in the dataset. Cane arrears show up in *both* places for a stressed miller:
₹3,541 crore in Bajaj Hindusthan's under-1-year bucket **and** ₹2,361 crore in a statutory escrow
account under other payables. So payables ÷ revenue is the signal to use for sugar, and the ageing
table alone still understates the position.

---

## 6. Graph coverage

`graph_valid` is 6 of 10, and the gap is entirely non-automotive. Confirmed edges from companies' own
filings:

- **Setco → Ashok Leyland** and **Setco → Tata Motors** — from the awards page, exactly as the brief
  predicted ("4th Rank amongst 164 suppliers in Supplier SAMRAT competition… by M/s. Ashok Leyland").
- **Shivam → Hero MotoCorp** (MD&A), plus new customers **Hilti** and **Mando**.
- **Lokesh → Mahindra & Mahindra**, and a **dated edge deletion**: OFAC sanctions caused M&M to
  suspend business, leaving "near Zero business" in the Component Division.
- **Setco ← Lava Cast Pvt Ltd** — a confirmed tier-2 *supplier* edge carrying its own going-concern
  qualification.

Outside automotive the counterparties are distributors, farmers and institutional buyers, and no named
edge is recoverable. Bajaj Hindusthan, Best Agrolife and Jaiprakash are all `graph_valid` false. **If
the demo graph needs density, it has to be built from automotive.**

---

## 7. Retrieval — solved, and three routes reopened

1. **BSE annual-report index API** — `api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w?scripcode=<code>`
   returns every annual report with a PDF URL **and `Fld_AuthoriseDate`**, the exact date BSE received
   it. Report discovery and the temporal-leakage date in one call.
2. **In-browser PDF parsing** — pdf.js from cdnjs inside a `bseindia.com` page: fetch a 369-page report,
   scan for a keyword, return only the two or three pages needed. No downloads, a few hundred tokens
   instead of a whole report.
3. **CRISIL is not a dead end.** The brief lists it as HTTP 406 to automated access; through a real
   browser it works, including the three-year rating history table. Largest Indian rating agency,
   back in the candidate pool.
4. **Chrome's automatic-downloads permission** blocks silently once triggered — as the brief warned.
   Now granted for `bseindia.com` and `[*.]crisil.com`; route everything through BSE-hosted copies.
5. **Still blocked:** container and device `curl` (proxy 403), WebFetch on large PDFs (truncates
   ~page 45; 413 above 30 MB), Google Drive (`ROBOTS_DISALLOWED`).
6. **One report in six is scanned** and needs OCR — Setco FY24 was rendered at 350–400 dpi, OCR'd, and
   verified against the FY25 comparative, which matched exactly.

---

## 8. Recommendations

1. **Adopt `distress_mechanism` and score only `trading_stress` and `external_shock`.** Without it the
   back-test understates the model by 38 percentage points.
2. **Adopt the control-tested signal ladder**, in this order: MSMED interest direction → Not Due
   migration (provisional +20 pp threshold) → payables ÷ revenue → non-MSME aged-bucket growth.
   **Retire MSME balance growth**, and demote the turnover ratio to context.
3. **Resolve the FY24 MSME reclassification question before any FY23→FY24 level comparison is used.**
   If Section 43B(h) is the cause, the whole FY24 step change is an artefact, and it currently sits
   underneath several of our observations.
4. **Check the MSMED note wording company by company.** Bharat Gears proves the original primary
   signal is filed by some companies; it was assumed extinct after seven companies without it.
5. **Treat automotive as the graph cohort and other industries as the signal cohort.** `graph_valid`
   is 6 of 16 and the gap is entirely non-automotive.
6. **Before adding a new industry, write its subsection in `DATA_DICTIONARY.md` §5b first.** The sugar
   finding would otherwise have produced a confidently wrong "no deterioration" result.
7. **Expand the control cohort before expanding distress.** Two signals survived only two or three
   control comparisons each; a third automotive-matched control pair would materially firm up the
   +20 pp threshold, which is currently the weakest quantitative claim in the set.

**Still open:** the ACMA seller directory, MCA master data and entity-pool work remain out of scope;
`msme_book_material`'s 5% threshold is untested in the 3–8% band (Neuland sits at 4.91%); no company
has two independent pre-event windows; and no control exists for Lokesh (`industrial_machinery`) —
listed peers at its ₹294 crore scale are scarce.

## 9. Data quality

A full consistency pass was run over all 44 rows:

- **MSME bucket sums vs stated MSME totals — 44/44 pass** (tolerance ±₹0.05 cr).
- **MSME + non-MSME + disputed vs total trade payables — all rows with the components present pass.**
- **No duplicate company-years; no row missing `report_url`, `units_as_reported` or `basis`.**
- Four rows show a small gap between the MSMED note's principal and the ageing table's MSME total
  (BHS FY24, Bharat Gears FY24, Dhanuka FY23 and FY24). All four are the documented note-split
  differences already recorded in `companies.csv` notes — both figures are transcribed as printed
  rather than reconciled.

Two figures in source documents were found to be **wrong in the report itself** and are recorded from
their own components instead: Neuland's FY24 ageing footings (printed 18,874.47 and 19,858.88 against
components summing to 18,879.47 and 19,853.88, which match its Note 17).

**Shivam FY24 — verification attempted and inconclusive.** The BSE-hosted FY24 report (filed
31-08-2024, never resubmitted) is identical to the separately-sourced copy, and the report contains
only one ageing table, so there is no internal cross-check. The discrepancy against the FY25
comparative is genuine and needs the company's confirmation. Shivam stays out of the event evidence.

## 10. Candidate pipeline and what limits it

**Checked and disqualified this session (all reaffirmations or upgrades):** Bharat Gears, Autoline
Industries, Automotive Stampings, Rico Auto, Precision Camshafts, Omax Autos, Kesoram Industries,
Jayaswal Neco, Himatsingka Seide (Crisil reaffirmed BBB+/Stable, Jan-2025). Four of these were
promoted to the control cohort.

**Still unchecked:** Bombay Rayon Fashions (textiles, CIRP), Sanghi Industries (cement), McNally
Bharat (heavy engineering), Sakthi Sugars, Ind-Swift Laboratories (pharma), Manpasand Beverages,
Hindusthan National Glass (glass — CIRP admitted Oct-2021, so its pre-event report predates Schedule
III ageing and it is probably unusable).

### Why the event side is hard to grow

Two independent filters compound:

1. **FY22+ distress among listed Indian manufacturers is rare.** 9 of 17 candidates checked turned
   out to be healthy — a ~53% disqualification rate — and the healthiest cluster was auto ancillaries.
2. **Only about a quarter of filers disclose a Not Due column** — 2 of 8 distress companies and 5 of 8
   overall. The migration signal is unavailable for the rest.

Combined, roughly one candidate in eight yields a usable migration observation. Reaching n = 5 events
would mean checking ~40 more candidates.

**Two discovery routes were tried and did not work.** BSE's announcements API (`AnnSubCategoryGetData`
with `subcategory=Credit Rating`) returns every rating disclosure by month, but the headlines are
generic ("Revision in credit rating of…"), so identifying downgrades needs reading each attachment.
Keyword web search runs at roughly 50% precision. A workable route would be to fetch the ~50
attachments per month and classify them, which is mechanical but not free.

**Cheaper ways to strengthen the evidence, in order:**

1. Resolve Shivam's FY24 discrepancy with the company — converts a disputed case into a second clean
   event at near-zero cost.
2. Extend the remaining distress panels to FY22–FY25 for the MSMED-interest signal, which needs no Not
   Due column and currently stands at 5 of 7 distress companies rising against 0 of 4 controls.
3. Only then hunt new distress companies.


---

# Session 2026-09-08 (second block) — Stage-2 collection brief

Appended, not rewritten. Where this overturns an earlier conclusion it says so.

## S2.1 What was completed

- **Identity (§4.5).** The duplicate Bharat Gears identity is resolved: `BGL` and `BGL_C` were the
  same company on the same NSE symbol. Merged to one row under `BGL`, cohort `control`, with the
  abandoned-distress reasoning preserved in a new `role_history` field and all references updated in
  the other three files. All six previously `unknown` tier roles assigned, each with a recorded reason.
  CINs collected for 5 of 15 researched companies (3 new, harvested from reports opened this session).
- **Graph anchors (§5.3).** 13 counterparties that existed only as free-text strings now have company
  rows with `cohort = counterparty`. Six Indian-listed anchors had their BSE scrip codes **verified
  against the BSE API** rather than recalled.
- **Edges restructured (§5.1).** All 21 rows carry `edge_id`, resolved supplier/buyer ids, normalised
  direction, `component`, `value_basis`, `data_source` and the single-source fields. The one
  `supplied_by` row (Lava Cast → Setco) was flipped so `from_company_id` is always the supplier.
- **Edge values (§5.2).** 2 of 21 edges now carry `annual_value_cr`, both derived as a
  rating-agency-stated percentage × that supplier's own recorded revenue.
- **`backtest_panel.csv` (§7).** 32 company-year transitions, entirely real, recomputed from
  `financials.csv` rather than transcribed. It reproduces the headline: **MSMED interest rose ahead of
  6 of 8 events and in 0 of the measurable control transitions.**
- **`schema_change_request.md` (§8.6).** Five gaps written up for the engine team.
- **Cash buffer, revenue, cost base (§4.1–4.3).** Completed for **Bharat Gears (4 years) and Rico Auto
  (3 years)** only. See S2.2.

## S2.2 Why the P0 financial sweep stopped early — and why that was the right call

The plan was one automated pass per report pulling cash, investments, revenue, total expenses,
depreciation, finance costs and cost base together. The extractor worked, but **spot-checking the
labels caught three wrong values in the first five documents**:

1. Precision Camshafts FY25 "depreciation" matched the **EBITDA** subtotal line (₹110 cr instead of
   ₹57 cr) because the label appears inside it.
2. Precision Camshafts FY25 revenue came from the **consolidated** P&L while its ageing rows are
   standalone — a Rule 5 violation that would have mixed two entities in one row.
3. Balance-sheet page selection was **not stable between runs** for the same document, so
   current-investments values differed run to run.

Any of the three would have put a confidently wrong number against a real company, which is the exact
defect class the brief forbids. **The automated sweep was stopped rather than continued at speed.**
Only figures whose source line was read and verified are recorded: 7 company-years.

**Recommendation:** this work is sound but costs roughly 2–3 verified calls per document, not one.
25 remaining documents is a session's work on its own. Do not batch it blind.

## S2.3 Coverage after this session

| Field | Populated | Of |
|---|---|---|
| `cash_buffer_days` | 5 | 46 |
| revenue | 33 | 46 |
| cost base | 30 | 46 |
| CIN | 5 | 15 researched |
| edges with `annual_value_cr` | 2 | 21 |
| edges with `is_single_source = true` | **0** | 21 |

## S2.4 `is_single_source` — zero, deliberately

No primary source in this dataset states sole-source status for any real edge. Per §5.5 of the brief
it must never be inferred from the sparsity of our own edge collection, so every real edge leaves it
**empty** (unknown), not `false`. The demo's chokepoints must come from the synthetic layer.

## S2.5 Nothing overturned

No new figure collected this session contradicts an earlier conclusion. The Bharat Gears revenue now
recorded (FY23 ₹766.37 cr → FY24 ₹663.05 cr → FY25 ₹647.53 cr, a 16% decline over two years) is
consistent with its existing control classification: CARE reaffirmed and then upgraded it through
that period, which is a useful reminder that a revenue decline alone is not a distress signal.


---

# Session 2026-09-08 (third block) — verified financial sweep

Appended, not rewritten. Every figure below was read from its own labelled line under the §2 protocol
of the Session-2 brief: caption checked against the item (not a subtotal containing the word), section
header confirmed standalone vs consolidated on the page actually read, location anchored on note
numbers, and depreciation cross-checked against a second disclosure.

## S3.1 Completed

**5 companies fully swept — Shivam Autotech, Setco Automotive, Lokesh Machines, Precision Camshafts,
plus the previously-done Bharat Gears and Rico Auto — giving 19 of 46 rows with a verified
`cash_buffer_days`.** All revenue, cost-base, total-expense, depreciation and finance-cost figures for
those rows were re-read or newly read from labelled lines.

## S3.2 The calibration answer — and it is not one number

The engine's mock assumes tier-1 manufacturers hold 60–100 days. Across **19 verified company-years**,
all tier-1:

| Cohort | n | min | median | max |
|---|---|---|---|---|
| tier1 · control | 9 | 3 | 15 | 266 |
| tier1 · distress | 10 | 1 | 12 | 50 |

| Company | Cohort | FY22 | FY23 | FY24 | FY25 |
|---|---|---|---|---|---|
| Shivam Autotech | distress | 1 | 50 | 1 | 1 |
| Setco Automotive | distress | 17 | 12 | — | 12 |
| Lokesh Machines | distress | — | 12 | 12 | 17 |
| Bharat Gears | control | — | 3 | 5 | 5 |
| Rico Auto | control | — | 14 | 15 | — |
| Precision Camshafts | control | 198 | 149 | 178 | 266 |

**The headline finding is not "tier-1s hold 3–15 days." It is that the spread within tier-1 is enormous
— 1 to 266 days — and it does not separate distress from control.** Bharat Gears, a company CARE
*upgraded*, runs the thinnest buffer in the set at 3–5 days. Precision Camshafts, also a control, runs
40–80× that.

Two consequences for the engine:

1. **A single tier-level buffer default is wrong in both directions.** Substituting 80 days would make
   Bharat Gears look 16× safer than it is; substituting 5 days would make Precision Camshafts look
   catastrophic. Where a real buffer is unavailable the node must be flagged, not defaulted quietly.
2. **Low buffer is not a distress signal on its own.** It is a *transmission* parameter — how hard a
   given company is hit when a buyer stops paying — not evidence that the company is failing. The
   distress cohort's median (12 days) is *lower* than the control median (15), and that is noise, not
   signal, on n=19.

Shivam's FY23 spike to 50 days is real and explained: it held ₹57.92 cr of cash at 31-Mar-2023 against
₹0.61 cr a year later, following its optionally-convertible-debenture funding. The buffer collapsed as
that money was spent.

## S3.3 Faults the protocol caught this session

- **A formula trap, not a reading error.** Precision Camshafts presents `Total expenses (II)` *above*
  its EBITDA subtotal, so it already excludes finance costs and depreciation. The standard buffer
  denominator would have subtracted them a second time and inflated its buffer. A new column,
  `total_expenses_includes_dep_fin`, now records this per row; PreCam is the only `false` so far.
- **The entity-mixing fault was real and is now avoided.** Reading PreCam's FY25 *standalone* P&L gives
  revenue of ₹612.00 cr; the consolidated page gives ₹865.36 cr. The earlier fast extraction had taken
  the consolidated figure into a standalone row.
- **The EBITDA-caption fault was real.** PreCam's cash flow discloses only "Depreciation on ROU asset"
  separately, so its depreciation was cross-checked against Note 27's total (₹4,023.31 lakh) instead.
- **Zero depreciation mismatches.** Every cross-check performed this session agreed exactly.

## S3.4 Restatements found

- **Setco FY2023 revenue.** The FY2023 report shows ₹54,557.17 lakh; the FY2024 report's comparative
  shows ₹54,567.17 lakh — a ₹0.10 cr difference. Rule 1 applied: the row now carries its own report's
  figure (₹545.57 cr, corrected from ₹545.67 cr).
- **Shivam FY2024 expense composition.** Total expenses agree between reports (₹52,002.67 lakh), but
  the FY2025 comparative reclassifies within it — employee benefits ₹5,744.03 → ₹5,866.51 lakh and
  other expenses ₹12,352.43 → ₹12,229.95 lakh. Totals unaffected; noted because it shows Shivam
  reclassifies between line items across reports, which is the same behaviour underlying its disputed
  FY24 Not Due figure.
- Precision Camshafts and Lokesh: comparatives agreed exactly with their own-year reports. No
  restatement.

## S3.5 §5.2 resolved — the BGL repeats are genuine

`BGL FY2023` and `BGL FY2025` share `cash_and_cash_equivalents_cr = 0.06` and
`finance_costs_cr = 17.08`. Both are **rounding coincidences, not copy errors**, confirmed against the
source lakh figures:

| | FY2023 | FY2025 |
|---|---|---|
| Cash (₹ lakh, as printed) | 6.29 | 6.48 |
| Finance costs (₹ lakh, as printed) | 1,708.40 | 1,708.07 |

Both pairs round to the same two-decimal crore value. Recorded here so the pattern is not re-flagged.

## S3.6 Not completed

27 of 46 rows remain, across roughly 15 documents: Balrampur (4), Nectar (3), Neuland (3), Dhanuka (3),
Gensol (3), BHS (3), Bestagro (2), JPA (2), Rico FY22/FY25, Setco FY2024, BGL FY2022.

Two specific blockers rather than simple shortfall:

- **Setco FY2024** cannot be completed from its own report — that report is a scan with no text layer,
  and its comparative in the FY2025 report is known to be restated (revenue ₹629.73 cr in the FY24
  report against ₹640.67 cr as the FY25 comparative). Rather than mix a known-restated comparative into
  a row whose revenue comes from the FY24 report, the expense and cash components are **left empty**.
  It needs OCR of the scanned FY24 report.
- **Browser tooling became unavailable** partway through this block (repeated safety-classifier
  timeouts), which stopped the sweep before the remaining documents.

The `undrawn_credit_facilities_cr` column exists but is unpopulated — it was defined as secondary
priority and no document opened this session disclosed it on a page already being read.

## Session 2026-09-09 — browser recovered (second route), partial sweep

**Tooling.** The Chrome extension route is still dead ("extension is not connected"). A second
route works: the Browser pane on the linked computer (`Claude_Browser__*`), after granting
access to `bseindia.com`. The BSE annual-report API and in-page pdf.js parsing both work there.
One constraint is new: that pane enforces a hard 45-second limit per JavaScript call, so the
old whole-document `LOAD()` times out on reports over ~200 pages. The extractor was rebuilt as
`OPEN()` (fetch + open the PDF) plus `PARSE(key, budgetMs)` (extract pages until a time budget
is spent, resumable across calls). Page text and the parse cursor survive between calls, so a
timed-out call loses nothing — the next call continues from `next`.

### §5.1 PreCam corrigendum — RESOLVED

Precision Camshafts filed the FY2023-24 annual report twice: 3 July 2024
(`526bb0b6-…`, 313 pages) and 6 July 2024 (`9246f059-…`, 314 pages, "Corrigendum to the
Annual Report for FY 2023-24", ref PCL/SEC/24-25/027). The corrigendum is a **complete
replacement filing, not a list of corrections** — which is why no correction list was ever
found. Both were parsed in full and diffed page by page.

Exactly three pages differ, and the one extra page is the corrigendum covering letter inserted
at the front. The two substantive changes are **narrative wording only**, both in the
management message:

| | 3 July text | 6 July text |
|---|---|---|
| MEMCO, Nashik | "demonstrated **growth** in total income, **reaching** ₹50.07 Crores" | "experienced a **decline** in total income, **recording** ₹50.07 Crores" |
| EMOSS, Netherlands | "witnessed a **substantial increase** in total income, **reaching** ₹147.69 Crores … compared to ₹231.5 Crores" | "witnessed a **decline** in total income, **recorded at** ₹147.69 Crores … compared to ₹231.5 Crores" |

The rupee figures are identical in both versions (50.07, 171, 147.69, 231.5); only the
direction words were wrong — the original described a fall as a rise. **No financial statement,
note, or ageing page changed.** The four PRECAM_C rows already in `financials.csv` are
unaffected, and the §8 caveat is closed.

### Financial sweep — RICO_C completed

| Row | Revenue (₹ cr) | Total expenses | Dep (P&L / CF) | Finance | Cash + bank other | Buffer |
|---|---|---|---|---|---|---|
| RICO_C FY2022 | 1,603.08 | 1,583.37 | 74.69 / 74.69 ✓ | 36.67 | 2.35 + 12.55 | **4 d** |
| RICO_C FY2025 | 1,607.02 | 1,605.87 | 88.91 / 88.91 ✓ | 40.41 | 0.58 + 5.82 | **2 d** |

Both standalone, unit "₹ in crores" read from the statement header, section confirmed on the
page ("This is the Standalone Statement of Profit and Loss" / "Standalone Statement of profit
and loss for the year ended 31 March 2025"). Depreciation cross-checked against the cash flow
add-back: **0 mismatches**. Current investments absent from current assets in both years —
recorded as `current_investments_absent_treated_nil`, not as a disclosed nil.

RICO_C is now complete for all four years: **FY22 4 d, FY23 14 d, FY24 15 d, FY25 2 d.**

This *widens* the calibration finding rather than changing it. A control company rated
investment-grade throughout runs on a 2–15 day buffer. Cash buffer remains a scale variable,
not a stress signal, and must not be weighted as one.

### Stopped

The linked computer disconnected from the bridge mid-way through opening the Neuland FY2023
report. 21 rows verified of 46; 25 remain. No partial or unverified row was written.

### Sweep continued 2026-09-09 (desktop back online)

**A duplicate-filing trap, found and fixed.** BSE's annual-report index can return **more than one
row for the same year**, and the authoritative one is not the one with the latest
`Fld_AuthoriseDate`. Neuland's FY2023-24 has two rows: the original (5 July 2024,
`Fld_AuthoriseDate` set, `status: New`) and a **revised** filing (15 July 2024,
`Fld_AuthoriseDate` **null**, `revised_date_time` set, `status: Revised`, reason: additional BRSR
Core indicators). A naive "pick the row with a date" rule selects the **superseded** copy.
The loader now ranks candidates by `revised_date_time || Fld_AuthoriseDate` and takes the newest,
and records `status`/`resub` alongside the filing date. **Any company-year in this data set with
more than one index row must be re-checked under this rule.**

Also fixed: BSE serves at least one malformed URL (Neuland FY2023 has a stray backslash after
`AttachHis/`), which fails silently as a fetch error. Backslashes are now stripped.

**Neuland FY2024 ageing footing — resolved against the authoritative copy.** The revised
15 July copy *still* prints Others `18,874.47` and total `19,858.88` in the ageing table while
Note 17 immediately above prints `18,879.47` and `19,853.88`. The ageing components sum to
18,879.47 and 19,853.88, matching Note 17 — so the printed Others/total are wrong by ₹5.00 lakh
(a 9↔4 transposition), the revision did not correct it, and the component-derived figures already
in `financials.csv` are confirmed correct.

**A two-up page layout trap.** Neuland's FY2025 report prints the balance sheet and the P&L
**side by side on one physical page**. Reading the page by text lines interleaves the two
statements, so "Revenue from operations" is followed by "Right-of-use assets". A column-aware
reader (`COLS`) that splits text items at the page midpoint by x-coordinate was added; both
statements then read cleanly and the FY2024 comparatives reconciled exactly to the FY2024 row.

#### Rows completed this block

| Row | Revenue | Total expenses | Dep P&L / CF | Buffer |
|---|---|---|---|---|
| NEULAND_C FY2023 | 1,19,119.80 L | 98,573.32 L | 5,277.62 ✓ | 23 d |
| NEULAND_C FY2024 | 1,55,858.05 L | 1,17,035.56 L | 5,969.91 ✓ | 38 d |
| NEULAND_C FY2025 | 1,47,683.73 L | 1,22,837.62 L | 6,554.19 ✓ | 115 d |
| DHANUKA_C FY2023 | 1,70,022.00 L | 1,44,224.93 L | 1,760.67 ✓ | 26 d |
| DHANUKA_C FY2024 | 1,75,854.39 L | 1,47,475.03 L | 4,056.36 ✓ | 19 d |
| DHANUKA_C FY2025 | 2,03,515.18 L | 1,67,911.60 L | 5,546.09 ✓ | 28 d |
| BALRAMPUR_C FY2022 | 4,84,602.68 L | 4,29,106.25 L | 11,386.49 ✓ | **0 d** |
| BALRAMPUR_C FY2023 | 4,66,586.17 L | 4,33,168.38 L | 12,950.30 ✓ | 6 d |
| BALRAMPUR_C FY2024 | 5,59,374.01 L | 5,05,755.61 L | 16,636.03 ✓ | **0 d** |
| BALRAMPUR_C FY2025 | 5,41,537.83 L | 4,97,713.90 L | 17,254.33 ✓ | **0 d** |

All standalone, all units read from the statement header, every depreciation figure reconciled
to the cash flow add-back: **0 mismatches**. Each year's comparatives were checked against the
prior year's extracted row — all reconciled, no restatements found in this block.

#### The cash-buffer finding is now settled

Balrampur Chini is the **strongest control in the data set** — investment grade throughout, trade
payables at 5.0% of revenue against Bajaj Hindusthan's 59.0% — and it runs a **0-day cash buffer
in three of four years** (₹3.3 cr of cash against ₹4,150 cr of annual operating cost). It funds
itself with ₹2,200–3,100 cr of inventory and working-capital limits, not cash. Its FY2022 report
discloses no undrawn facility figure, so the liquidity that actually backs it is not in the
filings at all.

Across 31 verified rows the buffer spans **0 to 266 days**, and the two extremes are both
controls. `cash_buffer_days` is a working-capital-structure variable, not a stress signal. The
engine must not weight it as one, and the mock's 60–100 day tier-1 assumption should be removed
rather than re-calibrated.

Cost base note: Dhanuka and Balrampur FY2025 report both materials consumed **and** purchases of
stock-in-trade, recorded as `cost_base_type = materials_plus_purchases`. Comparing their cost
base to a materials-only filer's is invalid.

### Sweep completed 2026-09-09 — 44 of 46 rows verified

The financial sweep is now finished to the extent the sources allow. Two rows remain empty, both
deliberately (below). Every value was read from its own labelled line except where noted, every
depreciation figure was cross-checked against the cash flow add-back, and every year's
comparatives were reconciled against the previously extracted row.

#### Rows completed in this block

| Row | Revenue | Total expenses | Dep P&L / CF | Buffer |
|---|---|---|---|---|
| NECTAR FY2023 | 15,236.69 M | 16,075.42 M † | 591.19 ✓ | 4 d |
| NECTAR FY2024 | 16,840.86 M | 16,803.85 M † | 607.18 ✓ | 5 d |
| NECTAR FY2025 | 16,699.74 M | 18,364.99 M † | 623.89 ✓ | 4 d |
| BHS FY2022 | 5,569.09 Cr | 5,812.58 Cr | 214.63 ✓ | 3 d ‡ |
| BHS FY2023 | 6,302.32 Cr | 6,470.68 Cr | 213.17 ✓ | 1 d |
| BHS FY2024 | 6,076.56 Cr | 6,185.27 Cr | 212.87 ✓ | 3 d |
| GENSOL FY2024 | 904.01 Cr | 836.39 Cr | 72.44 ✓ | 178 d |
| GENSOL FY2023 | 371.00 Cr | 344.31 Cr | 25.03 ✓ | 351 d |
| BESTAGRO FY2023 | 1,49,996.20 L | 1,44,303.80 L | 515.82 ✓ | 21 d |
| BESTAGRO FY2024 | 17,983.57 M | 17,855.64 M | 67.02 ✓ | 5 d |
| JPA FY2022 | 4,22,006 L | 5,82,780 L | 38,572 ✓ | 31 d |
| JPA FY2023 | 3,95,468 L | 4,65,570 L | **23,525 vs 36,605 ✗** | **none** |
| SETCO FY2024 | 64,066.71 L | 78,255.06 L | 3,465.10 ✓ | 9 d |
| BGL FY2022 | 72,944.16 L | 70,250.24 L | 2,039.44 ✓ | 5 d |

† total expenses printed without a caption — identity confirmed twice (components sum, and
total income minus it equals stated PBT). ‡ excludes ₹770.13 cr of pledged unquoted equity.

**Depreciation cross-check: 13 of 14 matched exactly; 1 disagreed and was recorded as neither.**
JPA FY2023's P&L depreciation covers continuing operations only while its cash flow add-back
covers total operations. Per the brief the row keeps no depreciation figure and no buffer, and
carries `DEP_MISMATCH pl=23525.0 cf=36605.0`. The mismatch is explained, but it is still a
mismatch, and the explanation is itself the finding: this company-year cannot be compared with
the year before it.

#### The two rows left empty, and why

- **GENSOL FY2022** — its own FY2022 and FY2023 annual reports are image-only PDFs with no text
  layer, and FY2022 predates the company's 1 April 2022 Ind AS transition, so even a successful
  OCR would produce previous-GAAP figures that cannot sit in the same series as FY2023-FY2024.
  Flagged `ROW_NOT_EXTRACTED_IMAGE_PDF_AND_GAAP_BREAK`.
- **JPA FY2023** — depreciation mismatch above.

Setco FY2024 was recovered despite its own report being a 29 MB image-only scan, by taking the
FY2025 report's consolidated comparative column; the source field records this.

#### §5.3 Tata Motors identity — RESOLVED, and the naive answer is wrong

Verified against the BSE `ComHeader` and `PeerSmartSearch` APIs:

| | scrip 500570 | scrip 544569 |
|---|---|---|
| ticker | TMPV | TMCV |
| ISIN | INE155A01022 | INE1TAE01010 |
| BSE industry | Passenger Cars & Utility Vehicles | **Commercial Vehicles** |
| current name | Tata Motors Passenger Vehicles Limited | **Tata Motors Limited** |

The **passenger-vehicle** company kept the original listing and ISIN and was renamed; the
**commercial-vehicle** business was demerged onto a new listing and took the "Tata Motors Limited"
name. So the company now called "Tata Motors Limited" is *not* the one that filed Tata Motors'
FY2022-FY2025 annual reports.

Worse for us: BSE displays the **current** name against **historic** filings — all of scrip
500570's FY2022-FY2025 annual reports now read "TATA MOTORS PASSENGER VEHICLES LIMITED". Resolving
a counterparty by the name the exchange shows today gives the wrong entity.

Setco supplies medium and heavy **commercial**-vehicle clutches. Edge E013 is dated FY2025, when
that business sat inside the undivided company on scrip 500570, so the edge is correct as it
stands; a note records that any FY2026+ edge must point to the new `TATAMOTORS_CV` node instead.
Edge E017 (Autoline, sheet-metal assemblies) is left pointing at the undivided company with an
explicit note that which successor inherits it is **not** established — sheet metal goes to both
vehicle lines and we have no evidence either way. CINs for both entities could not be obtained
from a primary source and are left empty rather than guessed.

#### Final verification pass

```
cash_buffer recompute:      44 verified, 0 failed
duplicate company-years:    none
orphan ids (financials):    none
orphan ids (edges):         none
buffer coverage:            44 of 46
flagged rows:               17
panel rows:                 32   buffer cells populated 62 of 64
companies:                  29   edges: 21
```

#### The headline result

`cash_buffer_days` does not discriminate distress from control. With 22 verified company-years on
each side, **AUC = 0.569** — a coin flip is 0.500.

| | n | min | Q1 | median | Q3 | max |
|---|---|---|---|---|---|---|
| distress | 22 | 1 | 3.0 | 10.5 | 18.0 | 351 |
| control | 22 | 0 | 3.75 | 14.5 | 57.25 | 266 |

The cohorts interleave at both extremes. The lowest buffers in the data set belong to a **control**
(Balrampur Chini: 0, 0, 0, 6 days — investment grade throughout, trade payables at 5.0% of
revenue). The highest belongs to a **distress** company: **Gensol Engineering at 351 days in
FY2023**, the year before it collapsed. A large cash buffer offered no protection there, which is
the sharpest possible illustration of why this field must not be scored.

This does not weaken the payment-stress result — it isolates it. The MSMED interest signal still
rose ahead of 6 of 8 events and 0 of the measurable control transitions. What has changed is that
we can now say, with measured evidence rather than assumption, that the balance-sheet liquidity
proxy the mock relied on carries no signal at all, and the engine should drop it as an input and
keep it only as displayed context.
