interface RankedListProps {
  scores: any[] | undefined;
  nodes?: any[] | undefined;
  simulationState?: 'idle' | 'cascading' | 'cascaded' | 'intervened';
  currentWave?: number;
}

/**
 * Ranked list of at-risk suppliers.
 * PERSON_C.md §5.3: "Per row: Rank, name, tier, risk_band chip,
 * reason_text (display in full), intervention_cost_cr and estimated_exposure_cr side by side"
 */
export default function RankedList({ scores, nodes, simulationState = 'idle', currentWave = 0 }: RankedListProps) {
  if (!scores || scores.length === 0) {
    return <div style={{ color: 'var(--text-secondary)' }}>No at-risk suppliers detected.</div>;
  }

  // Build node lookup for name resolution
  const nodeMap = new Map<string, any>();
  if (nodes) {
    nodes.forEach((n: any) => nodeMap.set(n.node_id, n));
  }

  // Filter out nulls and apply wave filter if cascading
  const sortedScores = [...scores]
    .filter((s: any) => {
      if (s.rank === null || s.rank === undefined) return false;
      if (simulationState === 'cascading') {
        const depth = s.propagation_depth ?? Infinity;
        if (depth > currentWave) return false;
      }
      return true;
    })
    .sort((a, b) => {
      if (a.rank === null) return 1;
      if (b.rank === null) return -1;
      return a.rank - b.rank;
    });

  const formatINR = (valueCr: number) => {
    if (valueCr >= 1) return `₹${valueCr.toFixed(1)} cr`;
    if (valueCr > 0) return `₹${(valueCr * 100).toFixed(0)} L`;
    return '₹0';
  };

  const bandClass = (band: string): string => {
    if (band === 'critical') return 'critical';
    if (band === 'high') return 'warning';
    if (band === 'watch') return 'moderate';
    return 'stable';
  };

  return (
    <div className="ranked-list">
      {sortedScores.map((score, i) => {
        const severity = bandClass(score.risk_band);
        const node = nodeMap.get(score.node_id);
        const companyName = node?.name || score.node_id;
        const tier = node?.tier;
        const dataSource = node?.data_source;

        return (
          <div key={score.node_id} className={`risk-card ${severity} animate-in`} style={{ animationDelay: `${i * 0.08}s` }}>
            <div className="risk-card-header">
              <div className="risk-card-rank">{score.rank || '-'}</div>
              <div className="risk-card-name-group">
                <div className="risk-card-name">{companyName}</div>
                <div className="risk-card-meta">
                  {tier !== undefined && <span className="risk-card-tier">Tier {tier}</span>}
                  <span className={`risk-band-chip ${score.risk_band}`}>{score.risk_band}</span>
                  {dataSource && (
                    <span className={`data-source-badge ${dataSource}`}>
                      {dataSource === 'real' ? '● Real' : '○ Synth'}
                    </span>
                  )}
                </div>
              </div>
            </div>
            {/* PERSON_C.md §5.3: "reason_text — display it in full. Do not truncate." */}
            <div className="risk-card-reason">
              {score.reason_text}
            </div>
            <div className="risk-card-scores">
              <div className="score-bar">
                <div className="score-bar-label">
                  <span>Fragility</span>
                  <span>{score.fragility.toFixed(2)}</span>
                </div>
                <div className="score-bar-track">
                  <div className={`score-bar-fill ${score.fragility > 0.6 ? 'red' : score.fragility > 0.3 ? 'amber' : 'blue'}`} style={{ width: `${score.fragility * 100}%` }}></div>
                </div>
              </div>
              <div className="score-bar">
                <div className="score-bar-label">
                  <span>Criticality</span>
                  <span>{score.criticality.toFixed(2)}</span>
                </div>
                <div className="score-bar-track">
                  <div className="score-bar-fill blue" style={{ width: `${score.criticality * 100}%` }}></div>
                </div>
              </div>
            </div>
            {score.intervention_cost_cr > 0 && (
              <div className="risk-card-metrics">
                <div className="risk-metric">
                  <div className="risk-metric-label">Intervention Cost</div>
                  <div className="risk-metric-value success">{formatINR(score.intervention_cost_cr)}</div>
                </div>
                <div className="risk-metric">
                  <div className="risk-metric-label">Exposure at Risk</div>
                  <div className="risk-metric-value danger">{formatINR(score.estimated_exposure_cr)}</div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
