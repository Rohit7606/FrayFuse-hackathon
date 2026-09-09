# PERSON_C.md — Frontend, Visualisation & Product UX

**Person C / Person 3 — "Build what the judge experiences."**

Read `AGENTS.md`, `SCHEMA.md` and `DEMO_SCENARIO.md` before starting. This file assumes all three.

---

## 1. What you own

| Path | Yours |
|---|---|
| `web/` | Everything |
| `tests/web/` | Everything |

Your reviewer for every PR is **Person B**.

You own everything the judge sees, and — importantly — **the demo flow itself**. A and B provide technical input on the sequence; you own it.

That is deliberate. The person who builds the visuals understands the visual story best. Splitting "who builds the demo" from "who explains the demo" reliably produces a beautiful UI and a rambling pitch.

---

## 2. The one thing that matters most

Your entire product argument is:

> **This is a network problem. Networks cannot be reasoned about in a spreadsheet.**

A judge who *sees* the cascade spread across a live graph has understood the thesis without anyone explaining it. A judge who reads a table of scores has not.

**So spend your effort on the graph and the cascade animation, not on having many screens.** One great visual beats four mediocre ones. If you run short of time, cut stakeholder views before you cut the animation.

---

## 3. Stack

| Layer | Choice |
|---|---|
| Framework | React + Vite |
| Graph | `react-force-graph-2d` or `d3-force`. 2D — 3D looks like a demo of a graph library, not of a risk product |
| Styling | Whatever you're fastest in. Tailwind is fine |
| State | React state. No Redux, no state library |
| Charts | Only if genuinely needed. The graph is the visual |

**Forbidden:** `localStorage`, `sessionStorage`, any browser storage. Keep everything in React state.

Do not add a component library for four screens.

---

## 4. Never block on the backend

`web/src/mocks/` holds hand-written responses for all four endpoints, matching `SCHEMA.md` exactly.

```
npm run dev        # committed mocks
npm run dev:live   # http://localhost:8000
```

One flag, one API client module. Every component consumes the client, never `fetch` directly.

**Your mocks must validate against `schema.json`.** A mock that doesn't validate is not a mock — it is a future integration bug you have hidden from yourself. Test this.

B will stub the real endpoints in Phase 0, so you can switch to live early. Do it as soon as the stubs exist — that's what makes Phase 2 cheap.

---

## 5. Components

### 5.1 Network graph — the centrepiece

Renders ~400 nodes, ~1,200 edges.

**Visual encoding:**

| Property | Meaning |
|---|---|
| Node colour | `risk_band` — critical / high / watch / stable |
| Node size | `revenue_cr`, log-scaled. Otherwise the anchor is a planet and Tier-3 is invisible |
| Node ring | Dashed outline for `data_source: "synthetic"`, solid for `"real"` |
| Node shape | Optional: square for `is_single_source` |
| Edge thickness | `annual_value_cr`, log-scaled |
| Edge colour | Highlighted when it carried stress in the last propagation |

**Layout:** radial by tier — anchor at centre, tiers moving outward. Do not use a raw force layout with no structure; it produces a hairball that communicates nothing.

**Performance:** 400 nodes is fine on canvas. Do not attempt SVG for the full network. Turn off physics once the layout settles — a drifting graph during a demo is distracting.

**The synthetic/real distinction is not optional.** A judge must never mistake a generated node for a real company. Legend it explicitly.

### 5.2 Cascade animation — the moment that sells it

Step 4 of the demo. Get this right before anything else.

**The sequence:**

1. All nodes neutral
2. Trigger node (`N007`) pulses, turns amber
3. Wave 1: its direct suppliers shift toward amber
4. Wave 2: their suppliers shift
5. Wave 3: red appears at the fragile-and-critical nodes
6. Settle — final `risk_band` colours

**How to drive it:** the engine returns `propagation_depth` on every score. Group nodes by depth and reveal one group per step. You are not re-simulating anything in the browser — you are animating a result the engine already computed.

**Timing:** 600–900 ms per wave. Under 400 ms and the eye can't follow it. Over 1.5 s and the room gets restless. Make it a constant you can tune during rehearsal.

Add a **replay button.** You will run this many times.

### 5.3 Ranked list

Four names out of 400+. The payoff of step 5.

Per row:

- Rank, name, tier
- `risk_band` chip
- `reason_text` — **display it in full.** This is what makes the product interpretable rather than a number generator
- `intervention_cost_cr` and `estimated_exposure_cr`, side by side
- Click → node detail, and centre the graph on that node

**Do not truncate the reason text.** It is the single most defensible thing on screen.

### 5.4 Node detail panel

- Name, tier, sector, revenue, cash buffer
- Fragility and criticality **shown separately**, not just the final score
- `reason_factors` as a small breakdown with weights
- Top buyers with `exposure_pct`
- Data source badge — real or synthetic
- If observable: the stress signals, with the ageing table beside the MSMED flow figure

