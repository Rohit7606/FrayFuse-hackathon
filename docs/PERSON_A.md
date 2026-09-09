# PERSON_A.md — Risk Engine & Network Logic

**Person A / Person 1 — "Build the brain."**

Read `AGENTS.md` and `SCHEMA.md` before starting. This file assumes both.

---

## 1. What you own

| Path | Yours |
|---|---|
| `engine/` | Everything |
| `data/` | Everything |
| `tests/engine/` | Everything |

Your reviewer for every PR is **Person B**.

You own the entire intelligence layer:

- Graph construction
- Stress detection
- Contagion propagation
- Fragility
- Criticality — betweenness and single-source
- Final ranking and reason generation
- Intervention cost, exposure, and counterfactual scoring
- Supply disruption — the second propagation, which is what makes the counterfactual reach the anchor
- **The mock data generator** — everyone's day-one dependency
- **The CSV → `network.json` transform** — the handoff when the real dataset lands

The last two were added to your track deliberately. The mock generator *is* the contract made concrete, and the transform requires knowing what the engine needs. Both belong with you.

**You do not collect data.** See `AGENTS.md` §1.4.

---

## 2. Your public surface

Person B calls exactly one function. Keep it that way.

```python
# engine/pipeline.py

def score_network(
    network: dict,
    scenario: Scenario | None = None,
) -> dict:
    """Score a network under an optional scenario.

    Args:
        network:  NetworkInput dict, validated against schema.json
        scenario: stress overrides and interventions; None means baseline

    Returns:
        ScoredNetwork dict, validated against schema.json

    Pure. Deterministic. No I/O, no globals, no mutation of the input.
    """
```

**Contract you must honour:**

- Same input → byte-identical output, always
- Never mutate the `network` argument. Deep-copy first
- Never read files or the clock inside this call
- Raise `UnknownNodeError` (defined in `engine/pipeline.py`) for a bad `node_id` so B can map it to a 400

Also expose the scenario type:

```python
@dataclass(frozen=True)
class Scenario:
    stress_overrides: tuple[StressOverride, ...] = ()
    interventions: tuple[Intervention, ...] = ()
```

Frozen and tuple-based so it cannot be mutated mid-scoring.

---

## 3. The algorithm

All constants live in `engine/config.py` with a one-line comment each. No magic numbers in the modules.

### 3.1 Stress detection — `engine/stress.py`

Produces `own_stress` ∈ [0, 1] for every observable node. Non-observable nodes get `0.0`.

> **This section was rewritten after the collection workstream reported.** The original spec ranked
> `msmed_principal_paid_beyond_appointed_day` as the primary signal at weight 0.65. Collection found
> that field disclosed in **3 of 46 verified company-years, all belonging to a single control
> company**. It cannot carry the model. The ladder below is what survived testing against a matched
> control cohort. Evidence: `data/real/DATA_DICTIONARY.md` §6 and `data/real/findings.md` §5.

**A ladder of four signals, not two.** Availability varies enormously between filers — most Indian
small-caps omit the columns the original spec assumed — so you compute whichever rungs are
available and **renormalise their weights over exactly those**. A company with only rung 1 available
scores on rung 1 at full weight.

**Rung 1 — MSMED interest direction (primary, `W_INTEREST_DIRECTION` 0.45)**

```
interest(t) = max(msmed_interest_accrued_unpaid_cr,
                  msmed_interest_due_unpaid_cr,
                  msmed_interest_due_on_payments_beyond_appointed_day_cr)

rung1 = 1.0 if interest(t) > interest(t−1) else 0.0
```

Interest accrues under the MSMED Act only past the appointed day, so any rise is a **statutory
admission of late payment**. It rose ahead of 6 of 8 documented distress events and in 0 of 7 control
transitions, and — decisively — it needs no Not Due column, so it is available for every filer.

Two caveats to honour. Some companies report a *frozen* accrued figure carried forward unchanged for
years (Bharat Gears at 2.37, Dhanuka at 13.65) — so trust a **rise**, never the absence of movement.
And `nil → positive` is the strongest form of this signal.

**Rung 2 — Not Due → overdue migration (`W_MIGRATION` 0.25)**

