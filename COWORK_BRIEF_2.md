# FrayFuse — Session 2: Finish the Financial Sweep (verified extraction)

**One job this session: complete the per-row financial figures across ~25 annual reports, with every
value read from its own labelled line.** Nothing else. Do not touch the graph, do not add companies,
do not start P2.

Your last session was right to stop. The automated extractor produced three wrong values in five
documents, and you caught them by spot-checking. This brief exists to make that failure mode
structurally impossible rather than relying on spot-checks catching it again.

Read `DATA_DICTIONARY.md` §2 (the seven rules) before starting. They still apply in full.

---

## 1. Why this matters more than it looked

The five rows you did complete have already overturned a project assumption.

The engine's mock generator assumes tier-1 manufacturers hold **60–100 days** of cash buffer. Your two
real listed tier-1 auto ancillaries came in at **3–5 days** (Bharat Gears) and **14–15 days** (Rico
Auto) — the band the mock reserves for tier-3.

That figure feeds the contagion damping term directly: `buffer_strength = clamp(days / 90, 0, 0.9)`,
and per-hop stress transmission is `DAMPING × (1 − buffer_strength)`. At 80 days that is 0.083. At 5
days it is 0.708 — roughly **8.5× more transmission per hop**. On real buffers the contagion model
will behave completely differently from every test run so far.

**This currently rests on two companies.** That is too thin to recalibrate a model on, and it is
exactly the kind of n=2 claim this dataset has repeatedly flagged as its own weakest point. Finishing
the sweep converts an anomaly into a calibration input.

So: accuracy matters more than coverage. **A verified 30 rows beats an unverified 41.** If you run out
of budget, stop and report — do not switch to fast extraction to finish.

---

## 2. The extraction protocol — mandatory, per figure

Three specific faults occurred last session. Each has a specific counter. Apply all of them to
**every** figure, including ones that look obvious.

### Fault 1 — label collision (depreciation matched an EBITDA subtotal)

`Depreciation` appears inside subtotal captions such as "Profit before interest, depreciation and tax."
A keyword match found the subtotal (₹110 cr) instead of the expense line (₹57 cr).

**Counter — three conditions, all required before recording a P&L figure:**
1. The value must sit on a line whose caption is the item itself, not a caption that merely *contains*
   the word. Reject any caption containing "before", "EBITDA", "profit", "total" unless the field you
   want *is* a total.
2. The line must fall inside the expenses block, between "Revenue from operations" and "Profit before
   tax".
3. **Cross-check depreciation against the cash flow statement's add-back line** ("Depreciation and
   amortisation expense" in operating activities). If the two disagree, record neither — flag it.

### Fault 2 — entity mixing (consolidated revenue into a standalone row)

A row carried standalone ageing figures and consolidated revenue. This breaks `DATA_DICTIONARY.md`
Rule 5 and produces a ratio between two different entities.

**Counter:**
1. Read the row's existing `basis` value **first**. Every figure you add must come from that same
   statement set.
2. Indian annual reports print standalone and consolidated statements as two separate sections, often
   100+ pages apart, with near-identical layouts. Confirm the section header on the page you are
   reading, every time — not once per document.
3. Record which section you used in `source_page`, e.g. `standalone P&L p.148; standalone BS p.144`.
4. If only the other basis is available, **leave the cell empty**. Do not substitute. Note it in your
   report.

### Fault 3 — unstable page selection between runs

Balance-sheet page selection was not reproducible on the same document.

