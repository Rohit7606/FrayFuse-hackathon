# FrayFuse

**Which few suppliers are about to run out of cash *and* cannot be replaced, and how much money would stabilise each one?**

When a large Tier-1 company runs short of cash it quietly stretches payment to its suppliers. Those suppliers stretch theirs. Small firms two and three tiers down run out of cash and fail — which halts production for the large company at the top, who never knew they existed.

FrayFuse maps the chain, detects the payment-stress trigger from published filings, propagates it downstream, and turns it into a specific funding decision.

> **In one sentence:** stress flows down the chain as invoices that were never paid; failure flows back up it as parts that never arrived.

---

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m engine.pipeline data/mock/network.json
```

That prints the ranked list and the anchor counterfactual, with no API and no frontend.

To run the whole demo — API and UI together, on Windows:

```powershell
./scripts/demo.ps1
./scripts/demo.ps1 -Network data/real/network.json    # the real dataset
```

The script waits on `/health` before starting the frontend and stops both on Ctrl+C. A `Makefile` wraps the same commands for anyone who has `make`; it is not installed on the demo machine, so `demo.ps1` is the working path.

---

## How it works

Four stages, no machine learning anywhere. A transparent propagation rule that can be explained in one sentence beats a trained model that cannot be justified — and at these data volumes ML would be theatre.

**1. Stress detection** — `engine/stress.py`
A ladder of four signals read from published ageing tables and MSMED disclosures, weights renormalised over whichever rungs a filer actually discloses. A rise in MSMED interest is a *statutory admission* of late payment, which is why it leads the ladder. No rung is ever substituted with a default.

**2. Contagion** — `engine/contagion.py`
Stress propagates **buyer → supplier**, against goods flow, following the money that failed to arrive. Scaled by revenue dependency, damped per hop, iterated to convergence. Cycles are expected and handled.

**3. Criticality** — `engine/criticality.py`
Betweenness, sole-source status, and share of trade flow — normalised **within tier**, not across the network. Network-wide normalisation hands every maximum to the tier-1 hub and buries exactly the small, irreplaceable suppliers the product exists to find.

**4. Ranking** — `engine/ranking.py`
`final_score = fragility × criticality`, multiplicative and deliberately so. A robust chokepoint is fine. A fragile commodity supplier is replaceable. **We rank by fragile × irreplaceable**, which is the whole argument.

Then, running the other way:

**5. Supply disruption** — `engine/disruption.py`
Whose line stops when a supplier stops delivering. Seeded by the part of a node's fragility it did *not* generate itself, because a company stretching its own payables is conserving cash, not stopping its line. This is what lets a failure deep in the chain reach the anchor at the top.

Every constant lives in `engine/config.py` with the evidence for its value. Several are stated assumptions rather than measurements, and they say so.

---

## What it produces

**On the mock network** (412 nodes, seed 42 — complete rupee values throughout):

| | |
|---|---|
| Ranked at risk | 15, of which 4 are named in the demo |
| Headline finding | `N042` Sealsworks — fragile **and** sole-source |
| Cost to stabilise | ₹16.54 cr |
| Exposure if nobody moves | ₹738.18 cr |

Funding `N042` with **₹2.04 cr** takes it `critical → stable`, takes `N118` `high → stable`, and drains the anchor's supply risk from **₹848.96 cr → ₹308.36 cr**.

**On the real dataset** (298 nodes — 43 real companies from published filings, plus a generated deep tier):

Hero MotoCorp Limited, a real tier-0 anchor, reaches `critical` supply disruption at **0.2089**, ₹37.94 cr of inbound supply at risk, stopped by Shivam Autotech Limited — whose stress comes from its own MSMED disclosures.

> **Quote the mock network for rupee-for-rupee figures, and the real network for the mechanism.** 13 of the 30 real edges carry no disclosed `annual_value_cr`, so exposure understates on real data. That is the deliberate consequence of never inventing a rupee figure beside a real company's name.

---

## Real versus synthetic — the line we do not cross

Every node and edge carries `data_source` at row level. The rules are in `data/real/DATA_DICTIONARY.md` §3b and two of them are enforced in code with tests, not left to care:

- **No sole-source claim against a real company.** An edge flagged `is_single_source` whose buyer is real would assert that firm single-sources a part — a fabricated claim about its supply chain. Chokepoints are confined to synthetic buyers
- **No generated rupee figure beside a real name.** A real company with an undisclosed field carries `null` and names it in `substituted`, so the engine's runtime fill stays a visible modelling decision rather than a fabricated fact frozen into a file

Tier-2 and tier-3 companies are **generated**, with names drawn from a fictional entity pool. They are not real businesses, and the UI must never present one as a real filer.

---

## Layout

```
engine/     the model — graph, stress, contagion, criticality, ranking,
            intervention, disruption, plus mockgen and the CSV transform
api/        FastAPI, four endpoints, stateless
web/        React frontend (scaffold — see Status)
data/       mock network, demo fixture, real collection CSVs
tests/      85 tests across all three tracks
```

Contracts and briefs, all worth reading before changing anything:

| File | What it governs |
|---|---|
| `AGENTS.md` | Rules every contributor follows — determinism, ownership, git discipline |
| `SCHEMA.md` + `schema.json` | The frozen contract between the three tracks |
| `DEMO_SCENARIO.md` | The canonical demo, with fixed node IDs |
| `docs/PERSON_A/B/C.md` | Per-track briefs |

---

## Commands

```bash
python -m engine.pipeline data/mock/network.json      # score and print
python -m engine.mockgen --seed 42 --out data/mock/network.json
python -m engine.transform --in data/real/ --out data/real/network.json
uvicorn api.main:app --port 8000                      # no --reload during a demo
pytest tests/ -q
ruff check .
cd web && npm install && npm run dev                  # mocks; dev:live for the API
```

`FRAYFUSE_NETWORK` selects the dataset the API serves. That one variable is the entire real-data switch.

**Determinism is mandatory** — the same input must give byte-identical output, because a judge will re-run the counterfactual on stage:

```bash
python -m engine.pipeline data/mock/network.json --json > run1.json
python -m engine.pipeline data/mock/network.json --json > run2.json
diff run1.json run2.json && echo DETERMINISTIC
```

---

## Status

Engine, API and data pipeline are complete and tested end to end. 85 tests, lint clean, determinism verified for scoring, mock generation and the CSV transform.

**The frontend is still a scaffold.** `web/src/App.jsx` renders the ranked list from committed mocks and proves the seam works, but the network graph and the cascade animation — the things that actually sell this — are not built. The API already serves everything they need, including `summary.anchor_disruption` for the closing beat.

---

## Not building

Machine learning, blockchain, auth, runtime document parsing, streaming, mobile, database servers, and LLM calls at runtime. Reasons for each are in `AGENTS.md` §1.2. Reason strings are template-generated and deterministic.
