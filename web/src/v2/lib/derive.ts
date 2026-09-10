/**
 * Derivations the UI needs and the API does not return.
 *
 * The rule for this file: it may only *arrange* engine output — index it,
 * group it, walk it. It may not score anything. Every number that reaches the
 * screen was computed by engine/, and the moment this file starts averaging or
 * weighting, the figures on stage stop being the engine's.
 */

import type { Edge, Node, Score, StressSignal, Summary } from '../types';

export interface NetworkIndex {
  nodeById: Map<string, Node>;
  /** Edges leaving a node towards its buyers (goods direction). */
  bySupplier: Map<string, Edge[]>;
  /** Edges arriving from a node's suppliers. */
  byBuyer: Map<string, Edge[]>;
  signalsByNode: Map<string, StressSignal[]>;
}

export function buildIndex(
  nodes: Node[],
  edges: Edge[],
  signals: StressSignal[] = [],
): NetworkIndex {
  const nodeById = new Map(nodes.map((node) => [node.node_id, node]));
  const bySupplier = new Map<string, Edge[]>();
  const byBuyer = new Map<string, Edge[]>();

  for (const edge of edges) {
    const out = bySupplier.get(edge.supplier_id);
    if (out) out.push(edge);
    else bySupplier.set(edge.supplier_id, [edge]);

    const inbound = byBuyer.get(edge.buyer_id);
    if (inbound) inbound.push(edge);
    else byBuyer.set(edge.buyer_id, [edge]);
  }

  const signalsByNode = new Map<string, StressSignal[]>();
  for (const signal of signals) {
    const rows = signalsByNode.get(signal.node_id);
    if (rows) rows.push(signal);
    else signalsByNode.set(signal.node_id, [signal]);
  }
  // Oldest first, so "previous" and "latest" are the last two entries and the
  // ledger reads left to right the way a filing prints it.
  for (const rows of signalsByNode.values()) {
    rows.sort((a, b) => a.fy.localeCompare(b.fy));
  }

  return { nodeById, bySupplier, byBuyer, signalsByNode };
}

// ---------------------------------------------------------------------------
// Dependency path
// ---------------------------------------------------------------------------

export interface PathHop {
  edge: Edge;
  /** The buyer this hop arrives at. */
  to: string;
}

export interface DependencyPath {
  nodeIds: string[];
  hops: PathHop[];
  /** True once the walk actually reached a tier-0 anchor. */
  reachesAnchor: boolean;
}

/**
 * The chain of dependencies from `startId` up to the anchor.
 *
 * DIRECTION MATTERS AND IS EASY TO GET BACKWARDS. Edges are stored
 * supplier → buyer, which is how goods move. Payment stress moves the other
 * way, buyer → supplier, following the money that never arrived. What this
 * function walks is the goods direction, because the question it answers is
 * "whose line stops when this supplier stops delivering" — so it is the
 * *disruption* path, not the stress path, and the UI labels it that way. Never
 * describe it to an audience as the direction stress travelled.
 *
 * At each hop it takes the buyer this supplier depends on most, by
 * `exposure_pct` — the share of the supplier's own revenue riding on that
 * customer, which SCHEMA.md calls the single most important number in the
 * model. Ties break on annual value then edge id, so the path is the same on
 * every run; a demo path that moves between clicks is not a demo.
 */
export function dependencyPath(
  startId: string,
  index: NetworkIndex,
  maxHops = 8,
): DependencyPath {
  const nodeIds = [startId];
  const hops: PathHop[] = [];
  const seen = new Set([startId]);

  let current = startId;
  let reachesAnchor = index.nodeById.get(startId)?.tier === 0;

  while (hops.length < maxHops && !reachesAnchor) {
    const candidates = (index.bySupplier.get(current) ?? []).filter(
      (edge) => !seen.has(edge.buyer_id),
    );
    if (candidates.length === 0) break;

    candidates.sort(
      (a, b) =>
        b.exposure_pct - a.exposure_pct ||
        b.annual_value_cr - a.annual_value_cr ||
        a.edge_id.localeCompare(b.edge_id),
    );

    const next = candidates[0];
    hops.push({ edge: next, to: next.buyer_id });
    nodeIds.push(next.buyer_id);
    seen.add(next.buyer_id);
    current = next.buyer_id;
    reachesAnchor = index.nodeById.get(next.buyer_id)?.tier === 0;
  }

  return { nodeIds, hops, reachesAnchor };
}