**Counter — anchor on document structure, never on page position:**
1. Locate the **note number** first (from the index or the statement's own note reference), then go to
   that note.
2. Record the note number *and* the page in `source_page`: `Note 18 (p.176)`.
3. Two runs must return the same note number. If they do not, the document needs manual reading —
   flag it and move on.

### The self-check, required per row before you write it

```
1. recompute cash_buffer_days from the components you just recorded
2. confirm it matches the value you are about to write
3. confirm every figure in the row came from the basis named in `basis`
4. confirm the plausibility gate below
```

**Plausibility gate.** Flag for manual review, do not silently record, if:
- `cash_buffer_days` < 2 or > 400
- `depreciation_amortisation_cr` > 25% of `total_expenses_cr`
- `finance_costs_cr` > 20% of `total_expenses_cr`
- `total_expenses_cr` differs from revenue by more than 40% in either direction
- any value is identical to the same field in a different year of the same company to two decimals
  (see §5.2 — this pattern already appears once and needs checking)

A flagged row is a success, not a failure. Record it as flagged and keep going.

---

## 3. What to collect — everything in one pass per document

Open each annual report **once** and take every field below for the year(s) that report covers. Do not
make three separate passes; that is what made the last attempt expensive.

Remember Rule 1: **read each financial year from its own report**, not from a later report's
comparative column. If you must use a comparative, say so explicitly in `source_page`.

### Already-defined columns to fill

| Column | Where |
|---|---|
| `cash_and_cash_equivalents_cr` | Balance sheet, current assets |
| `bank_balances_other_cr` | Balance sheet, "Other bank balances" if shown separately |
| `current_investments_cr` | Balance sheet, current assets |
| `total_expenses_cr` | P&L, "Total expenses" |
| `depreciation_amortisation_cr` | P&L expense block — **cross-check against cash flow add-back** |
| `finance_costs_cr` | P&L expense block |
| `cash_buffer_days` | derived — see formula below |
| `cash_components_basis` | `all_disclosed` \| `current_investments_absent_treated_nil` \| etc. |
| `revenue_standalone` / `revenue_consolidated` | matching the row's `basis` |
| `cost_of_materials_consumed` or `purchases_stock_in_trade_cr` | whichever the company reports |
| `cost_base_type` | `materials_consumed` \| `stock_in_trade` \| `both` |
| `msmed_interest_due_unpaid`, `msmed_interest_accrued_unpaid`, `msmed_interest_due_on_payments_made_beyond_appointed_day` | MSMED note |
| `msmed_interest_lines_disclosed`, `msmed_note_format`, `msmed_note_verbatim` | MSMED note — **empty on all 46 rows, do every row you open** |

```
cash_buffer_days = (cash_and_cash_equivalents_cr + bank_balances_other_cr + current_investments_cr)
                   / ((total_expenses_cr − depreciation_amortisation_cr − finance_costs_cr) / 365)
```

Rounded to a whole number. If any component is undisclosed, leave `cash_buffer_days` **empty** — never
partially compute. Record how you treated absences in `cash_components_basis`.

### One new column — undrawn credit facilities

A company with 3 days of cash but ₹200 crore of committed unutilised working capital limits is not as
fragile as the cash figure implies. This is very likely why a 3-day buffer is survivable at all, and
it materially affects how the model should read these numbers.

| New column | Source |
|---|---|
| `undrawn_credit_facilities_cr` | Rating rationale ("unutilised working capital limits", "average utilisation of X%"), or the borrowings / liquidity note |
| `undrawn_source` | `rating_rationale` \| `annual_report_note` \| `not_disclosed` |

**Secondary priority.** Take it when it is in a document you already have open. Do not open new
documents for it, and never let it delay the primary fields. Leave empty where not disclosed.

### `msmed_note_verbatim` — do not skip this

It is empty on all 46 rows and it is cheap while you are already in the note.

`findings.md` §4 is the reason: the brief's original primary signal
(`msmed_principal_paid_beyond_appointed_day`) was assumed extinct after seven companies, then found in
Bharat Gears — which files it as its own named line. Wording varies enough that only verbatim capture
settles whether a line is genuinely absent or merely differently worded. Quote the exact caption or
sentence as printed.

---

## 4. Scope — 41 rows, ~25 documents

```
BALRAMPUR_C  FY2022 FY2023 FY2024 FY2025
BESTAGRO     FY2023 FY2024
BGL          FY2022
BHS          FY2022 FY2023 FY2024
DHANUKA_C    FY2023 FY2024 FY2025
GENSOL       FY2022 FY2023 FY2024
JPA          FY2022 FY2023
LOKESH       FY2023 FY2024 FY2025
NECTAR       FY2023 FY2024 FY2025
NEULAND_C    FY2023 FY2024 FY2025
PRECAM_C     FY2022 FY2023 FY2024 FY2025
RICO_C       FY2022 FY2025
SETCO        FY2022 FY2023 FY2024 FY2025
SHIVAM       FY2022 FY2023 FY2024 FY2025
```

Also still outstanding on these rows: **13 missing revenue**, **16 missing cost base**, **12 missing
all three MSMED interest lines**, **46 missing `msmed_note_verbatim`**. All are covered by the
one-pass-per-document approach above.

### Suggested order

1. **SHIVAM, SETCO, LOKESH** — the core distress cases. Highest value, and you know these documents.
2. **PRECAM_C, RICO_C** — automotive controls; PreCam is missing all four years of nearly everything.
3. **NEULAND_C, DHANUKA_C, BALRAMPUR_C** — remaining controls.
4. **NECTAR, BESTAGRO, BHS, GENSOL, JPA** — non-automotive distress.
5. **BGL FY2022** — single row, finishes that panel.

Note that SETCO is recorded **consolidated** (its standalone entity is a holding shell) — read the
consolidated statements for every SETCO figure. Its FY24 report is scanned and needs OCR at 350–400
dpi; verify anything you OCR against another disclosure of the same figure.

---

## 5. Verification backlog — small, do it alongside

### 5.1 The PreCam corrigendum you found and did not read

Precision Camshafts filed a *Corrigendum to the Annual Report for FY 2023-24* on **06-07-2024**. You
logged it unread.

Shivam's corrigendum turned out to be decisive — it corrected eleven pages to one-paisa precision but
**not** page 117, which carried the ageing table, and that absence is what upgraded Shivam from
disputed to a qualified event observation. Read PreCam's the same way: **does it touch the trade
payables ageing table, the MSMED note, or any figure in our rows?** Record the answer either way,
including an explicit "corrects nothing we use" — that is a finding, not a null result.

### 5.2 Two suspicious repeats in BGL

`BGL FY2023` and `BGL FY2025` carry identical values in two fields: `cash_and_cash_equivalents_cr =
0.06` and `finance_costs_cr = 17.08`. `depreciation` and `total_expenses` differ between those rows,
so it is not a whole-row copy and may well be genuine.

Re-read both from their own reports and confirm or correct. If genuine, note it in the caveat register
so it is not re-flagged later.

### 5.3 The Tata Motors scrip code

You flagged that BSE scrip 500570 now returns **Tata Motors Passenger Vehicles Limited** after the
CV/PV demerger, so it no longer maps cleanly to the entity our edges reference.

Resolve which entity the edges actually mean. `SETCO → Tata Motors` concerns **clutches for M&HCV** —
commercial vehicles — so the correct post-demerger counterparty is almost certainly the **commercial
vehicles** entity (Tata Motors Limited, as renamed) rather than the passenger-vehicle company. Confirm
this from the demerger scheme or the exchange notice, correct the scrip code and CIN, and record both
the pre- and post-demerger identity in `role_history`. Do not silently repoint the edge.

---

## 6. Report back

- Rows completed, rows flagged by the plausibility gate, rows left empty and why
- **Every figure where the P&L line and the cash flow add-back disagreed on depreciation**
- Any document where two runs returned different note numbers
- Any restatement found between a report and a later report's comparative
- The distribution of `cash_buffer_days` by `tier_role` — this is the calibration input the engine
  team needs, so report it explicitly as a table
- How many companies disclose undrawn credit facilities, and the range
- The verbatim MSMED captions, grouped by wording, and specifically **any company beyond Bharat Gears
  that discloses "principal paid beyond the appointed day"** as its own line
- Answers to §5.1, §5.2, §5.3

Update `DATA_DICTIONARY.md` (new columns, version bump, change-log entry under §9) and append a dated
session section to `findings.md`. Do not rewrite existing narrative in either file.

---

## 7. Do not

- Do not batch-extract without the §2 checks, however slow it feels. That is what produced the three
  wrong values.
- Do not estimate, interpolate, or carry a figure across from another year, entity or peer.
- Do not mix `standalone` and `consolidated` within a row.
- Do not take a year from a later report's comparative column without saying so in `source_page`.
- Do not touch `edges.csv`, `companies.csv` (except the §5.3 fix and caveat-register entries), or
  `backtest_panel.csv` — regenerate the panel only at the end, from the updated `financials.csv`.
- Do not start P2, add companies, or collect `entity_pool.csv`. The naming decision on the entity pool
  is still with the project owner.
- Do not stop early and fill remaining rows quickly to finish the list. Report the shortfall instead.

---

## 8. Delivery

Return **every** file in the data set, including ones you did not change. `distress_events.csv` was
missing from the last delivery and had to be recovered from an older copy — it is untracked in version
control, so a dropped file is a permanently lost file.

Final file list: `companies.csv`, `financials.csv`, `edges.csv`, `distress_events.csv`,
`backtest_panel.csv`, `DATA_DICTIONARY.md`, `findings.md`, `schema_change_request.md`.
