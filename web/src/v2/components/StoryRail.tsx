/**
 * The demo's spine: seven ordered steps, each clickable so a question in the
 * Q&A does not force a restart.
 *
 * The numbers are here because this genuinely is a sequence and the order
 * carries the argument — step 5 only means something after step 4. They are a
 * stepper, not a set of decorative section markers.
 *
 * It doubles as the legend, because the legend has to be on screen whenever
 * the graph is: colour is carrying data there, and it never gets to do that
 * without its name beside it.
 */

import { BAND_COLOR, BAND_MEANING, BAND_ORDER } from '../lib/bands';
import { num } from '../lib/format';
import type { RiskBand, Summary } from '../types';

export const STEPS = [
  { id: 'network', name: 'The chain' },
  { id: 'visibility', name: 'What the anchor sees' },
  { id: 'evidence', name: 'Ageing vs reality' },
  { id: 'cascade', name: 'Stress propagates' },
  { id: 'rank', name: 'Fragile × irreplaceable' },
  { id: 'path', name: 'Why this one matters' },
  { id: 'act', name: 'Fund it, then undo it' },
] as const;

export type StepId = (typeof STEPS)[number]['id'];

interface Props {
  current: StepId;
  reached: Set<StepId>;
  summary: Summary | null;
  showBands: boolean;
  onSelect: (step: StepId) => void;
}

export default function StoryRail({ current, reached, summary, showBands, onSelect }: Props) {
  const counts = summary?.band_counts ?? {};
  const currentIndex = STEPS.findIndex((step) => step.id === current);

  return (
    <nav className="ff-rail" aria-label="Walkthrough">
      <div className="ff-rail-head">
        <div className="ff-rail-title">Walkthrough</div>
        <div className="ff-rail-sub">
          Step {currentIndex + 1} of {STEPS.length}
        </div>
      </div>

      <div className="ff-steps">
        {STEPS.map((step, index) => {
          const state =
            step.id === current
              ? 'active'
              : index < currentIndex || reached.has(step.id)
                ? 'done'
                : 'ahead';
          return (
            <button
              key={step.id}
              className="ff-step"
              data-state={state}
              aria-current={step.id === current ? 'step' : undefined}
              onClick={() => onSelect(step.id)}
            >
              <span className="ff-step-no">{String(index + 1).padStart(2, '0')}</span>
              <span className="ff-step-name">{step.name}</span>
            </button>
          );
        })}
      </div>

      <div className="ff-rail-foot">
        {showBands ? (
          <>
            <div className="ff-rail-foot-title">Risk band</div>
            <div className="ff-legend">
              {BAND_ORDER.map((band: RiskBand) => (
                <div className="ff-legend-row" key={band}>
                  <span className="ff-legend-dot" style={{ background: BAND_COLOR[band] }} />
                  <span>
                    {band}
                    <span className="ff-legend-note">{BAND_MEANING[band]}</span>
                  </span>
                  <span className="ff-legend-count">{num(counts[band] ?? 0)}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="ff-rail-foot-title">Reading the graph</div>
            <div className="ff-legend">
              <div className="ff-legend-row">
                <span className="ff-legend-dot" style={{ background: '#6B675B' }} />
                <span>
                  Anchor
                  <span className="ff-legend-note">Tier 0, boxed on the graph</span>
                </span>
                <span className="ff-legend-count" />
              </div>
              <div className="ff-legend-row">
                <span className="ff-legend-dot" style={{ background: '#B4B0A0' }} />
                <span>
                  Supplier
                  <span className="ff-legend-note">Tiers 1 to 3, unscored so far</span>
                </span>
                <span className="ff-legend-count" />
              </div>
            </div>
          </>
        )}
      </div>
    </nav>
  );
}