```
overdue_share(t) = under_1yr / (not_due + under_1yr)
rung2 = 1.0 if (overdue_share(t) − overdue_share(t−1)) * 100 > MIGRATION_THRESHOLD_PP else 0.0
```

**Unavailable when `has_not_due_column` is `false`** — that filer's `under_1yr` silently includes
amounts not yet due. Do not compute it and do not substitute a default; drop the rung and
renormalise.

The +20pp threshold is measured, not assumed: across a FY22–FY25 panel, **18 no-event transitions
top out at +15.5pp** while the 2 pre-event transitions are +25.2 and +22.1pp. Note the null is
strongly asymmetric — healthy companies fall as far as −62.9pp but only one of eighteen rose above
+10pp. Weighted below rung 1 because n = 2 on the event side, and one of those two is disputed by a
restatement.

**Rung 3 — payables outgrowing revenue (`W_PAYABLES_REVENUE` 0.20)**

```
ratio(t) = total_trade_payables_cr / revenue_cr
rung3 = 1.0 if (ratio(t) − ratio(t−1)) > 0 else 0.0
```

Used where the MSME book is immaterial (`msme_book_material` false) and every MSMED line reads nil.
Distress cases moved +4.0 to +5.2pp; all three tested controls **fell**, −1.8 to −2.2pp.

**Rung 4 — non-MSME aged-bucket growth (`W_NONMSME_AGEING` 0.10)**

Last resort where nothing above is computable. Only partially control-tested — weight accordingly.

**Combine**

```
available = [rungs whose inputs exist for this company]
if not available: own_stress = 0.0        # never guess
w_total   = Σ weight(r) for r in available
raw       = Σ (weight(r) / w_total) * rung_value(r) for r in available
own_stress = clamp(raw, 0.0, 1.0)
```

**Do not z-score against sector statistics.** The original spec did; the collected cohort has 7
industry groups across 16 companies, so all but automotive fall below `MIN_SECTOR_SAMPLE` and would
silently use global stats — comparing an agrochemical trader against an auto ancillary. Cross-industry
comparison is valid only for *changes and directions*, never levels, which is exactly what the rungs
above encode. `MIN_SECTOR_SAMPLE` is retained for any future statistic that genuinely needs peers.

**Retired — do not reinstate without re-testing against controls:** MSME balance growth. Control
Bharat Gears posted **+629%** in a year CARE *upgraded* it, against distress case Nectar's +583%. The
suspected cause is s.43B(h) reclassification, not payment behaviour, which also means **any FY23→FY24
MSME level comparison is currently uninterpretable**.

**Edge cases you must handle explicitly:**

| Case | Behaviour |
|---|---|
| Only one year of data | `own_stress = 0.0`. Cannot compute a change. Record `insufficient_history` |
| `has_not_due_column` false | Rung 2 unavailable. Renormalise over the rest |
| No rung computable | `own_stress = 0.0`. Never guess |
| Explicit `0.0` vs `null` | Different. `0.0` is real data; `null` is absence. See `AGENTS.md` §3.6 |
| `series_break` set on a year | That year is not comparable with the previous one. Skip the transition |
| `ageing_basis` differs between two companies | Never compare their buckets. Due-date and transaction-date clocks measure different things |

### 3.2 Graph construction — `engine/graph.py`

```python
G = networkx.DiGraph()
```

**Edge direction:** add edges as `G.add_edge(supplier_id, buyer_id, ...)` — matching goods flow. Stress propagates *against* this direction, buyer → supplier. Write that in a comment at the top of the file; it is the easiest thing in the project to get backwards.

- Node attributes from the `Node` object
- Edge attributes: `exposure_pct`, `annual_value_cr`, `is_single_source`, `component`
- Validate every `supplier_id` and `buyer_id` exists in `nodes`; raise on dangling references
- Validate that outgoing `exposure_pct` per supplier sums to ≤ 1.02
- **Sort node and edge lists by ID before adding.** NetworkX preserves insertion order, and betweenness can differ on ties otherwise

**Repeated supplier→buyer pairs — handle this explicitly.** `DiGraph.add_edge` on a pair that already
exists **overwrites its attributes silently**. The collected dataset has multiple rows per pair,
because a relationship is recorded once per financial year, and the naive loop loses data on both of
them:

