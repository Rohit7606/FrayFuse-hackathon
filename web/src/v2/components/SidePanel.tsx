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
import { cr, num, pct, score as fmtScore, shortName, times } from '../lib/format';
import type {
  AllocateResponse,
  Delta,
  Edge,
  Meta,
  Node,
  ReasonFactor,
  RiskBand,
  Score,
  StressSignal,
  SubstitutionCandidate,
  Summary,
} from '../types';
import type { Wave } from '../lib/derive';

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

// ---------------------------------------------------------------------------
// VisibilityBreakdown — step 02
// ---------------------------------------------------------------------------

/**
 * Per-tier observability breakdown. The step's argument is "the anchor sees
 * almost none of it" — this panel puts the numbers on that claim.
 */
export function VisibilityBreakdown({ nodes, meta }: { nodes: Node[]; meta: Meta }) {
  const tiers = new Map<number, { total: number; observable: number }>();
  for (const node of nodes) {
    const entry = tiers.get(node.tier) ?? { total: 0, observable: 0 };
    entry.total += 1;
    if (node.is_observable) entry.observable += 1;
    tiers.set(node.tier, entry);
  }
  const sorted = [...tiers.entries()].sort((a, b) => a[0] - b[0]);
  const totalObservable = nodes.filter((n) => n.is_observable).length;
  const coverage = nodes.length > 0 ? totalObservable / nodes.length : 0;

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">Observability by tier</h2>
        <span className="ff-h-note">{pct(coverage)} visible</span>
      </div>

      <div className="ff-tier-breakdown">
        {sorted.map(([tier, data]) => {
          const ratio = data.total > 0 ? data.observable / data.total : 0;
          return (
            <div className="ff-tier-row" key={tier}>
              <div className="ff-tier-label">
                <span className="ff-tier-name">{tier === 0 ? 'Anchor' : `Tier ${tier}`}</span>
                <span className="ff-tier-count">
                  {num(data.observable)} of {num(data.total)}
                </span>
              </div>
              <div className="ff-tier-track">
                <div
                  className="ff-tier-fill"
                  style={{ transform: `scaleX(${ratio})` }}
                  data-full={ratio >= 1 ? 'true' : undefined}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="ff-figures" style={{ marginTop: 14 }}>
        <Figure label="Total companies" value={num(meta.node_count)} lead />
        <Figure label="With filed data" value={num(totalObservable)} />
        <Figure label="Dark — no filings" value={num(meta.node_count - totalObservable)} />
      </div>

      <p className="ff-note" style={{ marginTop: 14 }}>
        Everything dimmed on the graph is a firm nobody upstream has filings for. Tier-1 suppliers
        publish because they are large enough to be obligated. The firms two and three tiers down
        are under no such obligation — and they are where the cash runs out.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TriggerEvidence — step 03
// ---------------------------------------------------------------------------

/**
 * The trigger company's filing evidence. Step 03 says "the filing admits it is
 * paying late" — this panel lays out exactly what the filing says.
 */
export function TriggerEvidence({
  node,
  signals,
  score,
}: {
  node: Node;
  signals: StressSignal[];
  score: Score | undefined;
}) {
  const latest = signals.length > 0 ? signals[signals.length - 1] : null;
  const previous = signals.length > 1 ? signals[signals.length - 2] : null;

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">What the filing says</h2>
        <span className="ff-h-note">{node.node_id}</span>
      </div>

      <p className="ff-note" style={{ marginBottom: 14 }}>
        {shortName(node.name)}'s own year-end disclosure. The ageing schedule and the MSMED
        lines are two readings of the same company — and they rarely agree.
      </p>

      {latest && (
        <>
          <div className="ff-figures">
            <Figure label="Filing year" value={latest.fy} lead />
            {latest.msmed_principal_unpaid_year_end_cr !== null && (
              <Figure
                label="MSMED principal unpaid at year-end"
                value={cr(latest.msmed_principal_unpaid_year_end_cr)}
              />
            )}
            {latest.msmed_principal_paid_beyond_appointed_day_cr !== null && (
              <Figure
                label="Paid beyond appointed day"
                value={cr(latest.msmed_principal_paid_beyond_appointed_day_cr)}
              />
            )}
            {latest.msme_total_cr !== null && (
              <Figure label="MSME payables, total" value={cr(latest.msme_total_cr)} />
            )}
            {latest.total_trade_payables_cr !== null && (
              <Figure label="Total trade payables" value={cr(latest.total_trade_payables_cr)} />
            )}
            {latest.trade_payables_turnover_ratio !== null && (
              <Figure
                label="Payables turnover ratio"
                value={latest.trade_payables_turnover_ratio.toFixed(2)}
              />
            )}
          </div>

          {latest.msme_under_1yr_cr !== null && (
            <>
              <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 6px' }}>
                Ageing schedule
              </h3>
              <div className="ff-ageing">
                {latest.msme_not_due_cr !== null && (
                  <div className="ff-ageing-row">
                    <span className="ff-ageing-label">Not due</span>
                    <span className="ff-ageing-value">{cr(latest.msme_not_due_cr)}</span>
                  </div>
                )}
                <div className="ff-ageing-row">
                  <span className="ff-ageing-label">Under 1 year</span>
                  <span className="ff-ageing-value">{cr(latest.msme_under_1yr_cr)}</span>
                </div>
                {latest.msme_1_2yr_cr !== null && (
                  <div className="ff-ageing-row">
                    <span className="ff-ageing-label">1–2 years</span>
                    <span className="ff-ageing-value">{cr(latest.msme_1_2yr_cr)}</span>
                  </div>
                )}
                {latest.msme_2_3yr_cr !== null && (
                  <div className="ff-ageing-row">
                    <span className="ff-ageing-label">2–3 years</span>
                    <span className="ff-ageing-value">{cr(latest.msme_2_3yr_cr)}</span>
                  </div>
                )}
                {latest.msme_over_3yr_cr !== null && (
                  <div className="ff-ageing-row">
                    <span className="ff-ageing-label">Over 3 years</span>
                    <span className="ff-ageing-value">{cr(latest.msme_over_3yr_cr)}</span>
                  </div>
                )}
              </div>
            </>
          )}

          {previous && (
            <>
              <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 6px' }}>
                Year-on-year
              </h3>
              <div className="ff-yoy">
                {previous.msme_total_cr !== null && latest.msme_total_cr !== null && (
                  <div className="ff-yoy-row">
                    <span className="ff-yoy-label">MSME payables</span>
                    <span className="ff-yoy-values">
                      {cr(previous.msme_total_cr)} → {cr(latest.msme_total_cr)}
                    </span>
                    <span className="ff-yoy-change" data-dir={
                      latest.msme_total_cr > previous.msme_total_cr ? 'up' : latest.msme_total_cr < previous.msme_total_cr ? 'down' : 'flat'
                    }>
                      {times(previous.msme_total_cr, latest.msme_total_cr) ?? '—'}
                    </span>
                  </div>
                )}
                {previous.msmed_principal_unpaid_year_end_cr !== null &&
                  latest.msmed_principal_unpaid_year_end_cr !== null && (
                    <div className="ff-yoy-row">
                      <span className="ff-yoy-label">MSMED unpaid</span>
                      <span className="ff-yoy-values">
                        {cr(previous.msmed_principal_unpaid_year_end_cr)} →{' '}
                        {cr(latest.msmed_principal_unpaid_year_end_cr)}
                      </span>
                      <span className="ff-yoy-change" data-dir={
                        latest.msmed_principal_unpaid_year_end_cr > previous.msmed_principal_unpaid_year_end_cr
                          ? 'up' : latest.msmed_principal_unpaid_year_end_cr < previous.msmed_principal_unpaid_year_end_cr ? 'down' : 'flat'
                      }>
                        {times(previous.msmed_principal_unpaid_year_end_cr, latest.msmed_principal_unpaid_year_end_cr) ?? '—'}
                      </span>
                    </div>
                )}
              </div>
            </>
          )}
        </>
      )}

      {score && score.reason_factors && score.reason_factors.length > 0 && (
        <>
          <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 6px' }}>
            What drives the stress score
          </h3>
          <div className="ff-factors">
            {score.reason_factors.map((factor: ReasonFactor) => (
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

      {score && (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', margin: '14px 0 0' }}>
          <Chip band={score.risk_band} />
          <span className="ff-rank-meta">
            own stress {fmtScore(score.own_stress)}
          </span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CascadeProgress — step 04
// ---------------------------------------------------------------------------

/**
 * Live cascade tracker. Step 04's argument is that stress propagates wave by
 * wave — this panel shows each wave as it lands, with running totals.
 */
export function CascadeProgress({
  waves,
  waveIndex,
  summary,
  running,
}: {
  waves: Wave[];
  waveIndex: number;
  summary: Summary;
  running: boolean;
}) {
  const visibleWaves = waves.slice(0, waveIndex + 1);
  let cumulative = 0;

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">Cascade progress</h2>
        <span className="ff-h-note">
          {running ? 'propagating…' : `${waves.length} waves settled`}
        </span>
      </div>

      <div className="ff-wave-log">
        {visibleWaves.map((wave, i) => {
          cumulative += wave.nodeIds.length;
          const isActive = i === waveIndex && running;
          return (
            <div
              className="ff-wave-entry"
              key={wave.depth}
              data-active={isActive ? 'true' : undefined}
              data-settled={!running || i < waveIndex ? 'true' : undefined}
            >
              <span className="ff-wave-depth">
                {wave.depth === 0 ? 'Origin' : `Hop ${wave.depth}`}
              </span>
              <span className="ff-wave-count">
                {num(wave.nodeIds.length)} {wave.nodeIds.length === 1 ? 'supplier' : 'suppliers'}
              </span>
              <span className="ff-wave-cumulative">
                {num(cumulative)} total
              </span>
            </div>
          );
        })}
      </div>

      {!running && summary && (
        <div className="ff-figures" style={{ marginTop: 14 }}>
          <Figure label="Suppliers reached" value={num(summary.at_risk_count)} lead />
          <Figure label="Total exposure" value={cr(summary.total_estimated_exposure_cr, 0)} />
          <Figure label="Cost to stabilise all" value={cr(summary.total_intervention_cost_cr, 0)} />
          <Figure label="Deepest hop" value={num(summary.max_propagation_depth)} />
          <Figure label="Iterations to converge" value={num(summary.iterations_to_converge)} />
        </div>
      )}

      <p className="ff-note-sm" style={{ marginTop: 12 }}>
        {running
          ? 'Each wave is one hop of propagation the engine recorded. Stress scales by revenue dependency and damps per hop.'
          : 'The cascade has settled. Every supplier that inherited stress is now scored — fragility × criticality ranks what to do about them.'}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PathBreakdown — step 06
// ---------------------------------------------------------------------------

/**
 * Hop-by-hop dependency path. Step 06 says "this is the chain by which a halt
 * reaches the anchor" — this panel itemises every hop with edge economics.
 */
export function PathBreakdown({
  path,
  scores,
  nodeById,
}: {
  path: { nodeIds: string[]; hops: { edge: Edge; to: string }[]; reachesAnchor: boolean };
  scores: Map<string, Score>;
  nodeById: Map<string, Node>;
}) {
  if (path.hops.length === 0) return null;

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">Dependency chain</h2>
        <span className="ff-h-note">
          {path.hops.length} {path.hops.length === 1 ? 'hop' : 'hops'}
          {path.reachesAnchor ? ' → anchor' : ''}
        </span>
      </div>

      <div className="ff-hop-list">
        {path.hops.map((hop, i) => {
          const fromId = path.nodeIds[i];
          const fromNode = nodeById.get(fromId);
          const toNode = nodeById.get(hop.to);
          const fromScore = scores.get(fromId);
          const toScore = scores.get(hop.to);

          return (
            <div className="ff-hop" key={hop.edge.edge_id}>
              <div className="ff-hop-header">
                <span className="ff-hop-no">{i + 1}</span>
                <span className="ff-hop-names">
                  <span className="ff-hop-from">
                    {shortName(fromNode?.name ?? fromId)}
                  </span>
                  <span className="ff-hop-arrow">→</span>
                  <span className="ff-hop-to">
                    {shortName(toNode?.name ?? hop.to)}
                  </span>
                </span>
              </div>
              <div className="ff-hop-detail">
                <span className="ff-hop-meta">
                  {hop.edge.component.replace(/_/g, ' ')}
                </span>
                <span className="ff-hop-meta">
                  {cr(hop.edge.annual_value_cr)} / year
                </span>
                <span className="ff-hop-meta">
                  {pct(hop.edge.exposure_pct)} of supplier revenue
                </span>
                {hop.edge.is_single_source === true && (
                  <span className="ff-hop-sole">sole source</span>
                )}
              </div>
              <div className="ff-hop-bands">
                {fromScore && (
                  <span className="ff-hop-band">
                    <Chip band={fromScore.risk_band} />
                    <span className="ff-rank-meta">{shortName(fromNode?.name ?? fromId)}</span>
                  </span>
                )}
                {i === path.hops.length - 1 && toScore && (
                  <span className="ff-hop-band">
                    <Chip band={toScore.risk_band} />
                    <span className="ff-rank-meta">{shortName(toNode?.name ?? hop.to)}</span>
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <p className="ff-note-sm" style={{ marginTop: 12 }}>
        {path.reachesAnchor
          ? 'Edges point the way goods move. Stress moved the other way — buyer to supplier — following the money that never arrived. A halt at the bottom of this chain stops the anchor\'s line.'
          : 'This chain does not reach an anchor in this dataset. The supplier matters to the network, but the disruption path does not terminate at a tier-0 company.'}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AllocationSummary — step 08 enhancement
// ---------------------------------------------------------------------------

/**
 * Post-allocation analysis. Shown after the engine has run the allocation, to
 * give the audience the "what just happened" breakdown.
 */
export function AllocationSummary({
  allocation,
  nodeById,
}: {
  allocation: AllocateResponse;
  nodeById: Map<string, Node>;
}) {
  const improved = allocation.delta.per_node.filter((r) => r.band_before !== r.band_after);
  const efficiencyRanked = [...allocation.allocations].sort(
    (a, b) => b.efficiency - a.efficiency,
  );

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">Allocation analysis</h2>
        <span className="ff-h-note">{allocation.scoring_runs} scoring runs</span>
      </div>

      <div className="ff-figures">
        <Figure
          label="Anchor inflow removed from risk"
          value={cr(allocation.objective.reduced_cr, 0)}
          lead
        />
        <Figure
          label="Before"
          value={cr(allocation.objective.before_cr, 0)}
        />
        <Figure
          label="After"
          value={cr(allocation.objective.after_cr, 0)}
        />
        <Figure label="Budget committed" value={cr(allocation.allocated_cr)} />
        <Figure label="Left unallocated" value={cr(allocation.unallocated_cr)} />
      </div>

      {efficiencyRanked.length > 0 && (
        <>
          <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 6px' }}>
            Efficiency — anchor exposure removed per ₹ spent
          </h3>
          <div className="ff-efficiency">
            {efficiencyRanked.map((row, i) => (
              <div className="ff-efficiency-row" key={row.node_id}>
                <span className="ff-efficiency-rank">{i + 1}</span>
                <span className="ff-efficiency-name">{shortName(row.name)}</span>
                <span className="ff-efficiency-value">
                  {row.efficiency.toFixed(2)}×
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {improved.length > 0 && (
        <>
          <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 4px' }}>
            Bands that moved
          </h3>
          <div className="ff-transitions">
            {improved.map((row) => (
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
                <span className="ff-transition-arrow" aria-hidden="true">→</span>
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

      <p className="ff-note-sm" style={{ marginTop: 12 }}>
        {allocation.note}
      </p>
    </div>
  );
}
