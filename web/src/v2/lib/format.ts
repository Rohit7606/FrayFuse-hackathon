/**
 * Number formatting.
 *
 * All money is in INR crore — `meta.currency_unit` says so and no endpoint
 * ever mixes units. Figures are printed at the precision the engine returned;
 * rounding a ₹2.04 cr intervention to ₹2 cr on stage invites the one question
 * you cannot answer, which is what the other four lakh were.
 */

const CRORE = '₹'; // ₹

export function cr(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${CRORE}${value.toLocaleString('en-IN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} cr`;
}

/** Whole crore, for headline figures where the paise are noise. */
export function crRound(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${CRORE}${Math.round(value).toLocaleString('en-IN')} cr`;
}

export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

/** Engine scores live in [0, 1] and are narrow — three decimals, not two. */
export function score(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toFixed(3);
}

export function num(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toLocaleString('en-IN');
}

/**
 * A year-on-year change, and the three cases are genuinely different facts.
 *
 * `null` means undisclosed, and an undisclosed line has no direction — it must
 * not read as 0% (AGENTS.md §3.6). A rise from nil is not a ratio, so it says
 * "new" rather than a division by zero dressed up as a percentage.
 */
export type Direction = 'up' | 'down' | 'flat';

export function yoy(
  previous: number | null | undefined,
  latest: number | null | undefined,
): { label: string; dir: Direction } | null {
  if (previous === null || previous === undefined) return null;
  if (latest === null || latest === undefined) return null;

  if (previous === 0) {
    if (latest === 0) return { label: 'nil both years', dir: 'flat' };
    return { label: 'new this year', dir: 'up' };
  }

  const change = (latest - previous) / previous;
  if (Math.abs(change) < 0.005) return { label: 'unchanged', dir: 'flat' };

  const dir: Direction = change > 0 ? 'up' : 'down';
  const sign = change > 0 ? '+' : '−';
  return { label: `${sign}${Math.abs(change * 100).toFixed(0)}%`, dir };
}

/** Multiple, the way the engine's own reason text puts it ("rose 2.1x"). */
export function times(
  previous: number | null | undefined,
  latest: number | null | undefined,
): string | null {
  if (!previous || latest === null || latest === undefined) return null;
  const ratio = latest / previous;
  if (!Number.isFinite(ratio) || ratio <= 1) return null;
  return `${ratio.toFixed(1)}x`;
}

/**
 * A company name short enough to sit inside a control label.
 *
 * Drops the legal suffix only. It never abbreviates the distinguishing part of
 * a name, because "Sealsworks" and "Sealsworks Rubber" must not become the
 * same string on a screen that is naming a specific filer.
 */
export function shortName(name: string): string {
  return name
    .replace(/\s+(Private\s+Limited|Pvt\.?\s+Ltd\.?|Limited|Ltd\.?|LLP|Inc\.?)$/i, '')
    .trim();
}
