interface RankedListProps {
  scores: any[];
}

export default function RankedList({ scores }: RankedListProps) {
  if (!scores || scores.length === 0) {
    return <div style={{ color: 'var(--text-secondary)' }}>No at-risk suppliers detected.</div>;
  }

  // Ensure we sort by rank (nulls at the bottom if any)
  const sortedScores = [...scores].sort((a, b) => {
    if (a.rank === null) return 1;
    if (b.rank === null) return -1;
    return a.rank - b.rank;
  });

  const formatINR = (valueCr: number) => {
    if (valueCr >= 1) return `₹${valueCr.toFixed(1)}Cr`;
    if (valueCr > 0) return `₹${(valueCr * 100).toFixed(0)}L`;
    return '₹0';
  };

  return (
    <div className="ranked-list">
      {sortedScores.map((score, i) => {
        const severity = score.final_score > 0.6 ? 'critical' : score.final_score > 0.4 ? 'warning' : 'moderate';
        return (
          <div key={score.node_id} className={`risk-card ${severity} animate-in`} style={{ animationDelay: `${i * 0.08}s` }}>
            <div className="risk-card-header">
              <div className="risk-card-rank">{score.rank || '-'}</div>
              <div className="risk-card-name">{score.node_id}</div>
              <div className="risk-card-tier">{score.risk_band}</div>
            </div>
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
                  <div className={`score-bar-fill ${score.fragility > 0.6 ? 'red' : 'amber'}`} style={{ width: `${score.fragility * 100}%` }}></div>
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
                  <div className="risk-metric-label">Exposure</div>
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
