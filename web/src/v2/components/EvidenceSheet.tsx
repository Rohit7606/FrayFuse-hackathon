/**
 * Ageing vs Reality — the evidence panel.
 *
 * It answers exactly one question: "how do you know this company is under
 * payment stress?" The answer is not the score. The answer is the company's
 * own two disclosures, printed side by side:
 *
 *   AGEING SNAPSHOT   what was still unpaid at 31 March. One day of the year,
 *                     and the one day a company can prepare for.
 *   PAYMENT REALITY   the MSMED lines, which describe the whole year's
 *                     behaviour and cannot be tidied up before the snapshot.
 *
 * Every figure here is a filed number carried through the API verbatim. This
 * component computes percentage changes between two disclosed values and
 * nothing else — no score, no weight, no substituted default. An undisclosed
 * line prints as a dash and says so, because `null` and `0.0` are different
 * facts (AGENTS.md §3.6) and a filing that omits a line is not a filing that
 * declared it nil.
 */

import { useEffect, useRef } from 'react';
import { cr, num, pct, times, yoy } from '../lib/format';
import type { Node, Score, StressSignal } from '../types';

interface Props {
  node: Node;
  signals: StressSignal[];
  score: Score | undefined;
  /** Name of the buyer whose stress reached this node, when it was inherited. */
  inheritedFrom?: string | null;
  onClose: () => void;
}

function Delta({
  previous,
  latest,
}: {
  previous: number | null | undefined;
  latest: number | null | undefined;
}) {
  const change = yoy(previous, latest);
  if (!change) return <span className="ff-delta" data-dir="flat">not disclosed</span>;
  return (
    <span className="ff-delta" data-dir={change.dir}>
      {change.label}
    </span>
  );
}

function LedgerRow({
  label,
  previous,
  latest,
  total,
  lead,
}: {
  label: string;
  previous: number | null | undefined;
  latest: number | null | undefined;
  total?: boolean;
  lead?: boolean;
}) {
  return (
    <div className="ff-ledger-row" data-total={total ? 'true' : undefined} data-lead={lead ? 'true' : undefined}>
      <span className="ff-ledger-key">{label}</span>
      <span className="ff-ledger-prev">{cr(previous)}</span>
      <span className="ff-ledger-now">{cr(latest)}</span>
    </div>
  );
}

/** Share of disclosed MSME dues that are past their due date. */
function overdueShare(row: StressSignal): number | null {
  const total = row.msme_total_cr;
  if (total === null || total === 0) return null;
  const buckets = [
    row.msme_under_1yr_cr,
    row.msme_1_2yr_cr,
    row.msme_2_3yr_cr,
    row.msme_over_3yr_cr,
  ];
  if (buckets.every((value) => value === null)) return null;
  // An undisclosed bucket contributes nothing rather than blocking the whole
  // share — but if every bucket is undisclosed there is no share to report,
  // which is the guard above.
  const overdue = buckets.reduce<number>((sum, value) => sum + (value ?? 0), 0);
  return overdue / total;
}

/** The largest of the three MSMED interest lines — the comparable quantity. */
function largestInterest(row: StressSignal): number | null {
  const lines = [
    row.msmed_interest_accrued_unpaid_cr,
    row.msmed_interest_due_unpaid_cr ?? null,
    row.msmed_interest_due_on_payments_beyond_appointed_day_cr ?? null,
  ].filter((value): value is number => value !== null && value !== undefined);
  return lines.length ? Math.max(...lines) : null;
}

function payablesRatio(row: StressSignal): number | null {
  if (!row.total_trade_payables_cr || !row.revenue_cr) return null;
  return row.total_trade_payables_cr / row.revenue_cr;
}

