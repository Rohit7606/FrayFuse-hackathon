/**
 * The single API client. Components consume this and never call fetch directly.
 *
 * `npm run dev` serves the committed mocks in ../mocks and needs no backend at
 * all; `npm run dev:live` hits the API. That is the whole switch — see
 * AGENTS.md §3.3, which makes "blocked waiting for the backend" a design fault
 * rather than a scheduling one.
 *
 * The mocks are generated from the live API, so they are the real contract
 * rather than hand-written guesses that drift.
 */

const USE_LIVE = typeof __USE_LIVE_API__ !== 'undefined' && __USE_LIVE_API__
const BASE = typeof __API_BASE__ !== 'undefined' ? __API_BASE__ : 'http://localhost:8000'

export const isLive = USE_LIVE

/** Shape the API returns on a handled error — see SCHEMA.md §5.6. */
export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || `Request failed with ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.code = body?.error
    this.nodeId = body?.node_id
  }
}

async function request(path, options) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, body)
  return body
}

// Mocks load through a dynamic import so a live build never ships them — they
// are ~3.5 MB of fixtures. Vite code-splits them into their own chunks, which
// mock mode fetches on demand and live mode never requests at all.
//
// No artificial delay: a fake latency only teaches you to design around a
// wait that will not be there on the day.
const mocked = (loader) => loader().then((module) => module.default)

/** Raw network for the initial render. No scoring — this one gates first paint. */
export function getNetwork() {
  return USE_LIVE ? request('/api/network') : mocked(() => import('../mocks/network.json'))
}

/** Baseline scoring, ranked nodes only. The default view. */
export function getAtRisk(limit = 10) {
  return USE_LIVE ? request(`/api/at-risk?limit=${limit}`) : mocked(() => import('../mocks/at-risk.json'))
}

/**
 * Score under a scenario. Drives the what-if slider.
 * Debounce callers at ~300ms — do not fire a request per pixel.
 */
export function simulate(scenario) {
  return USE_LIVE
    ? request('/api/simulate', { method: 'POST', body: JSON.stringify({ scenario }) })
    : mocked(() => import('../mocks/simulate.json'))
}

/**
 * Before, after and delta in one response.
 *
 * Both states come back together, so the counterfactual toggle switches
 * between two results already in hand. Never re-fetch on toggle.
 */
export function intervene(interventions, baselineScenario = null) {
  return USE_LIVE
    ? request('/api/intervene', {
        method: 'POST',
        body: JSON.stringify({
          interventions,
          baseline_scenario: baselineScenario ?? { stress_overrides: [], interventions: [] },
        }),
      })
    : mocked(() => import('../mocks/intervene.json'))
}

export function health() {
  return USE_LIVE ? request('/health') : Promise.resolve({ status: 'ok', network: 'committed mocks', nodes: 412 })
}
