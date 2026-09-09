# DEMO_SCENARIO.md — FrayFuse

**This file has no single owner.** Changes require both other team members named on the PR. See `AGENTS.md` §4.3.

This is the one scenario all three tracks build toward. Node IDs here are **fixed and committed**. If Person C animates a cascade through nodes Person A's engine does not flag, the demo breaks — and that only gets caught if everyone points at the same identifiers.

---

## 1. The story in one line

> Upstream payment stress → deep-tier contagion → fragile-and-critical supplier identified → intervention → reduced cascade.

---

## 2. The cast — fixed node IDs

These IDs are guaranteed present in `data/mock/network.json` at seed `42`, and must survive any regeneration.

| ID | Name | Tier | Role in the demo |
|---|---|---|---|
| `N001` | Hindmark Motors India Ltd | 0 | The anchor. Pays on time. Has idle cash. Ends up with the halted line in the counterfactual |
| `N007` | Brakecraft Components Ltd | 1 | **The trigger.** Observable, real-shaped disclosures. Quietly stretching supplier payments |
| `N042` | Sealsworks Rubber Industries Pvt Ltd | 2 | **The headline finding.** Fragile *and* single-source. Rank 1 |
| `N118` | Precision Polymer Works Pvt Ltd | 3 | Second-order casualty. Supplies N042 |
| `N203` | Kalyani Fastener Systems Pvt Ltd | 2 | Rank 2. Fragile but *not* single-source — shows the ranking is doing real work |
| `N087` | Vaayu Thermal Products Pvt Ltd | 2 | Rank 3. Moderate. Included so the list isn't suspiciously short |

**The chain that matters:**

```
N001 Hindmark  ◀── N007 Brakecraft ◀── N042 Sealsworks ◀── N118 Precision Polymer
   (anchor)          (trigger)          (rank 1)            (collateral)
```

Read arrows as "buys from." Stress travels left to right — from buyer to supplier, following the money that failed to arrive.

---

## 3. Why N042 outranks N203 — the point of the whole product

Both are fragile. Only one is irreplaceable.

| | N042 Sealsworks | N203 Kalyani Fastener |
|---|---|---|
| Revenue dependency on N007 | 78% | 61% |
| Cash buffer | 18 days | 34 days |
| Alternative suppliers exist? | **No — sole source** | Yes, three others |
| Fragility | ~0.63 | ~0.44 |
| Criticality | ~0.88 | ~0.31 |
| **Final score** | **~0.56** | **~0.14** |

A judge who asks *"why is the second one lower when it's also in trouble?"* gets the entire thesis in one answer: **fragility alone is not enough — we rank by fragile × irreplaceable.**

Keep this contrast intact through any tuning. It is the most defensible thing in the demo.

---

## 4. The seven steps

| # | On screen | Said aloud | Owner |
|---|---|---|---|
| 1 | Full network, ~400 nodes, all neutral. Anchor at centre | "One car manufacturer's supply chain, four tiers deep. Today they can see only this innermost ring." | C |
| 2 | Observable nodes highlighted — a handful. Everything else dimmed | "Everything else is dark to them. Not because they're careless — because the data doesn't exist." | C |
| 3 | N007's disclosure panel opens. Ageing table beside MSMED note | "This company's ageing table looks clean. Its whole-year figure shows late payments doubling. Both are in the same public filing." | C |
| 4 | **Cascade runs.** Stress spreads outward in stages. Amber, then red | "Watch where that goes." | C |
| 5 | Ranked list appears. 4 names from 400+. Reasons and rupee figures | "Four suppliers. Here's why each one, in plain English." | C |
| 6 | Cost vs exposure, side by side | "₹14.2 crore to stabilise all four. ₹189.6 crore at risk if nobody moves." | C |
| 7 | **Intervene.** Red drains from the branch. Then toggle off — cascade completes, N001 turns red | "₹4.8 crore, or a stopped production line." | C |

**Step 4 sells the project. Step 7 closes it.** Everything else is setup.

---

## 5. The numbers on screen

Indicative, from the mock network at seed `42`. Person A owns the exact values; these are what the other two should design around.

**Baseline:**

| Metric | Value |
|---|---|
| Total nodes | ~412 |
| Stressed origin | `N007` |
| At-risk count | 4 |
| Bands | 1 critical, 3 high, 11 watch |
| Total intervention cost | ~₹14.2 cr |
| Total exposure at risk | ~₹189.6 cr |
| Iterations to converge | 4 |

**After intervening on `N042` at ₹4.8 cr:**

| Metric | Value |
|---|---|
| Nodes improved | 7 |
| Nodes worsened | 0 |
| Exposure reduced | ~₹148.3 cr |
| N042 band | `critical` → `stable` |
| N118 band | `high` → `watch` |

**The line that lands:** ₹4.8 crore of early payment removes ₹148 crore of exposure. Roughly 30× return. It should be visible on screen without being narrated.

---

## 6. The counterfactual

Step 7's second half. Toggle the intervention **off** and let the cascade complete.

- N042 fails
- N118 loses its only customer
- N007 cannot source the seal kit
- **N001 — the anchor — turns red**

The anchor going red is the emotional beat. It is also the honest one: the company that did nothing wrong, paid on time, and had the money, ends up with a stopped line.

Do not over-narrate this. Let the graph do it.

---

## 7. The fixture file

`data/fixtures/demo_scenario.json`:

```json
{
  "scenario_id": "canonical_v1",
  "description": "Brakecraft payment stretch cascades to deep-tier suppliers",
  "trigger_node": "N007",
  "expected_ranking": ["N042", "N203", "N087", "N118"],
  "expected_bands": {
    "N042": "critical",
    "N203": "high",
    "N087": "high",
    "N118": "high"
  },
  "intervention": {
    "node_id": "N042",
    "amount_cr": 4.80
  },
  "expected_after_bands": {
    "N042": "stable",
    "N118": "watch"
  },
  "counterfactual_anchor": "N001"
}
```

**This file is a test fixture, not just documentation.**

- **Person A** asserts in `tests/engine/` that the pipeline reproduces `expected_ranking` and `expected_bands` on the mock network
- **Person B** asserts the `/api/intervene` response matches `expected_after_bands`
- **Person C** reads `trigger_node` and `intervention` rather than hardcoding them in components

If a model tuning change breaks these assertions, that is the system working. Either retune, or update the fixture deliberately with both others named on the PR.

---

## 8. Rules

- **Never hardcode these IDs in application logic.** Read them from the fixture. Demo data must not leak into the engine, the API, or component internals
- **Regenerating the mock network must preserve these six IDs.** `mockgen.py` places them explicitly before generating filler nodes
- **The demo must run without a refresh or a manual fix.** If any step needs a human to intervene, it isn't done
- **No new names.** Everything on screen comes from this file or the mock network

---

## 9. Naming note

All company names here are **fictional**, constructed for the mock network. They are deliberately plausible rather than obviously fake — anonymous placeholders like `Company_47` make the whole demo read as a toy.

When the real dataset lands, real listed companies appear at tiers 0–1 with `data_source: "real"`, and the synthetic deep-tier layer keeps generated names drawn from the entity pool. **The UI must always show which is which.** Never let a judge think a synthetic node is a real company.

---

## 10. Changelog

| Version | Change |
|---|---|
| 1.0 | Initial. Six fixed node IDs, seven-step flow, N042-vs-N203 contrast established as the core ranking argument |