- `SHIVAM → HERO` has three rows. Only one carries `annual_value_cr` (₹181.59 cr). Add them in row
  order and the last row wins, discarding the only rupee figure on the most important edge in the set.
- `LOKESH → MAHINDRA` has two rows, and the later one is `relationship_terminated` — the OFAC
  sanctions edge deletion. Collapse them carelessly and you either lose the termination or silently
  keep an edge that no longer exists.

Required behaviour: **group rows by `(supplier_id, buyer_id)` first, then reduce each group to one
edge deterministically.** Take the most recent `fy`; prefer `confirmed` over `probable` over
`concentration_only`; and carry forward the best non-null value of each attribute across the group
rather than taking them all from the winning row. A pair whose most recent row is
`relationship_terminated` must not be added to the graph at all — record it in the summary so the UI
can show that the edge existed and ended.

**Related-party edges need their own caveat.** Every named supplier edge in the collected data comes
from a related-party note under Ind AS 24 — meaning all of them are promoter-affiliated or group
entities, because those are the only counterparties a filer is *compelled* to name. This is a real
dependency and belongs in the graph, but it is not an arm's-length supply relationship: a group
supplier's failure dynamics are entangled with the parent's, and the same promoter may support both.
Do not present a related-party edge as evidence of an independent supply chain. `edge_provenance`
(see `data/real/schema_change_request.md`) exists to carry this distinction into the UI.

### 3.3 Contagion — `engine/contagion.py`

The core of the product.

```python
buffer_strength(n) = clamp(cash_buffer_days / BUFFER_REF_DAYS, 0.0, MAX_BUFFER_STRENGTH)
# BUFFER_REF_DAYS = 90, MAX_BUFFER_STRENGTH = 0.35
```

Nobody is fully immune — hence the cap.

**The cap was lowered from 0.9 to 0.35 after collection measured this field.** Across 44 verified
company-years — 22 distress, 22 control — `cash_buffer_days` does **not** separate the two cohorts:
AUC 0.569 against a 0.500 coin flip. The lowest buffers in the set belong to an investment-grade
control (Balrampur Chini, 0 days) and the highest to a company that collapsed months later (Gensol,
351 days, whose cash was later found not to be what the balance sheet claimed).

Keep the term — surviving a payment delay longer when you hold more cash is mechanically real, and
this is a shock-absorption term rather than a predictive signal, so the AUC does not condemn it. But
a measurement this noisy must **nudge, not decide**. At 0.9 the buffer swung per-hop transmission by
10x and dominated propagation; at 0.35 the swing is 1.54x.

Two consequences worth internalising. First, real buffers are far thinner than the mock assumed
(tier-1 median **12 days**, not 60–100), so on real data the buffer term damps almost nothing and
contagion runs much deeper than any mock run will suggest. Second, reported cash is a poor proxy for
usable liquidity — one company's ₹770 crore of "current investments" turned out to be unquoted equity
pledged against loans. Prefer undrawn committed facilities once that field is populated.

```
fragility⁰(n) = own_stress(n)

for i in 1 .. MAX_ITERATIONS:                      # MAX_ITERATIONS = 10
    for each node s, in sorted(node_ids):
        inherited(s) = Σ over buyers b of s:
                           fragility^(i−1)(b) × exposure_pct(s → b)
        inherited(s) × = DAMPING                    # DAMPING = 0.75
        inherited(s) × = (1 − buffer_strength(s))
        fragility^i(s) = min(1.0, own_stress(s) + inherited(s))

    if max |fragility^i − fragility^(i−1)| < EPSILON:   # EPSILON = 0.001
        break
```

**Non-negotiable implementation details:**

- **Synchronous update.** Compute the whole new vector from the previous one, then swap. Updating in place makes the result depend on iteration order
- **Sorted iteration**, always
- **Cycles are expected.** Supply chains contain them. Synchronous iteration with damping handles them; do not attempt a topological sort
- Record `iterations_to_converge` in the summary
- Compute `propagation_depth` with a BFS from the originating stress nodes, following edges buyer → supplier

Why damping: without it, a long chain accumulates stress without limit and everything ends up at 1.0. `0.75` means each hop transmits three-quarters of what reached it, which produces sensible three-to-four-hop decay.

