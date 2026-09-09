/**
 * The what-if control.
 *
 * "What happens if the tier-1's payment stress gets worse?" is the question
 * this exists to answer, and it answers it by asking the engine — every stop
 * on this slider is a real `/api/simulate` result, not an interpolation
 * between two endpoints drawn on this side of the wire.
 *
 * It is a native range input on purpose: keyboard, screen reader and touch all
 * work without a line of code, which a div with a drag handler never manages.
 */

import { cr, num, pct, shortName } from '../lib/format';
import { STRESS_LEVELS } from '../api';
import { bandStyle } from '../lib/bands';
import type { RiskBand, Summary } from '../types';

interface Props {
  triggerName: string;
  levelIndex: number;
  baselineIndex: number;
  busy: boolean;
  summary: Summary | null;
  watchedName: string;
  watchedBand: RiskBand | undefined;
  anchorInflow: number | null;
  onChange: (index: number) => void;
}

/** Only the ends and the baseline get a printed tick — the rest are noise. */
function tickLabel(level: number, index: number, baselineIndex: number): string | null {
  if (index === 0) return '0%';
  if (index === STRESS_LEVELS.length - 1) return '100%';
  if (index === baselineIndex) return `${Math.round(level * 100)}% filed`;
  return null;
}

export default function WhatIfBar({
  triggerName,
  levelIndex,
  baselineIndex,
  busy,
  summary,
  watchedName,
  watchedBand,
  anchorInflow,
  onChange,
}: Props) {
  const level = STRESS_LEVELS[levelIndex];
  const fill = (levelIndex / (STRESS_LEVELS.length - 1)) * 100;

  return (
    <div className="ff-whatif">
      <div>
        <div className="ff-slider-head">
          <label className="ff-slider-label" htmlFor="ff-stress">
            What if <strong>{shortName(triggerName)}</strong> paid even later?
          </label>
          <span className="ff-slider-value">
            own_stress {level.toFixed(2)}
            {levelIndex === baselineIndex ? ' · as filed' : ''}
            {busy ? ' · scoring' : ''}
          </span>
        </div>

        <div className="ff-range" style={{ ['--fill' as string]: `${fill}%` }}>
          <input
            id="ff-stress"
            type="range"
            min={0}
            max={STRESS_LEVELS.length - 1}
            step={1}
            value={levelIndex}
            onChange={(event) => onChange(Number(event.target.value))}
            aria-valuetext={`own stress ${level.toFixed(2)} of 1`}
          />
        </div>

        <div className="ff-ticks" aria-hidden="true">
          {STRESS_LEVELS.map((stop, index) => (
            <span
              className="ff-tick"
              key={stop}
              data-baseline={index === baselineIndex ? 'true' : undefined}
            >
              {tickLabel(stop, index, baselineIndex)}
            </span>
          ))}
        </div>
      </div>

      <div className="ff-whatif-out">
        <div className="ff-out">
          <span className="ff-label">{watchedName}</span>
          <span className="ff-out-value">
            <span className="ff-chip" style={bandStyle(watchedBand)}>
              {watchedBand ?? '—'}
            </span>
          </span>
        </div>
        <div className="ff-out">
          <span className="ff-label">At risk</span>
          <span className="ff-out-value">{num(summary?.at_risk_count ?? 0)}</span>
        </div>
        <div className="ff-out">
          <span className="ff-label">Anchor inflow at risk</span>
          <span className="ff-out-value">{anchorInflow === null ? '—' : cr(anchorInflow, 0)}</span>
        </div>
        <div className="ff-out">
          <span className="ff-label">Deepest hop</span>
          <span className="ff-out-value">{summary?.max_propagation_depth ?? 0}</span>
        </div>
      </div>

      <p className="ff-sr" role="status">
        {`Own stress ${pct(level)}. ${num(summary?.at_risk_count ?? 0)} suppliers at risk. ${
          watchedName
        } is ${watchedBand ?? 'unscored'}.`}
      </p>
    </div>
  );
}
