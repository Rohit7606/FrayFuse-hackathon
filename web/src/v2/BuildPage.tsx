/**
 * The live build — a zip of filings becoming a scored supply chain.
 *
 * The judges asked to see the graph constructed from uploaded source documents
 * rather than read from a committed JSON file, so this is its own page rather
 * than a step inside the console: nothing here is about risk yet, and mixing it
 * into the walkthrough would blur the one thing it exists to show.
 *
 * WHAT IS AND IS NOT HAPPENING, because the difference matters and a judge may
 * well ask. The archive is processed in a single pass on the server and comes
 * back complete — `score_network()` is a pure function over a whole network and
 * stays that way (AGENTS.md §1.5, §3.1). Nothing streams. What this page
 * animates is the *reveal* of a finished result, in the order the work
 * actually happened, and the page says so on screen rather than dressing a
 * completed job up as a progress bar.
 *
 * MOTION (animate skill):
 *   Frequency  rare / first-time — the delight budget lives here.
 *   Purpose    EXPLANATION. "We built this from filings" is the one claim the
 *              product cannot make in text without sounding like an assertion.
 *   Tool       the existing canvas draw loop for the graph (per-node alpha and
 *              radius off one reveal ramp), CSS transitions for the log.
 *   Curve      ease-out throughout, matching --ease-out.
 *   Two beats  structure first, colour second. The skeleton assembles in ink;
 *              risk only resolves once it is whole, in the console.
 *   Interrupt  a click anywhere, or the skip control, jumps to the finished
 *              graph. Nobody is ever made to wait for choreography.
 *   Reduced    prefers-reduced-motion goes straight to the completed graph with
 *              every figure filled in. Fewer and gentler, not nothing.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api';
import GraphStage from './components/GraphStage';
import { cr, num } from './lib/format';
import type { IngestReport, IngestResponse, Node } from './types';

/** Gap between one tier appearing and the next. */
const TIER_MS = 850;
/** The whole stagger inside one tier, however many nodes it holds. */
const TIER_SPREAD_MS = 620;
/** Gap between two lines of the ingest log. */
const LOG_MS = 420;

interface Stage {
  id: string;
  label: string;
  value: (report: IngestReport, response: IngestResponse) => string;
  note: string;
}

/**
 * The pass the server made, in the order it made it.
 *
 * Every figure is read off the ingest report — there is no counter here that
 * the backend did not produce.
 */
const STAGES: Stage[] = [
  {
    id: 'read',
    label: 'Read the archive',
    value: (report) => `${num(report.files_seen.length)} files`,
    note: 'Unpacked offline, into a temporary directory. Nothing was fetched.',
  },
  {
    id: 'classify',
    label: 'Recognised the collection CSVs',
    value: (report) => `${num(Object.keys(report.files_used).length)} of ${num(report.files_seen.length)}`,
    note: 'Matched by filename, then by header signature. The rest rode along ignored.',
  },
  {
    id: 'parse',
    label: 'Parsed the rows',
    value: (report) =>
      `${num(Object.values(report.rows_parsed).reduce((sum, count) => sum + count, 0))} rows`,
    note: 'The same transform the committed dataset was built with.',
  },
  {
    id: 'companies',
    label: 'Mapped the companies',
    value: (report) => `${num(report.companies_read)} filers`,
    note: 'Real companies, named in their own filings.',
  },
  {
    id: 'disclosure',
    label: 'Read what they disclosed',
    value: (report) => `${num(report.fields_present)} filled, ${num(report.fields_null)} blank`,
    note: 'A blank field stays null. Nothing was estimated to fill a gap.',
  },
  {
    id: 'deeptier',
    label: 'Generated the deep tier',
    value: (report) => `${num(report.generated_nodes)} nodes`,
    note: 'Named from a fictional entity pool. These are not real businesses, and the graph marks them.',
  },
  {
    id: 'edges',
    label: 'Linked the relationships',
    value: (report) => `${num(report.edges_built)} edges`,
    note: 'Supplier to buyer, the direction goods move.',
  },
  {
    id: 'score',
    label: 'Scored the network',
    value: (_report, response) => `${num(response.summary.at_risk_count)} at risk`,
    note: 'Stress, contagion, criticality, ranking — unchanged by any of this.',
  },
];

