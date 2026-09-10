import { useState } from 'react';

interface RankedListProps {
  scores: any[] | undefined;
  nodes?: any[] | undefined;
  simulationState?: 'idle' | 'cascading' | 'cascaded' | 'intervened';
  currentWave?: number;
  onFundNode?: (nodeId: string, amountCr: number) => void;
}

/**
 * Classify a scored node into an action queue.
 *
 * "Fund Now" — irreplaceable chokepoint under stress (criticality >= 0.60).
 * "De-risk"  — fragile but replaceable (fragility >= 0.50, criticality < 0.60).
 * "Monitor"  — everything else that made the ranked list.
 */
function actionQueue(score: any): 'fund' | 'derisk' | 'monitor' {
  if (score.criticality >= 0.60) return 'fund';
  if (score.fragility >= 0.50) return 'derisk';
  return 'monitor';
}

/**
 * Ranked list of at-risk suppliers with action buttons.
 * PERSON_C.md §5.3: "Per row: Rank, name, tier, risk_band chip,
 * reason_text (display in full), intervention_cost_cr and estimated_exposure_cr side by side"
 */
export default function RankedList({ scores, nodes, simulationState = 'idle', currentWave = 0, onFundNode }: RankedListProps) {
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

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

  const toggleExpand = (nodeId: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  // Extract buyer dependency from reason_factors
  const getBuyerDependency = (score: any): string | null => {
    if (!score.reason_factors) return null;
    const exposure = score.reason_factors.find((f: any) => f.kind === 'exposure');
    return exposure ? exposure.detail : null;
  };

  return (
    <div className="ranked-list">
      {sortedScores.map((score, i) => {
        const severity = bandClass(score.risk_band);
        const node = nodeMap.get(score.node_id);
        const companyName = node?.name || score.node_id;
        const tier = node?.tier;
        const dataSource = node?.data_source;
        const queue = actionQueue(score);
        const isExpanded = expandedCards.has(score.node_id);
        const buyerDep = getBuyerDependency(score);

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
                  <span className={`action-queue-badge ${queue}`}>
                    {queue === 'fund' ? '🚨 Fund Now' : queue === 'derisk' ? '⚠ De-risk' : '👁 Monitor'}
                  </span>
                </div>
              </div>
            </div>

            {/* Status badges */}
            <div className="risk-card-status">
              {score.fragility >= 0.50 && (
                <span className="status-badge fragile">⚠ Financially fragile</span>
              )}
              {score.criticality >= 0.60 ? (
                <span className="status-badge irreplaceable">🚨 Irreplaceable chokepoint</span>
              ) : (
                <span className="status-badge replaceable">✓ Relatively replaceable</span>
              )}
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
                  <div className="risk-metric-label">Stabilisation Cost</div>
                  <div className="risk-metric-value success">{formatINR(score.intervention_cost_cr)}</div>
                </div>
                <div className="risk-metric">
                  <div className="risk-metric-label">Exposure at Risk</div>
                  <div className="risk-metric-value danger">{formatINR(score.estimated_exposure_cr)}</div>
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="risk-card-actions">
              {queue === 'fund' && simulationState === 'cascaded' && onFundNode && (
                <button
                  className="btn btn-fund"
                  onClick={() => onFundNode(score.node_id, score.intervention_cost_cr)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                  Fund Supplier {formatINR(score.intervention_cost_cr)}
                </button>
              )}
              {queue === 'derisk' && (
                <button
                  className="btn btn-derisk"
                  onClick={() => toggleExpand(score.node_id)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  {isExpanded ? 'Hide Plan' : 'Create De-risking Plan'}
                </button>
              )}
              {queue === 'monitor' && (
                <button
                  className="btn btn-monitor"
                  onClick={() => toggleExpand(score.node_id)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  {isExpanded ? 'Hide Details' : 'Enhanced Monitoring'}
                </button>
              )}
            </div>

            {/* Expandable De-risking Plan */}
            {isExpanded && (queue === 'derisk' || queue === 'monitor') && (
              <div className="derisk-plan">
                <div className="derisk-plan-title">
                  {queue === 'derisk' ? 'De-risking Plan' : 'Monitoring Plan'}
                </div>
                <div className="derisk-plan-grid">
                  <div className="derisk-item">
                    <div className="derisk-item-icon">📊</div>
                    <div>
                      <div className="derisk-item-label">Monitoring Status</div>
                      <div className="derisk-item-value flagged">Flagged for enhanced monitoring</div>
                    </div>
                  </div>
                  <div className="derisk-item">
                    <div className="derisk-item-icon">🔔</div>
                    <div>
                      <div className="derisk-item-label">Review Trigger</div>
                      <div className="derisk-item-value">Alert if fragility crosses 0.90</div>
                    </div>
                  </div>
                  {buyerDep && (
                    <div className="derisk-item">
                      <div className="derisk-item-icon">🔗</div>
                      <div>
                        <div className="derisk-item-label">Buyer Dependency</div>
                        <div className="derisk-item-value">{buyerDep}</div>
                      </div>
                    </div>
                  )}
                  <div className="derisk-item">
                    <div className="derisk-item-icon">💰</div>
                    <div>
                      <div className="derisk-item-label">Potential Exposure</div>
                      <div className="derisk-item-value danger">{formatINR(score.estimated_exposure_cr)}</div>
                    </div>
                  </div>
                  <div className="derisk-item">
                    <div className="derisk-item-icon">🛡️</div>
                    <div>
                      <div className="derisk-item-label">Stabilisation Cost</div>
                      <div className="derisk-item-value success">{formatINR(score.intervention_cost_cr)}</div>
                    </div>
                  </div>
                  <div className="derisk-item">
                    <div className="derisk-item-icon">📋</div>
                    <div>
                      <div className="derisk-item-label">Queue Assignment</div>
                      <div className={`derisk-item-value ${queue === 'derisk' ? 'amber' : 'blue'}`}>
                        {queue === 'derisk' ? 'Watch / De-risk Queue' : 'Enhanced Monitoring Queue'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