That last item **is** demo step 3. It is where the judge sees the ageing table looking clean while the whole-year figure rises. Build it as a comparison, side by side, so the contradiction is visible at a glance.

### 5.5 Intervention UI

- Select node, enter amount (pre-filled from `intervention_cost_cr`)
- "Apply" → `POST /api/intervene`
- Before/after graph state, toggleable
- Delta summary: nodes improved, exposure reduced, cost
- **Counterfactual toggle** — flip back to "no intervention" and let the cascade complete to the anchor

The counterfactual is demo step 7's second half. When intervention is off, `N001` turns red. Do not narrate it — let the graph do it.

Make the toggle **instant.** Both results are already in the `/api/intervene` response; you are switching between two known states, not re-fetching.

### 5.6 Stakeholder views

A filter on the same data, not three separate apps.

| View | Shows |
|---|---|
| **Anchor** | Full network, ranked list, intervention controls, total exposure |
| **Bank** | One borrower at a time — its buyers, their stress, network-adjusted risk, recommended limit change |
| **Supplier** | Own position, buyer concentration, incoming offer |

**Cut these first if time runs short.** They satisfy a requirement; the graph and cascade win the room.

### 5.7 What-if controls

A slider on the trigger node's stress → `POST /api/simulate` → recolour.

Debounce at ~300 ms. Do not fire a request per pixel.

This is your best asset in Q&A. When a judge asks "what if the stress were worse?", you move a slider instead of explaining.

---

## 6. Presentation rules

- **Every number carries its unit.** `₹4.80 cr`, `78%`, `18 days`. Never a bare float
- **Round for humans.** `₹4.8 cr`, not `4.7983`
- **Colour is not the only signal.** Add shape or a label — some judges have colour vision deficiency, and projectors distort hues
- **Legend always visible.** A judge shouldn't have to ask what amber means
- **No loading spinners longer than a beat.** Pre-fetch the baseline at mount
- **Design for a projector:** larger fonts than feel right, high contrast, test at 1280×720

---

## 7. Tests — `tests/web/`

Keep it light. You are not shipping to production.

| Test | Asserts |
|---|---|
| `test_mocks_valid` | Every file in `src/mocks/` validates against `schema.json` |
| `test_renders_network` | Graph renders from mock data without errors |
| `test_ranked_list` | Correct number of rows, reason text present and untruncated |
| `test_cascade_completes` | Animation runs to settle without console errors |
| `test_intervention_toggle` | Before/after switch changes node colours |
| `test_no_browser_storage` | Grep the bundle for `localStorage` / `sessionStorage` |

`test_mocks_valid` is the one that pays for itself — it catches contract drift before Phase 2.

---

## 8. Phases

**Phase 0 — Contract freeze**
- Agree `SCHEMA.md` and `schema.json` with A and B
- Write `web/src/mocks/` for all four endpoints
- Vite app shell, API client with the mock/live flag
- **Exit:** you can build with the backend switched off

**Phase 1 — Independent build**
- Network graph rendering from mocks
- Ranked list, node detail panel
- **Exit:** graph and list render correctly from committed mocks

**Phase 2 — Integration**
- Switch to B's live API, fix mismatches at the contract
- Cascade animation against real `propagation_depth`
- **Exit:** live data renders end to end

**Phase 3 — Demo path**
- Intervention UI, counterfactual, what-if slider
- Stakeholder views
- **Rehearse the seven steps end to end, repeatedly**
- **Exit:** the demo runs clean without a refresh

**Phase 4 — Hardening**
- Empty and error states, projector testing, final rehearsal

---

## 9. You own the demo flow

`DEMO_SCENARIO.md` §4 has the seven steps. Beyond building them:

- **Read node IDs from `data/fixtures/demo_scenario.json`.** Never hardcode `N042` in a component
- **Rehearse on the actual machine and projector**, not just your laptop
- **Time it.** Seven minutes. Step 4 and step 7 get the most air
- **Have a fallback.** A recorded video or screenshots, in case the network fails on the day
- **Open with the problem, not the engine.** A stopped production line and a CFO who had the money and didn't know where to send it. The technique only lands after the stakes do

---

## 10. Traps specific to your track

- **Building screens instead of depth.** Four polished views beat eight rough ones. The graph and cascade are the product
- **Force layout with no structure.** Produces a hairball. Constrain radially by tier
- **Truncating reason text.** Removes the most defensible thing on screen
- **Re-fetching on the counterfactual toggle.** Both states are already in the response; switching should be instant
- **Blurring real and synthetic nodes.** A judge must never mistake a generated company for a real one
- **Hardcoding demo node IDs in components.** Read the fixture
- **Browser storage.** Forbidden — `AGENTS.md` §1.2
- **Leaving the demo until Phase 3 to rehearse.** Rehearse from Phase 2, roughly, and keep rehearsing
