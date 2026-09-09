# FrayFuse — Data Dictionary and Comparability Rules

**Version 2.1 · Stage 1B-2  · Last updated 2026-09-08**

This document is the contract for the FrayFuse evidence set. If you are adding a company, adding an
industry, or building a model on these files, read sections 2 and 5 first — they are where silent
errors come from.

---

## 1. What this dataset is

Four CSVs describing Indian listed manufacturers that suffered a documented distress event in
FY2021-22 or later, and how their supplier-payment behaviour looked **before** that event.

| File | Grain | One row is |
|---|---|---|
| `companies.csv` | company | one company, its classification and its four validity flags |
| `financials.csv` | company × financial year | payment figures for one company in one financial year |
| `distress_events.csv` | company × event | one dated distress event (a company may have more than one) |
| `edges.csv` | company × counterparty × year | one supply-chain relationship |
| `findings.md` | — | the narrative analysis and session log |

`company_id` joins all four files. It is a short uppercase code, stable forever once assigned.

---

## 2. The five rules that prevent silent errors

These exist because each one has already caused, or nearly caused, a wrong number in this dataset.

**Rule 1 — Read each financial year from its own annual report.**
Do not take a year from a later report's comparative column. Companies restate. Shivam Autotech's FY24
"Not Due" figure was ₹0.04 lakh in the FY24 report and ₹639.06 lakh in the FY25 report's comparative —
the same year, restated by a factor of ~16,000 on the line that carries the signal. The `report_url`
and `report_filing_date` on every row tell you which report the figure actually came from. Where a row
*is* sourced from a comparative column, `source_page` says so explicitly.

**Rule 2 — Empty and `nil` are different, and neither is zero-by-assumption.**
- empty cell = the source did not disclose this line at all
- `nil` = the source explicitly printed a zero or a dash
- a number = the source printed that number
Never infer, never estimate, never carry a figure across from a related entity. An empty cell is a
fact about disclosure; a guessed number is a defect.

**Rule 3 — Every figure is in ₹ crore, regardless of how the company reported it.**
`units_as_reported` records the source unit (`lakh`, `million`, `crore`). Conversions applied:
lakh ÷ 100, million ÷ 10. Where rounding to 2 decimals would turn a real non-zero figure into `0.00`,
more decimals are used (Shivam FY24 `msme_not_due` = `0.0004`). Do not re-round these away.

**Rule 4 — Never compare an ageing bucket across companies without checking two flags.**
See section 5. `has_not_due_column` and `ageing_basis` both change what "under 1 year" means.

**Rule 5 — Never mix `basis` within a row.**
`standalone` and `consolidated` are different entities. Setco Automotive is recorded consolidated
because its standalone entity is a holding shell (₹0.35 crore of trade payables) after the operating
business moved to a subsidiary. Everything else here is standalone.

---

## 3. `companies.csv`

| Field | Type | Meaning |
|---|---|---|
| `company_id` | code | Stable uppercase join key |
| `name` | text | Legal name as it appears in the filing |
| `cin` | text | Corporate Identity Number, verbatim from a filing. Empty if not verified against one |
| `bse_code` | text | BSE scrip code. **Verify before use** — needed for the BSE API in section 7 |
| `nse_symbol` | text | NSE trading symbol |
| `industry_group` | enum | Broad comparability bucket — see below |
| `sector` | text | Finer sector label |
| `product_category` | text | What the company actually makes |
| `cohort` | enum | `distress` or `control` |
| `tier_role` | enum | `oem` / `tier1` / `tier2` / `unknown` — position in the supply chain |
| `event_valid` | bool | A distress event is documented, dated, and from a credible source |
| `signal_valid` | bool | Payment figures were actually extracted into `financials.csv` |
| `backtest_valid` | bool | Payment data exists that was **published before** the event — see section 6 |
| `graph_valid` | bool | Sector plus at least one named counterparty identified |
| `abandoned_reason` | text | Why the company was dropped. Empty if fully researched |
| `distress_mechanism` | enum | **What kind of failure this was** — see below. Critical for scoring |
| `ageing_basis` | enum | `due_date` or `transaction_date` — see section 5 |
| `has_not_due_column` | bool | Whether the ageing table separates "Not Due" — see section 5 |
| `msme_book_material` | bool | Whether MSME dues are ≥5% of total trade payables |
| `msme_pct_of_trade_payables` | number | MSME dues as % of total trade payables, latest pre-event year |
| `signal_path` | enum | Which signal actually fired — see the vocabulary below and section 6 |
| `notes` | text | Per-company caveats. **Always read before using a company's rows** |

### `industry_group` vocabulary

`automotive` · `industrial_machinery` · `chemicals` · `energy_infrastructure` · `metals` ·
`textiles` · `cement` · `food_agri` · `pharma` · `other`

Add a value only when no existing one fits, and record the addition in section 9. `industry_group` is
the unit at which cross-company comparisons should be made by default; comparing across groups
requires the checks in section 5.

### `signal_path` vocabulary

| Value | Meaning |
|---|---|
| `msme_not_due_migration` | Share of MSME dues past due rose while the total stayed flat |
| `msme_balance_growth` | MSME payables rose sharply relative to revenue |
| `msmed_interest_accrued` | MSMED interest due or accrued went nil → positive, or jumped |
| `nonmsme_ageing_growth` | Non-MSME aged buckets grew; used where the MSME book is immaterial |
| `payables_outgrowing_revenue` | Total payables grew materially faster than revenue |
| `mixed_partial` | Some indicators fired and others moved the other way — read the notes |
| `none_fired` | No signal fired. A legitimate result — read with `distress_mechanism` |
| `quiet_as_expected` | **Control cohort**: the signals stayed quiet, as a healthy company should |
| `false_positive_risk` | **Control cohort**: one or more signals fired on a company that is demonstrably healthy. Read the notes — these rows are how signal thresholds get calibrated |
| `not_researched` | Company abandoned before extraction |

