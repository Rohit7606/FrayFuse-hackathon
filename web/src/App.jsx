import { useEffect, useState } from 'react'
import { getAtRisk, getNetwork, isLive } from './api/client.js'

/**
 * Scaffold shell — Person C owns everything below this comment.
 *
 * This exists to prove the seam works end to end and to give the track a
 * running start; it is deliberately NOT the product. The graph and the cascade
 * animation are the product (PERSON_C.md §2), and one great visual beats four
 * screens. Replace this component.
 *
 * Two rules it already follows and that should survive the rewrite: every
 * number carries its unit, and the data-source badge is never blurred — a judge
 * must never mistake a generated company for a real one.
 */
export default function App() {
  const [atRisk, setAtRisk] = useState(null)
  const [network, setNetwork] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([getAtRisk(10), getNetwork()])
      .then(([ranked, net]) => {
        setAtRisk(ranked)
        setNetwork(net)
      })
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <main style={S.page}><p className="band-critical">{error}</p></main>
  if (!atRisk || !network) return <main style={S.page}><p>Loading…</p></main>

  const nodesById = Object.fromEntries(network.nodes.map((n) => [n.node_id, n]))
  const { summary } = atRisk

  return (
    <main style={S.page}>
      <header style={S.header}>
        <h1 style={S.h1}>FrayFuse</h1>
        <span style={S.mode}>{isLive ? 'live API' : 'committed mocks'}</span>
      </header>

      <p style={S.lede}>
        {summary.total_nodes} companies · {summary.at_risk_count} at risk ·
        {' '}stress originates at {summary.stressed_origin_nodes.join(', ')} ·
        {' '}converged in {summary.iterations_to_converge} iterations
      </p>

      <p style={S.lede}>
        <strong>₹{summary.total_intervention_cost_cr} cr</strong> to stabilise ·
        {' '}<strong>₹{summary.total_estimated_exposure_cr} cr</strong> at risk if nobody moves
      </p>

      <ol style={S.list}>
        {atRisk.ranking.map((nodeId) => {
          const score = atRisk.scores.find((s) => s.node_id === nodeId)
          const node = nodesById[nodeId]
          return (
            <li key={nodeId} style={S.row}>
              <div style={S.rowHead}>
                <strong>{node?.name ?? nodeId}</strong>
                <span className={`band-${score.risk_band}`}>{score.risk_band}</span>
                <span style={S.badge}>
                  {node?.data_source === 'real' ? 'real filing' : 'synthetic'}
                </span>
              </div>
              {/* Never truncated — the most defensible thing on screen. */}
              <p style={S.reason}>{score.reason_text}</p>
              <p style={S.figures}>
                tier {node?.tier} · fragility {score.fragility.toFixed(4)} ×
                {' '}criticality {score.criticality.toFixed(4)} = {score.final_score.toFixed(4)} ·
                {' '}stabilise ₹{score.intervention_cost_cr} cr ·
                {' '}exposure ₹{score.estimated_exposure_cr} cr
              </p>
            </li>
          )
        })}
      </ol>
    </main>
  )
}

const S = {
  page: { maxWidth: 900, margin: '0 auto', padding: '32px 24px' },
  header: { display: 'flex', alignItems: 'baseline', gap: 12 },
  h1: { fontSize: 32, margin: 0 },
  mode: { color: 'var(--muted)', fontSize: 14 },
  lede: { color: 'var(--muted)', margin: '8px 0' },
  list: { listStyle: 'none', padding: 0, marginTop: 24 },
  row: {
    background: 'var(--panel)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
  },
  rowHead: { display: 'flex', alignItems: 'center', gap: 12 },
  badge: {
    marginLeft: 'auto',
    fontSize: 12,
    color: 'var(--muted)',
    border: '1px solid var(--line)',
    borderRadius: 999,
    padding: '2px 10px',
  },
  reason: { margin: '10px 0 6px' },
  figures: { color: 'var(--muted)', fontSize: 14, margin: 0 },
}