export default function EvidenceSheet({ node, signals, score, inheritedFrom, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);

  // A sheet that traps nothing and cannot be dismissed with a key is a
  // half-built dialog. Escape closes, focus lands on the close control.
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const latest = signals.length ? signals[signals.length - 1] : null;
  const previous = signals.length > 1 ? signals[signals.length - 2] : null;

  // The lime bar is the one place a surface is marked as engine-facing, and it
  // is the only sticky part: the title scrolls away with the document, the way
  // a page header does not.
  const header = (
    <>
      <div className="ff-sheet-head">
        <span className="ff-sheet-kind">evidence · published filings</span>
        <button ref={closeRef} className="ff-sheet-close" onClick={onClose} aria-label="Close evidence">
          ✕
        </button>
      </div>
      <div className="ff-sheet-title-block">
        <h2 className="ff-sheet-title">{node.name}</h2>
        <p className="ff-sheet-sub">
          {node.node_id} · Tier {node.tier} · {node.sector.replace(/_/g, ' ')}
          {node.cin ? ` · CIN ${node.cin}` : ''}
        </p>
      </div>
    </>
  );

  // ---- The unobservable case. This is not an error state; it is the finding.
  if (!latest) {
    return (
      <>
        <div className="ff-scrim" onClick={onClose} />
        <aside className="ff-sheet" role="dialog" aria-modal="true" aria-label={`Evidence for ${node.name}`}>
          {header}
          <div className="ff-sheet-body">
            <div className="ff-verdict" data-tone="quiet">
              <span className="ff-verdict-title">This company files nothing we can read</span>
              <span className="ff-verdict-text">
                No ageing table, no MSMED disclosure, no interest line. A company this small is
                not required to publish one, which is precisely why nobody upstream can see it
                coming. Its stress is not measured here — it is{' '}
                <strong>inherited</strong>
                {inheritedFrom ? ` from ${inheritedFrom}` : ''}, propagated from a buyer that does
                file.
              </span>
            </div>

            <div>
              <div className="ff-col-head">
                <span className="ff-col-name">What is known about it</span>
                <span className="ff-col-basis">from network structure, not from filings</span>
              </div>
              <div className="ff-ledger">
                <div className="ff-ledger-row">
                  <span className="ff-ledger-key">Revenue</span>
                  <span className="ff-ledger-prev" />
                  <span className="ff-ledger-now">{cr(node.revenue_cr)}</span>
                </div>
                <div className="ff-ledger-row">
                  <span className="ff-ledger-key">Cash buffer</span>
                  <span className="ff-ledger-prev" />
                  <span className="ff-ledger-now">
                    {node.cash_buffer_days === null ? '—' : `${num(node.cash_buffer_days)} days`}
                  </span>
                </div>
                <div className="ff-ledger-row">
                  <span className="ff-ledger-key">Employees</span>
                  <span className="ff-ledger-prev" />
                  <span className="ff-ledger-now">{num(node.employees)}</span>
                </div>
                <div className="ff-ledger-row">
                  <span className="ff-ledger-key">Own stress (measured)</span>
                  <span className="ff-ledger-prev" />
                  <span className="ff-ledger-now">{score ? score.own_stress.toFixed(4) : '—'}</span>
                </div>
                <div className="ff-ledger-row" data-total>
                  <span className="ff-ledger-key">Inherited stress (propagated)</span>
                  <span className="ff-ledger-prev" />
                  <span className="ff-ledger-now">
                    {score ? score.inherited_stress.toFixed(4) : '—'}
                  </span>
                </div>
              </div>
            </div>

            {score?.reason_text && (
              <div>
                <div className="ff-col-head">
                  <span className="ff-col-name">Why the engine ranked it</span>
                  <span className="ff-col-basis">generated from a fixed template</span>
                </div>
                <p className="ff-note-sm">{score.reason_text}</p>
              </div>
            )}

            <div className="ff-tags">
              <span className="ff-tag" data-kind={node.data_source}>
                {node.data_source}
              </span>
              <span className="ff-tag">tier {node.tier}</span>
              <span className="ff-tag">{node.is_observable ? 'observable' : 'not observable'}</span>
            </div>
            <p className="ff-note-sm">
              Tier-2 and tier-3 companies in this dataset are generated, with names drawn from a
              fictional entity pool. They are not real businesses.
            </p>
          </div>
        </aside>
      </>
    );
  }

  // ---- The filed case: snapshot against whole-year behaviour.

  const shareBefore = previous ? overdueShare(previous) : null;
  const shareNow = overdueShare(latest);
  const migrationPp =
    shareBefore !== null && shareNow !== null ? (shareNow - shareBefore) * 100 : null;

  const paidLateBefore = previous?.msmed_principal_paid_beyond_appointed_day_cr ?? null;
  const paidLateNow = latest.msmed_principal_paid_beyond_appointed_day_cr;
  const paidLateChange = yoy(paidLateBefore, paidLateNow);
  const paidLateTimes = times(paidLateBefore, paidLateNow);

  const interestBefore = previous ? largestInterest(previous) : null;
  const interestNow = largestInterest(latest);
  const interestTimes = times(interestBefore, interestNow);

  const barScale = Math.max(
    paidLateBefore ?? 0,
    paidLateNow ?? 0,
    previous?.msmed_principal_unpaid_year_end_cr ?? 0,
    latest.msmed_principal_unpaid_year_end_cr ?? 0,
    1,
  );

  // The headline is a comparison of two disclosed figures, stated as a
  // comparison. It asserts nothing the two rows do not already say.
  const snapshotQuiet = migrationPp !== null && Math.abs(migrationPp) < 2;
  const realityLoud = paidLateChange?.dir === 'up' || interestTimes !== null;

  // Rung availability, not rung outcomes. Which rungs FIRED lives in
  // engine/stress.py and is not on the wire, so this reports only what the
  // filing can support — and prints the engine's own reason text underneath as
  // the authoritative statement of what it actually did.
  const rungs = [
    {
      name: 'MSMED interest direction',
      note: 'A rise is a statutory admission of late payment — it accrues only past the appointed day.',
      available: interestBefore !== null && interestNow !== null,
    },
    {
      name: 'Not-due → overdue migration',
      note: latest.has_not_due_column
        ? 'Needs a separate not-due column in both years. This filing has one.'
        : 'Needs a separate not-due column. This filing folds not-yet-due amounts into under-1-year, so the rung is not comparable and is dropped.',
      available: latest.has_not_due_column && shareBefore !== null && shareNow !== null,
    },
    {
      name: 'Payables against revenue',
      note: 'Payables growing faster than revenue is cash being held back.',
      available:
        previous !== null && payablesRatio(latest) !== null && payablesRatio(previous) !== null,
    },
    {
      name: 'Non-MSME aged payables',
      note: 'The weakest rung, and the only one available for filers who disclose nothing under MSMED.',
      available: previous !== null && latest.nonmsme_total_cr !== null && previous.nonmsme_total_cr !== null,
    },
  ];

  return (
    <>
      <div className="ff-scrim" onClick={onClose} />
      <aside className="ff-sheet" role="dialog" aria-modal="true" aria-label={`Evidence for ${node.name}`}>
        {header}
        <div className="ff-sheet-body">
          <div className="ff-verdict" data-tone={realityLoud ? undefined : 'quiet'}>
            <span className="ff-verdict-title">
              {snapshotQuiet && realityLoud
                ? 'The snapshot looks clean. The year does not.'
                : realityLoud
                  ? 'Both disclosures moved the same way.'
                  : 'Nothing in either disclosure moved much.'}
            </span>
            <span className="ff-verdict-text">
              Overdue MSME dues{' '}
              {migrationPp === null ? (
                'cannot be compared across these two years'
              ) : (
                <>
                  moved{' '}
                  <strong>
                    {migrationPp >= 0 ? '+' : '−'}
                    {Math.abs(migrationPp).toFixed(1)} pp
                  </strong>{' '}
                  of the MSME book
                </>
              )}
              , while principal actually <em>paid late during the year</em>{' '}
              {paidLateChange ? (
                <strong>
                  {paidLateChange.label}
                  {paidLateTimes ? ` (${paidLateTimes})` : ''}
                </strong>
              ) : (
                'was not disclosed in both years'
              )}
              . The ageing table is a single day — 31 March — and dues can be cleared just before
              it. The MSMED lines describe twelve months of behaviour, which is why the engine
              leads with them.
            </span>
          </div>

          <div className="ff-cols">
            <section>
              <div className="ff-col-head">
                <span className="ff-col-name">Ageing snapshot</span>
                <span className="ff-col-basis">
                  as at 31 March · {latest.ageing_basis.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="ff-ledger">
                <LedgerRow label="Not due" previous={previous?.msme_not_due_cr} latest={latest.msme_not_due_cr} />
                <LedgerRow label="Under 1 year" previous={previous?.msme_under_1yr_cr} latest={latest.msme_under_1yr_cr} />
                <LedgerRow label="1–2 years" previous={previous?.msme_1_2yr_cr} latest={latest.msme_1_2yr_cr} />
                <LedgerRow label="2–3 years" previous={previous?.msme_2_3yr_cr} latest={latest.msme_2_3yr_cr} />
                <LedgerRow label="Over 3 years" previous={previous?.msme_over_3yr_cr} latest={latest.msme_over_3yr_cr} />
                <LedgerRow label="MSME total" previous={previous?.msme_total_cr} latest={latest.msme_total_cr} total />
              </div>
              <div className="ff-ledger-row ff-ledger-derived">
                <span className="ff-ledger-key">Overdue share of MSME book</span>
                <span className="ff-ledger-prev">{shareBefore === null ? '—' : pct(shareBefore, 1)}</span>
                <span className="ff-ledger-now">{shareNow === null ? '—' : pct(shareNow, 1)}</span>
              </div>
            </section>

            <section>
              <div className="ff-col-head">
                <span className="ff-col-name">Payment reality</span>
                <span className="ff-col-basis">whole year · MSMED s.22 disclosure</span>
              </div>
              <div className="ff-ledger">
                <LedgerRow
                  label="Principal paid beyond appointed day"
                  previous={paidLateBefore}
                  latest={paidLateNow}
                  lead
                />
                <LedgerRow
                  label="Principal unpaid at year end"
                  previous={previous?.msmed_principal_unpaid_year_end_cr}
                  latest={latest.msmed_principal_unpaid_year_end_cr}
                />
                <LedgerRow
                  label="Interest accrued and unpaid"
                  previous={previous?.msmed_interest_accrued_unpaid_cr}
                  latest={latest.msmed_interest_accrued_unpaid_cr}
                />
                <LedgerRow
                  label="Total trade payables"
                  previous={previous?.total_trade_payables_cr}
                  latest={latest.total_trade_payables_cr}
                />
                <LedgerRow label="Revenue" previous={previous?.revenue_cr} latest={latest.revenue_cr} total />
              </div>
              <div className="ff-ledger-row ff-ledger-derived">
                <span className="ff-ledger-key">Payables ÷ revenue</span>
                <span className="ff-ledger-prev">
                  {previous && payablesRatio(previous) !== null ? pct(payablesRatio(previous), 1) : '—'}
                </span>
                <span className="ff-ledger-now">
                  {payablesRatio(latest) !== null ? pct(payablesRatio(latest), 1) : '—'}
                </span>
              </div>
            </section>
          </div>

          <section>
            <div className="ff-col-head">
              <span className="ff-col-name">Same two years, drawn to scale</span>
              <span className="ff-col-basis">
                {previous ? `${previous.fy} against ${latest.fy}` : `${latest.fy} only`}
              </span>
            </div>
            <div className="ff-bars">
              {[
                {
                  label: 'Principal paid late during the year',
                  before: paidLateBefore,
                  now: paidLateNow,
                  quiet: false,
                },
                {
                  label: 'Principal still unpaid at year end',
                  before: previous?.msmed_principal_unpaid_year_end_cr ?? null,
                  now: latest.msmed_principal_unpaid_year_end_cr,
                  quiet: true,
                },
              ].map((measure) => (
                <div className="ff-bar-group" key={measure.label}>
                  <div className="ff-bar-label">
                    {measure.label}{' '}
                    <Delta previous={measure.before} latest={measure.now} />
                  </div>
                  {[
                    { fy: previous?.fy ?? '—', value: measure.before, year: 'prev' as const },
                    { fy: latest.fy, value: measure.now, year: 'now' as const },
                  ].map((bar) => (
                    <div className="ff-bar-line" key={`${measure.label}-${bar.year}`}>
                      <span className="ff-bar-fy">{bar.fy}</span>
                      <div className="ff-bar-track">
                        <div
                          className="ff-bar-fill"
                          data-year={bar.year}
                          data-tone={measure.quiet ? 'quiet' : undefined}
                          style={{ transform: `scaleX(${(bar.value ?? 0) / barScale})` }}
                        />
                      </div>
                      <span className="ff-bar-figure">{cr(bar.value)}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <p className="ff-note-sm" style={{ marginTop: 12 }}>
              Both measures are drawn on one shared scale, so their sizes are comparable. The
              upper pair is twelve months of payment behaviour; the lower pair is what remained
              outstanding on the last day of each year.
            </p>
          </section>

          <section>
            <div className="ff-col-head">
              <span className="ff-col-name">What this filing can support</span>
              <span className="ff-col-basis">four rungs · weights renormalised over those available</span>
            </div>
            <div className="ff-rungs">
              {rungs.map((rung) => (
                <div className="ff-rung" key={rung.name} data-fired={rung.available ? 'true' : 'false'}>
                  <span className="ff-rung-mark">{rung.available ? '●' : '○'}</span>
                  <span>
                    <strong>{rung.name}</strong> — {rung.note}
                  </span>
                </div>
              ))}
            </div>
            <p className="ff-note-sm" style={{ marginTop: 12 }}>
              A filled marker means this filing discloses the inputs the rung needs in both years.
              A rung without inputs is dropped and the remaining weights are renormalised — never
              filled in with a default.{' '}
              {score && (
                <>
                  The engine scored this company at <strong>own_stress {score.own_stress.toFixed(4)}</strong>
                  {score.reason_text ? ` — “${score.reason_text}”` : '.'}
                </>
              )}
            </p>
          </section>

          <div className="ff-tags">
            <span className="ff-tag" data-kind={latest.data_source}>
              {latest.data_source}
            </span>
            <span className="ff-tag">{latest.basis}</span>
            <span className="ff-tag">{latest.fy}</span>
            <span className="ff-tag">
              {latest.has_not_due_column ? 'not-due column' : 'no not-due column'}
            </span>
            {latest.series_break && <span className="ff-tag">series break</span>}
            {latest.msme_book_material === false && <span className="ff-tag">msme book immaterial</span>}
          </div>

          {!latest.has_not_due_column && (
            <p className="ff-note-sm">
              This filer folds not-yet-due amounts into the under-1-year bucket, so that bucket is
              not comparable with a filer who separates them. The migration rung is dropped rather
              than estimated.
            </p>
          )}
          {latest.data_source !== 'real' && (
            <p className="ff-note-sm">
              These figures are synthetic — generated by <code>engine/mockgen</code> with a fixed
              seed so the demo is reproducible. Real collected filings carry{' '}
              <code>data_source: real</code> and are never mixed with generated rupee values.
            </p>
          )}
        </div>
      </aside>
    </>
  );
}