### How the flags behave for `cohort = control`

Controls have no distress event, so three fields are read differently:

| Field | Meaning for a control |
|---|---|
| `event_valid` | The company's **non-distress status** is documented by a dated rating action or equivalent evidence |
| `backtest_valid` | Payment data exists for the same observation window as the matched distress company |
| `matched_to` | `company_id` of the distress company this control is matched against |
| `distress_mechanism` | Always `not_applicable` |

A control must be in the **same `industry_group`**, a **comparable size band**, and cover the **same
financial years** as its match. Where it also shares the matched company's `ageing_basis` and
`has_not_due_column` conventions — as Dhanuka does with Best Agrolife — the pair is directly
comparable with no adjustment, which is the whole argument for industry-matching.

### `distress_mechanism` vocabulary — and why it matters

| Value | Meaning | Should the payment signal fire? |
|---|---|---|
| `trading_stress` | Operating losses, margin collapse, working-capital squeeze | **Yes** — this is what FrayFuse models |
| `external_shock` | A sudden outside event: sanctions, customer loss, regulation | Usually yes, with a shorter lead time |
| `governance` | Fraud, fund diversion, falsified records | **No** — cash can vanish without suppliers being stretched |
| `financial_structure` | Default driven by debt structure, group exposure or a specific instrument rather than operations | **Not reliably** — the company may still be paying trade suppliers normally |
| `not_applicable` | Company abandoned; no valid event | — |

**Score the back-test only on `trading_stress` and `external_shock`.** Including `governance` or
`financial_structure` cases makes the model look worse at something it never claimed to do. Two worked
examples, both of which failed to fire and both of which *should* have failed to fire:
- **Gensol Engineering** (`governance`) — cash was diverted; suppliers were never stretched.
- **Bajaj Hindusthan Sugar** (`financial_structure`) — defaulted on a convertible-debenture instalment
  with ₹5,383 crore locked in group companies, while its trade payables actually *fell* 20% and its
  payables turnover ratio *improved*. CARE's own rationale made no mention of payables stress.

---

## 3b. The real / synthetic boundary

Transcribed from the Stage-2 collection brief so the rule outlives any one session. **Every node and
edge carries `data_source`. Fill it at row level, never at file level.**

**The test.** Ask of every field: *if this number were wrong, would we be making a false claim about a
real, identifiable company — or merely making the demo less plausible?* False claim → must be real, or
empty, never modelled. Less plausible → synthetic is fine, if labelled.

**Must be real (or empty):** every field in `financials.csv`; everything in `distress_events.csv`;
`report_url`, `report_filing_date` and `source_page` on every row; the comparability flags
(`has_not_due_column`, `ageing_basis`, `basis`, `msme_book_material`, `cost_base_type`);
`cash_buffer_days` for named companies; identity fields; edges between two real named companies; and
`is_single_source = true` on any real edge.

**Should be synthetic:** all tier-2 and tier-3 nodes and the edges below tier-1; `component` strings,
`is_single_source` and `annual_value_cr` on synthetic edges; `employees` anywhere; and the 400-node
scale itself. The real cohort is ~28 nodes; everything else is generated by the engine team.

**The grey zone — a real company with a field we cannot find: leave it empty.** Do not model it, do
not carry it across from a peer. If the engine needs a value it substitutes one at runtime and flags
the node — a visible modelling decision, not a fabricated fact frozen into a data file.

**The one legitimate derivation:** `annual_value_cr` = a disclosed percentage × that company's real
revenue. Record `value_basis = derived_from_disclosed_pct` or `rating_agency_stated_pct` so it is
never mistaken for a disclosed amount.

**Never synthetic under any circumstances:** the `data_source` flag itself; any rupee figure shown
next to a real company's name; any distress event, rating action or date; any statement that a real
company is a sole source.

### A documented judgement: absent lines in an exhaustive block

A balance sheet's current-assets block is exhaustive. Where "Current investments" does not appear in
it, the company held none, and `current_investments_cr` is recorded as `nil` with
`cash_components_basis = current_investments_absent_treated_nil`. This is the one place we treat
absence as zero, it is flagged per row, and it is reversible. Everywhere else, absence stays empty.

---

## 4. `financials.csv`

One row per company-year. 29 columns.

**Identity and provenance**

| Field | Meaning |
|---|---|
| `company_id`, `fy` | Join key and financial year, written `FY2024` = year ended 31-Mar-2024 |
| `report_url` | The exact document the figures were read from |
| `report_filing_date` | When that document became public. Used for the temporal-leakage check |
| `source_page` | Note number and page. Says explicitly when a row came from a comparative column |
| `units_as_reported` | `lakh` / `million` / `crore` — the source unit before conversion |
| `basis` | `standalone` or `consolidated` |
| `has_not_due_column` | See section 5 |
| `ageing_basis` | See section 5 |

**Schedule III trade-payables ageing** (the point-in-time snapshot at 31 March)

`msme_unbilled`, `msme_not_due`, `msme_under_1yr`, `msme_1_2yr`, `msme_2_3yr`, `msme_over_3yr`,
`msme_total`, `nonmsme_total`, `disputed_total`, `total_trade_payables`

Buckets should sum to `msme_total` within rounding. The 1yr+ buckets are near-empty across this
cohort — capture them, but an empty aged bucket is **not** evidence of health.

**MSMED Act note** (whole-year flow figures, which cannot be tidied up before year end)

| Field | Source line |
|---|---|
| `msmed_principal_unpaid_year_end` | Principal remaining unpaid to any supplier at year end |
| `msmed_interest_due_unpaid` | Interest due on that unpaid principal |
| `msmed_principal_paid_beyond_appointed_day` | Principal paid late during the year. **Empty in all 14 rows — see section 6** |
| `msmed_interest_paid_u_s16` | Interest actually paid under section 16 |
| `msmed_interest_accrued_unpaid` | Interest accrued and remaining unpaid at year end |
| `msmed_interest_due_on_payments_made_beyond_appointed_day` | **Added in v1.0.** Interest due for the period of delay on payments that *were* made but beyond the appointed day |

