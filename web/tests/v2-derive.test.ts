/**
 * Tests for the v2 console's derivations, run against the committed engine
 * output rather than hand-built fixtures.
 *
 * These functions may only ARRANGE engine output — index it, group it, walk
 * it. The assertions here are mostly about that boundary holding: the waves
 * must be the engine's own `propagation_depth`, and the path must be the
 * network's own edges. If a future change starts computing a figure in the
 * browser, the counts below stop matching what the pipeline prints.
 */

import { describe, expect, test } from 'vitest';
import network from '../src/mocks/network.json';
import baseline from '../src/mocks/simulate.json';
import sweep from '../src/mocks/simulate-sweep.json';
import demo from '../src/mocks/demo-scenario.json';
import { anchorAtRisk, buildIndex, buildWaves, dependencyPath } from '../src/v2/lib/derive';
import { STRESS_LEVELS } from '../src/v2/api';
import type { Edge, Node, Score, StressSignal, Summary } from '../src/v2/types';

const index = buildIndex(
  network.nodes as unknown as Node[],
  network.edges as unknown as Edge[],
  (network.stress_signals ?? []) as unknown as StressSignal[],
);

const scores = baseline.scores as unknown as Score[];
const summary = baseline.summary as unknown as Summary;

describe('network index', () => {
  test('every edge endpoint resolves to a node', () => {
    for (const edge of network.edges as unknown as Edge[]) {
      expect(index.nodeById.has(edge.supplier_id)).toBe(true);
      expect(index.nodeById.has(edge.buyer_id)).toBe(true);
    }
  });

  test('GET /api/network carries the stress signals the evidence panel needs', () => {
    // Optional and additive in schema 1.2. If it ever goes missing the panel
    // has nothing to show but a score, which is the thing it exists to avoid.
    expect((network.stress_signals ?? []).length).toBeGreaterThan(0);
    const trigger = index.signalsByNode.get(demo.trigger_node) ?? [];
    expect(trigger.length).toBeGreaterThanOrEqual(2);
    // Oldest first, so "previous" and "latest" are the last two entries.
    expect(trigger[0].fy < trigger[trigger.length - 1].fy).toBe(true);
  });
});

describe('cascade waves', () => {
  const waves = buildWaves(scores, summary);

  test('wave 0 is exactly the engine-reported stressed origins', () => {
    expect(waves[0].depth).toBe(0);
    expect(waves[0].nodeIds).toEqual([...summary.stressed_origin_nodes].sort());
  });

  test('waves run to the engine-reported maximum depth, with no gaps', () => {
    expect(waves.map((wave) => wave.depth)).toEqual(
      Array.from({ length: summary.max_propagation_depth + 1 }, (_, depth) => depth),
    );
  });

  test('untouched nodes are in no wave, so they stay unlit', () => {
    const inAWave = new Set(waves.flatMap((wave) => wave.nodeIds));
    const untouched = scores.filter((score) => !inAWave.has(score.node_id));
    expect(untouched.length).toBeGreaterThan(0);
    for (const score of untouched) expect(score.fragility).toBe(0);
  });
});

describe('dependency path', () => {
  test('the demo supplier reaches the anchor through the demo chain', () => {
    const path = dependencyPath(demo.expected_ranking[0], index);
    expect(path.reachesAnchor).toBe(true);
    expect(path.nodeIds[0]).toBe(demo.expected_ranking[0]);
    expect(path.nodeIds).toContain(demo.trigger_node);
    expect(path.nodeIds[path.nodeIds.length - 1]).toBe(demo.counterfactual_anchor);
    expect(index.nodeById.get(path.nodeIds[path.nodeIds.length - 1])?.tier).toBe(0);
  });

  test('every hop is a real edge, in the goods direction', () => {
    const path = dependencyPath(demo.expected_ranking[0], index);
    path.hops.forEach((hop, position) => {
      expect(hop.edge.supplier_id).toBe(path.nodeIds[position]);
      expect(hop.edge.buyer_id).toBe(path.nodeIds[position + 1]);
    });
  });

  test('it is deterministic — a demo path that moves between clicks is not a demo', () => {
    const first = dependencyPath(demo.expected_ranking[0], index);
    const second = dependencyPath(demo.expected_ranking[0], index);
    expect(second.nodeIds).toEqual(first.nodeIds);
  });

  test('an anchor is its own path and terminates immediately', () => {
    const path = dependencyPath(demo.counterfactual_anchor, index);
    expect(path.nodeIds).toEqual([demo.counterfactual_anchor]);
    expect(path.hops).toEqual([]);
  });
});

describe('anchor pairing', () => {
  test('the worst-hit anchor is picked by disruption, not by list position', () => {
    const worst = anchorAtRisk(summary);
    expect(worst).not.toBeNull();
    for (const row of summary.anchor_disruption ?? []) {
      expect(worst!.supply_disruption).toBeGreaterThanOrEqual(row.supply_disruption);
    }
  });
});

describe('committed stress sweep', () => {
  test('it carries a step for every slider stop', () => {
    expect(sweep.steps.map((step) => step.own_stress)).toEqual([...STRESS_LEVELS]);
    expect(sweep.trigger_node).toBe(demo.trigger_node);
  });

  test('each step scores the whole network, reasons included', () => {
    // A field whitelist here once dropped reason_text, so mock mode silently
    // lost every explanation the live API returns. Both modes must agree.
    for (const step of sweep.steps) {
      expect(step.scores.length).toBe(network.nodes.length);
      const ranked = step.ranking[0];
      if (!ranked) continue;
      const top = step.scores.find((score) => score.node_id === ranked);
      expect(top?.reason_text).toBeTruthy();
      expect(top?.reason_factors?.length).toBeGreaterThan(0);
    }
  });

  test('the trigger override is what the engine actually scored', () => {
    for (const step of sweep.steps) {
      const trigger = step.scores.find((score) => score.node_id === sweep.trigger_node);
      expect(trigger?.own_stress).toBeCloseTo(step.own_stress, 6);
    }
  });

  test('more trigger stress never means less exposure', () => {
    // Monotonicity is a property of the engine, not of this file — but the
    // slider's whole claim is "worse in, worse out", so it is worth asserting
    // that the committed steps really do behave that way.
    const exposures = sweep.steps.map((step) => step.summary.total_estimated_exposure_cr);
    for (let i = 1; i < exposures.length; i += 1) {
      expect(exposures[i]).toBeGreaterThanOrEqual(exposures[i - 1]);
    }
  });

  test('the slider opens on a stop the sweep actually contains', () => {
    const own = scores.find((score) => score.node_id === demo.trigger_node)?.own_stress;
    expect(own).toBeDefined();
    expect(STRESS_LEVELS.some((stop) => Math.abs(stop - own!) < 1e-9)).toBe(true);
  });
});
