/**
 * FrayFuse Console — the v2 UI.
 *
 * The whole screen is one argument told in seven beats, and the beats are the
 * order the argument has to be made in:
 *
 *   01 CHAIN       here is a four-tier supply chain
 *   02 VISIBILITY  the anchor can see almost none of it
 *   03 EVIDENCE    the tier-1's own filing says it is paying late
 *   04 CASCADE     that stress propagates, wave by wave, to companies
 *                  nobody upstream has heard of
 *   05 RANK        the supplier to rescue is not the one that started it
 *   06 PATH        and this is the chain by which it reaches the anchor
 *   07 ACT         fund it, measure it, then turn the funding off
 *
 * Every figure on screen came from engine/ through api/. This file sequences
 * and arranges; it does not compute a risk number, and the cascade it animates
 * is the engine's own `propagation_depth`, revealed in order.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import './console.css';
import { STRESS_LEVELS, api, type StressStep } from './api';
import { PAPER } from './lib/bands';
import { anchorAtRisk, buildIndex, buildWaves, dependencyPath, scoresById } from './lib/derive';
import { cr, num, pct } from './lib/format';
import EvidenceSheet from './components/EvidenceSheet';
import GraphStage, { type StageMode } from './components/GraphStage';
import { Dossier, NetworkStats, Outcome, RankList, RiskStats } from './components/SidePanel';
import StoryRail, { STEPS, type StepId } from './components/StoryRail';
import WhatIfBar from './components/WhatIfBar';
import type {
  DemoScenario,
  InterveneResponse,
  NetworkPayload,
  ScoredNetwork,
} from './types';

/** Gap between propagation waves. Explanatory tier — a beat, not a UI delay. */
const WAVE_MS = 900;

const STEP_INDEX = new Map(STEPS.map((step, index) => [step.id, index]));

function BrandMark() {
  return (
    <svg className="ff-brand-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {/* An anchor at the top, two tiers below it, and one strand that has
          parted. The mark is the argument. */}
      <circle cx="12" cy="4" r="2.3" fill={PAPER.forest} />
      <circle cx="5" cy="13" r="1.7" fill={PAPER.ink} opacity="0.4" />
      <circle cx="19" cy="13" r="1.7" fill={PAPER.ink} opacity="0.4" />
      <circle cx="12" cy="21" r="2.1" fill="#8E1230" />
      <path d="M12 6.3 5 11.3M12 6.3l7 5" stroke={PAPER.ink} strokeWidth="1" opacity="0.28" />
      <path d="M5 14.7 12 18.9" stroke="#8E1230" strokeWidth="1.3" />
      <path d="M19 14.7 16 16.5" stroke="#8E1230" strokeWidth="1.3" opacity="0.5" />
    </svg>
  );
}

