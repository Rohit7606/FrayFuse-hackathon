/**
 * The reading panel: what is at risk, why, what it costs, and what changed.
 *
 * Three rules it follows throughout:
 *   1. A band is never shown as colour alone — every chip prints its name.
 *   2. Figures keep the precision the engine returned them at.
 *   3. Sections get real headings, not a tracked mono eyebrow apiece. Mono is
 *      reserved for the things that genuinely are machine output: node ids,
 *      rupee figures, scores.
 */

import { BAND_COLOR, BAND_WASH, bandStyle } from '../lib/bands';
import { cr, num, pct, score as fmtScore, shortName } from '../lib/format';
import type { Delta, Meta, Node, RiskBand, Score, SubstitutionCandidate, Summary } from '../types';

function Chip({ band }: { band: RiskBand | undefined }) {
  if (!band) return null;
  return (
    <span className="ff-chip" style={bandStyle(band)}>
      {band}
    </span>
  );
}

function Figure({
  label,
  value,
  lead,
}: {
  label: string;
  value: string;
  lead?: boolean;
}) {
  return (
    <div className="ff-figure">
      <span className="ff-figure-label">{label}</span>
      <span className="ff-figure-value" data-lead={lead ? 'true' : undefined}>
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function NetworkStats({ meta, nodes }: { meta: Meta; nodes: Node[] }) {
  const observable = nodes.filter((node) => node.is_observable).length;
  const tiers = new Set(nodes.map((node) => node.tier)).size;

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">The network</h2>
        <span className="ff-h-note">schema {meta.schema_version}</span>
      </div>

      <div className="ff-figures">
        <Figure label="Companies" value={num(meta.node_count)} lead />
        <Figure label="Supply relationships" value={num(meta.edge_count)} />
        <Figure label="Tiers, anchor to deepest" value={num(tiers)} />
        <Figure label="Companies that publish anything" value={num(observable)} />
      </div>

      <p className="ff-note" style={{ marginTop: 14 }}>
        {num(meta.node_count - observable)} of these file nothing an anchor can read. Tier-1
        suppliers publish; the firms two and three tiers down are under no obligation to, and they
        are where the cash runs out.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function RiskStats({ summary }: { summary: Summary }) {
  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">Exposure</h2>
        <span className="ff-h-note">converged in {summary.iterations_to_converge}</span>
      </div>

      <div className="ff-figures">
        <Figure label="Suppliers at risk" value={num(summary.at_risk_count)} lead />
        <Figure label="Exposure if nobody moves" value={cr(summary.total_estimated_exposure_cr, 0)} />
        <Figure label="Cost to stabilise all of them" value={cr(summary.total_intervention_cost_cr, 0)} />
        <Figure label="Deepest hop reached" value={num(summary.max_propagation_depth)} />
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
        <h2 className="ff-h">Ranked by fragile × irreplaceable</h2>
        <span className="ff-h-note">{ranking.length} at risk</span>
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
                aria-pressed={selectedId === nodeId}
                onClick={() => onSelect(nodeId)}
              >
                <span className="ff-rank-no">{row.rank ?? index + 1}</span>
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

      <p className="ff-note-sm" style={{ marginTop: 12 }}>
        A robust chokepoint is fine and a fragile commodity supplier is replaceable — only the
        product of the two is a problem. Stressed origins are excluded: the tier-1 that started
        this is not the one to rescue.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------

/**
 * The other end of the criticality distribution.
 *
 * Three states, and they are three different facts (SCHEMA.md §4.6). The
 * component renders all three rather than treating two of them as "nothing to
 * show", because "we looked and found nobody" is a finding — on the real
 * network it is the answer for every eligible node.
 */
function Alternatives({
  candidates,
  node,
}: {
  candidates: SubstitutionCandidate[] | null | undefined;
  node: Node;
}) {
  // Not considered. The dossier stays silent rather than explaining an absence
  // the reader did not ask about — for a critical supplier the whole panel is
  // already saying it cannot be replaced.
  if (candidates === null || candidates === undefined) return null;

  return (
    <section className="ff-alt">
      <div className="ff-alt-head">
        <h3 className="ff-alt-title">
          {candidates.length > 0 ? 'Replaceable — alternatives exist' : 'Replaceable, but no alternative found'}
        </h3>
        <span className="ff-alt-fit">{candidates.length > 0 ? `${candidates.length} found` : '0 found'}</span>
      </div>

      {candidates.length === 0 ? (
        <p className="ff-alt-note">
          This supplier is not a chokepoint, so switching away from it is possible in principle —
          but no other tier-{node.tier} supplier in this network makes the same part. Funding it is
          not the only option; finding a second source is simply not something this dataset can
          point at.
        </p>
      ) : (
        <>
          <p className="ff-alt-note">
            Low criticality and no sole-source claim, so the volume could move. Ranked on the
            candidate's own health and the revenue it has not already committed.
          </p>
          <div className="ff-alt-list">
            {candidates.map((candidate) => (
              <div className="ff-alt-row" key={`${candidate.node_id}-${candidate.replaces_edge_id}`}>
                <div className="ff-alt-line">
                  <span className="ff-alt-name">{candidate.name}</span>
                  <span className="ff-alt-fit">fit {candidate.fitness.toFixed(2)}</span>
                </div>
                <div className="ff-alt-meta">
                  {candidate.node_id} · {candidate.component.replace(/_/g, ' ')} ·{' '}
                  {candidate.capacity_headroom_cr === null
                    ? 'headroom undisclosed'
                    : `${cr(candidate.capacity_headroom_cr)} spare`}
                </div>
                <p className="ff-alt-why">{candidate.reason_text}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
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
    <div className="ff-block" id="ff-dossier">
      <div className="ff-block-head">
        <h2 className="ff-h">{node.name}</h2>
        <button className="ff-ghost" onClick={onEvidence}>
          {hasFilings ? 'See the filing' : 'Why no filing'}
        </button>
      </div>

      <p className="ff-rank-meta" style={{ marginTop: -8, marginBottom: 13 }}>
        {node.node_id} · tier {node.tier} · {node.sector.replace(/_/g, ' ')} ·{' '}
        {node.is_observable ? 'observable' : 'not observable'}
      </p>

      <div className="ff-figures">
        <Figure label="Fragility" value={fmtScore(score?.fragility)} />
        <Figure label="Criticality, within tier" value={fmtScore(score?.criticality)} />
        <Figure
          label="Cash buffer"
          value={node.cash_buffer_days === null ? '—' : `${num(node.cash_buffer_days)} days`}
        />
        <Figure label="Revenue" value={cr(node.revenue_cr)} />
      </div>

      {score && (
        <>
          <div
            style={{
              display: 'flex',
              gap: 10,
              alignItems: 'center',
              flexWrap: 'wrap',
              margin: '14px 0 4px',
            }}
          >
            <Chip band={score.risk_band} />
            <span className="ff-rank-meta">
              own {fmtScore(score.own_stress)} + inherited {fmtScore(score.inherited_stress)}
            </span>
          </div>

          {score.reason_factors && score.reason_factors.length > 0 && (
            <>
              <h3 className="ff-h" style={{ fontSize: 12.5, margin: '14px 0 2px' }}>
                What drives it
              </h3>
              <div className="ff-factors">
                {score.reason_factors.map((factor) => (
                  <div className="ff-factor" key={`${factor.kind}-${factor.detail}`}>
                    <div className="ff-factor-row">
                      <span className="ff-factor-label">{factor.detail}</span>
                      <span className="ff-factor-weight">{pct(factor.weight)}</span>
                    </div>
                    <div className="ff-factor-track">
                      <div
                        className="ff-factor-fill"
                        style={{ transform: `scaleX(${factor.weight})` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {score.disruption_reason && (
            <>
              <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 4px' }}>
                If it stops delivering
              </h3>
              <p className="ff-note">{score.disruption_reason}</p>
            </>
          )}

          <Alternatives candidates={score.substitution_candidates} node={node} />
        </>
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
      <div className="ff-output">
        <div className="ff-output-head">
          <span className="ff-output-title">
            {counterfactual ? 'counterfactual · no funding' : 'engine · after funding'}
          </span>
          <button className="ff-ghost" onClick={onToggleCounterfactual}>
            {counterfactual ? 'Fund it again' : 'Turn it off'}
          </button>
        </div>

        <div className="ff-output-body">
          <div>
            <div className="ff-headline">{cr(fundedAmount)}</div>
            <p className="ff-note" style={{ marginTop: 4 }}>
              into {shortName(fundedName)} removes {cr(delta.total_exposure_reduced_cr, 0)} of
              exposure and moves {num(delta.nodes_improved)} companies to a better band.{' '}
              {delta.nodes_worsened === 0
                ? 'None got worse.'
                : `${num(delta.nodes_worsened)} got worse.`}
            </p>
          </div>

          {anchorBefore && anchorAfter && (
            <div>
              <h3 className="ff-h" style={{ fontSize: 12.5, marginBottom: 9 }}>
                {anchorName ?? 'Anchor'} — inbound supply at risk
              </h3>
              <div className="ff-ba">
                <div className="ff-ba-side" data-side="before">
                  <span className="ff-ba-label">Before</span>
                  <span className="ff-ba-value">{cr(anchorBefore.disrupted_inflow_cr, 0)}</span>
                  <Chip band={anchorBefore.disruption_band} />
                </div>
                <div className="ff-ba-arrow" aria-hidden="true">
                  →
                </div>
                <div className="ff-ba-side" data-side="after">
                  <span className="ff-ba-label">After</span>
                  <span className="ff-ba-value">{cr(anchorAfter.disrupted_inflow_cr, 0)}</span>
                  <Chip band={anchorAfter.disruption_band} />
                </div>
              </div>
              <p className="ff-note-sm" style={{ marginTop: 9 }}>
                The anchor paid on time, had the cash, and did nothing wrong. This is what reaches
                it anyway when a supplier three tiers down runs out of money.
              </p>
            </div>
          )}

          {moved.length > 0 && (
            <div>
              <h3 className="ff-h" style={{ fontSize: 12.5, marginBottom: 4 }}>
                Bands that moved
              </h3>
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
