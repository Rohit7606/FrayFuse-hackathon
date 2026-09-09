/**
 * The network stage.
 *
 * One canvas, four reading modes, and the mode is what changes — never the
 * data. Nothing in this file computes a score, a depth or a path; it is handed
 * engine output and decides how brightly to draw it.
 *
 * MOTION BUDGET (animate skill, step 1/2): this is a rare, first-time,
 * explanatory surface — a judge sees the cascade once — so it sits in the tier
 * where longer, choreographed motion is allowed. Its named purpose is
 * EXPLANATION: stress arriving in waves is the one claim the product cannot
 * make in text without sounding like an assertion. Nothing else here animates
 * for its own sake: hover is instant, selection is instant, and the graph does
 * not drift, breathe or track the mouse, because a reader is trying to read
 * positions off it.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import {
  BAND_COLOR,
  CHROME,
  NEUTRAL,
  NEUTRAL_ANCHOR,
  easeOut,
  mix,
  rgba,
} from '../lib/bands';
import type { Edge, Node, Score } from '../types';

export type StageMode = 'network' | 'observability' | 'cascade' | 'focus';

/** How long one node takes to take on its band colour. */
const ARRIVE_MS = 620;
/** How long the ring that marks an arrival lives. */
const PULSE_MS = 1100;
/** Ceiling on the focus-mode zoom, so a two-node path is not magnified absurdly. */
const MAX_FOCUS_ZOOM = 2.2;

/** Graph-space y of each tier's band, and the labels drawn against them. */
const TIER_BANDS = [
  { tier: 0, label: 'TIER 0 · ANCHOR' },
  { tier: 1, label: 'TIER 1 · DIRECT SUPPLIERS' },
  { tier: 2, label: 'TIER 2' },
  { tier: 3, label: 'TIER 3 · DEEPEST' },
];

const bandY = (tier: number) => -390 + Math.min(tier, 3) * 260;

interface GraphNode extends Node {
  id: string;
  x?: number;
  y?: number;
}

interface GraphLink extends Edge {
  source: string | GraphNode;
  target: string | GraphNode;
}

interface Props {
  nodes: Node[];
  edges: Edge[];
  scores: Map<string, Score>;
  mode: StageMode;
  /**
   * Per-node reveal offset in ms from `cascadeStartedAt`. `null` means show
   * every band immediately — the state the graph sits in after a cascade has
   * run, and the state the slider re-scores into.
   */
  arrival: Map<string, number> | null;
  cascadeStartedAt: number | null;
  pathNodeIds: Set<string> | null;
  pathEdgeIds: Set<string> | null;
  selectedId: string | null;
  triggerNode: string | null;
  onSelect: (nodeId: string | null) => void;
}

/**
 * Tiers are laid out top to bottom instead of left as a hairball.
 *
 * A force-directed blob is honest about connectivity and useless for the
 * question on screen, which is how far down the chain something sits. This
 * pins each tier to a band with a custom y force — the same thing d3's
 * forceY does, written out so the app does not take a direct dependency on
 * a package it gets transitively.
 */
function tierBandForce(strength: number) {
  // Wide bands, strongly held. The first attempt used a soft force and the
  // tiers collapsed into one pyramid — connectivity won and the picture stopped
  // answering "how far down the chain is this", which is the only question the
  // layout exists to answer.
  let nodes: GraphNode[] = [];

  const force = (alpha: number) => {
    for (const node of nodes) {
      if (typeof node.y !== 'number') continue;
      // @ts-expect-error d3 writes velocity onto the node
      node.vy += (bandY(node.tier) - node.y) * strength * alpha;
    }
  };
  force.initialize = (simulationNodes: GraphNode[]) => {
    nodes = simulationNodes;
  };
  return force;
}