That last field is an addition to the original brief's schema. It is the best available proxy for the
missing primary signal: it can only be non-zero if the company actually paid suppliers late during
the year, so like a flow figure it cannot be window-dressed at year end.

**Normalisation**

`revenue_standalone`, `revenue_consolidated`, `cost_of_materials_consumed`,
`trade_payables_turnover_ratio`

Populate the revenue field matching `basis`; leave the other empty. Some companies disclose no
payables turnover ratio (Best Agrolife) or report "Purchase of stock-in-trade" instead of cost of
materials (Best Agrolife again) — leave those empty rather than substituting a different line.

### Columns added in v2.0 (Stage-2 collection brief)

**Cash-buffer components** — raws are stored so the formula can be revised without re-collecting.

| Field | Meaning |
|---|---|
| `cash_and_cash_equivalents_cr` | Balance sheet, current assets, as printed |
| `bank_balances_other_cr` | "Bank balances other than cash and cash equivalents", if shown separately |
| `current_investments_cr` | Current investments. `nil` where the current-assets block has no such line (see §3b) |
| `total_expenses_cr` | P&L total expenses |
| `depreciation_amortisation_cr` | P&L. Note: grab the expense line, **not** an EBITDA subtotal that contains the word |
| `finance_costs_cr` | P&L |
| `cash_buffer_days` | `(cash + bank_other + current_inv) / ((total_expenses − depreciation − finance_costs) / 365)`, integer. **Either fully computed or empty — never partial.** |
| `cash_components_basis` | `all_disclosed` \| `current_investments_absent_treated_nil` |

**Cost base**

| Field | Meaning |
|---|---|
| `purchases_stock_in_trade_cr` | For trading-heavy filers that report purchases rather than materials consumed |
| `cost_base_type` | `materials_consumed` \| `stock_in_trade` \| `both` |

**MSMED note shape** — added because the "primary signal" was assumed extinct after seven companies
and then found in Bharat Gears, which discloses it as its own named line. Check the wording company by
company; never assume absence.

| Field | Meaning |
|---|---|
| `msmed_interest_lines_disclosed` | pipe-separated: `accrued_unpaid` \| `due_unpaid` \| `due_on_payments_beyond_appointed_day` \| `none` |
| `msmed_note_format` | `tabular` \| `narrative` \| `absent` |
| `msmed_note_verbatim` | the exact line label as printed, quoted |

### `companies.csv` additions

`data_source` (`real` \| `synthetic`), `entity_status` (`listed_india` \| `unlisted_india` \|
`foreign_listed` \| `foreign_private`), `role_history` (why a company changed cohort — used for the
merged Bharat Gears identity).

`cohort` gains a third value: **`counterparty`** — a graph anchor added for its position in the
network, with no signal extraction performed.

`tier_role` definitions, applied consistently: **`tier0`** an anchor/end-producer whose output goes to
end customers or distribution and which has its own upstream supplier base; **`tier1`** a direct
supplier to a tier0; **`tier2`/`tier3`** deeper. It is an analytical assignment, not a disclosed fact,
and the reason is recorded per company.

### `edges.csv` — restructured in v2.0

`edge_id`, `from_company_id`, `to_company_id` (resolved ids; `from_` is **always the supplier**),
`direction_normalised` (`supplier_to_buyer` \| `not_applicable`), `component`, `annual_value_cr`,
`value_basis` (`disclosed_amount` \| `derived_from_disclosed_pct` \| `rating_agency_stated_pct` \|
`not_available`), `is_single_source`, `single_source_evidence`, `data_source`, `notes`.

`from_company` and `to_company` keep the **as-disclosed name strings** — that is provenance and is not
overwritten by the resolved ids.

**`is_single_source` is empty on every real edge and must stay that way** unless a primary source says
so verbatim. Empty means unknown. `false` is itself a claim that alternatives exist. Never infer it
from the sparsity of our own edge collection — that would manufacture the product's headline finding
out of our own ignorance.

`relationship_type = concentration_disclosure_unnamed` marks a real disclosed percentage against an
unnamed counterparty. Those rows have no `to_company_id` by design and are **not** graph edges.

### Columns added in v2.1 (Session-2 verified sweep)

| Field | Meaning |
|---|---|
| `undrawn_credit_facilities_cr` | Committed but unutilised working-capital limits. A company with 3 days of cash and large undrawn lines is not as fragile as the cash figure implies |
| `undrawn_source` | `rating_rationale` \| `annual_report_note` \| `not_disclosed` |
| `plausibility_flags` | Pipe-separated gate hits: `BUFFER_<n>d` (buffer <2 or >400), `DEP_GT_25PCT`, `FIN_GT_20PCT`, `TEXP_VS_REV_GT_40PCT`, `DEP_MISMATCH pl=… cf=…`. **A flag is a "read this row before using it" marker, not an error** |
| `total_expenses_includes_dep_fin` | `true` \| `false`. **Load-bearing for the cash-buffer formula** — see below |

### `total_expenses_includes_dep_fin` — a formula trap

Most filers present `Total expenses` **including** finance costs and depreciation, so the operating
cash cost is `total_expenses − depreciation − finance_costs`.

Precision Camshafts does not. It presents `Total expenses (II)` **above** an EBITDA subtotal, with
finance costs and depreciation disclosed *below* it. Its `Total expenses` already excludes both.
Applying the standard formula would subtract them twice and understate the denominator, inflating the
buffer.

**Always read this flag before recomputing `cash_buffer_days`.** Where it is `false`, the denominator
is `total_expenses` as printed, with no subtraction.

### The depreciation cross-check

