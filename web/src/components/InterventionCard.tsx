interface InterventionCardProps {
  delta: any;
  onCounterfactual: () => void;
}

export default function InterventionCard({ delta, onCounterfactual }: InterventionCardProps) {
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
            <div className="intervention-title">Early Payment to {targetNode}</div>
            <div className="intervention-desc">Release payment through Tier-1 channel</div>
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
