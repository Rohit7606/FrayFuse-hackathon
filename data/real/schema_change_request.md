# Schema change request — data collection → engine

**From:** data-collection workstream · **Date:** 2026-09-08 · **Against:** the runtime node/edge/stress contract

Five gaps where the collected data cannot be expressed in the current runtime schema. Each one is a
place where the engine would either lose information or silently accept a false claim. We have not
changed any engine code; these are requests.

---

## 1. Edges cannot carry `confidence` — the schema forces inference to look like disclosure

The runtime edge schema has `data_source: real | synthetic` and nothing else about evidential weight.
But `edges.csv` distinguishes four levels, and they are not interchangeable:

| `confidence` | Meaning | Count |
|---|---|---|
| `confirmed` | Counterparty explicitly named in the company's own filing | 8 |
| `probable` | Strongly implied — e.g. named in a rating rationale, not in a filing | 8 |
| `concentration_only` | A percentage is disclosed but the counterparty is unnamed | 5 |

**8 of 21 edges are `probable`** — inference from a third party, not disclosure by the company. Loading
them as `data_source: real` asserts the same standing as a company's own statement.

**Request:** add `confidence` to the edge schema, and let the graph builder decide which levels
become live edges. Our recommendation, carried over from the original brief: only `confirmed` edges
should propagate automatically.

## 2. No way to express "real company, unavailable field"

`data_source` is per-row, but provenance is really per-field. A real company with a real revenue and
an unavailable cash buffer is not a synthetic node, and calling it `real` implies every field is
sourced.

This is not hypothetical: **`cash_buffer_days` is populated for 5 of 46 company-years**. The other 41
are real companies with an unavailable field.

**Request:** either a third `data_source` value `mixed`, or per-field provenance. Until one exists,
the engine must not infer that a `real` node has all fields sourced. Where the engine substitutes a
default at runtime it should flag the node in its output, so the substitution is visible rather than
frozen into data.

## 3. The stress schema weights a field that almost never exists

The runtime stress schema weights `msmed_principal_paid_beyond_appointed_day` at **0.65**. That field
has a value in **3 of 46 company-years, all belonging to one control company** (Bharat Gears). For
every other company the term contributes zero, so the stress score is effectively driven by whatever
carries the remaining 0.35.

The validated ladder in `DATA_DICTIONARY.md` §6 is not represented in the schema at all. It is, in
priority order:

1. **MSMED interest direction** (accrued / due / delay-interest rising) — rose ahead of 6 of 8 events
   and in 0 of the measurable control transitions. Needs no Not Due column, so it is computable for
   every company.
2. **Not Due → under-1-year migration** > +20 pp — 18 no-event transitions max +15.5 pp; 2 pre-event
   at +25.2 and +22.1 pp. Only computable for the ~1 in 3 filers that disclose a Not Due column.
3. **Payables ÷ revenue rising** while matched controls fall.
4. **Non-MSME aged-bucket growth**, for filers with an immaterial MSME book.

**Request:** re-weight against this ladder, and make every term degrade gracefully when its inputs are
absent rather than silently scoring zero. Note that `msme_balance_growth` is **retired** — a control
that was upgraded posted +629% against a distress case's +583%.

## 4. No slot for the back-test result

The runtime output has nowhere to carry the evidence for the product's headline claim. We now ship
`backtest_panel.csv` (32 company-year transitions, entirely real, fully recomputable from
`financials.csv`).

**Request:** a place in the output for per-transition back-test rows, or at minimum a link from a node
to its transitions, so the claim is inspectable in the product rather than only in a repo file.

## 5. Comparability flags must travel with the node

`has_not_due_column`, `ageing_basis`, `basis`, `msme_book_material` and `cost_base_type` decide
whether two companies' numbers mean the same thing. `DATA_DICTIONARY.md` §5 documents three traps that
produce confidently wrong answers when these are ignored — including two filers that age from
**transaction date** rather than due date, whose "under 1 year" is a different quantity with the same
column name.

**Request:** carry these flags on the node and refuse cross-company comparisons that mix them, rather
than leaving it to the caller.

---

## Also worth knowing

- **`is_single_source` is empty on all 21 real edges.** No primary source in this dataset states sole-
  source status. Per the brief it must never be inferred from the sparsity of our own edge data. The
  engine's chokepoints must come from the synthetic layer until a real one is evidenced.
- **2 of 21 edge rows intentionally have no `to_company_id`** (of 5 marked `concentration_only`, 3 do name a counterparty and 2 do not) (`relationship_type =
  concentration_disclosure_unnamed`). They record a real disclosed percentage against an unnamed
  counterparty. They are not graph edges and should be excluded from graph construction.
- **Real-layer size for the engine team:** 28 company rows (15 researched + 13 counterparty anchors)
  and 19 real graph edges. Everything below tier-1 needs generating.