Every `depreciation_amortisation_cr` in v2.1 was verified against a second disclosure of the same
figure — normally the cash-flow add-back, or the depreciation note where the cash flow presents it
differently (Precision Camshafts discloses only "Depreciation on ROU asset" separately in its cash
flow, so Note 27's total was used). Where the two disagreed the value was **not recorded** and the row
carries `DEP_MISMATCH`.

This exists because a keyword match previously captured an EBITDA subtotal caption containing the word
"depreciation" instead of the expense line — ₹110 cr against a true ₹57 cr.

---

## 5. Comparability — the three traps

Everything in this section is a way to get a confidently wrong answer.

### Trap 1 — the missing "Not Due" column

Some filers omit it. Their "less than 1 year" figure then contains **both** amounts not yet due and
amounts overdue, so it is not comparable with a filer that separates them. A healthy company can be
made to look badly overdue, or a stressed one to look normal.

Check `has_not_due_column` before comparing `msme_under_1yr` across companies.

- `true`: Shivam, Setco — **2 of 8**
- `false`: Lokesh, Gensol, Best Agrolife, Bajaj Hindusthan Sugar, Nectar, Jaiprakash Associates

Most filers omit it. Treat its presence as the exception, not the norm.

### Trap 2 — the ageing clock starts in different places

Schedule III says buckets run from the **due date of payment**. Best Agrolife instead ages **from the
date of transaction**. A 60-day invoice on 45-day terms is 60 days old on a transaction-date clock and
15 days overdue on a due-date clock. These are different quantities with the same column name.

Check `ageing_basis` before comparing any bucket across companies.

- `due_date`: Shivam, Lokesh, Setco, Gensol, Bajaj Hindusthan Sugar, Nectar
- `transaction_date`: Best Agrolife, Jaiprakash Associates

### Trap 3 — the MSME book can be too small to carry a signal

Where MSME dues are a rounding error, every MSMED-based signal returns nil and the company looks
pristine. Best Agrolife's MSME book is ₹0.15 crore (0.04% of trade payables) with every MSMED line nil
— yet its payables grew three times faster than revenue.

Check `msme_book_material` before concluding "no deterioration". Where it is `false`, use the
non-MSME path in section 6.

**The threshold gates levels, never growth.** Nectar Lifesciences sits at 2.59% — `msme_book_material`
is `false` — yet its MSME payables rose **583%** in the pre-event year, and that was the clearest
signal the company produced. Use `msme_book_material` to decide whether a *level* or *share* is
comparable across companies. Never use it to suppress a growth signal.

### Cross-industry comparisons

Within an `industry_group`, compare levels and ratios directly once traps 1–3 are cleared.

Across `industry_group`s, compare **changes and ratios, never levels**. Payables-to-revenue is
structurally different by industry: an agrochemical trader running 20% of revenue in payables is
normal; an auto tier-1 at 20% is not. The comparable quantities across industries are:
- year-on-year change in the share of MSME dues that are overdue
- year-on-year change in payables ÷ revenue (or ÷ purchases)
- direction of the MSMED interest lines (nil → positive is the strongest cross-industry signal,
  because it is a statutory admission and unit-free)

---

## 5b. Industry-specific rules

**The single most dangerous assumption in this dataset is that "trade payables" means the same thing
in every industry. It does not.** Check this section before adding a company from a new
`industry_group`, and add a subsection when you find a new quirk.

### Sugar (`food_agri`) — the signal is not in trade payables at all

A sugar mill's largest supplier obligation is cane price dues to farmers. These are **statutory**, not
commercial, and they do not sit in trade payables. In Bajaj Hindusthan Sugar's FY24 accounts,
₹2,361 crore of the ₹2,494 crore in "Other payables" (Note 27, *other current liabilities*) is cane
price dues routed through a statutory cane-price escrow account under the UP Sugar Cane (Regulation of
Supply and Purchase) Act, 1953. Trade payables of ₹3,585 crore contain essentially none of it, and the
MSME book is 0.05% of the total.

**Refined by the control (Balrampur Chini Mills, added v1.3):** cane arrears show up in **both**
places for a stressed miller. Bajaj Hindusthan carries ₹3,541 crore in its under-1-year trade-payables
bucket *and* ₹2,361 crore in the escrow account. Balrampur, healthy and of comparable scale (₹5,594
crore revenue vs ₹6,077 crore), carries trade payables of just **5.0% of revenue against Bajaj
Hindusthan's 59.0%** — a ten-fold difference within one industry, and the single strongest
discriminator in the dataset.

Consequences: (a) **payables ÷ revenue is the signal to use for sugar**, and it works extremely well;
(b) the trade-payables ageing alone still under-states the position, so cane arrears in other current
liabilities must be captured separately for any sugar company added here. The same caution applies to
any industry where a statutory or regulated payable dominates.

### Automotive (`automotive`) — the reference case

MSME books are material (9–27% of trade payables here), ageing runs from due date, and named OEM
customers are recoverable from awards pages and MD&A. This is the industry the signal was designed
around and where it behaves best. Treat other industries' results as needing an explicit path, not as
a default.

### Agrochemicals / trading-heavy models (`chemicals`)

Companies that buy formulations rather than raw materials may report "Purchase of stock-in-trade"
instead of cost of materials consumed, and may age from transaction date. Normalise by revenue, not by
cost of materials, and check `ageing_basis`.

### Pharmaceuticals (`pharma`)

MSME books can be small in level but move violently — Nectar's went from ₹1.59 crore to ₹10.86 crore
in one year on a ₹420 crore payables book. Some filers present the MSMED disclosure as **narrative
prose rather than a table**, giving only principal unpaid and section-16 interest; the remaining MSMED
fields are then genuinely absent and must be left empty, not `nil`.

### Cement and heavy EPC (`cement`)

Long project cycles put a large share of payables in the 1-year-plus buckets as a matter of course —
about a third of Jaiprakash Associates' non-MSME payables are over a year old in a normal year. **The
aged buckets are not an anomaly signal in this industry; only their rate of change is.** These filers
may also split payables into current and non-current, and their ageing table may cover only one of
those, or may fold in liabilities held for sale. Record the exact scope in `source_page` and never
reconcile to the balance-sheet total without checking it.

### Any industry — the checklist before you trust a row

1. Is there a large non-trade supplier liability (statutory dues, escrow accounts, farmer or grower
   arrears, regulated pass-throughs)? If yes, the trade-payables signal is incomplete.
2. Is the MSME book material (`msme_book_material`)? If no, use the non-MSME path.
3. Does the ageing run from due date or transaction date?
4. Is there a Not Due column?
5. Is the company's cost base "materials consumed" or "stock-in-trade"?

---

## 6. Signal definitions and the fallback ladder

### What the original brief specified, and what actually exists

The brief's primary signal was `msmed_principal_paid_beyond_appointed_day`. **It is empty in all 14
company-years in this dataset.** Small-cap Indian filers either omit the line, or bundle it into a
combined sentence with interest paid under section 16 and report the pair as nil. The large,
well-resourced filers that motivated the original brief (Motherson Sumi, Gabriel) are not
representative of distressed small-caps.

### The ladder actually used, in priority order

| # | Signal | Fires when | Control-tested? |
|---|---|---|---|
| 1 | **MSMED interest direction** — the largest of (accrued & unpaid / due on unpaid principal / interest due on payments made beyond the appointed day) rises year on year | Any upward move | **Yes — strongest, and quantified.** Pre-event: rose in **6 of 8**. Controls: rose in **0 of 7** transitions. Needs no Not Due column, so it is available for every company. Caveat: two controls report a *frozen* accrued figure (Bharat Gears 2.37 three years running; Dhanuka 13.65), so trust a rise, not the absence of movement |
| 2 | **Not Due → under-1-year migration** | Share of MSME dues past due rises **more than +20 pp** year on year | **Yes, quantified on a FY22–FY25 panel.** 18 no-event transitions, maximum **+15.5 pp**; 2 pre-event transitions, **+25.2 and +22.1 pp**. Complete separation, 6.6 pp margin. Note the null is strongly asymmetric — healthy companies fall as far as −62.9 pp but only one of eighteen rose above +10 pp. Caveat: n = 2 events, and one of those (Shivam) is disputed by a restatement |
| 3 | **Payables ÷ revenue rising** while matched controls fall | Used where the MSME book is immaterial | **Yes.** Distress +4.0 to +5.2 pp; all three tested controls −1.8 to −2.2 pp |
| 4 | **Non-MSME aged-bucket growth, normalised** | Where `msme_book_material` is false | Partially — Best Agrolife ×4 vs Dhanuka +7% |
| — | ~~MSME balance growth~~ | **RETIRED — see below** | **Failed.** Control Bharat Gears +629% vs distress Nectar +583% |
| — | *(context only)* trade payables turnover ratio | — | Improved pre-event in two of three auto distress cases |

### Retired signal: MSME balance growth

Do not use year-on-year growth in the MSME payables balance as a distress signal. Bharat Gears — a
company CARE **upgraded** — posted +629% in FY24, higher than distress case Nectar's +583%. Four
companies across four industries show large FY24 MSME jumps (Lokesh +3,544%, Bajaj Hindusthan
+1,560%, Bharat Gears +629%, Nectar +583%), including a healthy control.

**Working hypothesis, not yet verified:** this is a reclassification effect, not a payment effect.
Section 43B(h) of the Income Tax Act took effect for FY2024 and gave buyers a strong incentive to
identify and register MSME vendors properly, moving balances from "Others" into "MSME" without any
change in payment behaviour. Bharat Gears is consistent with this — its MSME balance rose 7.3× while
its *total* trade payables **fell** 8%. Someone should confirm the statutory cause before the FY24
comparison is used for anything. Until then, **treat any FY23→FY24 MSME level change as
uninterpretable** and rely on shares, ratios and flow figures instead.

Signal 4 is deliberately demoted. It **improved** during the pre-event window for Shivam (2.43 → 2.85)
and Setco (3.49 → 3.53), and Best Agrolife does not disclose it. Treating it as a signal would have
produced two false negatives out of three.

`signal_path` = `none_fired` records a company where no signal fired. That is a legitimate value, not
a gap — read it together with `distress_mechanism`.

### The temporal-leakage rule

`backtest_valid` is `true` only if payment data was **published before** the event.

`days_between_ar_and_event` in `distress_events.csv` is the check: **positive means the report
preceded the event**; negative means that report cannot be used to claim prediction. Compare the
report's *publication* date, not merely the board-approval date — Shivam's FY25 statements were
approved 12-May-2025, but the ageing and MSMED notes only reached the public with the annual report on
14-Aug-2025, three weeks after the event.

---

## 7. Sources and retrieval

**Source hierarchy for events**, most to least preferred:
`rating_rationale` > `exchange_disclosure` > `nclt_ibbi` > `auditor_report` > `annual_report` > `press`

**Retrieval playbook** (all verified working as of 2026-09-08):

1. **Find annual reports and their filing dates** —
   `https://api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w?scripcode=<bse_code>`
   returns every report BSE holds, each with a PDF URL and `Fld_AuthoriseDate`, the date BSE received
   it. That date is the correct `report_filing_date`. An empty `Table` means the scrip code is wrong,
   not that no reports exist.
2. **Extract from the PDF without downloading it** — load pdf.js from cdnjs inside a `bseindia.com`
   page, fetch the report same-origin, scan for a keyword, and return only the two or three relevant
   pages as text. Costs a few hundred tokens instead of a whole report.
3. **Rating agencies** — CARE and ICRA serve small rationale PDFs that fetch directly. CRISIL requires
   a real browser (it returns HTTP 406 to automated fetchers) and works fine through one; take bounded
   ~2,000-character text slices rather than whole pages.
4. **Scanned reports** — roughly one in six has no text layer. Download, render at 350–400 dpi, OCR
   with tesseract, then **verify against a later report's comparative column** before trusting it.

**Known blocked routes — do not retry:** container and device `curl` (proxy 403 on all these domains),
WebFetch on large PDFs (truncates around page 45; HTTP 413 above 30 MB), Google Drive
(`ROBOTS_DISALLOWED`), MSME Samadhaan (no public case search by buyer), data.gov.in (robots),
MCA21 MSME Form I (paid, per-company).

**Candidate discovery warning:** a rating-agency press release that surfaces in a search for
"downgrade" is usually a reaffirmation or an upgrade. Six of eleven candidates were disqualified this
way. Always read the rating-action table before adding a name to the shortlist.

---

## 8. Per-company caveat register

Read alongside the `notes` column in `companies.csv`.

| Company | Caveat |
|---|---|
| **SHIVAM** | FY24 Not Due and interest-accrued figures **restated** in the FY25 report. Rows use the FY24 report. Both reports carry a footnote asserting no MSME amounts are overdue, directly contradicted by their own ageing tables — do not read that footnote as evidence of health |
| **LOKESH** | No Not Due column. Its `msme_under_1yr` is not comparable with Shivam's or Setco's |
| **SETCO** | Recorded **consolidated**; standalone is a holding shell. FY24 report was scanned and OCR'd, then verified against the FY25 comparative. FY24 revenue restated between reports (₹629.73 cr vs ₹640.67 cr) |
| **GENSOL** | `governance` mechanism — exclude from back-test scoring. No Not Due column. MSME book immaterial. Ind AS transition gives three balance-sheet dates in one report |
| **BESTAGRO** | Ages **from transaction date**, not due date — buckets not comparable with anything else here. No Not Due column. MSME book immaterial (0.04%). No payables turnover ratio disclosed; reports "Purchase of stock-in-trade" rather than cost of materials, so both fields are empty. `graph_valid` false — sells through distributors, no named customer |
| **BHS** | `financial_structure` mechanism — exclude from back-test scoring. **Cane dues to farmers are outside trade payables** (see section 5b); the trade-payables signal is structurally incomplete for this company. No Not Due column. MSME book immaterial (0.05%). FY23 figures cross-checked against the FY23 report and identical — no restatement. `graph_valid` false |
| **NECTAR** | Reported in ₹ millions. No Not Due column. MSMED note is **narrative, not tabular** — only principal unpaid and section-16 interest disclosed, so the other MSMED fields are empty, not nil. Threshold edge case: `msme_book_material` false at 2.59% while MSME payables rose 583% |
| **JPA** | `financial_structure` mechanism. Ages **from transaction date**. No Not Due column. Rows cover **current trade payables only** — non-current payables (₹77.06 cr FY23 / ₹66.96 cr FY22) are excluded, and the ageing table folds in liabilities held for sale. Do not reconcile to the balance-sheet total without adjusting. Signal is `mixed_partial`: MSME principal fell 64% while MSMED interest accrued rose 66% and the turnover ratio deteriorated 14% |
| **BGL_C** *(control)* | The calibration case. MSE balance rose 7.3× and MSE overdue share rose 20.5%→36.1% in a company CARE **upgraded** — a false positive on two signals. Yet it is the ONLY company in the dataset disclosing "principal paid beyond the appointed day", which **fell 65%** and correctly says healthy. Note 32.2 principal differs slightly from Note 23 MSE payables; both recorded as printed |
| **RICO_C** *(control)* | Splits under-1-year into "<6 months" and "6 months–1 year"; these are SUMMED into `msme_under_1yr`. Balance-sheet Note 22 shows FY23 MSME of ₹17.84 cr against the ageing table's ₹18.90 cr; the ageing figure is used |
| **PRECAM_C** *(control)* | `total_expenses_includes_dep_fin = false` — its Total expenses sits above the EBITDA subtotal and already excludes finance costs and depreciation, so the standard cash-buffer denominator must NOT subtract them again. Depreciation cross-checked to Note 27, not the cash flow, which discloses only "Depreciation on ROU asset" separately. Current investments are large (₹170–312 cr) and sit under current assets — an earlier reading mistook the non-current Investments line for them. **OPEN ITEM: a "Corrigendum to the Annual Report for FY 2023-24" was filed 06-07-2024 for "certain typographical errors"; the covering letter was read but the list of corrections was not reached before tooling failed. It carries a 314-page attachment which may be a revised annual report. The FY2023/FY2024 rows may need re-checking against it** |
| **NEULAND_C, DHANUKA_C, BALRAMPUR_C** *(controls)* | All behave as controls should. Neuland's FY24 ageing table has two footing typos (Others printed 18,874.47 and total 19,858.88 against components summing to 18,879.47 and 19,853.88, which match Note 17); component-derived figures are used. Dhanuka's MSMED Note 41 principal differs slightly from its Note 18 MSME payables; both recorded as printed |
| **BGL** *(merged identity)* | Was carried as two rows, `BGL` (abandoned distress candidate) and `BGL_C` (control), both NSE `BHARATGEAR`. Merged 2026-09-08 to a single row `BGL`, cohort `control`, with the abandoned-distress reasoning preserved in `role_history`. All references in the other files updated |
| **Anchors** *(cohort `counterparty`)* | 13 identity-only rows: HERO, TATAMOTORS, ASHOKLEY, MAHINDRA, EICHER, KIRLOSKAROIL, INTLTRACTORS, DEERE, HILTI, MANDO, GSK, BLUSMART, LAVACAST. No financial extraction performed. **TATAMOTORS identity caution:** BSE scrip 500570 now returns "Tata Motors Passenger Vehicles Limited" after the CV/PV demerger; edges reference "Tata Motors Limited" as disclosed at the time, so do not assume the code maps to the pre-demerger entity |
| **AUTOIND** | Abandoned. No qualifying FY22+ event — both were reaffirmations/upgrades. Kept as documented negatives |

---

## 9. Change log and open decisions

**v1.0 (2026-09-08)** — first formal schema. Added to the original brief:
- `msmed_interest_due_on_payments_made_beyond_appointed_day` (financials)
- `ageing_basis` (financials, companies)
- `industry_group`, `distress_mechanism`, `msme_book_material`,
  `msme_pct_of_trade_payables`, `signal_path` (companies)

**v1.1 (2026-09-08)** — added `financial_structure` to `distress_mechanism`; added section 5b
(industry-specific rules) after the sugar finding.

**v2.1 (2026-09-08)** — Session-2 verified financial sweep. Added `undrawn_credit_facilities_cr`,
`undrawn_source`, `plausibility_flags`, `total_expenses_includes_dep_fin`. Every figure read from its
own labelled line, with the depreciation cross-check, an explicit standalone/consolidated section
confirmation per page, and note-anchored rather than page-anchored location. Setco FY2023 revenue
corrected to its own report's figure after a restatement was found.

**v2.0 (2026-09-08)** — Stage-2 collection. Added §3b (the real/synthetic boundary) and the v2.0
column set: cash-buffer components, cost-base type, MSMED note shape, `data_source`, `entity_status`,
`role_history`. `edges.csv` restructured with resolved ids, normalised direction, components and
values. 13 counterparty anchor rows added. Bharat Gears' duplicate identity (`BGL` / `BGL_C`) merged
to a single row under `BGL`, cohort `control`, with the abandoned-distress history preserved in
`role_history`. `backtest_panel.csv` added.

**v1.6 (2026-09-08)** — MSMED-interest panels extended across both cohorts and the signal quantified
(pre-event 6/8 vs controls 0/7). Shivam upgraded from `disputed_see_notes` to
`msme_not_due_migration_qualified` after its FY24 corrigendum was found not to correct the ageing
table. Nectar's s.16 interest re-mapped from `msmed_interest_paid_u_s16` to
`msmed_interest_accrued_unpaid` (the note says it "remains unpaid").

**v1.5 (2026-09-08)** — full consistency pass over all 44 rows (bucket sums, component totals,
duplicates, provenance completeness): all pass, with four documented note-split differences. Shivam's
FY24 figure verified against the BSE-hosted copy (identical, never resubmitted) and left unresolved.

**v1.4 (2026-09-08)** — every Not Due-disclosing company extended to a full FY22–FY25 panel, giving
18 measured no-event transitions against 2 pre-event ones; the +20 pp migration threshold is now
empirical rather than assumed. Shivam flagged `disputed_see_notes` after its FY24 Not Due figure was
found to reverse the signal depending on which report is used.

**v1.3 (2026-09-08)** — control cohort added (6 companies). Retired the MSME balance growth signal
after it produced a false positive on Bharat Gears; re-ranked the ladder by control-tested strength;
added `quiet_as_expected` and `false_positive_risk` to `signal_path`; documented the FY24
reclassification hypothesis; added the control-flag semantics and `matched_to`.

**v1.2 (2026-09-08)** — formalised the `signal_path` vocabulary; added `pharma` and `cement` sections
to 5b; added the "threshold gates levels, not growth" rule to trap 3; repaired `edges.csv`, which had
been written with unescaped quotes and parsed one column wide on some rows.

**Open decisions for the next session:**
1. Cohort composition — the auto distress pool in the Schedule III era is thin (6 of 11 candidates
   disqualified, and the healthiest four were all auto ancillaries). Decision taken: widen to other
   industries, accepting weaker graph edges outside automotive.
2. The control cohort (six companies) has not been started.
3. `msme_book_material` threshold is set at 5% of trade payables. The current cohort splits cleanly
   (27.4 / 16.2 / 9.0 vs 2.8 / 0.04), so the threshold is untested in the 3–8% band.
4. No company yet has more than one distress event with independent pre-event windows.

---

# v2.2 additions (2026-09-09)

## §5c New comparability traps found during the verified financial sweep

These are all real, observed in the filings named. Each one silently corrupts a cross-company
or cross-year comparison if it is not carried with the data.

### T1 — Duplicate BSE index rows; the authoritative filing may have a NULL date
`AnnualReport_New` can return several rows for one company-year. The superseding filing is
identified by `status = "Revised"` and a `revised_date_time`, and its `Fld_AuthoriseDate` is
**null**. Ranking by `Fld_AuthoriseDate` therefore selects the SUPERSEDED copy.
Rule: rank candidates by `revised_date_time || Fld_AuthoriseDate`, take the newest, and record
`status` and `Fld_ReSubmit` next to the filing date.
Observed: Neuland FY2023-24 (original 5 Jul 2024; revised 15 Jul 2024 adding BRSR Core indicators).

### T2 — Malformed attachment URLs
At least one index row returns a path containing a stray backslash
(`.../AttachHis/\29fe1a51-....pdf`, Neuland FY2023). It fails as a generic fetch error.
Rule: strip backslashes from `PDFDownload` before fetching.

### T3 — Two statements printed side by side on one page
Neuland FY2025 prints the balance sheet and the P&L as two columns of one physical page.
Reading by text line interleaves them, producing lines like "Revenue from operations …" followed
by "Right-of-use assets …". Rule: split text items by x-coordinate at the page midpoint before
assembling lines whenever a page matches more than one statement heading.

### T4 — The expenses total may have no caption
Nectar Lifesciences prints its total expenses as a **bare number line** with no "Total expenses"
label, in all three years. Rule: never take an uncaptioned number without confirming its identity
at least twice — components must sum to it, AND total income minus it must equal the stated
profit before tax. Rows built this way carry `plausibility_flags = TEXP_CAPTION_ABSENT_DERIVED_TOTAL_VERIFIED`.

### T5 — Presentation units can change between years for the same company
Best Agrolife reports in **lakhs** for FY2023 and in **millions** for FY2024. A single
`units_as_reported` value per company would be wrong. Rule: read the unit caption from the page
the figure is on, every time; `units_as_reported` is a per-row field and must stay that way.

### T6 — "Current investments" are not necessarily liquid
Bajaj Hindusthan Sugar FY2022 carries ₹770.13 cr of *Current Investments* which note 10 discloses
as unquoted equity shares of Lalitpur Power Generation Company Ltd, **pledged against loans**.
Counting them as liquidity would have reported a ~55-day cash buffer for a distressed company
whose real buffer is 3 days. Rule: read the investments note before including the figure in any
liquidity measure; where excluded, keep the disclosed balance-sheet figure in
`current_investments_cr` and record the exclusion in `cash_components_basis` plus the flag
`CURRENT_INV_ILLIQUID_EXCLUDED`. (The company itself reclassified this holding out of current
assets in FY2023, restating FY2022 total current assets from 6,558.76 to 5,788.63.)

### T7 — Not every filer splits "bank balances other than cash equivalents"
Nectar reports a single *Cash & Cash Equivalents* line whose note 2.10 already contains fixed
deposits and dividend accounts — the components other filers show separately. Rule: where the
separate line is absent, check the cash note before treating it as nil, and record what the
single line contains in `cash_components_basis`.

### T8 — Discontinued operations create a scope break, not a restatement
Jaiprakash Associates' FY2023 report restates FY2022 revenue from 422,006 to 296,741 lakh while
the bottom line is unchanged at (123,188) — the difference is FY2022 activity reclassified as
discontinued. This is a **change of scope**, so Rule 1 (prefer the later report's comparative)
does NOT apply: the two years are simply not comparable and both rows carry
`SCOPE_BREAK_DISCONTINUED_OPS_FY23`. Symptom to watch for: the cash flow statement's depreciation
add-back covers total operations while the P&L line covers continuing operations only
(JPA FY2023: 36,605 vs 23,525), which correctly trips the depreciation cross-check.

### T9 — An Ind AS transition breaks the series
Gensol Engineering adopted Ind AS with a transition date of **1 April 2022**, shown by the
three-column balance sheet in its FY2024 report. FY2022 and earlier are previous-GAAP and cannot
be compared with FY2023 onward. Rule: a third balance-sheet column dated "April 1, YYYY" is the
signal; treat the transition date as a hard break in the series.

### T10 — Image-only annual reports
Some filers submit scans with no text layer: Gensol FY2022 and FY2023, and Setco FY2024
(a 29 MB scan). Rule: where the company's own report is an image, the next-best PRIMARY source is
the following year's report comparative column, which must be recorded as the source. Where even
that is unavailable, leave the row empty and record why — never estimate.

### T11 — BSE displays a company's CURRENT name against its HISTORIC filings
Every annual report filed under scrip 500570 from FY2022 to FY2025 — filings of the undivided
Tata Motors Limited — is now labelled "TATA MOTORS PASSENGER VEHICLES LIMITED", because that
scrip and ISIN were retained by the passenger-vehicle company after the demerger. Rule: resolve
counterparty identity by scrip code and ISIN as at the period of the edge, never by the name the
exchange shows today. See `role_history` on TATAMOTORS and TATAMOTORS_CV.

## §11 Entity identity over time — Tata Motors (worked example)

| | company_id TATAMOTORS | company_id TATAMOTORS_CV |
|---|---|---|
| BSE scrip | 500570 | 544569 |
| ISIN | INE155A01022 | INE1TAE01010 |
| BSE ticker | TMPV | TMCV |
| BSE industry | Passenger Cars & Utility Vehicles | Commercial Vehicles |
| Current name | Tata Motors Passenger Vehicles Limited | Tata Motors Limited |
| Holds pre-demerger history | **yes** (undivided company, to FY2025) | no (first AR is FY2026) |

All six values verified against the BSE `ComHeader` and `PeerSmartSearch` APIs on 2026-09-09.
CINs were not obtainable from a primary source and are deliberately left empty.

The counter-intuitive part: the entity that kept the original listing is the **passenger-vehicle**
company, while the **commercial-vehicle** company took the "Tata Motors Limited" name on a new
listing. Setco supplies medium and heavy commercial-vehicle clutches, so any edge dated FY2026 or
later belongs to TATAMOTORS_CV; edges up to FY2025 belong to the undivided company on scrip 500570.

## §12 cash_buffer_days — measured, and NOT a stress signal

Across 44 verified company-years the buffer runs from **0 to 351 days**, and it does not separate
the cohorts.

| | n | min | Q1 | median | Q3 | max |
|---|---|---|---|---|---|---|
| distress | 22 | 1 | 3.0 | **10.5** | 18.0 | 351 |
| control | 22 | 0 | 3.75 | **14.5** | 57.25 | 266 |

**AUC = 0.569** (probability a randomly chosen control has a higher buffer than a randomly chosen
distress company-year; 0.5 is no separation at all). The controls hold both the lowest observed
value (Balrampur Chini, 0 days in three of four years, investment grade throughout) and one of the
highest (Precision Camshafts, 149-266). The distress cohort holds the single highest value in the
data set — **Gensol Engineering at 351 days in FY2023**, the year before it collapsed.

Consequence for the engine: `cash_buffer_days` is a working-capital-structure variable, not a
fragility input. The mock's assumption of 60-100 days for a tier-1 supplier should be **removed**,
not re-calibrated, and the field should be presented as context (with its comparability flags),
never scored. Where a company's real liquidity sits in undrawn bank limits, the filings often do
not disclose it at all (Balrampur FY2022 discloses no undrawn figure anywhere in the report).
