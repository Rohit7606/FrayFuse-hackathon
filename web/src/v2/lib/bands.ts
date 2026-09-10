/**
 * The severity encoding, in one place.
 *
 * These four values are the only colours in the product that carry data. They
 * were measured against the tan desk (#F3F1E5) rather than picked by eye.
 *
 * The three ACTIVE bands are an ordered ramp, not a category set: watch → high
 * → critical descend in lightness (relative luminance 0.263 → 0.143 → 0.064),
 * so the order reads even to someone who cannot separate the hues, and the
 * ramp still passes the dataviz validator's adjacent-pair separation. Contrast
 * against the desk: watch 3.21, high 4.80, critical 8.13.
 *
 * `stable` deliberately sits OUTSIDE the ramp as a low-chroma grey-green at
 * 4.02 contrast. 396 of 412 nodes are stable; "nothing reached it" is not a
 * severity and must not compete with the three that are.
 *
 * Lime is absent from this file on purpose. It is interface chrome — the
 * primary action, the current step, an engine-output header — and it never
 * encodes a value.
 */

import type { CSSProperties } from 'react';
import type { RiskBand } from '../types';

export const BAND_COLOR: Record<RiskBand, string> = {
  stable: '#6E7A5E',
  watch: '#BC7413',
  high: '#B8431A',
  critical: '#8E1230',
};

export const BAND_WASH: Record<RiskBand, string> = {
  stable: 'rgba(110, 122, 94, 0.10)',
  watch: 'rgba(188, 116, 19, 0.11)',
  high: 'rgba(184, 67, 26, 0.10)',
  critical: 'rgba(142, 18, 48, 0.09)',
};

/** Worst first — the order the legend and the counts are read in. */
export const BAND_ORDER: RiskBand[] = ['critical', 'high', 'watch', 'stable'];

export const BAND_MEANING: Record<RiskBand, string> = {
  critical: 'Fragile and hard to replace',
  high: 'Under real strain',
  watch: 'Stress arriving',
  stable: 'No stress reached it',
};

/**
 * Canvas ink. The graph is drawn on paper, so its structure is dark-on-light:
 * edges and guides are washes of the ink colour, never light strokes.
 */
export const PAPER = {
  desk: '#F3F1E5',
  sheet: '#F8F7F2',
  ink: '#141414',
  inkMid: '#4A473E',
  inkDim: '#6B675B',
  lime: '#D2FF5C',
  forest: '#012F13',
  apple: '#8BC53D',
  mint: '#E2F0CC',
};

/** Nodes before any scoring is shown, and the anchors among them. */
export const UNSCORED = '#B4B0A0';
export const UNSCORED_ANCHOR = '#6B675B';

export function bandStyle(band: RiskBand | undefined): CSSProperties {
  const key: RiskBand = band ?? 'stable';
  return {
    ['--band' as string]: BAND_COLOR[key],
    ['--band-wash' as string]: BAND_WASH[key],
  } as CSSProperties;
}

// ---------------------------------------------------------------------------
// Canvas colour helpers
// ---------------------------------------------------------------------------

function parseHex(hex: string): [number, number, number] {
  const value = hex.replace('#', '');
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
  ];
}

/**
 * Blend two hex colours in sRGB.
 *
 * sRGB rather than a perceptual space on purpose: this only runs across a few
 * hundred milliseconds between two already-validated endpoints, and those
 * endpoints are what a reader actually judges. Nothing here produces a colour
 * that has to stand on its own.
 */
export function mix(from: string, to: string, t: number): string {
  const a = parseHex(from);
  const b = parseHex(to);
  const clamped = t <= 0 ? 0 : t >= 1 ? 1 : t;
  const channel = (index: number) => Math.round(a[index] + (b[index] - a[index]) * clamped);
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`;
}

export function rgba(hex: string, alpha: number): string {
  const [r, g, b] = parseHex(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Strong ease-out, matching --ease-out so canvas and DOM motion agree. */
export function easeOut(t: number): number {
  const clamped = t <= 0 ? 0 : t >= 1 ? 1 : t;
  return 1 - Math.pow(1 - clamped, 3);
}
