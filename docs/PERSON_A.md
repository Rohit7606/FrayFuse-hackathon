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

Two signals, from the two disclosures that can disagree.

**Signal 1 — migration ratio**

```
migration(t) = under_1yr / (not_due + under_1yr)
```

Money moving from "not yet due" into "overdue" means the company is slipping.

**Unavailable when `has_not_due_column` is `false`** — that filer's `under_1yr` silently includes not-yet-due amounts. Do not compute it, do not substitute a default. Fall back to signal 2 alone and reweight.

**Signal 2 — late-payment intensity (primary)**

```
late_intensity(t) = msmed_principal_paid_beyond_appointed_day_cr / cost_of_materials_cr
```

This is the whole-year flow figure. It cannot be tidied up before 31 March, which is why it carries more weight.

Fall back to `revenue_cr` as the denominator if `cost_of_materials_cr` is `null`, and record that you did.

**Combine**

```
Δmigration = migration(t) − migration(t−1)
Δlate      = late_intensity(t) − late_intensity(t−1)

z_m = (Δmigration − sector_median_Δmigration) / max(sector_std_Δmigration, EPSILON)
z_l = (Δlate      − sector_median_Δlate)      / max(sector_std_Δlate,      EPSILON)

raw = W_MIGRATION * z_m + W_LATE * z_l          # W_MIGRATION 0.35, W_LATE 0.65
own_stress = clamp(2 / (1 + exp(−raw)) − 1, 0.0, 1.0)
```

That last transform maps `raw = 0` to `own_stress = 0` and rises monotonically. A plain logistic would give a stable company 0.5, which is wrong.

**Sector statistics:** computed across all observable nodes in the same `sector`. With fewer than `MIN_SECTOR_SAMPLE` (3) nodes, fall back to global statistics and note it in the reason factors.

**Edge cases you must handle explicitly:**

| Case | Behaviour |
|---|---|
| Only one year of data | `own_stress = 0.0`. Cannot compute a change. Record `insufficient_history` |
| `has_not_due_column` false | Signal 1 unavailable. Use signal 2 at full weight |
| Both signals null | `own_stress = 0.0`. Never guess |
| Explicit `0.0` vs `null` | Different. `0.0` is real data; `null` is absence. See `AGENTS.md` §3.6 |

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

### 3.3 Contagion — `engine/contagion.py`

The core of the product.

```python
buffer_strength(n) = clamp(cash_buffer_days / BUFFER_REF_DAYS, 0.0, MAX_BUFFER_STRENGTH)
# BUFFER_REF_DAYS = 90, MAX_BUFFER_STRENGTH = 0.9
```

Nobody is fully immune — hence the 0.9 cap.

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
| Buffers by tier | Tier 0: 150–250 days. Tier 1: 60–100. Tier 2: 15–40. Tier 3: 5–25 |
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
- Be able to explain the propagation rule in one sentence, out loud

---

## 8. Traps specific to your track

- **Edge direction.** Goods flow supplier → buyer; stress flows buyer → supplier. Get this backwards and stress climbs *up* the chain, which looks plausible and is completely wrong
- **In-place updates in the contagion loop.** Makes results order-dependent and breaks determinism
- **Unseeded betweenness sampling.** Only if you switch to `k`-sampling — but if you do, seed it
- **Defaulting `has_not_due_column`.** Silently corrupts a company's stress score
- **Switching `final_score` to a weighted sum.** Destroys the N042-vs-N203 contrast, which is the core argument
- **Adding ML "because the score could be learned."** Explicitly out of scope — `AGENTS.md` §1.2
