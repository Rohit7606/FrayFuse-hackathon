interface AnchorDisruption {
  node_id: string;
  supply_disruption: number;
  disruption_band: string;
  disrupted_inflow_cr: number;
  stopped_by?: string | null;
}

interface InterventionCardProps {
  delta: any;
  nodes?: any[];
  /** summary.anchor_disruption[0] before and after funding — DEMO_SCENARIO.md §6. */
  anchorBefore?: AnchorDisruption;
  anchorAfter?: AnchorDisruption;
  onCounterfactual: () => void;
}

export default function InterventionCard({
  delta,
  nodes,
  anchorBefore,
  anchorAfter,
  onCounterfactual,
}: InterventionCardProps) {
  if (!delta || !delta.per_node || delta.per_node.length === 0) return null;

  const nodeMap = new Map<string, any>();
  if (nodes) nodes.forEach((n: any) => nodeMap.set(n.node_id, n));

  const formatINR = (valueCr: number) => {
    if (valueCr >= 1) return `₹${valueCr.toFixed(1)} cr`;
    return `₹${(valueCr * 100).toFixed(0)} L`;
  };

  const bandColor: Record<string, string> = {
    critical: 'var(--accent-red)',
    high: 'var(--accent-amber)',
    watch: 'var(--accent-blue)',
    stable: 'var(--accent-green)',
  };

  return (
    <div className="panel-section">
      <div className="panel-section-title">Intervention Results</div>
      <div className="intervention-card">
        {/* Summary stats */}
        <div className="intervention-summary-row">
          <div className="intervention-stat">
            <div className="intervention-stat-value green">{delta.nodes_improved}</div>
            <div className="intervention-stat-label">Suppliers improved</div>
          </div>
          <div className="intervention-stat">
            <div className="intervention-stat-value">{delta.nodes_worsened}</div>
            <div className="intervention-stat-label">Worsened</div>
          </div>
        </div>

        <div className="intervention-comparison">
          <div className="comparison-box cost">
            <div className="comparison-label">Capital Deployed</div>
            <div className="comparison-value green">{formatINR(delta.total_intervention_cost_cr)}</div>
          </div>
          <div className="comparison-vs">→</div>
          <div className="comparison-box exposure">
            <div className="comparison-label">Exposure Reduced</div>
            <div className="comparison-value blue">{formatINR(delta.total_exposure_reduced_cr)}</div>
          </div>
        </div>

        {/* Per-node band transitions */}
        <div className="intervention-transitions">
          {delta.per_node.map((pn: any) => {
            const nodeName = nodeMap.get(pn.node_id)?.name || pn.node_id;
            return (
              <div key={pn.node_id} className="transition-row">
                <div className="transition-name">{nodeName.length > 25 ? nodeName.substring(0, 23) + '…' : nodeName}</div>
                <div className="transition-bands">
                  <span className="transition-band" style={{ color: bandColor[pn.band_before] || '#9aa0b0' }}>
                    {pn.band_before}
                  </span>
                  <span className="transition-arrow">→</span>
                  <span className="transition-band" style={{ color: bandColor[pn.band_after] || '#9aa0b0' }}>
                    {pn.band_after}
                  </span>
                </div>
                <div className="transition-fragility">
                  {pn.fragility_before.toFixed(2)} → {pn.fragility_after.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>

        {anchorBefore && anchorAfter && (
          /* The closing beat. Payment stress alone can never reach the anchor —
             it is the top buyer, so nothing propagates into it. This is the
             supply-disruption layer: what stops arriving when a supplier fails,
             and how much of that the funding takes off the table. */
          <div className="anchor-beat">
            <div className="comparison-label">
              Anchor supply at risk &mdash; {nodeMap.get(anchorBefore.node_id)?.name || anchorBefore.node_id}
              {anchorBefore.stopped_by ? ` via ${nodeMap.get(anchorBefore.stopped_by)?.name || anchorBefore.stopped_by}` : ''}
            </div>
            <div className="anchor-beat-values">
              <span className="comparison-value red">{formatINR(anchorBefore.disrupted_inflow_cr)}</span>
              <span className="anchor-beat-arrow">&rarr;</span>
              <span className="comparison-value green">{formatINR(anchorAfter.disrupted_inflow_cr)}</span>
            </div>
            <div className="intervention-desc">
              Line-stop risk {anchorBefore.disruption_band} ({anchorBefore.supply_disruption.toFixed(4)})
              &rarr; {anchorAfter.disruption_band} ({anchorAfter.supply_disruption.toFixed(4)})
            </div>
          </div>
        )}
        <div className="intervention-actions">
          <button className="btn" onClick={onCounterfactual}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
            Counterfactual Toggle
          </button>
        </div>
      </div>
    </div>
  );
}
