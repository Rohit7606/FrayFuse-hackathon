/**
 * The demo's spine.
 *
 * Seven steps, in the order the argument is made, each one clickable so a
 * question in the Q&A does not force a restart. It doubles as the legend,
 * because the legend has to be on screen whenever the graph is — colour is
 * carrying data and it never gets to do that unlabelled.
 */

import { BAND_COLOR, BAND_MEANING, BAND_ORDER } from '../lib/bands';
import { num } from '../lib/format';
import type { RiskBand, Summary } from '../types';

export const STEPS = [
  { id: 'network', code: '01 / CHAIN', name: 'The chain' },
  { id: 'visibility', code: '02 / VISIBILITY', name: 'What the anchor sees' },
  { id: 'evidence', code: '03 / EVIDENCE', name: 'Ageing vs reality' },
  { id: 'cascade', code: '04 / CASCADE', name: 'Stress propagates' },
  { id: 'rank', code: '05 / RANK', name: 'Fragile × irreplaceable' },
  { id: 'path', code: '06 / PATH', name: 'Why this one matters' },
  { id: 'act', code: '07 / ACT', name: 'Fund it, then undo it' },
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
    <nav className="ff-rail" aria-label="Demo steps">
      <div className="ff-rail-head">
        <span className="ff-label">Walkthrough</span>
      </div>

      {STEPS.map((step, index) => {
        const state =
          step.id === current ? 'active' : index < currentIndex || reached.has(step.id) ? 'done' : 'ahead';
        return (
          <button
            key={step.id}
            className="ff-step"
            data-state={state}
            aria-current={step.id === current ? 'step' : undefined}
            onClick={() => onSelect(step.id)}
          >
            <span className="ff-step-dot" />
            <span className="ff-step-body">
              <span className="ff-step-code">{step.code}</span>
              <span className="ff-step-name">{step.name}</span>
            </span>
          </button>
        );
      })}

      <div className="ff-rail-foot">
        <span className="ff-label">{showBands ? 'Risk band' : 'Network'}</span>
        {showBands ? (
          <div className="ff-legend">
            {BAND_ORDER.map((band: RiskBand) => (
              <div className="ff-legend-row" key={band}>
                <span className="ff-legend-swatch" style={{ background: BAND_COLOR[band] }} />
                <span>
                  {band}
                  <span style={{ display: 'block', fontSize: 10.5, opacity: 0.72 }}>
                    {BAND_MEANING[band]}
                  </span>
                </span>
                <span className="ff-legend-count">{num(counts[band] ?? 0)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="ff-legend">
            <div className="ff-legend-row">
              <span className="ff-legend-swatch" style={{ background: '#5B7A5F' }} />
              <span>Tier 0 — anchor</span>
              <span className="ff-legend-count" />
            </div>
            <div className="ff-legend-row">
              <span className="ff-legend-swatch" style={{ background: '#3A5340' }} />
              <span>Tier 1–3 — suppliers</span>
              <span className="ff-legend-count" />
            </div>
            <div className="ff-legend-row">
              <span className="ff-legend-swatch" style={{ background: '#D2FF5C' }} />
              <span>Selection and path</span>
              <span className="ff-legend-count" />
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