### 3.4 Criticality — `engine/criticality.py`

```
bt          = networkx.betweenness_centrality(G, normalized=True)
bt_norm(n)  = bt(n) / max(bt.values())            # 0 if max is 0

single_source(n) = 1.0 if any outgoing edge has is_single_source else 0.0

flow_share(n)      = Σ annual_value_cr on outgoing edges / Σ over all edges
flow_share_norm(n) = flow_share(n) / max(flow_share.values())

criticality(n) = clamp(
      W_BETWEENNESS  * bt_norm(n)          # 0.45
    + W_SINGLE_SOURCE * single_source(n)   # 0.35
    + W_FLOW_SHARE   * flow_share_norm(n), # 0.20
    0.0, 1.0)
```

Betweenness on a few hundred nodes is fast enough. If it becomes slow, use `k`-sampling **with a fixed seed** — never unseeded.

### 3.5 Ranking — `engine/ranking.py`

```
final_score(n) = fragility(n) × criticality(n)
```

**Multiplicative, deliberately.** If either factor is near zero the node does not belong on the list. A robust chokepoint is fine. A fragile commodity supplier is replaceable. This is the argument the product rests on — do not switch to a weighted sum.

Bands, from `config.py`:

| Band | `final_score` |
|---|---|
| `critical` | ≥ 0.50 |
| `high` | 0.30 – 0.50 |
| `watch` | 0.15 – 0.30 |
| `stable` | < 0.15 |

Sort descending by `final_score`, **ties broken by `node_id` ascending**. Required for determinism. `rank` is `null` for `stable` nodes.

### 3.6 Reasons — `engine/ranking.py`

Every score carries a non-empty `reason_text`. Template-generated, deterministic, no LLM.

Build `reason_factors` first, then compose the sentence from the top two or three.

| `kind` | Template |
|---|---|
| `exposure` | `"{pct}% of revenue depends on {buyer_name}"` |
| `upstream_stress` | `"{buyer_name} late supplier payments rose {ratio}x in {fy}"` |
| `single_source` | `"Sole source for {component}"` |
| `chokepoint` | `"{n} downstream suppliers route through this node"` |
| `thin_buffer` | `"{days} days of cash buffer"` |
| `own_stress` | `"Own payment behaviour deteriorated in {fy}"` |

Factor `weight` values are each contributor's share of `final_score` and **must sum to 1.0** — schema enforces it.

Target output:

> "78% of revenue depends on Brakecraft Components, whose late supplier payments rose sharply in FY24. Sole source for hydraulic seal kit."

A judge should understand why a node is flagged without asking. Interpretability is what makes this a credible risk product rather than a number generator.

### 3.7 Intervention — `engine/intervention.py`

**Cost to stabilise:**

```
quarterly_receivable(n) = Σ annual_value_cr on outgoing edges / 4
intervention_cost_cr(n) = round(quarterly_receivable(n) × fragility(n), 2)
```

One quarter of receivables, scaled by how stressed the node is.

**Exposure if it fails:**

```
value_through(n)          = Σ annual_value_cr on all paths from n to any tier-0 node
estimated_exposure_cr(n)  = round(value_through(n) × (DISRUPTION_MONTHS / 12) × final_score(n), 2)
# DISRUPTION_MONTHS = 3
```

Both are **stated assumptions, not measurements.** Document them in `config.py` and be ready to say so. "We assume a three-month disruption window" is a defensible answer; pretending it is measured is not.

**Applying an intervention:** funding reduces the node's inherited stress in proportion to coverage.

```
coverage = clamp(amount_cr / intervention_cost_cr, 0.0, 1.0)
inherited_stress_after = inherited_stress × (1 − coverage)
```

Then re-run propagation from scratch with that node's stress pinned. Do not patch scores in place — a full re-run is what makes downstream improvements appear, which is the whole point of step 7.

### 3.8 Supply disruption — `engine/disruption.py`

**A second propagation, running WITH goods flow.** Added in schema 1.2 to close the
`DEMO_SCENARIO.md` §6 counterfactual, which §3.3 structurally cannot reach: the anchor is the
top buyer, so no payment stress propagates into it and its fragility is `0.0` by construction.

    contagion:   buyer -> supplier   (money that failed to arrive)
    disruption:  supplier -> buyer   (parts that failed to arrive)