export default function GraphStage({
  nodes,
  edges,
  scores,
  mode,
  arrival,
  cascadeStartedAt,
  pathNodeIds,
  pathEdgeIds,
  selectedId,
  triggerNode,
  onSelect,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const hoverRef = useRef<GraphNode | null>(null);
  const [size, setSize] = useState({ width: 900, height: 600 });

  const reducedMotion = useRef(false);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotion.current = query.matches;
    const onChange = () => {
      reducedMotion.current = query.matches;
    };
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  // Live props read from inside the per-frame paint callbacks. Canvas painting
  // happens outside React's render, so the callbacks must not close over stale
  // values — and re-creating them every frame would rebuild the graph.
  const live = useRef({
    mode,
    arrival,
    cascadeStartedAt,
    pathNodeIds,
    pathEdgeIds,
    selectedId,
    triggerNode,
    scores,
  });
  live.current = {
    mode,
    arrival,
    cascadeStartedAt,
    pathNodeIds,
    pathEdgeIds,
    selectedId,
    triggerNode,
    scores,
  };

  useEffect(() => {
    const measure = () => {
      if (!hostRef.current) return;
      setSize({
        width: hostRef.current.clientWidth,
        height: hostRef.current.clientHeight,
      });
    };
    measure();
    const observer = new ResizeObserver(measure);
    if (hostRef.current) observer.observe(hostRef.current);
    return () => observer.disconnect();
  }, []);

  const graphData = useMemo(
    () => ({
      nodes: nodes.map((node) => ({ ...node, id: node.node_id })) as GraphNode[],
      links: edges.map((edge) => ({
        ...edge,
        source: edge.supplier_id,
        target: edge.buyer_id,
      })) as GraphLink[],
    }),
    [nodes, edges],
  );

  // Forces are configured once. Re-applying them on a data change restarts the
  // simulation, which throws the layout away mid-demo.
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph || graphData.nodes.length === 0) return;
    graph.d3Force('tier', tierBandForce(1));
    // Repulsion spreads a tier along its band; a weak, short link force keeps
    // partners near each other without dragging them out of their tier.
    graph.d3Force('charge')?.strength(-72);
    graph.d3Force('link')?.distance(22).strength(0.07);
    const fit = window.setTimeout(() => graph.zoomToFit?.(600, 46), 420);
    return () => window.clearTimeout(fit);
  }, [graphData]);

  // Entering focus mode frames the path. This is spatial consistency, not
  // decoration: the path is four nodes out of 412 and would otherwise be a
  // detail the audience has to be told where to look for.
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;
    if (mode === 'focus' && pathNodeIds && pathNodeIds.size > 0) {
      const onPath = (node: GraphNode) => pathNodeIds.has(node.id);
      graph.zoomToFit?.(700, 150, onPath);
      // Fit twice. The first fit can land while the layout is still settling
      // from the previous step, which left the deepest node of the path just
      // outside the frame with its edge running off the corner.
      const refit = window.setTimeout(() => graph.zoomToFit?.(420, 150, onPath), 900);
      // And cap the result: fitting two nodes to a 1,200px stage magnifies them
      // to the size of saucers and pushes their labels off the bottom edge.
      const clamp = window.setTimeout(() => {
        const level = graph.zoom?.();
        if (typeof level === 'number' && level > MAX_FOCUS_ZOOM) {
          graph.zoom?.(MAX_FOCUS_ZOOM, 320);
        }
      }, 1400);
      return () => {
        window.clearTimeout(refit);
        window.clearTimeout(clamp);
      };
    }
    graph.zoomToFit?.(700, 46);
  }, [mode, pathNodeIds]);

  /** 0 → still neutral, 1 → fully in its band colour. */
  const revealOf = useCallback((nodeId: string, now: number) => {
    const { arrival: offsets, cascadeStartedAt: startedAt } = live.current;
    if (!offsets) return 1;
    const offset = offsets.get(nodeId);
    if (offset === undefined) return 0;
    if (startedAt === null) return 0;
    return easeOut((now - startedAt - offset) / ARRIVE_MS);
  }, []);

  const radiusOf = useCallback((node: GraphNode, score: Score | undefined) => {
    const base = 3 + (3 - Math.min(node.tier, 3)) * 0.95;
    const band = score?.risk_band;
    const bump = band === 'critical' ? 1.5 : band === 'high' ? 0.8 : 0;
    return base + bump;
  }, []);

  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (typeof node.x !== 'number' || typeof node.y !== 'number') return;

      const state = live.current;
      const now = performance.now();
      const score = state.scores.get(node.id);
      const isAnchor = node.tier === 0;
      const hovered = hoverRef.current?.id === node.id;
      const selected = state.selectedId === node.id;
      const onPath = state.pathNodeIds?.has(node.id) ?? false;

      let fill: string;
      let alpha = 1;
      let radius = radiusOf(node, score);

      if (state.mode === 'network') {
        fill = isAnchor ? NEUTRAL_ANCHOR : NEUTRAL;
        alpha = 0.9;
      } else if (state.mode === 'observability') {
        // Step 2 makes the product's premise visible: 8 of 412 companies
        // publish anything at all. The other 404 are not dim for effect —
        // being unobservable is the finding.
        fill = node.is_observable ? CHROME.inkHi : NEUTRAL;
        alpha = node.is_observable ? 1 : 0.22;
        radius = node.is_observable ? radius + 1.2 : radius * 0.8;
      } else {
        const band = score?.risk_band ?? 'stable';
        const reveal = revealOf(node.id, now);
        const target = BAND_COLOR[band];
        const touched = state.arrival?.has(node.id) ?? true;
        fill = touched ? mix(NEUTRAL, target, reveal) : BAND_COLOR.stable;
        alpha = touched ? 0.55 + 0.45 * reveal : 0.4;
        radius = touched ? radius * (0.86 + 0.14 * reveal) : radius * 0.78;
      }

      // Focus dims everything off the path. Everything, including the anchor's
      // own neighbours — the point of the mode is that four nodes matter.
      if (state.mode === 'focus' && state.pathNodeIds) {
        alpha = onPath ? 1 : 0.08;
        if (onPath) radius += 1.2;
      }

      if (hovered) radius += 1.6;

      ctx.save();
      ctx.globalAlpha = alpha;

      // Arrival ring. Draws once per node as its wave lands, then is gone —
      // a marker for a moment, not a permanent decoration.
      if (
        !reducedMotion.current &&
        state.arrival &&
        state.cascadeStartedAt !== null &&
        state.mode !== 'network' &&
        state.mode !== 'observability'
      ) {
        const offset = state.arrival.get(node.id);
        if (offset !== undefined) {
          const age = now - state.cascadeStartedAt - offset;
          if (age > 0 && age < PULSE_MS) {
            const k = age / PULSE_MS;
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius + easeOut(k) * 17, 0, 2 * Math.PI);
            ctx.strokeStyle = rgba(BAND_COLOR[score?.risk_band ?? 'watch'], (1 - k) * 0.55);
            ctx.lineWidth = 1.4 / globalScale;
            ctx.stroke();
          }
        }
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = fill;
      ctx.fill();

      // Chrome rings: selection, path membership, observability, the trigger.
      // Lime only ever appears as a ring, never as the fill, so it can never
      // be misread as a severity value.
      const ring =
        selected || onPath
          ? CHROME.lime
          : state.mode === 'observability' && node.is_observable
            ? CHROME.limeDeep
            : node.id === state.triggerNode && state.mode !== 'network'
              ? CHROME.lime
              : null;

      if (ring) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 2.6, 0, 2 * Math.PI);
        ctx.strokeStyle = ring;
        ctx.lineWidth = (selected ? 2 : 1.3) / globalScale;
        ctx.stroke();
      }

      // Anchors get a square notch so tier 0 is identifiable without colour
      // and without waiting for a label — there are two of them in 412 nodes.
      if (isAnchor && state.mode !== 'observability') {
        ctx.beginPath();
        ctx.rect(node.x - radius - 4.5, node.y - radius - 4.5, (radius + 4.5) * 2, (radius + 4.5) * 2);
        ctx.strokeStyle = rgba(CHROME.ink, state.mode === 'focus' && !onPath ? 0.1 : 0.32);
        ctx.lineWidth = 1 / globalScale;
        ctx.stroke();
      }

      ctx.restore();

      // Labels are earned, not sprayed: the node under the pointer, the
      // selected node, and the nodes on a highlighted path.
      const labelled = hovered || selected || (state.mode === 'focus' && onPath);
      if (!labelled) return;

      const fontSize = Math.max(11 / globalScale, 3.4);
      const text = `${node.node_id}  ${node.name}`;
      ctx.save();
      ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      const width = ctx.measureText(text).width;
      const padX = fontSize * 0.5;
      const padY = fontSize * 0.32;
      const top = node.y + radius + 5;

      ctx.fillStyle = 'rgba(1, 18, 7, 0.92)';
      ctx.strokeStyle = rgba(CHROME.lime, 0.35);
      ctx.lineWidth = 1 / globalScale;
      ctx.beginPath();
      const boxX = node.x - width / 2 - padX;
      const boxW = width + padX * 2;
      const boxH = fontSize + padY * 2;
      if (ctx.roundRect) ctx.roundRect(boxX, top, boxW, boxH, 3 / globalScale);
      else ctx.rect(boxX, top, boxW, boxH);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = CHROME.inkHi;
      ctx.fillText(text, node.x, top + padY);
      ctx.restore();
    },
    [radiusOf, revealOf],
  );

  /**
   * Tier guides, drawn beneath everything.
   *
   * The layout pins each tier to a band, and without a labelled rule the
   * bands are a shape the audience has to be told about. Drawn in graph space
   * so they track pan and zoom, and kept at hairline contrast so they frame
   * the nodes instead of competing with them.
   */
  const paintGuides = useCallback((ctx: CanvasRenderingContext2D, globalScale: number) => {
    const graph = graphRef.current;
    if (!graph) return;
    const half = size.width / (2 * globalScale);
    const centre = graph.centerAt?.() ?? { x: 0 };
    const left = (centre.x ?? 0) - half;
    const right = (centre.x ?? 0) + half;

    ctx.save();
    ctx.lineWidth = 1 / globalScale;
    ctx.font = `500 ${9.5 / globalScale}px 'JetBrains Mono', ui-monospace, monospace`;
    ctx.textBaseline = 'bottom';
    for (const band of TIER_BANDS) {
      const y = bandY(band.tier);
      ctx.strokeStyle = rgba(CHROME.ink, 0.07);
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(right, y);
      ctx.stroke();

      ctx.fillStyle = rgba(CHROME.ink, 0.3);
      ctx.textAlign = 'left';
      ctx.fillText(band.label, left + 14 / globalScale, y - 5 / globalScale);
    }
    ctx.restore();
  }, [size.width]);

  const linkColor = useCallback((link: GraphLink) => {
    const state = live.current;
    if (state.mode === 'focus' && state.pathEdgeIds) {
      return state.pathEdgeIds.has(link.edge_id)
        ? rgba(CHROME.lime, 0.9)
        : rgba(CHROME.ink, 0.025);
    }
    if (state.mode === 'observability') return rgba(CHROME.ink, 0.04);
    const hover = hoverRef.current;
    if (hover) {
      const source = typeof link.source === 'object' ? link.source.id : link.source;
      const target = typeof link.target === 'object' ? link.target.id : link.target;
      if (source === hover.id || target === hover.id) return rgba(CHROME.lime, 0.55);
      return rgba(CHROME.ink, 0.03);
    }
    // Sole-source edges read slightly stronger at rest. They are the edges
    // that make a supplier irreplaceable, so they are worth seeing before
    // anyone clicks anything.
    return link.is_single_source === true ? rgba(CHROME.ink, 0.14) : rgba(CHROME.ink, 0.06);
  }, []);

  const linkWidth = useCallback((link: GraphLink) => {
    const state = live.current;
    if (state.mode === 'focus' && state.pathEdgeIds?.has(link.edge_id)) return 2.4;
    const hover = hoverRef.current;
    if (hover) {
      const source = typeof link.source === 'object' ? link.source.id : link.source;
      const target = typeof link.target === 'object' ? link.target.id : link.target;
      if (source === hover.id || target === hover.id) return 1.6;
    }
    return 0.6;
  }, []);

  if (nodes.length === 0) {
    return <div className="ff-boot">Loading network…</div>;
  }

  return (
    <div ref={hostRef} className="ff-canvas-host">
      <ForceGraph2D
        ref={graphRef}
        width={size.width}
        height={size.height}
        graphData={graphData}
        backgroundColor="rgba(0,0,0,0)"
        nodeRelSize={5}
        nodeLabel={() => ''}
        cooldownTime={4200}
        d3AlphaDecay={0.026}
        d3VelocityDecay={0.32}
        linkDirectionalArrowLength={2.6}
        linkDirectionalArrowRelPos={1}
        linkDirectionalArrowColor={((link: GraphLink) => {
          const state = live.current;
          if (state.mode === 'focus' && state.pathEdgeIds) {
            return state.pathEdgeIds.has(link.edge_id)
              ? rgba(CHROME.lime, 0.9)
              : rgba(CHROME.ink, 0.02);
          }
          if (state.mode === 'observability') return rgba(CHROME.ink, 0.03);
          return rgba(CHROME.ink, 0.18);
        }) as any}
        linkColor={linkColor as any}
        linkWidth={linkWidth as any}
        onRenderFramePre={paintGuides as any}
        nodeCanvasObject={paintNode as any}
        nodePointerAreaPaint={(node: GraphNode, colour: string, ctx: CanvasRenderingContext2D) => {
          if (typeof node.x !== 'number' || typeof node.y !== 'number') return;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 9, 0, 2 * Math.PI);
          ctx.fillStyle = colour;
          ctx.fill();
        }}
        onNodeHover={(node: GraphNode | null) => {
          hoverRef.current = node ?? null;
          if (hostRef.current) hostRef.current.style.cursor = node ? 'pointer' : 'grab';
        }}
        onNodeClick={(node: GraphNode) => onSelect(node.id)}
        onBackgroundClick={() => onSelect(null)}
        onNodeDragEnd={(node: GraphNode) => {
          // Release the node so the layout stays one coherent picture rather
          // than accumulating hand-placed outliers over a long demo.
          delete (node as any).fx;
          delete (node as any).fy;
        }}
      />
    </div>
  );
}
