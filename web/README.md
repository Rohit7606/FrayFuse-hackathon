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