**The seed is the decision that matters.** `own_stress` measures *payment behaviour*. A company
stretching its payables is conserving cash, not stopping its line — it is exporting the problem
downstream rather than absorbing it. Seeding halt risk from `own_stress` would say the visible
tier-1 is the one about to stop, which is the belief this product exists to correct. So:

```
seed(n) = max(0.0, fragility(n) - own_stress(n))     # money owed that never arrived
```

For a funded node this is the *relieved* inherited stress, because `intervention.py` pins
fragility to `own_stress + relieved`. **Do not seed from the reported `inherited_stress`** — the
pin does not appear there, so the intervention would change nothing downstream, which is the
whole demo beat. This bit me once; it is the easiest thing here to get subtly wrong.

**Replaceability, not rupee value.**

```
supply_impact(s -> b) = 1.0                        if is_single_source is True
                      = annual_value(s,b) / inbound_value(b)   otherwise
```

A confirmed sole source counts fully whatever the part costs — a ₹19 cr seal kit stops a
₹1,241 cr brake assembly. Same insight as §3.4's within-tier normalisation: size is not
importance. `is_single_source` of `None` takes the fallback, which implicitly assumes the part
is replaceable — a real limitation on real data, where all 37 edges are `null`. Say so.

**Noisy-OR, not a sum.** A line stops if *any* input it cannot replace stops:

```
disruption(b) = 1 - Π over suppliers s of (1 - halt(s) * supply_impact(s,b))
halt(n)       = 1 - (1 - seed(n)) * (1 - disruption(n))
```

Two independent reasons to stop delivering: no cash, or no parts. Bounded in [0,1] by
construction, so it needs no cap and no damping constant, and it converges on cycles because the
iteration is monotone increasing and bounded. Summing instead would let forty mildly-wobbly
suppliers halt a healthy plant.

Synchronous update over sorted node ids, exactly as §3.3. `disrupted_inflow_cr` uses
`halt(s) × annual_value(s,b)` with **no** impact weight — the weight answers "does the line
stop", the money answers "how much trade fails to arrive", and they take different weights on
purpose.

**Bands** are their own constants (`DISRUPTION_BAND_*`), currently equal to the risk bands.
They are deliberately not calibrated to put the demo's anchor in the top band — see
`config.py`.

**One sentence, out loud:** stress flows down the chain as invoices that were never paid;
failure flows back up it as parts that never arrived.

---

## 4. Mock data generator — `engine/mockgen.py`

**Build this first.** Everyone is blocked until it exists.

```bash
python -m engine.mockgen --seed 42 --out data/mock/network.json
```

**Requirements:**

- ~400 nodes across 4 tiers, ~1,200 edges
- **The six `DEMO_SCENARIO.md` IDs placed explicitly first**, with their specified names, tiers and relationships, before generating filler
- Deterministic: same seed → byte-identical file. Seed a local `random.Random(seed)`, never the global module
- Output validates against `NetworkInput` before writing
- Randomness is permitted **here and nowhere else**

**Plausibility bar — this is not cosmetic.** Fake-looking data is the most likely thing to make judges dismiss the project.

| Property | Requirement |
|---|---|
| Names | Realistic Indian manufacturing names. **Never `Company_47`** |
| Fan-out | Tier-1 has 20–50 suppliers, not 3 |
| Size distribution | Heavily skewed — a few large, many tiny |
| Buffers by tier | Tier 1: 3–45 days, **empirical** (29 real company-years: median 12, quartiles 4 and 30.5). Tier 0: 60–200, Tier 2: 2–30, Tier 3: 1–20 — **stated assumptions, no observations exist** |
| Chokepoints | 3–5 genuine single-source nodes so criticality has something real to find |
| Numbers | Non-round. `24.70` not `25.00` |
| Stress signals | 6–10 observable nodes with two years each, shaped like real Schedule III data |

Give `N007` disclosures matching the real pattern you're modelling: a clean-looking ageing table beside a sharply rising MSMED flow figure. That contrast is the demo's step 3.

---

## 5. Transform — `engine/transform.py`

Written in Phase 2 or 3. Not needed for the demo to work.

```bash
python -m engine.transform --in data/real/ --out data/real/network.json
```

