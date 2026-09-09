# FrayFuse — Web Frontend

Person C's track. React + Vite.

## Setup

```bash
cd web
npm install
npm run dev        # uses committed mocks by default
npm run dev:live   # points at http://localhost:8000
npm run build
npm run lint
```

## Stack

- React + Vite
- `react-force-graph-2d` or `d3-force` for the network graph (2D only)
- Vanilla CSS or Tailwind
- React state only — no Redux, no state library

## Mocks

`src/mocks/` holds hand-written responses for all four API endpoints,
matching `SCHEMA.md` exactly. These must validate against `schema.json`.

## Status

Scaffold only — Person C owns everything in `src/` and should replace
`App.jsx`, which exists to prove the seam works, not to be the product.

`src/mocks/` is **generated from the live API**, not hand-written, so it is the
real contract rather than a guess that drifts. Regenerate after any engine or
schema change:

```bash
python -m engine.mockgen --seed 42 --out data/mock/network.json
python scripts/refresh_web_mocks.py
```

`tests/web/test_mocks_valid.py` validates all four against `schema.json` and
against `data/fixtures/demo_scenario.json`, so drift fails the suite rather
than surfacing in a rehearsal.

## What to build first

The graph and the cascade animation are the product (`PERSON_C.md` §2). The
engine already returns `propagation_depth` on every score, so the cascade is
grouping nodes by depth and revealing one group per wave — the browser is not
re-simulating anything.
