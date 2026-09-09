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
