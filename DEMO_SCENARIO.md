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
| Suppliers routing through it | 6 | **12 — better connected** |
| Alternative suppliers exist? | **No — sole source** | Yes |
| Fragility | 0.3498 | 0.2230 |
| Criticality | **0.5838** | 0.4034 |
| **Final score** | **0.2042** | **0.0900** |

**N203 is the more central node** — twice the supplier base routing through it — and it
still ranks second. That is the argument in its sharpest form: being well connected is not
the same as being irreplaceable. N042 wins on the sole-source term alone.

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
| 6 | Cost vs exposure, side by side | "₹8 crore to stabilise all four. ₹370 crore at risk if nobody moves." | C |
| 7 | **Intervene.** Red drains from the branch. Then toggle off — cascade completes, N001 turns red | "₹2 crore, or a stopped production line." | C |

**Step 4 sells the project. Step 7 closes it.** Everything else is setup.

---

## 5. The numbers on screen

Indicative, from the mock network at seed `42`. Person A owns the exact values; these are what the other two should design around.

**Baseline:**

| Metric | Value |
|---|---|
| Total nodes | 412 |
| Stressed origin | `N007` |
| Ranked at-risk suppliers | 4 named below, 15 non-stable in total |
| Bands | 2 critical, 4 high, 10 watch |
| Cost to stabilise the top four | ₹8.02 cr |
| Exposure across the top four | ₹369.92 cr |
| Iterations to converge | 3 |

The second `critical` is `N007` itself. It is stressed by its own published disclosures, so
it appears in `summary.stressed_origin_nodes` and keeps its band, but it is **not ranked** —
the ranked list answers "which suppliers are in trouble that you could not already see."
`SCHEMA.md` §4.3 does the same in its own worked example.

**After intervening on `N042` at ₹2.04 cr — its computed `intervention_cost_cr`:**

| Metric | Value |
|---|---|
| Nodes improved | 8 |
| Nodes worsened | 0 |
| Exposure reduced | ₹278.66 cr |
| N042 band | `critical` → `stable` |
| N118 band | `high` → `stable` |

N118 clears completely rather than easing to `watch`: its only stress path runs through
N042, so fully covering N042 leaves nothing to inherit.

**At the anchor** (§6, the supply-disruption layer):

| Metric | Baseline | After |
|---|---|---|
| `N001` supply disruption | 0.1076 (`high`) | 0.0392 (`watch`) |
| `N001` inbound supply at risk | ₹848.96 cr | ₹308.36 cr |

**The line that lands:** ₹2.04 crore of early payment removes ₹278 crore of exposure and
₹540 crore of at-risk supply at the anchor. Well over 100× return. It should be visible on
screen without being narrated.

---

## 6. The counterfactual

Step 7's second half. Toggle the intervention **off** and let the cascade complete.

- N042 fails
- N118 loses its only customer
- N007 cannot source the seal kit
- **N001 — the anchor — turns red**

The anchor going red is the emotional beat. It is also the honest one: the company that did nothing wrong, paid on time, and had the money, ends up with a stopped line.

Do not over-narrate this. Let the graph do it.

### How the engine produces it

`engine/disruption.py` — a **second propagation, running with goods flow**, added in schema 1.2.
The payment-stress model alone can never reach the anchor: `N001` is the top buyer, so nothing
propagates *into* it and its fragility is `0.0` by construction. What reaches it is its supplier
failing to deliver, which is a different mechanism travelling the other way.

    contagion:   buyer -> supplier   (money that failed to arrive)
    disruption:  supplier -> buyer   (parts that failed to arrive)

**The one decision that matters:** own payment stress does *not* seed a halt. `own_stress` is
measured from payment behaviour, and a company stretching its payables is conserving cash, not
stopping its line — it is exporting the problem downstream. So halt risk is seeded by the part
of a node's fragility it did **not** generate itself, `fragility − own_stress`: money owed to it
that never arrived. Seed it from `own_stress` instead and the model says the visible tier-1 is
the one about to stop, which is the belief this product exists to correct.

That is also what makes the beat work. `N007`'s halt risk is *entirely* supply-driven, so
funding `N042` drains it — and the anchor with it.

**Measured on the mock at seed 42:**

| | Baseline | After ₹2.04 cr to `N042` |
|---|---|---|
| `N001` supply disruption | **0.1076** (`high`) | **0.0392** (`watch`) |
| `N001` inbound supply at risk | **₹848.96 cr** | **₹308.36 cr** |
| `N007` supply disruption | 0.5916 (`critical`) | 0.1612 (`high`) |
| `N042` halt risk | 0.5132 | 0.0003 |
| `N118` halt risk | 0.1721 | 0.0000 |

`N001` is the highest-disruption anchor in the network and the third-highest node of 412, behind
only `N007` and `N042` — the two nodes the story runs through. Read `summary.anchor_disruption`
rather than scanning the score list.

**₹2.04 crore removes ₹540.6 crore of at-risk inbound supply at the anchor.** That is step 7's
closing number, and it is on top of the ₹278.66 cr of exposure reduction already in §5.

### ⚠ One honest caveat — the anchor bands `high`, not `critical`

