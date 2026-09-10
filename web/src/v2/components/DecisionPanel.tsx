/**
 * The decision layer: which queue a supplier is in, and where a budget goes.
 *
 * The ranked list answers "who is fragile AND irreplaceable". These three
 * blocks answer the questions that follow it, and none of them computes
 * anything — every figure arrives from `/api/derisk` or `/api/allocate`, which
 * is where the thresholds and the optimisation live.
 *
 *   QueueBoard    the network split into "fund now" and "watch / de-risk"
 *   DeriskPanel   one supplier's plan: status, exposure, triggers, action
 *   BudgetPanel   a limited budget spread across several of them
 *
 * The same two rules the rest of the panel follows: a queue is never colour
 * alone, and every number keeps the precision the engine returned it at.
 */

import { bandStyle } from '../lib/bands';
import { cr, num, pct, score as fmtScore, shortName } from '../lib/format';
import type {
  AllocateResponse,
  DeriskPlan,
  Node,
  RiskBand,
  Score,
  TriageQueue,
} from '../types';

/**
 * Queue styling.
 *
 * Deliberately NOT the band ramp. A queue is a decision and a band is a
 * severity; giving them the same four colours would make the screen assert
 * that critical means fund, which is exactly the collapse triage exists to
 * prevent. These are ink weights, and every chip prints its own name.
 */
const QUEUE_STYLE: Record<TriageQueue, { label: string; ink: string; wash: string }> = {
  fund_now: { label: 'fund now', ink: '#012F13', wash: 'rgba(1, 47, 19, 0.10)' },
  derisk: { label: 'watch / de-risk', ink: '#8A5A00', wash: 'rgba(138, 90, 0, 0.10)' },
  monitor: { label: 'monitor', ink: '#4A473E', wash: 'rgba(74, 71, 62, 0.09)' },
  clear: { label: 'no action', ink: '#6B675B', wash: 'rgba(107, 103, 91, 0.07)' },
  origin: { label: 'stress origin', ink: '#8E1230', wash: 'rgba(142, 18, 48, 0.09)' },
};

export function QueueChip({ queue }: { queue: TriageQueue | null | undefined }) {
  if (!queue) return null;
  const style = QUEUE_STYLE[queue];
  return (
    <span
      className="ff-chip"
      style={{ ['--band' as string]: style.ink, ['--band-wash' as string]: style.wash }}
    >
      {style.label}
    </span>
  );
}

