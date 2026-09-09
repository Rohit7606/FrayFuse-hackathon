# FrayFuse — Session 4: Close the data set for good

**This is the final collection session.** It is deliberately small. Two jobs, then the dataset is
frozen and the project moves entirely to engine work.

Dataset lives at `data/real/` in the `FrayFuse-hackathon` repo and is under version control. Work
against that copy. `DATA_DICTIONARY.md` §2 rules apply in full, as always.

---

## Job 1 — One pass over eleven reports: verbatim + CIN together

These two items overlap heavily, so do them in a single sweep per document. The CIN is on the cover or
corporate-information page of the same report you open for the MSMED note.

### 1a. `msmed_note_verbatim` — 15 rows remaining (31/46 filled)

```
BALRAMPUR_C  FY2022 FY2023        GENSOL   FY2022 FY2023 FY2024
BGL          FY2022               JPA      FY2022 FY2023
BHS          FY2022               NECTAR   FY2023
DHANUKA_C    FY2023               NEULAND_C FY2025
RICO_C       FY2022 FY2025        SETCO    FY2024
```

Quote the exact caption or sentence as printed. Your three-regime finding (caption with values /
caption with nil / caption absent) is established across ten companies — this completes the panel so
the claim is about the whole set rather than most of it.

**Carry forward the trap you found:** in five-line MSMED formats, "beyond the appointed day" is a
sub-clause of the section 16 interest caption. A dash there means no s.16 interest was paid, not that
nothing was paid late. That distinction should be visible in the verbatim text you capture.

### 1b. CIN — 9 researched companies

`SETCO, AUTOIND, GENSOL, BHS, NECTAR, JPA, NEULAND_C, DHANUKA_C, BALRAMPUR_C`

Eight of these nine are already in the 1a list, so this is nearly free.

**Do not collect CINs for the 28 counterparty rows.** Four are foreign entities — Deere & Company,
Hilti, Mando and GlaxoSmithKline — and a CIN is an Indian registration number, so they do not have
one. Leave those empty and record `not_applicable_foreign_entity` in the notes rather than leaving it
looking like a gap. The unlisted group entities would need MCA lookups for a join nobody is
performing; skip them too.

---

## Job 2 — Two customer edges

Rico Auto and Precision Camshafts both score **betweenness 0.0000** despite Rico having eight supplier
edges, because neither has a single outbound buyer edge. Betweenness counts paths *through* a node, so
inbound edges alone contribute nothing.

This is a structural artefact of the collection method, not of the companies: related-party notes only
ever reveal one hop **up**, so every edge you recovered points inward. **One customer edge each moves
two nodes off zero** — worth more than the next twenty supplier edges.

Both are established auto ancillaries with real OEM customers. Likely sources:
- **OEM supplier-award and vendor-recognition pages** — this is how the Setco → Ashok Leyland edge was
  found ("4th Rank amongst 164 suppliers in Supplier SAMRAT competition")
- Rating rationales, which routinely state customer concentration and sometimes name customers
- MD&A and business-overview sections
- Precision Camshafts is a camshaft specialist with a well-documented export customer base

Same evidence standards as always. `confirmed` requires a primary-source statement; `probable` is
fine and honest if that is what the evidence supports; do not promote to improve connectivity. If you
genuinely cannot find one for either company, say so — that is a finding consistent with everything
else you have measured, not a failure.

---

## Explicitly out of scope — do not start these

- `entity_pool.csv` — permanently deferred. `mockgen.py` already generates plausible Indian
  manufacturer names without it, so it blocks nothing
- New distress companies, new industries, new controls
- The third automotive control pair, the Shivam FY24 resolution, the s.43B(h) confirmation. All three
  are genuine improvements and none is worth another session at this stage
- Counterparty CINs (see 1b)
- Any further supplier-edge hunting beyond Job 2. You measured the ceiling; it holds

---

## Report back

Short report this time:
- verbatim 46/46 or the reasons for any remainder
- CIN count for the nine
- whether the three-regime caption pattern held across the completed panel
- the two customer edges, with confidence and evidence — or an explicit statement that none was
  recoverable

Update `DATA_DICTIONARY.md` (version bump, change-log entry) and append a short dated section to
`findings.md` marking the dataset closed. State the final counts in that section: companies,
company-years, edges, resolvable edges, nodes with non-zero betweenness, and the back-test result.
That section is the one someone will read first in six months.

## Delivery

Return **all eight files**, correctly named, including ones you did not change:
`companies.csv`, `financials.csv`, `edges.csv`, `distress_events.csv`, `backtest_panel.csv`,
`DATA_DICTIONARY.md`, `findings.md`, `schema_change_request.md`.

`distress_events.csv` went missing from two of three handoffs and files have arrived as `-1` and `_2`
duplicates. Please check the full set is present and correctly named before sending.