export default function Console() {
  const [network, setNetwork] = useState<NetworkPayload | null>(null);
  const [baseline, setBaseline] = useState<ScoredNetwork | null>(null);
  const [demo, setDemo] = useState<DemoScenario | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [step, setStep] = useState<StepId>('network');
  const [reachedIndex, setReachedIndex] = useState(0);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sheetNodeId, setSheetNodeId] = useState<string | null>(null);

  const [cascadeAt, setCascadeAt] = useState<number | null>(null);
  const [waveIndex, setWaveIndex] = useState(-1);

  const [levelIndex, setLevelIndex] = useState<number | null>(null);
  const [stressStep, setStressStep] = useState<StressStep | null>(null);
  const [scoring, setScoring] = useState(false);

  const [intervention, setIntervention] = useState<InterveneResponse | null>(null);
  const [counterfactual, setCounterfactual] = useState(false);

  // Read synchronously on the first render, then kept in state, because the
  // wave offsets are computed during render and a ref set in an effect arrives
  // one render too late: the person who asked for less motion would get all of
  // it, once, and no recompute.
  const [reducedMotion, setReducedMotion] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReducedMotion(query.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  // ---- Load ---------------------------------------------------------------

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [net, base, scenario] = await Promise.all([
          api.network(),
          api.baseline(),
          api.demoScenario(),
        ]);
        if (cancelled) return;
        setNetwork(net);
        setBaseline(base);
        setDemo(scenario);
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : String(cause));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const index = useMemo(
    () =>
      network
        ? buildIndex(network.nodes, network.edges, network.stress_signals ?? [])
        : null,
    [network],
  );

  const triggerNode = demo?.trigger_node ?? baseline?.summary.stressed_origin_nodes[0] ?? null;

  /** The slider's home position: the trigger's own filed stress. */
  const baselineLevelIndex = useMemo(() => {
    if (!baseline || !triggerNode) return STRESS_LEVELS.length - 1;
    const own = baseline.scores.find((row) => row.node_id === triggerNode)?.own_stress ?? 0;
    const exact = STRESS_LEVELS.findIndex((stop) => Math.abs(stop - own) < 1e-9);
    if (exact >= 0) return exact;
    // No exact stop means this file and refresh_web_mocks.py have drifted.
    // Land on the nearest rather than crash, and the readout stops saying
    // "as filed", so the mismatch is visible instead of silent.
    let nearest = 0;
    for (let i = 1; i < STRESS_LEVELS.length; i += 1) {
      if (Math.abs(STRESS_LEVELS[i] - own) < Math.abs(STRESS_LEVELS[nearest] - own)) nearest = i;
    }
    return nearest;
  }, [baseline, triggerNode]);

  const activeLevelIndex = levelIndex ?? baselineLevelIndex;
  const atBaselineLevel = activeLevelIndex === baselineLevelIndex;

  // ---- Which scored network the screen is reading ------------------------

  const scored = useMemo<ScoredNetwork | StressStep | null>(() => {
    if (intervention) {
      // The counterfactual is not a different calculation — it is the
      // `before` half of the same /api/intervene response.
      const half = counterfactual ? intervention.before : intervention.after;
      return { ...half, meta: baseline?.meta ?? half.meta };
    }
    if (!atBaselineLevel && stressStep) return stressStep;
    return baseline;
  }, [intervention, counterfactual, atBaselineLevel, stressStep, baseline]);

  const scores = useMemo(() => scoresById(scored?.scores ?? []), [scored]);
  const summary = scored?.summary ?? null;
  const ranking = useMemo(() => scored?.ranking ?? [], [scored]);

  const waves = useMemo(
    () => (scored && summary ? buildWaves(scored.scores, summary) : []),
    [scored, summary],
  );

  /** nodeId → ms after the cascade starts that this node lights up. */
  const arrival = useMemo(() => {
    if (waves.length === 0) return null;
    const map = new Map<string, number>();
    for (const wave of waves) {
      const offset = reducedMotion ? 0 : wave.depth * WAVE_MS;
      for (const nodeId of wave.nodeIds) map.set(nodeId, offset);
    }
    return map;
  }, [waves, reducedMotion]);

  const path = useMemo(() => {
    if (!index || !selectedId) return null;
    return dependencyPath(selectedId, index);
  }, [index, selectedId]);

  const pathNodeIds = useMemo(() => (path ? new Set(path.nodeIds) : null), [path]);
  const pathEdgeIds = useMemo(
    () => (path ? new Set(path.hops.map((hop) => hop.edge.edge_id)) : null),
    [path],
  );

  const anchor = summary ? anchorAtRisk(summary) : null;

  const triggerName = triggerNode && index ? index.nodeById.get(triggerNode)?.name ?? triggerNode : '—';

  const watchedId = demo?.expected_ranking[0] ?? ranking[0] ?? null;
  const watchedNode = watchedId && index ? index.nodeById.get(watchedId) : null;

  // ---- Cascade timing ----------------------------------------------------

  const runCascade = useCallback(() => {
    setCascadeAt(performance.now());
    // Reduced motion jumps straight to the settled state: the waves still
    // happened and the readout still names the last one, there is just nothing
    // travelling across the screen to watch.
    setWaveIndex(reducedMotion ? Math.max(waves.length - 1, 0) : 0);
  }, [reducedMotion, waves.length]);

  useEffect(() => {
    if (cascadeAt === null || waveIndex < 0) return;
    if (waveIndex >= waves.length - 1) return;
    const timer = window.setTimeout(() => setWaveIndex((current) => current + 1), WAVE_MS);
    return () => window.clearTimeout(timer);
  }, [cascadeAt, waveIndex, waves.length]);

  const cascadeRunning =
    step === 'cascade' && cascadeAt !== null && waveIndex >= 0 && waveIndex < waves.length - 1;

  // ---- Stress level ------------------------------------------------------

  const changeLevel = useCallback(
    async (nextIndex: number) => {
      if (!triggerNode) return;
      setLevelIndex(nextIndex);
      // Funding is applied against the baseline scenario, so an intervention
      // result and a re-scored trigger cannot both be on screen truthfully.
      setIntervention(null);
      setCounterfactual(false);

      if (nextIndex === baselineLevelIndex) {
        setStressStep(null);
        return;
      }
      setScoring(true);
      try {
        const next = await api.atStressLevel(triggerNode, STRESS_LEVELS[nextIndex]);
        setStressStep(next);
        setError(null);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause));
      } finally {
        setScoring(false);
      }
    },
    [triggerNode, baselineLevelIndex],
  );

  // ---- Step navigation ---------------------------------------------------

  const goTo = useCallback(
    async (next: StepId, select?: string) => {
      setStep(next);
      setReachedIndex((current) => Math.max(current, STEP_INDEX.get(next) ?? 0));

      // The funded network exists only at step 07. Stepping back used to leave
      // it on screen underneath a caption describing the unfunded one — the
      // cascade beat read "13 at risk" because the money had already landed.
      if (next !== 'act') {
        setIntervention(null);
        setCounterfactual(false);
      }

      switch (next) {
        case 'network':
        case 'visibility':
          setSheetNodeId(null);
          break;

        case 'evidence':
          setSelectedId(triggerNode);
          setSheetNodeId(triggerNode);
          break;

        case 'cascade':
          setSheetNodeId(null);
          runCascade();
          break;

        case 'rank':
          setSheetNodeId(null);
          // Arriving here without watching the cascade should still show its
          // result, so backdate the start past every wave.
          if (cascadeAt === null) {
            setCascadeAt(performance.now() - (waves.length + 2) * WAVE_MS);
            setWaveIndex(waves.length - 1);
          }
          break;

        case 'path':
          setSheetNodeId(null);
          if (cascadeAt === null) {
            setCascadeAt(performance.now() - (waves.length + 2) * WAVE_MS);
            setWaveIndex(waves.length - 1);
          }
          // Default to the top-ranked supplier, not to whatever was selected
          // last. Arriving here from the evidence beat carried the TRIGGER
          // forward, whose path to the anchor is one hop — the opposite of the
          // point this step makes, which is how far down the chain the supplier
          // that matters actually sits.
          setSelectedId(select ?? watchedId ?? ranking[0] ?? null);
          break;

        case 'act': {
          setSheetNodeId(null);
          // The funding decision is defined against the baseline, so reset the
          // what-if before applying it rather than comparing two scenarios.
          setLevelIndex(baselineLevelIndex);
          setStressStep(null);
          setCounterfactual(false);
          if (!demo) break;
          setSelectedId(demo.intervention.node_id);
          try {
            setScoring(true);
            const result = await api.intervene([demo.intervention]);
            setIntervention(result);
            setError(null);
          } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause));
          } finally {
            setScoring(false);
          }
          break;
        }
      }
    },
    [triggerNode, runCascade, cascadeAt, waves.length, watchedId, ranking, demo, baselineLevelIndex],
  );

  const restart = useCallback(() => {
    setIntervention(null);
    setCounterfactual(false);
    setStressStep(null);
    setLevelIndex(baselineLevelIndex);
    setCascadeAt(null);
    setWaveIndex(-1);
    setSelectedId(null);
    setSheetNodeId(null);
    setReachedIndex(0);
    setStep('network');
  }, [baselineLevelIndex]);

  // ---- Presentation ------------------------------------------------------

  const mode: StageMode =
    step === 'network' || step === 'evidence'
      ? 'network'
      : step === 'visibility'
        ? 'observability'
        : step === 'path'
          ? 'focus'
          : 'cascade';

  const observableCount = network?.nodes.filter((node) => node.is_observable).length ?? 0;

  const showWhatIf =
    step !== 'network' && step !== 'visibility' && step !== 'act' && summary !== null;

  const caption = (() => {
    switch (step) {
      case 'network':
        return {
          title: `${num(network?.meta.node_count ?? 0)} companies, four tiers, one anchor at the top`,
          text: 'Goods flow upward along every edge. Money — when it arrives — flows back down.',
        };
      case 'visibility':
        return {
          title: `${observableCount} of these companies publish anything`,
          text: 'Everything dimmed is a firm the anchor has no filings for. That is where the cash runs out.',
        };
      case 'evidence':
        return {
          title: `${triggerName} files its own admission`,
          text: 'The year-end ageing table and the whole-year MSMED lines do not tell the same story.',
        };
      case 'cascade':
        return {
          title: 'Stress moves against the goods, buyer to supplier',
          text: 'Each wave is one hop of propagation the engine recorded — not an effect layered on afterwards.',
        };
      case 'rank':
        return {
          title: 'The supplier that starts it is not the one to save',
          text: `${num(summary?.at_risk_count ?? 0)} suppliers are at risk. Ranked on fragility × criticality.`,
        };
      case 'path':
        return {
          title: 'One dependency chain out of 1,339',
          text: 'Everything else is dimmed. This is the chain by which a halt here reaches the anchor.',
        };
      case 'act':
        return {
          title: counterfactual ? 'Nobody funds anything' : 'One payment, re-scored',
          text: counterfactual
            ? 'This is the same network with the funding withdrawn — the engine scored it, not a slide.'
            : 'Before and after are two scoring passes over the same network in one request.',
        };
    }
  })();

  const primary = (() => {
    switch (step) {
      case 'network':
        return { label: 'See what the anchor sees', code: '02', to: 'visibility' as StepId };
      case 'visibility':
        return { label: 'Open the tier-1 filing', code: '03', to: 'evidence' as StepId };
      case 'evidence':
        return { label: 'Run the cascade', code: '04', to: 'cascade' as StepId };
      case 'cascade':
        return { label: 'Rank what it hit', code: '05', to: 'rank' as StepId };
      case 'rank':
        return { label: 'Why this supplier', code: '06', to: 'path' as StepId };
      case 'path':
        return { label: 'Fund it', code: '07', to: 'act' as StepId };
      case 'act':
        return { label: 'Start again', code: '01', to: null };
    }
  })();

  const selectedNode = selectedId && index ? index.nodeById.get(selectedId) : null;
  const sheetNode = sheetNodeId && index ? index.nodeById.get(sheetNodeId) : null;
  const sheetSignals = sheetNodeId && index ? index.signalsByNode.get(sheetNodeId) ?? [] : [];
  const sheetInheritedFrom = (() => {
    if (!sheetNodeId || !index) return null;
    const hop = dependencyPath(sheetNodeId, index).hops[0];
    return hop ? index.nodeById.get(hop.to)?.name ?? hop.to : null;
  })();

  const currentWave = waveIndex >= 0 ? waves[Math.min(waveIndex, waves.length - 1)] : null;

  const anchorBefore = intervention ? anchorAtRisk(intervention.before.summary) : null;
  // THE SAME anchor after, found by id.
  //
  // `anchor_disruption` is sorted by disruption descending and the order moves
  // once funding lands: N001 leads before, and afterwards another anchor can
  // edge past it. Taking [0] from each list pairs one company's before with
  // another's after and prints a figure that belongs to neither — and names a
  // third. The name comes from `anchorBefore` for the same reason.
  const anchorAfterSame =
    intervention && anchorBefore
      ? (intervention.after.summary.anchor_disruption ?? []).find(
          (row) => row.node_id === anchorBefore.node_id,
        ) ?? null
      : null;
  const anchorPairName =
    anchorBefore && index
      ? index.nodeById.get(anchorBefore.node_id)?.name ?? anchorBefore.node_id
      : null;

  const reached = new Set(
    STEPS.filter((_, position) => position <= reachedIndex).map((entry) => entry.id),
  );

  if (error && !network) {
    return (
      <div className="ff-shell">
        <div className="ff-error">
          <strong>Could not load the network.</strong> {error}
          <br />
          {api.live
            ? 'Running in live mode — start the API with uvicorn api.main:app --port 8000.'
            : 'Running against committed mocks — re-run python scripts/refresh_web_mocks.py.'}
        </div>
      </div>
    );
  }

  return (
    <div className="ff-shell">
      <header className="ff-topbar">
        <div className="ff-brand">
          <BrandMark />
          <span className="ff-brand-name">
            Fray<span>Fuse</span>
          </span>
          <span className="ff-dataset">
            {api.live ? 'live engine' : 'committed engine output'} · schema{' '}
            {network?.meta.schema_version ?? '—'}
          </span>
        </div>

        <button
          className="ff-primary"
          onClick={() => (primary.to ? goTo(primary.to) : restart())}
          disabled={scoring && step === 'act'}
        >
          <span className="ff-primary-disc" aria-hidden="true">
            {primary.code}
          </span>
          {primary.label}
        </button>

        <div className="ff-topbar-right">
          <span>
            {num(network?.meta.node_count ?? 0)} nodes · {num(network?.meta.edge_count ?? 0)} edges
          </span>
          {step !== 'network' && (
            <button className="ff-ghost" onClick={restart}>
              Reset
            </button>
          )}
        </div>
      </header>

      <div className="ff-body">
        <StoryRail
          current={step}
          reached={reached}
          summary={summary}
          showBands={step !== 'network' && step !== 'visibility'}
          onSelect={goTo}
        />

        <main className="ff-stage">
          {network && index ? (
            <GraphStage
              nodes={network.nodes}
              edges={network.edges}
              scores={scores}
              mode={mode}
              arrival={mode === 'cascade' || mode === 'focus' ? arrival : null}
              cascadeStartedAt={cascadeAt}
              pathNodeIds={pathNodeIds}
              pathEdgeIds={pathEdgeIds}
              selectedId={selectedId}
              triggerNode={triggerNode}
              bottomInset={(showWhatIf ? 112 : 0) + (step === 'cascade' || step === 'path' ? 76 : 0)}
              onSelect={setSelectedId}
            />
          ) : (
            <div className="ff-boot">Loading the chain…</div>
          )}

          <div className="ff-stage-overlay" data-bar={showWhatIf ? 'true' : undefined}>
            <div className="ff-stage-caption">
              <h2>{caption.title}</h2>
              <p>{caption.text}</p>
            </div>

            {step === 'cascade' && currentWave && (
              <div className="ff-wave" role="status">
                {cascadeRunning && <span className="ff-wave-pip" />}
                <span className="ff-wave-text">
                  <span className="ff-wave-title">
                    {currentWave.depth === 0
                      ? `Origin — ${currentWave.nodeIds
                          .map((id) => index?.nodeById.get(id)?.name ?? id)
                          .join(', ')}`
                      : `Hop ${currentWave.depth} — ${num(currentWave.nodeIds.length)} suppliers reached`}
                  </span>
                  <span className="ff-wave-sub">
                    {currentWave.depth === 0
                      ? 'own_stress, read from its own filings'
                      : `propagation_depth ${currentWave.depth} · scaled by revenue dependency, damped per hop`}
                    {!cascadeRunning && anchor
                      ? ` · anchor inflow at risk ${cr(anchor.disrupted_inflow_cr, 0)}`
                      : ''}
                  </span>
                </span>
              </div>
            )}

            {step === 'path' && path && selectedNode && (
              <div className="ff-focus">
                <span className="ff-path">
                  {path.nodeIds.map((nodeId, position) => {
                    const node = index?.nodeById.get(nodeId);
                    const hop = path.hops[position];
                    return (
                      <span key={nodeId} style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
                        <span className="ff-path-node">
                          <span className="ff-path-id">{nodeId}</span>
                          <span className="ff-path-name">{node?.name ?? ''}</span>
                        </span>
                        {hop && (
                          <span
                            className="ff-path-arrow"
                            data-sole={hop.edge.is_single_source === true ? 'true' : undefined}
                            title={`${hop.edge.component.replace(/_/g, ' ')} · ${pct(
                              hop.edge.exposure_pct,
                            )} of supplier revenue · ${cr(hop.edge.annual_value_cr)}`}
                          >
                            →
                          </span>
                        )}
                      </span>
                    );
                  })}
                </span>
                <span className="ff-focus-note">
                  {path.reachesAnchor
                    ? 'The chain a halt here travels along to reach the anchor. Edges point the way goods move; stress moved the other way to get here.'
                    : 'This chain does not terminate at an anchor in this dataset.'}
                </span>
              </div>
            )}
          </div>

          {showWhatIf && summary && watchedNode && (
            <WhatIfBar
              triggerName={triggerName}
              levelIndex={activeLevelIndex}
              baselineIndex={baselineLevelIndex}
              busy={scoring}
              summary={summary}
              watchedName={watchedNode.name}
              watchedBand={watchedId ? scores.get(watchedId)?.risk_band : undefined}
              anchorInflow={anchor?.disrupted_inflow_cr ?? null}
              onChange={changeLevel}
            />
          )}
        </main>

        <aside className="ff-side">
          {error && network && <div className="ff-error">{error}</div>}

          {step === 'network' || step === 'visibility' ? (
            network && <NetworkStats meta={network.meta} nodes={network.nodes} />
          ) : (
            summary && <RiskStats summary={summary} />
          )}

          {intervention && demo && index && (
            <Outcome
              delta={intervention.delta}
              fundedName={index.nodeById.get(demo.intervention.node_id)?.name ?? demo.intervention.node_id}
              fundedAmount={demo.intervention.amount_cr}
              anchorBefore={anchorBefore}
              anchorAfter={anchorAfterSame}
              anchorName={anchorPairName}
              nodeById={index.nodeById}
              counterfactual={counterfactual}
              onToggleCounterfactual={() => setCounterfactual((current) => !current)}
            />
          )}

          {selectedNode && index && (
            <Dossier
              node={selectedNode}
              score={scores.get(selectedNode.node_id)}
              hasFilings={(index.signalsByNode.get(selectedNode.node_id) ?? []).length > 0}
              onEvidence={() => setSheetNodeId(selectedNode.node_id)}
            />
          )}

          {step !== 'network' && step !== 'visibility' && index && (
            <RankList
              ranking={ranking}
              scores={scores}
              nodeById={index.nodeById}
              selectedId={selectedId}
              onSelect={(nodeId) => {
                setSelectedId(nodeId);
                if (step === 'rank') goTo('path', nodeId);
              }}
            />
          )}
        </aside>
      </div>

      {sheetNode && (
        <EvidenceSheet
          node={sheetNode}
          signals={sheetSignals}
          score={scores.get(sheetNode.node_id)}
          inheritedFrom={sheetInheritedFrom}
          onClose={() => setSheetNodeId(null)}
        />
      )}
    </div>
  );
}