// ---------------------------------------------------------------------------
// Cascade waves
// ---------------------------------------------------------------------------

export interface Wave {
  depth: number;
  nodeIds: string[];
}

/**
 * Group the affected nodes into propagation waves.
 *
 * `propagation_depth` is already on every score — the engine recorded how many
 * hops from an origin each node's stress arrived through. The animation reveals
 * those groups in order; it does not re-derive them, and there is no second
 * propagation running in the browser.
 *
 * The one subtlety: depth 0 covers both the stressed origins and the 266 nodes
 * stress never reached, because untouched nodes were never assigned a depth.
 * `fragility > 0` separates them.
 */
export function buildWaves(scores: Score[], summary: Summary): Wave[] {
  const origins = new Set(summary.stressed_origin_nodes ?? []);
  const byDepth = new Map<number, string[]>();

  for (const score of scores) {
    const touched = score.fragility > 0 || origins.has(score.node_id);
    if (!touched) continue;
    // An origin is wave 0 whatever depth it carries; anything else touched at
    // depth 0 would be an engine surprise, and folding it into wave 0 shows it
    // rather than dropping it off the screen.
    const depth = origins.has(score.node_id) ? 0 : score.propagation_depth;
    const bucket = byDepth.get(depth);
    if (bucket) bucket.push(score.node_id);
    else byDepth.set(depth, [score.node_id]);
  }

  return [...byDepth.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([depth, nodeIds]) => ({ depth, nodeIds: nodeIds.sort() }));
}

/**
 * Failure travelling the other way: the chain that ends at the anchor.
 *
 * `summary.anchor_disruption[i].stopped_by` names the supplier whose halt
 * stops that anchor's line, and each score carries its own
 * `disruption_reason`. This returns the anchor and its blocker so the closing
 * beat can name both without the UI guessing at either.
 */
export function anchorAtRisk(summary: Summary) {
  const list = summary.anchor_disruption ?? [];
  if (list.length === 0) return null;
  // Already sorted by disruption descending, but sort defensively: the order
  // changes once an intervention lands, and reading [0] from two differently
  // ordered lists is how you pair one anchor's before with another's after.
  return [...list].sort((a, b) => b.supply_disruption - a.supply_disruption)[0];
}

export function scoresById(scores: Score[]): Map<string, Score> {
  return new Map(scores.map((score) => [score.node_id, score]));
}

// ---------------------------------------------------------------------------
// Trigger selection
// ---------------------------------------------------------------------------

/**
 * Which stressed origin the walkthrough should tell the story about.
 *
 * On the committed network this is answered by the fixture and this function
 * is never called. An INGESTED network has no fixture, and the engine hands
 * back a list of origins rather than one — the real collection produces nine,
 * five of them anchors. Taking `stressed_origin_nodes[0]` picked N005, a
 * TIER-0 sugar company whose own filing says nothing moved, and the evidence
 * beat ("the tier-1's own filing admits it is paying late") then opened on a
 * filing that admitted nothing.
 *
 * The origin worth naming is the one the supplier we are about to rescue
 * actually depends on, so that is what this looks for: walk the top-ranked
 * supplier's dependency path upward and take the first stressed origin on it.
 * That single choice makes steps 03, 04, 05 and 06 describe one chain instead
 * of three unrelated ones.
 *
 * Fallbacks, in order: the most-stressed origin that is not an anchor (an
 * anchor is the company being protected, not the company under strain), then
 * whatever the engine listed first, so this can always answer.
 */
export function pickTrigger(
  ranking: string[],
  scores: Map<string, Score>,
  summary: Summary,
  index: NetworkIndex,
): string | null {
  const origins = summary.stressed_origin_nodes ?? [];
  if (origins.length === 0) return null;
  if (origins.length === 1) return origins[0];

  const originSet = new Set(origins);
  const top = ranking[0];
  if (top) {
    for (const nodeId of dependencyPath(top, index).nodeIds) {
      if (nodeId !== top && originSet.has(nodeId)) return nodeId;
    }
  }

  const suppliers = origins.filter((nodeId) => (index.nodeById.get(nodeId)?.tier ?? 0) > 0);
  const pool = suppliers.length > 0 ? suppliers : origins;
  return [...pool].sort(
    (a, b) =>
      (scores.get(b)?.own_stress ?? 0) - (scores.get(a)?.own_stress ?? 0) || a.localeCompare(b),
  )[0];
}