function Figure({ label, value, lead }: { label: string; value: string; lead?: boolean }) {
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
// QueueBoard
// ---------------------------------------------------------------------------

interface QueueRow {
  nodeId: string;
  name: string;
  score: Score;
}

function collect(
  scores: Map<string, Score>,
  nodeById: Map<string, Node>,
  queue: TriageQueue,
  limit: number,
): { rows: QueueRow[]; total: number; cost: number; exposure: number } {
  const all: QueueRow[] = [];
  let cost = 0;
  let exposure = 0;
  for (const [nodeId, row] of scores) {
    if (row.triage_queue !== queue) continue;
    const node = nodeById.get(nodeId);
    if (!node) continue;
    all.push({ nodeId, name: node.name, score: row });
    cost += row.intervention_cost_cr;
    exposure += row.estimated_exposure_cr;
  }
  // Worst first, ties on node_id — the engine's own tiebreak.
  all.sort(
    (a, b) => b.score.final_score - a.score.final_score || a.nodeId.localeCompare(b.nodeId),
  );
  return { rows: all.slice(0, limit), total: all.length, cost, exposure };
}

/**
 * The two queues, side by side.
 *
 * The watch queue is NOT a slice of `ranking`: a supplier can be fragile and
 * genuinely replaceable, and `final_score` multiplies its low criticality away
 * so it never ranks at all. Reading `triage_queue` across every score is what
 * surfaces that population — see SCHEMA.md §4.7.
 */
export function QueueBoard({
  scores,
  nodeById,
  selectedId,
  watchlist,
  onSelect,
  limit = 4,
}: {
  scores: Map<string, Score>;
  nodeById: Map<string, Node>;
  selectedId: string | null;
  watchlist: Set<string>;
  onSelect: (nodeId: string) => void;
  limit?: number;
}) {
  const fund = collect(scores, nodeById, 'fund_now', limit);
  const watch = collect(scores, nodeById, 'derisk', limit);
  const rankedIds = new Set(
    [...scores.values()].filter((row) => row.rank !== null).map((row) => row.node_id),
  );
  const unranked = [...scores.values()].filter(
    (row) => row.triage_queue === 'derisk' && !rankedIds.has(row.node_id),
  ).length;

  const column = (
    title: string,
    queue: TriageQueue,
    data: ReturnType<typeof collect>,
    note: string,
  ) => (
    <div className="ff-queue">
      <div className="ff-queue-head">
        <QueueChip queue={queue} />
        <span className="ff-queue-count">{num(data.total)}</span>
      </div>
      <h3 className="ff-queue-title">{title}</h3>
      <p className="ff-queue-note">{note}</p>
      {data.rows.length === 0 ? (
        <p className="ff-empty">Nobody is in this queue at this stress level.</p>
      ) : (
        <div className="ff-queue-list">
          {data.rows.map((row) => (
            <button
              key={row.nodeId}
              className="ff-queue-row"
              aria-pressed={selectedId === row.nodeId}
              onClick={() => onSelect(row.nodeId)}
            >
              <span className="ff-queue-name">
                {shortName(row.name)}
                {watchlist.has(row.nodeId) && <span className="ff-queue-flag">queued</span>}
              </span>
              <span className="ff-queue-figs">
                <span>{cr(row.score.intervention_cost_cr)}</span>
                <span className="ff-queue-exposure">
                  {cr(row.score.estimated_exposure_cr, 0)} at risk
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
      <div className="ff-queue-total">
        {queue === 'fund_now' ? 'To stabilise all' : 'Held contingent'} {cr(data.cost, 0)}
      </div>
    </div>
  );

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">What to do about them</h2>
        <span className="ff-h-note">two queues, not one list</span>
      </div>

      <div className="ff-queues">
        {column(
          'Money is the answer',
          'fund_now',
          fund,
          'Fragile and hard to replace. Nobody else makes the part in time.',
        )}
        {column(
          'Watch and second-source',
          'derisk',
          watch,
          'Fragile, but not a chokepoint. Rescue is not prioritised — the money is better spent above.',
        )}
      </div>

      <p className="ff-note-sm" style={{ marginTop: 12 }}>
        {unranked > 0
          ? `${num(unranked)} of the watch queue never reach the ranked list at all — fragility × criticality multiplies their replaceability away. That is the population this split exists to surface.`
          : 'Both queues are read from the engine’s own triage, not from the risk band.'}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// DeriskPanel
// ---------------------------------------------------------------------------

export function DeriskPanel({
  plan,
  queued,
  fundable,
  busy,
  onFund,
  onQueue,
}: {
  plan: DeriskPlan;
  queued: boolean;
  /** null means funding is available for any supplier; a string names the only one. */
  fundable: string | null;
  busy: boolean;
  onFund: (nodeId: string, amountCr: number) => void;
  onQueue: (nodeId: string) => void;
}) {
  const action = plan.recommended_action;
  const canFund = fundable === null || fundable === plan.node_id;

  return (
    <div className="ff-block" id="ff-plan">
      <div className="ff-block-head">
        <h2 className="ff-h">Decision · {shortName(plan.name)}</h2>
        <QueueChip queue={plan.queue} />
      </div>

      <p className="ff-note">{plan.headline}</p>

      <div className="ff-verdicts">
        {plan.status.map((line) => (
          <div className="ff-verdict" key={line.kind} data-verdict={line.verdict}>
            <span className="ff-verdict-mark" aria-hidden="true">
              {line.verdict === 'fragile' || line.verdict === 'irreplaceable' ? '!' : '✓'}
            </span>
            <span className="ff-verdict-text">{line.detail}</span>
          </div>
        ))}
      </div>

      <div className="ff-figures" style={{ marginTop: 12 }}>
        <Figure label="Potential exposure" value={cr(plan.exposure_at_risk_cr, 0)} lead />
        <Figure label="Stabilisation cost" value={cr(plan.stabilisation_cost_cr)} />
        <Figure label="Fragility × criticality" value={`${fmtScore(plan.fragility)} × ${fmtScore(plan.criticality)}`} />
        <Figure label="Stress inherited, not its own" value={pct(plan.inherited_share)} />
        <Figure
          label="Alternatives found"
          value={
            plan.alternatives_found === null || plan.alternatives_found === undefined
              ? 'not assessed'
              : num(plan.alternatives_found)
          }
        />
      </div>

      {plan.dependency && (
        <p className="ff-note-sm" style={{ marginTop: 10 }}>
          {pct(plan.dependency.exposure_pct)} of its revenue comes from{' '}
          <strong>{shortName(plan.dependency.buyer_name)}</strong> ({cr(plan.dependency.annual_value_cr)} a
          year, {plan.dependency.component.replace(/_/g, ' ')})
          {plan.dependency.buyer_is_stressed_origin
            ? ' — the company this stress starts at.'
            : '.'}
        </p>
      )}

      <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 6px' }}>
        Review triggers
      </h3>
      <div className="ff-triggers">
        {plan.review_triggers.map((trigger) => (
          <div className="ff-trigger" key={`${trigger.metric}-${trigger.threshold}`}>
            <div className="ff-trigger-row">
              <span className="ff-trigger-metric">{trigger.metric.replace(/_/g, ' ')}</span>
              <span className="ff-trigger-figs">
                {trigger.current.toFixed(2)} → <strong>{trigger.threshold.toFixed(2)}</strong>
              </span>
            </div>
            <p className="ff-trigger-detail">{trigger.detail}</p>
          </div>
        ))}
      </div>

      <h3 className="ff-h" style={{ fontSize: 12.5, margin: '16px 0 6px' }}>
        The plan
      </h3>
      <ol className="ff-steps-list">
        {plan.actions.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ol>

      {action.kind === 'fund' && action.amount_cr !== null && action.amount_cr !== undefined && (
        <button
          className="ff-primary ff-primary-wide"
          disabled={busy || !canFund}
          title={
            canFund
              ? undefined
              : 'Committed mocks carry one funded supplier. Run npm run dev:live to fund any of them.'
          }
          onClick={() => onFund(plan.node_id, action.amount_cr as number)}
        >
          {busy ? 'Scoring…' : `Deploy ${cr(action.amount_cr)}`}
        </button>
      )}

      {(action.kind === 'derisk' || action.kind === 'monitor') && (
        <button className="ff-ghost ff-ghost-wide" onClick={() => onQueue(plan.node_id)}>
          {queued ? 'Remove from the watch queue' : action.label}
        </button>
      )}

      {action.kind === 'fund' && !canFund && (
        <p className="ff-note-sm" style={{ marginTop: 8 }}>
          Offline, only the committed intervention can be replayed. The cost above is still the
          engine’s own figure for this supplier.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// WatchQueue
// ---------------------------------------------------------------------------

/** Suppliers moved into the watch queue during this session. */
export function WatchQueue({
  nodeIds,
  scores,
  nodeById,
  onSelect,
  onRemove,
}: {
  nodeIds: string[];
  scores: Map<string, Score>;
  nodeById: Map<string, Node>;
  onSelect: (nodeId: string) => void;
  onRemove: (nodeId: string) => void;
}) {
  if (nodeIds.length === 0) return null;

  const contingent = nodeIds.reduce(
    (total, nodeId) => total + (scores.get(nodeId)?.intervention_cost_cr ?? 0),
    0,
  );
  const exposure = nodeIds.reduce(
    (total, nodeId) => total + (scores.get(nodeId)?.estimated_exposure_cr ?? 0),
    0,
  );

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">Watch queue</h2>
        <span className="ff-h-note">{num(nodeIds.length)} suppliers</span>
      </div>

      <div className="ff-figures">
        <Figure label="Capital held contingent" value={cr(contingent)} lead />
        <Figure label="Exposure being watched" value={cr(exposure, 0)} />
      </div>

      <div className="ff-queue-list" style={{ marginTop: 12 }}>
        {nodeIds.map((nodeId) => (
          <div className="ff-watch-row" key={nodeId}>
            <button className="ff-watch-name" onClick={() => onSelect(nodeId)}>
              {shortName(nodeById.get(nodeId)?.name ?? nodeId)}
            </button>
            <span className="ff-chip" style={bandStyle(scores.get(nodeId)?.risk_band)}>
              {scores.get(nodeId)?.risk_band ?? '—'}
            </span>
            <button
              className="ff-watch-remove"
              onClick={() => onRemove(nodeId)}
              aria-label={`Remove ${nodeById.get(nodeId)?.name ?? nodeId} from the watch queue`}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <p className="ff-note-sm" style={{ marginTop: 10 }}>
        Contingent, not committed. This is what stabilising these suppliers would cost if their
        review triggers fire — it is not money that has been deployed.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BudgetPanel
// ---------------------------------------------------------------------------

function BandPair({ before, after }: { before: RiskBand; after: RiskBand }) {
  return (
    <span className="ff-alloc-bands">
      <span className="ff-chip" style={bandStyle(before)}>
        {before}
      </span>
      <span aria-hidden="true">→</span>
      <span className="ff-chip" style={bandStyle(after)}>
        {after}
      </span>
    </span>
  );
}

export function BudgetPanel({
  budgets,
  budgetIndex,
  result,
  busy,
  error,
  onBudget,
  onRun,
  onSelect,
}: {
  budgets: readonly number[];
  budgetIndex: number;
  result: AllocateResponse | null;
  busy: boolean;
  error: string | null;
  onBudget: (index: number) => void;
  onRun: () => void;
  onSelect: (nodeId: string) => void;
}) {
  const budget = budgets[budgetIndex];

  return (
    <div className="ff-block">
      <div className="ff-block-head">
        <h2 className="ff-h">Spread a limited budget</h2>
        <span className="ff-h-note">{result ? `${result.scoring_runs} scoring runs` : 'engine'}</span>
      </div>

      <p className="ff-note">
        One cheque answers one supplier. This answers the question after it: with this much money
        and several suppliers failing, where does it go?
      </p>

      <div className="ff-budget" role="group" aria-label="Rescue budget">
        {budgets.map((amount, index) => (
          <button
            key={amount}
            className="ff-budget-stop"
            aria-pressed={index === budgetIndex}
            onClick={() => onBudget(index)}
          >
            {cr(amount, amount % 1 === 0 ? 0 : 1)}
          </button>
        ))}
      </div>

      <button className="ff-primary ff-primary-wide" disabled={busy} onClick={onRun}>
        {busy ? 'Probing candidates…' : `Auto-allocate ${cr(budget, budget % 1 === 0 ? 0 : 1)}`}
      </button>

      {error && (
        <p className="ff-note-sm" style={{ marginTop: 10 }}>
          {error}
        </p>
      )}

      {result && (
        <>
          <div className="ff-figures" style={{ marginTop: 16 }}>
            <Figure
              label="Anchor inflow at risk, removed"
              value={cr(result.objective.reduced_cr, 0)}
              lead
            />
            <Figure
              label="Anchor inflow at risk"
              value={`${cr(result.objective.before_cr, 0)} → ${cr(result.objective.after_cr, 0)}`}
            />
            <Figure label="Committed" value={cr(result.allocated_cr)} />
            <Figure label="Left unallocated" value={cr(result.unallocated_cr)} />
            <Figure label="Suppliers improved" value={num(result.delta.nodes_improved)} />
          </div>

          {result.allocations.length === 0 ? (
            <p className="ff-empty" style={{ marginTop: 12 }}>
              Nothing in this network would be measurably stabilised by this money, so none of it
              was committed.
            </p>
          ) : (
            <div className="ff-alloc-list">
              {result.allocations.map((row) => (
                <button
                  key={row.node_id}
                  className="ff-alloc"
                  onClick={() => onSelect(row.node_id)}
                >
                  <div className="ff-alloc-line">
                    <span className="ff-alloc-name">{shortName(row.name)}</span>
                    <span className="ff-alloc-amount">{cr(row.amount_cr)}</span>
                  </div>
                  <div className="ff-alloc-track" aria-hidden="true">
                    <div className="ff-alloc-fill" style={{ transform: `scaleX(${row.coverage})` }} />
                  </div>
                  <div className="ff-alloc-meta">
                    <span>
                      {row.coverage >= 1
                        ? 'fully stabilised'
                        : `${pct(row.coverage)} of ${cr(row.cost_cr)}`}
                    </span>
                    <BandPair before={row.band_before} after={row.band_after} />
                  </div>
                </button>
              ))}
            </div>
          )}

          <p className="ff-note-sm" style={{ marginTop: 12 }}>
            {result.note}
          </p>
        </>
      )}
    </div>
  );
}
