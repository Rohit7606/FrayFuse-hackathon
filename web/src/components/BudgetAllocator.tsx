import { useState, useMemo } from 'react';

interface BudgetAllocatorProps {
  scores: any[] | undefined;
  nodes?: any[] | undefined;
  onDeployBudget: (allocations: Array<{ node_id: string; amount_cr: number }>) => void;
}

interface Allocation {
  node_id: string;
  name: string;
  intervention_cost_cr: number;
  estimated_exposure_cr: number;
  ratio: number;
  allocated_cr: number;
  coverage: number; // 0-1, fraction of stabilisation cost covered
}

/**
 * Budget Allocation Optimizer.
 *
 * Greedy allocation: sort at-risk nodes by bang-for-buck ratio
 * (exposure / cost), fill until budget is exhausted.
 */
export default function BudgetAllocator({ scores, nodes, onDeployBudget }: BudgetAllocatorProps) {
  const [budgetCr, setBudgetCr] = useState(5.0);

  const nodeMap = useMemo(() => {
    if (!nodes) return new Map();
    const map = new Map<string, any>();
    nodes.forEach((n: any) => map.set(n.node_id, n));
    return map;
  }, [nodes]);

  const allocations = useMemo((): Allocation[] => {
    if (!scores) return [];

    // Only consider at-risk nodes with a positive cost
    const candidates = scores
      .filter((s: any) => s.rank !== null && s.rank !== undefined && s.intervention_cost_cr > 0)
      .map((s: any) => ({
        node_id: s.node_id,
        name: nodeMap.get(s.node_id)?.name || s.node_id,
        intervention_cost_cr: s.intervention_cost_cr,
        estimated_exposure_cr: s.estimated_exposure_cr,
        ratio: s.estimated_exposure_cr / Math.max(s.intervention_cost_cr, 0.01),
        allocated_cr: 0,
        coverage: 0,
      }))
      .sort((a, b) => b.ratio - a.ratio); // Highest bang-for-buck first

    let remaining = budgetCr;
    for (const alloc of candidates) {
      if (remaining <= 0) break;
      const needed = alloc.intervention_cost_cr;
      const given = Math.min(needed, remaining);
      alloc.allocated_cr = Math.round(given * 100) / 100;
      alloc.coverage = given / needed;
      remaining -= given;
    }

    return candidates;
  }, [scores, nodeMap, budgetCr]);

  const funded = allocations.filter(a => a.allocated_cr > 0);
  const totalAllocated = funded.reduce((sum, a) => sum + a.allocated_cr, 0);
  const totalExposureCovered = funded.reduce((sum, a) => sum + a.estimated_exposure_cr * a.coverage, 0);

  const formatINR = (v: number) => {
    if (v >= 1) return `₹${v.toFixed(1)} cr`;
    if (v > 0) return `₹${(v * 100).toFixed(0)} L`;
    return '₹0';
  };

  const handleDeploy = () => {
    const payload = funded.map(a => ({ node_id: a.node_id, amount_cr: a.allocated_cr }));
    onDeployBudget(payload);
  };

  return (
    <div className="budget-allocator">
      <div className="budget-header">
        <div className="budget-title">Budget Allocation Optimizer</div>
        <div className="budget-subtitle">
          Auto-distribute rescue capital for maximum impact
        </div>
      </div>

      <div className="budget-slider-group">
        <div className="budget-slider-label">
          <span>Rescue Budget</span>
          <span className="budget-value">{formatINR(budgetCr)}</span>
        </div>
        <input
          type="range"
          className="budget-slider"
          min={0.5}
          max={50}
          step={0.5}
          value={budgetCr}
          onChange={e => setBudgetCr(parseFloat(e.target.value))}
        />
        <div className="budget-slider-range">
          <span>₹0.5 cr</span>
          <span>₹50 cr</span>
        </div>
      </div>

      <div className="budget-summary">
        <div className="budget-summary-item">
          <div className="budget-summary-label">Deployed</div>
          <div className="budget-summary-value green">{formatINR(totalAllocated)}</div>
        </div>
        <div className="budget-summary-item">
          <div className="budget-summary-label">Exposure Covered</div>
          <div className="budget-summary-value blue">{formatINR(totalExposureCovered)}</div>
        </div>
        <div className="budget-summary-item">
          <div className="budget-summary-label">Suppliers Funded</div>
          <div className="budget-summary-value">{funded.length}</div>
        </div>
      </div>

      <div className="budget-table">
        {allocations.slice(0, 8).map(alloc => (
          <div key={alloc.node_id} className={`budget-row ${alloc.allocated_cr > 0 ? 'funded' : 'unfunded'}`}>
            <div className="budget-row-info">
              <div className="budget-row-name">{alloc.name.length > 22 ? alloc.name.substring(0, 20) + '…' : alloc.name}</div>
              <div className="budget-row-ratio">
                {alloc.ratio.toFixed(1)}x return
              </div>
            </div>
            <div className="budget-row-bar">
              <div className="budget-row-bar-track">
                <div
                  className={`budget-row-bar-fill ${alloc.coverage >= 1 ? 'full' : alloc.coverage > 0 ? 'partial' : 'none'}`}
                  style={{ width: `${alloc.coverage * 100}%` }}
                />
              </div>
            </div>
            <div className="budget-row-amount">
              {alloc.allocated_cr > 0 ? formatINR(alloc.allocated_cr) : '—'}
            </div>
          </div>
        ))}
      </div>

      <button
        className="btn btn-deploy"
        onClick={handleDeploy}
        disabled={funded.length === 0}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        Deploy {formatINR(totalAllocated)} across {funded.length} supplier{funded.length !== 1 ? 's' : ''}
      </button>
    </div>
  );
}
