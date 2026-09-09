/**
 * The reading panel: what is at risk, why, what it costs, and what changed.
 *
 * Two rules it follows throughout:
 *   1. A band is never shown as colour alone — every chip prints its name.
 *   2. Figures are printed at the precision the engine returned them.
 */

import { BAND_COLOR, BAND_WASH, bandStyle } from '../lib/bands';
import { cr, num, pct, score as fmtScore } from '../lib/format';
import type { Delta, Meta, Node, RiskBand, Score, Summary } from '../types';

function Chip({ band }: { band: RiskBand | undefined }) {
  if (!band) return null;
  return (
    <span className="ff-chip" style={bandStyle(band)}>
      {band}
    </span>
  );
}

// ---------------------------------------------------------------------------

export function NetworkStats({ meta, nodes }: { meta: Meta; nodes: Node[] }) {
  const tiers = new Map<number, number>();
  for (const node of nodes) tiers.set(node.tier, (tiers.get(node.tier) ?? 0) + 1);
  const observable = nodes.filter((node) => node.is_observable).length;

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <span className="ff-label">The network</span>
        <span className="ff-label">schema {meta.schema_version}</span>
      </div>
      <div className="ff-stats">
        <div className="ff-stat">
          <span className="ff-stat-value">{num(meta.node_count)}</span>
          <span className="ff-stat-unit">companies</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{num(meta.edge_count)}</span>
          <span className="ff-stat-unit">supply relationships</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{[...tiers.keys()].length}</span>
          <span className="ff-stat-unit">tiers, anchor to tier 3</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{num(observable)}</span>
          <span className="ff-stat-unit">publish anything at all</span>
        </div>
      </div>
      <p style={{ fontSize: 11.5, color: 'var(--ff-ink-dim)', marginTop: 12, lineHeight: 1.55 }}>
        {num(meta.node_count - observable)} of these companies file nothing an anchor can read.
        Tier-1 suppliers publish; the firms two and three tiers down are under no obligation to,
        and they are where the cash runs out.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function RiskStats({ summary }: { summary: Summary }) {
  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <span className="ff-label">Exposure</span>
        <span className="ff-label">converged in {summary.iterations_to_converge}</span>
      </div>
      <div className="ff-stats">
        <div className="ff-stat">
          <span className="ff-stat-value">{num(summary.at_risk_count)}</span>
          <span className="ff-stat-unit">suppliers at risk</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{summary.max_propagation_depth}</span>
          <span className="ff-stat-unit">hops of propagation</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{cr(summary.total_estimated_exposure_cr, 0)}</span>
          <span className="ff-stat-unit">exposure if nobody moves</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{cr(summary.total_intervention_cost_cr, 0)}</span>
          <span className="ff-stat-unit">cost to stabilise all of them</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function RankList({
  ranking,
  scores,
  nodeById,
  selectedId,
  onSelect,
  limit = 6,
}: {
  ranking: string[];
  scores: Map<string, Score>;
  nodeById: Map<string, Node>;
  selectedId: string | null;
  onSelect: (nodeId: string) => void;
  limit?: number;
}) {
  const rows = ranking.slice(0, limit);

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <span className="ff-label">Ranked · fragile × irreplaceable</span>
        <span className="ff-label">{ranking.length} at risk</span>
      </div>

      {rows.length === 0 ? (
        <p className="ff-empty">Nothing is at risk at this stress level.</p>
      ) : (
        <div className="ff-rank-list">
          {rows.map((nodeId, index) => {
            const row = scores.get(nodeId);
            const node = nodeById.get(nodeId);
            if (!row || !node) return null;
            return (
              <button
                key={nodeId}
                className="ff-rank"
                style={bandStyle(row.risk_band)}
                aria-pressed={selectedId === nodeId}
                onClick={() => onSelect(nodeId)}
              >
                <span className="ff-rank-no">#{row.rank ?? index + 1}</span>
                <span className="ff-rank-main">
                  <span className="ff-rank-name">{node.name}</span>
                  <span className="ff-rank-meta">
                    {nodeId} · tier {node.tier} · depth {row.propagation_depth}
                  </span>
                  <Chip band={row.risk_band} />
                  {row.reason_text && <span className="ff-rank-why">{row.reason_text}</span>}
                </span>
                <span className="ff-rank-figs">
                  <span className="ff-rank-cost">{cr(row.intervention_cost_cr)}</span>
                  <span className="ff-rank-exposure">{cr(row.estimated_exposure_cr, 0)} at risk</span>
                </span>
              </button>
            );
          })}
        </div>
      )}
      <p style={{ fontSize: 11, color: 'var(--ff-ink-faint)', marginTop: 10, lineHeight: 1.5 }}>
        Ranked on <code>fragility × criticality</code>. A robust chokepoint is fine and a fragile
        commodity supplier is replaceable — only the product of the two is a problem. Stressed
        origins are excluded: the tier-1 that started this is not the one to rescue.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function Dossier({
  node,
  score,
  onEvidence,
  hasFilings,
}: {
  node: Node;
  score: Score | undefined;
  onEvidence: () => void;
  hasFilings: boolean;
}) {
  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <span className="ff-label">Selected</span>
        <button className="ff-ghost" onClick={onEvidence}>
          {hasFilings ? 'See the filing' : 'Why no filing'}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 13 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ff-ink-hi)' }}>{node.name}</span>
        <span className="ff-rank-meta">
          {node.node_id} · tier {node.tier} · {node.sector.replace(/_/g, ' ')} ·{' '}
          {node.is_observable ? 'observable' : 'not observable'}
        </span>
      </div>

      <div className="ff-stats" style={{ marginBottom: 14 }}>
        <div className="ff-stat">
          <span className="ff-stat-value">{fmtScore(score?.fragility)}</span>
          <span className="ff-stat-unit">fragility</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{fmtScore(score?.criticality)}</span>
          <span className="ff-stat-unit">criticality (within tier)</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">
            {node.cash_buffer_days === null ? '—' : num(node.cash_buffer_days)}
          </span>
          <span className="ff-stat-unit">days of cash buffer</span>
        </div>
        <div className="ff-stat">
          <span className="ff-stat-value">{cr(node.revenue_cr, 2)}</span>
          <span className="ff-stat-unit">revenue</span>
        </div>
      </div>

      {score && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <Chip band={score.risk_band} />
            <span className="ff-rank-meta">
              own {fmtScore(score.own_stress)} + inherited {fmtScore(score.inherited_stress)}
            </span>
          </div>

          {score.reason_factors && score.reason_factors.length > 0 && (
            <>
              <span className="ff-label">What drives it</span>
              <div className="ff-factors">
                {score.reason_factors.map((factor) => (
                  <div className="ff-factor" key={`${factor.kind}-${factor.detail}`}>
                    <span className="ff-factor-label">{factor.detail}</span>
                    <span className="ff-factor-weight">{pct(factor.weight)}</span>
                    <span className="ff-factor-track">
                      <span
                        className="ff-factor-fill"
                        style={{
                          transform: `scaleX(${factor.weight})`,
                          background: BAND_COLOR[score.risk_band],
                        }}
                      />
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          {score.disruption_reason && (
            <p style={{ fontSize: 11.5, color: 'var(--ff-ink-dim)', lineHeight: 1.5 }}>
              <span className="ff-label" style={{ display: 'block', marginBottom: 3 }}>
                If it stops delivering
              </span>
              {score.disruption_reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

export function Outcome({
  delta,
  fundedName,
  fundedAmount,
  anchorBefore,
  anchorAfter,
  anchorName,
  nodeById,
  counterfactual,
  onToggleCounterfactual,
}: {
  delta: Delta;
  fundedName: string;
  fundedAmount: number;
  anchorBefore: { disrupted_inflow_cr: number; disruption_band: RiskBand } | null;
  anchorAfter: { disrupted_inflow_cr: number; disruption_band: RiskBand } | null;
  anchorName: string | null;
  nodeById: Map<string, Node>;
  counterfactual: boolean;
  onToggleCounterfactual: () => void;
}) {
  const moved = delta.per_node.filter((row) => row.band_before !== row.band_after);

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <span className="ff-label">{counterfactual ? 'Nobody moved' : 'After funding'}</span>
        <button className="ff-ghost" onClick={onToggleCounterfactual}>
          {counterfactual ? 'Fund it again' : 'Turn it off'}
        </button>
      </div>

      <div className="ff-outcome">
        <div className="ff-receipt">
          <span className="ff-receipt-figure">{cr(fundedAmount)}</span>
          <span className="ff-receipt-caption">
            into {fundedName} removes {cr(delta.total_exposure_reduced_cr, 0)} of exposure and moves{' '}
            {num(delta.nodes_improved)} companies to a better band. {num(delta.nodes_worsened)} got
            worse.
          </span>
        </div>

        {anchorBefore && anchorAfter && (
          <>
            <span className="ff-label">
              {anchorName ?? 'Anchor'} — inbound supply at risk
            </span>
            <div className="ff-ba">
              <div className="ff-ba-side" data-side="before">
                <span className="ff-label">before</span>
                <span className="ff-ba-value" style={{ color: BAND_COLOR[anchorBefore.disruption_band] }}>
                  {cr(anchorBefore.disrupted_inflow_cr, 0)}
                </span>
                <Chip band={anchorBefore.disruption_band} />
              </div>
              <div className="ff-ba-arrow" aria-hidden="true">
                →
              </div>
              <div className="ff-ba-side" data-side="after">
                <span className="ff-label">after</span>
                <span className="ff-ba-value" style={{ color: BAND_COLOR[anchorAfter.disruption_band] }}>
                  {cr(anchorAfter.disrupted_inflow_cr, 0)}
                </span>
                <Chip band={anchorAfter.disruption_band} />
              </div>
            </div>
            <p style={{ fontSize: 11, color: 'var(--ff-ink-faint)', lineHeight: 1.5 }}>
              The anchor paid on time, had the cash, and did nothing wrong. This is what reaches it
              anyway when a supplier three tiers down runs out of money.
            </p>
          </>
        )}

        {moved.length > 0 && (
          <>
            <span className="ff-label">Bands that moved</span>
            <div className="ff-transitions">
              {moved.map((row) => (
                <div className="ff-transition" key={row.node_id}>
                  <span className="ff-transition-name">
                    {nodeById.get(row.node_id)?.name ?? row.node_id}
                  </span>
                  <span
                    className="ff-chip"
                    style={{
                      ['--band' as string]: BAND_COLOR[row.band_before],
                      ['--band-wash' as string]: BAND_WASH[row.band_before],
                    }}
                  >
                    {row.band_before}
                  </span>
                  <span className="ff-transition-arrow" aria-hidden="true">
                    →
                  </span>
                  <span
                    className="ff-chip"
                    style={{
                      ['--band' as string]: BAND_COLOR[row.band_after],
                      ['--band-wash' as string]: BAND_WASH[row.band_after],
                    }}
                  >
                    {row.band_after}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