type Phase = 'idle' | 'reading' | 'log' | 'building' | 'done';

interface Props {
  onEnterConsole: (result: IngestResponse) => void;
  onUseCommittedNetwork: () => void;
}

export default function BuildPage({ onEnterConsole, onUseCommittedNetwork }: Props) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logIndex, setLogIndex] = useState(-1);
  const [dragging, setDragging] = useState(false);
  const [buildStartedAt, setBuildStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  const [reducedMotion, setReducedMotion] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReducedMotion(query.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  // ---- Upload -------------------------------------------------------------

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setPhase('reading');
      try {
        const response = await api.ingest(file);
        setResult(response);
        if (reducedMotion) {
          setLogIndex(STAGES.length - 1);
          setBuildStartedAt(performance.now() - 10_000);
          setPhase('done');
        } else {
          setLogIndex(0);
          setPhase('log');
        }
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause));
        setPhase('idle');
      }
    },
    [reducedMotion],
  );

  // ---- The log reveals, then the graph builds ------------------------------

  useEffect(() => {
    if (phase !== 'log') return;
    if (logIndex >= STAGES.length - 1) {
      const start = window.setTimeout(() => {
        setBuildStartedAt(performance.now());
        setPhase('building');
      }, LOG_MS);
      return () => window.clearTimeout(start);
    }
    const next = window.setTimeout(() => setLogIndex((current) => current + 1), LOG_MS);
    return () => window.clearTimeout(next);
  }, [phase, logIndex]);

  /** nodeId → ms after the build starts that this node lands. */
  const arrival = useMemo(() => {
    if (!result) return null;
    const byTier = new Map<number, Node[]>();
    for (const node of result.nodes) {
      const bucket = byTier.get(node.tier);
      if (bucket) bucket.push(node);
      else byTier.set(node.tier, [node]);
    }

    const map = new Map<string, number>();
    const tiers = [...byTier.keys()].sort((a, b) => a - b);
    tiers.forEach((tier, tierIndex) => {
      // Sorted, so the same archive builds in the same order every time — a
      // demo whose graph assembles differently on the second run is not a demo.
      const nodes = [...(byTier.get(tier) ?? [])].sort((a, b) =>
        a.node_id.localeCompare(b.node_id),
      );
      const step = nodes.length > 1 ? TIER_SPREAD_MS / (nodes.length - 1) : 0;
      nodes.forEach((node, index) => {
        map.set(node.node_id, tierIndex * TIER_MS + index * step);
      });
    });
    return map;
  }, [result]);

  const buildDuration = useMemo(() => {
    if (!arrival || arrival.size === 0) return 0;
    return Math.max(...arrival.values()) + 700;
  }, [arrival]);

  // A frame loop while the graph assembles, so the counters count something
  // real: they read the same arrival map the canvas is painting from.
  useEffect(() => {
    if (phase !== 'building' || buildStartedAt === null) return;
    let raf = 0;
    const tick = () => {
      const now = performance.now() - buildStartedAt;
      setElapsed(now);
      if (now >= buildDuration) {
        setPhase('done');
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase, buildStartedAt, buildDuration]);

  /** Jump to the finished graph. Nobody waits for choreography. */
  const skip = useCallback(() => {
    if (!result) return;
    setLogIndex(STAGES.length - 1);
    setBuildStartedAt(performance.now() - buildDuration - 1000);
    setElapsed(buildDuration);
    setPhase('done');
  }, [result, buildDuration]);

  // ---- Live counters ------------------------------------------------------

  const placed = useMemo(() => {
    if (!arrival || !result) return { nodes: 0, edges: 0, value: 0 };
    if (phase === 'done') {
      return {
        nodes: result.nodes.length,
        edges: result.edges.length,
        value: result.edges.reduce((sum, edge) => sum + edge.annual_value_cr, 0),
      };
    }
    const live = new Set<string>();
    for (const [nodeId, offset] of arrival) {
      if (offset <= elapsed) live.add(nodeId);
    }
    let edges = 0;
    let value = 0;
    for (const edge of result.edges) {
      if (live.has(edge.supplier_id) && live.has(edge.buyer_id)) {
        edges += 1;
        value += edge.annual_value_cr;
      }
    }
    return { nodes: live.size, edges, value };
  }, [arrival, result, elapsed, phase]);

  const report = result?.ingest_report ?? null;
  const visibleStages = STAGES.slice(0, Math.max(0, logIndex + 1));

  // ---- Render -------------------------------------------------------------

  return (
    <div className="ff-shell">
      <header className="ff-topbar">
        <div className="ff-brand">
          <span className="ff-brand-name">FrayFuse</span>
          <span className="ff-dataset">
            {api.live ? 'live ingest' : 'committed ingest output'} · offline, no lookups
          </span>
        </div>

        <button
          className="ff-primary"
          onClick={() => {
            if (result && phase === 'done') onEnterConsole(result);
            else if (phase === 'log' || phase === 'building') skip();
            else fileRef.current?.click();
          }}
          disabled={phase === 'reading'}
        >
          <span className="ff-primary-disc" aria-hidden="true">
            {phase === 'done' ? '→' : phase === 'log' || phase === 'building' ? '»' : '↑'}
          </span>
          {phase === 'done'
            ? 'Open the console'
            : phase === 'reading'
              ? 'Reading…'
              : phase === 'log' || phase === 'building'
                ? 'Skip to the finished graph'
                : 'Choose a zip'}
        </button>

        <div className="ff-topbar-right">
          <button className="ff-ghost" onClick={onUseCommittedNetwork}>
            Use committed network
          </button>
        </div>
      </header>

      <div className="ff-body">
        <nav className="ff-rail" aria-label="Ingest log">
          <div className="ff-rail-head">
            <div className="ff-rail-title">Ingest log</div>
            <div className="ff-rail-sub">
              {report
                ? 'One pass, shown in the order it happened'
                : 'Upload a zip of collection CSVs'}
            </div>
          </div>

          <div className="ff-steps">
            {report && result
              ? visibleStages.map((stage) => (
                  <div className="ff-logline" key={stage.id}>
                    <span className="ff-logline-head">
                      <span className="ff-logline-label">{stage.label}</span>
                      <span className="ff-logline-value">{stage.value(report, result)}</span>
                    </span>
                    <span className="ff-logline-note">{stage.note}</span>
                  </div>
                ))
              : STAGES.map((stage) => (
                  <div className="ff-logline" data-waiting="true" key={stage.id}>
                    <span className="ff-logline-head">
                      <span className="ff-logline-label">{stage.label}</span>
                      <span className="ff-logline-value">—</span>
                    </span>
                  </div>
                ))}
          </div>

          {report && report.warnings.length > 0 && (
            <div className="ff-rail-foot">
              <div className="ff-rail-foot-title">
                {num(report.warnings.length)} rows the transform set aside
              </div>
              <ul className="ff-warnings">
                {report.warnings.slice(0, 4).map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </nav>

        <main className="ff-stage" onClick={phase === 'building' ? skip : undefined}>
          {result ? (
            <GraphStage
              nodes={result.nodes}
              edges={result.edges}
              scores={new Map()}
              mode="build"
              arrival={arrival}
              cascadeStartedAt={buildStartedAt}
              pathNodeIds={null}
              pathEdgeIds={null}
              selectedId={null}
              triggerNode={null}
              bottomInset={112}
              onSelect={() => {}}
            />
          ) : null}

          <div className="ff-stage-overlay" data-bar="true">
            <div className="ff-stage-caption">
              <h2>
                {phase === 'idle' && 'Build the chain from the filings themselves'}
                {phase === 'reading' && 'Reading the archive'}
                {phase === 'log' && 'One pass over the archive'}
                {phase === 'building' && 'Placing the chain, tier by tier'}
                {phase === 'done' && `${num(result?.nodes.length ?? 0)} companies, built from ${num(report?.companies_read ?? 0)} filings`}
              </h2>
              <p>
                {phase === 'idle' &&
                  'A zip of collection CSVs — the whole folder is fine. Everything happens on this machine: nothing is fetched, nothing is uploaded anywhere, and no language model reads your files.'}
                {phase === 'reading' && 'Unpacking, classifying and scoring in a single pass.'}
                {(phase === 'log' || phase === 'building') &&
                  'The archive was processed in one pass and came back complete. These figures are its results, revealed in the order the work happened — not a progress bar.'}
                {phase === 'done' &&
                  'The structure is real. Risk has not been coloured in yet — that happens in the console, on the next screen.'}
              </p>
            </div>

            {phase === 'idle' && (
              <div
                className="ff-drop"
                data-dragging={dragging ? 'true' : undefined}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  const file = event.dataTransfer.files?.[0];
                  if (file) handleFile(file);
                }}
              >
                <p className="ff-drop-lead">Drop a zip here</p>
                <p className="ff-drop-note">
                  Expected inside: <code>companies.csv</code>, <code>financials.csv</code>,{' '}
                  <code>edges.csv</code>, and <code>entity_pool.csv</code> for the deep tier.
                  Anything else in the archive is ignored, not refused.
                </p>
                <button className="ff-ghost" onClick={() => fileRef.current?.click()}>
                  Or choose a file
                </button>
                {error && (
                  <p className="ff-drop-error" role="alert">
                    {error}
                  </p>
                )}
              </div>
            )}

            {(phase === 'building' || phase === 'done') && (
              <div className="ff-counters">
                <div className="ff-counter">
                  <span className="ff-counter-value">{num(placed.nodes)}</span>
                  <span className="ff-counter-label">companies placed</span>
                </div>
                <div className="ff-counter">
                  <span className="ff-counter-value">{num(placed.edges)}</span>
                  <span className="ff-counter-label">relationships drawn</span>
                </div>
                <div className="ff-counter">
                  <span className="ff-counter-value">{cr(placed.value, 0)}</span>
                  <span className="ff-counter-label">of trade mapped</span>
                </div>
              </div>
            )}
          </div>

          <input
            ref={fileRef}
            className="ff-sr"
            type="file"
            accept=".zip,application/zip"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) handleFile(file);
              event.target.value = '';
            }}
          />
        </main>

        <aside className="ff-side">
          {report ? (
            <>
              <div className="ff-block">
                <div className="ff-block-head">
                  <h2 className="ff-h">What the upload held</h2>
                  <span className="ff-h-note">{num(report.files_seen.length)} members</span>
                </div>
                <div className="ff-figures">
                  {Object.entries(report.files_used)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([canonical, member]) => (
                      <div className="ff-figure" key={canonical}>
                        <span className="ff-figure-label">
                          {canonical}
                          <span className="ff-file-from">{member}</span>
                        </span>
                        <span className="ff-figure-value">{num(report.rows_parsed[canonical] ?? 0)}</span>
                      </div>
                    ))}
                </div>
                {report.files_ignored.length > 0 && (
                  <p className="ff-note-sm" style={{ marginTop: 12 }}>
                    Ignored: {report.files_ignored.join(', ')}. A real upload is a folder, not a
                    curated set of five files.
                  </p>
                )}
              </div>

              <div className="ff-block">
                <div className="ff-block-head">
                  <h2 className="ff-h">What they disclosed</h2>
                </div>
                <div className="ff-figures">
                  <div className="ff-figure">
                    <span className="ff-figure-label">Fields filled</span>
                    <span className="ff-figure-value">{num(report.fields_present)}</span>
                  </div>
                  <div className="ff-figure">
                    <span className="ff-figure-label">Fields left blank</span>
                    <span className="ff-figure-value" data-lead="true">
                      {num(report.fields_null)}
                    </span>
                  </div>
                  <div className="ff-figure">
                    <span className="ff-figure-label">Companies with enough to score</span>
                    <span className="ff-figure-value">{num(report.observable_nodes)}</span>
                  </div>
                  <div className="ff-figure">
                    <span className="ff-figure-label">Companies generated beneath them</span>
                    <span className="ff-figure-value">{num(report.generated_nodes)}</span>
                  </div>
                </div>
                <p className="ff-note" style={{ marginTop: 14 }}>
                  {num(report.fields_null)} fields across these filings say nothing at all, and{' '}
                  {num(report.nodes_built - report.observable_nodes)} of the{' '}
                  {num(report.nodes_built)} companies here publish nothing an anchor could read.
                  That is not a gap in the data — it is the problem the product exists for.
                </p>
              </div>
            </>
          ) : (
            <div className="ff-block">
              <div className="ff-block-head">
                <h2 className="ff-h">Nothing loaded yet</h2>
              </div>
              <p className="ff-note">
                This page builds the network from documents you already have. If the upload fails,
                or you would rather not use it, <strong>Use committed network</strong> opens the
                console on the dataset in the repository and the demo continues unaffected.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