At the committed thresholds `N001` moves `high` → `watch`, not `critical` → `stable`. Setting
`DISRUPTION_BAND_CRITICAL` to 0.10 would make it `critical`, and we deliberately did not: the
gap between `N001`'s 0.1076 and the 0.0980 below it is 9%, which is not a break the distribution
supports. Calibrating a threshold to flatter one node in the demo is the kind of thing a judge
is right to catch.

Two honest ways to stage it, both fine:

- **Colour the disruption layer on its own scale.** `high` on an anchor that is normally `stable`
  is already the reddest thing on that part of the graph. Person C's call
- **Lead with the rupee figure.** "₹849 crore of Hindmark's parts inflow at risk, ₹308 crore
  after" needs no band at all, and it is the number that lands

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
    "amount_cr": 2.04
  },
  "expected_after_bands": {
    "N042": "stable",
    "N118": "stable"
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

## 9. The live build, and what to do when it fails

Shared ownership — this section was added with ingestion (AGENTS.md §1.5) and
touches all three tracks.

### 9.1 The opening

The console opens on the **build page**, not on the walkthrough. Upload a zip of
the collection CSVs — the whole `data/real` folder zipped is exactly right, and
the markdown and the committed `network.json` inside it are ignored rather than
refused. The archive is unpacked, transformed, validated and scored in one pass
on the server; the page then reveals that result, in the order the work
happened, and builds the graph tier by tier from the anchors down.

**Say what it is.** The page states on screen that the figures are results being
revealed rather than a progress bar, because they are. If a judge asks whether
the engine streams: it does not, and it must not — `score_network()` is a pure
function over a complete network (§3.1), which is what makes the two-run
determinism check possible at all.

Then **Open the console**, and the seven-step walkthrough runs on the network
that was just built. Its trigger, its top-ranked supplier and its funding amount
all come from the engine's own output rather than from
`data/fixtures/demo_scenario.json` — the fixture's node IDs describe the mock
network and do not exist in an uploaded one.

### 9.2 Recovery — read this before going on stage

**If the upload fails, do not retry it in front of the audience.**

Press **Use committed network** in the top right of the build page. The console
opens immediately on `data/mock/network.json`, the walkthrough is exactly the
one documented in §2 to §6 of this file, and every figure quoted there still
holds. Nothing about the rehearsed demo depends on ingestion succeeding.

The same control is available before any upload, so the fallback is one click
from the opening screen and needs no explanation to reach.

Two failure modes worth recognising:

| What you see | What it is | What to do |
|---|---|---|
| A red line under the drop zone naming a file | A 422 — wrong archive, or one missing a required CSV | Read it out; it names the file. Then use the committed network |
| The page sits on "Reading…" | The API is not running | Use the committed network. `npm run dev` alone serves the committed ingest response, so the build animation still plays |

### 9.3 What the figures are on the real collection

Quote these only if you actually uploaded `data/real`. The mock network's
figures in §5 are the rupee-for-rupee ones and do not apply here.

| | |
|---|---|
| Files in the archive | 11, of which 5 are recognised collection CSVs |
| Companies read | 43 real filers |
| Generated beneath them | 255 nodes, fictional entity pool, marked in the graph |
| Network built | 298 nodes, 302 edges |
| Fields disclosed | 618 filled against 440 left blank |
| Companies with enough to score | 14 of 298 |

That last pair is the line worth landing: **440 fields across these filings say
nothing at all, and 284 of the 298 companies publish nothing an anchor could
read.** That is not a gap in the collection — it is the problem the product
exists for, and the graph is mostly dark because the chain is.

---

## 10. Naming note

All company names here are **fictional**, constructed for the mock network. They are deliberately plausible rather than obviously fake — anonymous placeholders like `Company_47` make the whole demo read as a toy.

When the real dataset lands, real listed companies appear at tiers 0–1 with `data_source: "real"`, and the synthetic deep-tier layer keeps generated names drawn from the entity pool. **The UI must always show which is which.** Never let a judge think a synthetic node is a real company.

---

## 11. Changelog

| Version | Change |
|---|---|
| 1.0 | Initial. Six fixed node IDs, seven-step flow, N042-vs-N203 contrast established as the core ranking argument |
| 1.2 | §6's counterfactual **implemented** — `engine/disruption.py` adds a second propagation running with goods flow, so a supplier failing now reaches the anchor. §6 rewritten from "not yet implemented" to the measured behaviour; §5 gains the anchor figures. The six node IDs, the seven steps and the N042-vs-N203 argument are unchanged, and no baseline number in §3 or §5 moves — the layer is additive. `SCHEMA.md` 1.2. Caveat recorded in §6: the anchor bands `high`, not `critical`, and we declined to move the threshold to make it `critical`. Needs Person B and Person C review |
| 1.1 | Numbers in §3, §5 and the fixture replaced with the engine's actual output. The originals were written against an undamped model and were arithmetically unreachable: N042's fragility is bounded by N007's own_stress (0.75) × its exposure (0.7773) = 0.583 before any damping, against the stated 0.63. The six node IDs, the seven steps, the cast's roles and the N042-vs-N203 argument are all unchanged. N203 is now the *better-connected* node and still ranks second, which sharpens the argument rather than weakening it. Stressed origins are excluded from `ranking` per `SCHEMA.md` §4.3. §6's counterfactual documented as not yet implemented. Agreed with Person B and Person C |