Reads the five collection CSVs (`SCHEMA.md` §7) and emits the **identical shape** as `mockgen`. Steps are specified in `SCHEMA.md` §7.1.

**This is the only module that knows CSVs exist.** No other file imports pandas for data loading.

Two things that will silently corrupt the model if you get them wrong:

- **Units.** Source reports mix ₹ million and ₹ crore. Convert once, here, and record the original in `meta`
- **`has_not_due_column`.** Do not default it to `true`. A filer who omits the column produces an `under_1yr` figure that means something different, and defaulting will make a healthy company look badly overdue

---

## 6. Tests — `tests/engine/`

| Test | Asserts |
|---|---|
| `test_determinism` | Pipeline run twice on the same input gives byte-identical JSON |
| `test_schema_valid` | `mockgen` output validates against `NetworkInput`; pipeline output against `ScoredNetwork` |
| `test_demo_scenario` | Ranking and bands match `data/fixtures/demo_scenario.json` |
| `test_fragility_bounds` | No score outside [0, 1] on any node |
| `test_convergence` | Contagion terminates under `MAX_ITERATIONS` |
| `test_cycles` | A network with a cycle converges rather than diverging |
| `test_reasons_present` | Every score has a non-empty `reason_text` and factors summing to 1.0 |
| `test_null_vs_zero` | A `null` stress input and a `0.0` input produce different behaviour |
| `test_intervention_monotonic` | Funding a node never *increases* fragility anywhere |
| `test_no_input_mutation` | The input dict is unchanged after `score_network` |
| `test_own_payment_stress_does_not_seed_a_halt` | A node stressed only by its own disclosures has halt risk entirely from *its* suppliers |
| `test_disruption_reaches_the_anchor` | The tier-0 anchor carries non-zero `supply_disruption` despite fragility 0.0 |
| `test_intervention_reduces_anchor_disruption` | Funding `N042` drains supply risk out of `N001` — `DEMO_SCENARIO.md` §6 |
| `test_intervention_never_worsens_disruption` | Funding never raises `supply_disruption` anywhere |
| `test_disruption_converges_on_a_cycle` | Noisy-OR settles on a cycle rather than ratcheting to 1.0 |

`test_demo_scenario` is your safety net. If a tuning change breaks it, that is the system working — retune, or update the fixture deliberately with both others named on the PR.

---

## 7. Phases

**Phase 0 — Contract freeze**
- Agree `SCHEMA.md` and `schema.json` with B and C
- Ship `mockgen.py` and commit `data/mock/network.json`
- Commit `data/fixtures/demo_scenario.json`
- **Exit:** B and C can both work without you

**Phase 1 — Independent build**
- `graph.py`, `stress.py`, `contagion.py`, `criticality.py`, `ranking.py`
- `pipeline.py` producing a valid `ScoredNetwork`
- **Exit:** `python -m engine.pipeline data/mock/network.json` prints a sensible ranked list

**Phase 2 — Integration**
- `intervention.py` and scenario handling
- Wire to B's API, fix contract mismatches
- **Exit:** one node flows end to end, even if numbers are rough

**Phase 3 — Demo path**
- Tune until `test_demo_scenario` passes
- Determinism check green
- `transform.py` if the real dataset has landed
- **Exit:** the seven-step demo runs correctly

**Phase 4 — Hardening**
- Edge cases, error messages, `config.py` comments
- Be able to explain the propagation rule in one sentence, out loud:
  *stress flows down the chain as invoices that were never paid; failure flows back up it as
  parts that never arrived*

---

## 8. Traps specific to your track

- **Edge direction.** Goods flow supplier → buyer; stress flows buyer → supplier. Get this backwards and stress climbs *up* the chain, which looks plausible and is completely wrong
- **In-place updates in the contagion loop.** Makes results order-dependent and breaks determinism
- **Unseeded betweenness sampling.** Only if you switch to `k`-sampling — but if you do, seed it
- **Defaulting `has_not_due_column`.** Silently corrupts a company's stress score
- **Switching `final_score` to a weighted sum.** Destroys the N042-vs-N203 contrast, which is the core argument
- **Adding ML "because the score could be learned."** Explicitly out of scope — `AGENTS.md` §1.2
