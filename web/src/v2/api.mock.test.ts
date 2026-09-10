/**
 * The offline path, exercised.
 *
 * `npm run dev` is what gets demoed when the venue's network misbehaves, so
 * every control has to work with the backend switched off. The Python suite
 * validates the committed mocks against schema.json; this checks the lookups
 * the client performs on them, which is the half that breaks silently — a
 * budget stop with no committed run, or a node with no committed plan, is a
 * dead button that only shows itself when somebody presses it.
 */

import { describe, expect, it } from 'vitest';

import { BUDGET_LEVELS, api } from './api';
import type { ScoredNetwork } from './types';

describe('offline decision layer', () => {
  it('has a plan for every node the graph can select', async () => {
    const baseline = (await api.baseline()) as ScoredNetwork;
    const sample = [
      baseline.ranking[0],
      baseline.summary.stressed_origin_nodes[0],
      baseline.scores[0].node_id,
      baseline.scores[baseline.scores.length - 1].node_id,
    ];

    for (const nodeId of sample) {
      const plan = await api.derisk(nodeId);
      expect(plan.node_id).toBe(nodeId);
      expect(plan.headline.length).toBeGreaterThan(10);
      expect(plan.review_triggers.length).toBeGreaterThan(0);
    }
  });

  it('never recommends money for a supplier that is not in the funding queue', async () => {
    const baseline = (await api.baseline()) as ScoredNetwork;
    const origin = baseline.summary.stressed_origin_nodes[0];
    const plan = await api.derisk(origin);

    expect(plan.queue).toBe('origin');
    // null, not 0 — money is not the answer here, which is a different fact
    // from a zero-rupee requirement.
    expect(plan.recommended_action.amount_cr ?? null).toBeNull();
  });

  it('has a committed allocation for every budget stop the UI offers', async () => {
    for (const budget of BUDGET_LEVELS) {
      const run = await api.allocate(budget);
      expect(run.budget_cr).toBe(budget);
      expect(run.allocated_cr).toBeLessThanOrEqual(budget + 1e-9);
      expect(run.allocated_cr + run.unallocated_cr).toBeCloseTo(budget, 6);
    }
  });

  it('spends more usefully than it spends', async () => {
    const run = await api.allocate(5);
    expect(run.allocations.length).toBeGreaterThan(1);
    expect(run.objective.reduced_cr).toBeGreaterThan(run.allocated_cr);
    expect(run.delta.nodes_worsened).toBe(0);
  });

  it('names the one supplier offline funding can replay', async () => {
    const fundable = await api.fundable();
    const demo = await api.demoScenario();
    expect(fundable).toBe(demo.intervention.node_id);
  });
});
