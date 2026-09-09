interface AnchorDisruption {
  node_id: string;
  supply_disruption: number;
  disruption_band: string;
  disrupted_inflow_cr: number;
  stopped_by?: string | null;
}

interface InterventionCardProps {
  delta: any;
  /** summary.anchor_disruption[0] before and after funding — DEMO_SCENARIO.md §6. */
  anchorBefore?: AnchorDisruption;
  anchorAfter?: AnchorDisruption;
  onCounterfactual: () => void;
}

export default function InterventionCard({
  delta,
  anchorBefore,
  anchorAfter,
  onCounterfactual,
}: InterventionCardProps) {
  if (!delta || !delta.per_node || delta.per_node.length === 0) return null;
  
  const targetNode = delta.per_node[0].node_id;

  const formatINR = (valueCr: number) => {
    if (valueCr >= 1) return `₹${valueCr.toFixed(1)}Cr`;
    return `₹${(valueCr * 100).toFixed(0)}L`;
  };

  return (
    <div className="panel-section">
      <div className="panel-section-title">Intervention</div>
      <div className="intervention-card">
        <div className="intervention-header">
          <div className="intervention-icon pay">₹</div>
          <div>
            <div className="intervention-title">Intervene: {targetNode}</div>
            <div className="intervention-desc">Stabilise supplier with early payment (₹{delta.total_intervention_cost_cr.toFixed(1)} Cr)</div>
          </div>
        </div>
        <div className="intervention-comparison">
          <div className="comparison-box cost">
            <div className="comparison-label">Intervention Cost</div>
            <div className="comparison-value green">{formatINR(delta.total_intervention_cost_cr)}</div>
          </div>
          <div className="comparison-vs">vs</div>
          <div className="comparison-box exposure">
            <div className="comparison-label">Exposure if No Action</div>
            <div className="comparison-value red">{formatINR(delta.total_exposure_reduced_cr)}</div>
          </div>
        </div>
        {anchorBefore && anchorAfter && (
          /* The closing beat. Payment stress alone can never reach the anchor —
             it is the top buyer, so nothing propagates into it. This is the
             supply-disruption layer: what stops arriving when a supplier fails,
             and how much of that the funding takes off the table. */
          <div className="anchor-beat">
            <div className="comparison-label">
              Anchor supply at risk &mdash; {anchorBefore.node_id}
              {anchorBefore.stopped_by ? ` via ${anchorBefore.stopped_by}` : ''}
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
