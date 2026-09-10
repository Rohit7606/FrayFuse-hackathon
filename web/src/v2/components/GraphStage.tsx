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
  PAPER,
  UNSCORED,
  UNSCORED_ANCHOR,
  easeOut,
  mix,
  rgba,
} from '../lib/bands';
import type { Edge, Node, Score } from '../types';

export type StageMode = 'network' | 'observability' | 'cascade' | 'focus' | 'build';

/** How long one node takes to take on its band colour. */
const ARRIVE_MS = 620;
/** How long one node takes to appear during the live build. */
const PLACE_MS = 420;
/** How long the ring that marks an arrival lives. */
const PULSE_MS = 1100;
/**
 * Pixels the caption occupies at the top of the stage. The bottom overlays
 * vary with the step and arrive as a prop; the caption is always there.
 */
const TOP_INSET = 96;

/** Ceiling on the focus-mode zoom, so a two-node path is not magnified absurdly. */
const MAX_FOCUS_ZOOM = 2.2;

/** Graph-space y of each tier's band, and the labels drawn against them. */
const TIER_BANDS = [
  { tier: 0, label: 'TIER 0 · ANCHOR' },
  { tier: 1, label: 'TIER 1 · DIRECT SUPPLIERS' },
  { tier: 2, label: 'TIER 2' },
  { tier: 3, label: 'TIER 3 · DEEPEST' },
];

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
  /**
   * Pixels of the canvas covered by the overlays that sit on top of it — the
   * what-if bar and the wave or path banner. The canvas fills the whole stage
   * so that panning works everywhere, but a fit that ignores this puts the
   * deepest tier, and the deepest node of a highlighted path, underneath the
   * furniture.
   */
  bottomInset: number;
  onSelect: (nodeId: string | null) => void;
}

/**
 * Tiers are laid out as strata instead of as one hairball.
 *
 * A force-directed blob is honest about connectivity and useless for the
 * question on screen, which is how far down the chain something sits.
 *
 * The first attempt pulled each tier toward a line with a spring. It lost:
 * tier 3 has 251 nodes, every one of them linked upward, and the link force
 * dragged the whole stratum up into tier 2 — the guide lines and the nodes
 * stopped agreeing, which is worse than no guides at all. So `y` is PINNED and
 * only `x` is simulated.
 *
 * Within a tier the exact row is meaningless, so nodes are spread across a few
 * sub-rows inside the band. That is what keeps 251 nodes from forming a single
 * strip five times wider than the stage, and it is deterministic — derived
 * from the node id, so the layout is identical on every run.
 */
const BAND_GAP = 280;
const SUB_ROWS = 5;
const SUB_ROW_GAP = 26;

const bandY = (tier: number) => -420 + Math.min(tier, 3) * BAND_GAP;

/**
 * Sub-rows only where a tier is crowded. Splitting 28 tier-1 suppliers across
 * five rows turns a band into a column and makes a small tier look like a
 * cluster; 251 tier-3 suppliers on one row is a strip five times wider than
 * the stage. The count decides.
 */
function subRowOffset(nodeId: string, tierSize: number): number {
  const rows = tierSize > 60 ? SUB_ROWS : tierSize > 16 ? 2 : 1;
  if (rows === 1) return 0;
  let hash = 0;
  for (let i = 0; i < nodeId.length; i += 1) hash = (hash * 31 + nodeId.charCodeAt(i)) >>> 0;
  return ((hash % rows) - (rows - 1) / 2) * SUB_ROW_GAP;
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
  bottomInset,
  onSelect,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const hoverRef = useRef<GraphNode | null>(null);
  const insetRef = useRef(bottomInset);
  const tierSizeRef = useRef(new Map<number, number>());
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
  // Written after commit, not during render. The canvas paints on the next
  // animation frame, so an effect is early enough, and assigning during render
  // is not safe under concurrent rendering.
  useEffect(() => {
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
  }, [mode, arrival, cascadeStartedAt, pathNodeIds, pathEdgeIds, selectedId, triggerNode, scores]);

  // Read back inside a timeout after a fit, so it is written after commit.
  useEffect(() => {
    insetRef.current = bottomInset;
  }, [bottomInset]);

  useEffect(() => {
    const sizes = new Map<number, number>();
    for (const node of nodes) sizes.set(node.tier, (sizes.get(node.tier) ?? 0) + 1);
    tierSizeRef.current = sizes;
  }, [nodes]);

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

  const graphData = useMemo(() => {
    const tierSize = new Map<number, number>();
    for (const node of nodes) tierSize.set(node.tier, (tierSize.get(node.tier) ?? 0) + 1);

    return {
      nodes: nodes.map((node) => ({
        ...node,
        id: node.node_id,
        // fy pins the row; fx is left free so the simulation still spreads the
        // stratum horizontally and keeps linked partners near each other.
        fy: bandY(node.tier) + subRowOffset(node.node_id, tierSize.get(node.tier) ?? 1),
      })) as GraphNode[],
      links: edges.map((edge) => ({
        ...edge,
        source: edge.supplier_id,
        target: edge.buyer_id,
      })) as GraphLink[],
    };
  }, [nodes, edges]);

  /**
   * Fit, then lift the view clear of the bottom overlays.
   *
   * `zoomToFit` centres on the whole canvas, including the strip the what-if
   * bar covers. Raising the camera's centre by half the inset shifts the
   * content up by exactly the covered height, so nothing the fit just framed
   * ends up behind the furniture.
   */
  const fitWithInset = useCallback(
    (ms: number, padding: number, filter?: (node: GraphNode) => boolean) => {
      const graph = graphRef.current;
      if (!graph) return () => {};
      graph.zoomToFit?.(ms, padding, filter);
      const lift = window.setTimeout(() => {
        const zoom = graph.zoom?.() ?? 1;
        const centre = graph.centerAt?.() ?? { x: 0, y: 0 };
        // Centre on the VISIBLE rectangle, not the canvas. Lifting by the
        // bottom inset alone cleared the what-if bar and pushed the topmost
        // node straight under the caption instead.
        const shift = (insetRef.current - TOP_INSET) / 2;
        if (Math.abs(shift) > 1) {
          graph.centerAt?.(centre.x ?? 0, (centre.y ?? 0) + shift / zoom, 260);
        }
      }, ms + 40);
      return () => window.clearTimeout(lift);
    },
    [],
  );

  // Forces are configured once. Re-applying them on a data change restarts the
  // simulation, which throws the layout away mid-demo.
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph || graphData.nodes.length === 0) return;
    // Repulsion spreads a stratum sideways; a short link force pulls partners
    // towards each other's column. Neither can move a node off its row.
    graph.d3Force('charge')?.strength(-46);
    graph.d3Force('link')?.distance(18).strength(0.08);
    let cancelLift = () => {};
    const fit = window.setTimeout(() => {
      cancelLift = fitWithInset(600, 46);
    }, 420);
    return () => {
      window.clearTimeout(fit);
      cancelLift();
    };
  }, [graphData, fitWithInset]);

  // Entering focus mode frames the path. This is spatial consistency, not
  // decoration: the path is four nodes out of 412 and would otherwise be a
  // detail the audience has to be told where to look for.
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;
    if (mode === 'focus' && pathNodeIds && pathNodeIds.size > 0) {
      const onPath = (node: GraphNode) => pathNodeIds.has(node.id);
      let cancelFirst = fitWithInset(700, 150, onPath);
      // Fit twice. The first fit can land while the layout is still settling
      // from the previous step, which left the deepest node of the path just
      // outside the frame with its edge running off the corner.
      let cancelSecond = () => {};
      const refit = window.setTimeout(() => {
        cancelSecond = fitWithInset(420, 150, onPath);
      }, 900);
      // And cap the result: fitting two nodes to a 1,200px stage magnifies them
      // to the size of saucers and pushes their labels off the bottom edge.
      const clamp = window.setTimeout(() => {
        const level = graph.zoom?.();
        if (typeof level === 'number' && level > MAX_FOCUS_ZOOM) {
          graph.zoom?.(MAX_FOCUS_ZOOM, 320);
        }
      }, 1500);
      return () => {
        window.clearTimeout(refit);
        window.clearTimeout(clamp);
        cancelFirst();
        cancelSecond();
      };
    }
    return fitWithInset(700, 46);
  }, [mode, pathNodeIds, fitWithInset]);

  /**
   * 0 → not yet, 1 → fully arrived.
   *
   * One ramp, two jobs: during the cascade it is how far a node has taken on
   * its band colour, during the build it is how far it has been placed on the
   * page. The brief for the build said to extend this mechanism rather than
   * invent a second one, and there was nothing to add — the shape is the same.
   */
  const revealOf = useCallback((nodeId: string, now: number, span = ARRIVE_MS) => {
    const { arrival: offsets, cascadeStartedAt: startedAt } = live.current;
    if (!offsets) return 1;
    const offset = offsets.get(nodeId);
    if (offset === undefined) return 0;
    if (startedAt === null) return 0;
    return easeOut((now - startedAt - offset) / span);
  }, []);

  const radiusOf = useCallback((node: GraphNode, score: Score | undefined) => {
    const base = 3.6 + (3 - Math.min(node.tier, 3)) * 1.05;
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
        fill = isAnchor ? UNSCORED_ANCHOR : UNSCORED;
        alpha = 0.9;
      } else if (state.mode === 'observability') {
        // Step 2 makes the product's premise visible: 8 of 412 companies
        // publish anything at all. The other 404 are not dim for effect —
        // being unobservable is the finding.
        fill = node.is_observable ? PAPER.forest : UNSCORED;
        alpha = node.is_observable ? 1 : 0.22;
        radius = node.is_observable ? radius + 1.2 : radius * 0.8;
      } else if (state.mode === 'build') {
        // Structure first, colour second — two beats, not one. During the
        // build a node is only ever ink on paper; nothing here knows its band.
        const placed = revealOf(node.id, now, PLACE_MS);
        if (placed <= 0) return;
        fill = isAnchor ? UNSCORED_ANCHOR : UNSCORED;
        alpha = placed;
        radius *= 0.55 + 0.45 * placed;
      } else {
        const band = score?.risk_band ?? 'stable';
        const reveal = revealOf(node.id, now);
        const target = BAND_COLOR[band];
        const touched = state.arrival?.has(node.id) ?? true;
        fill = touched ? mix(UNSCORED, target, reveal) : BAND_COLOR.stable;
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
      // A hairline edge, so a pale node still has a boundary against paper.
      ctx.strokeStyle = rgba(PAPER.ink, 0.3);
      ctx.lineWidth = 0.7 / globalScale;
      ctx.stroke();

      // Chrome rings: selection, path membership, observability, the trigger.
      // Lime only ever appears as a ring, never as the fill, so it can never
      // be misread as a severity value.
      const ring =
        selected || onPath || (node.id === state.triggerNode && state.mode !== 'network')
          ? PAPER.forest
          : state.mode === 'observability' && node.is_observable
            ? PAPER.forest
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
        ctx.strokeStyle = rgba(PAPER.ink, state.mode === 'focus' && !onPath ? 0.08 : 0.38);
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

      ctx.fillStyle = PAPER.sheet;
      ctx.strokeStyle = rgba(PAPER.ink, 0.3);
      ctx.lineWidth = 1 / globalScale;
      ctx.beginPath();
      const boxX = node.x - width / 2 - padX;
      const boxW = width + padX * 2;
      const boxH = fontSize + padY * 2;
      if (ctx.roundRect) ctx.roundRect(boxX, top, boxW, boxH, 3 / globalScale);
      else ctx.rect(boxX, top, boxW, boxH);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = PAPER.ink;
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
      ctx.strokeStyle = rgba(PAPER.ink, 0.1);
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(right, y);
      ctx.stroke();

      // Above the topmost sub-row, not on the band's centre line — a tier
      // spread across sub-rows would otherwise print its label through its
      // own nodes.
      const clearance = ((SUB_ROWS - 1) / 2) * SUB_ROW_GAP + 14;
      ctx.fillStyle = rgba(PAPER.ink, 0.34);
      ctx.textAlign = 'left';
      ctx.fillText(band.label, left + 14 / globalScale, y - clearance);
    }
    ctx.restore();
  }, [size.width]);

  const linkColor = useCallback((link: GraphLink) => {
    const state = live.current;

    if (state.mode === 'build') {
      // An edge cannot be drawn to a node that is not there yet. Waiting for
      // both endpoints is what makes the build read as a chain assembling
      // rather than a mesh fading up.
      const now = performance.now();
      const source = typeof link.source === 'object' ? link.source.id : link.source;
      const target = typeof link.target === 'object' ? link.target.id : link.target;
      const ready = Math.min(revealOf(source, now, PLACE_MS), revealOf(target, now, PLACE_MS));
      if (ready <= 0.35) return 'rgba(0,0,0,0)';
      return rgba(PAPER.ink, 0.05 + 0.05 * ready);
    }

    if (state.mode === 'focus' && state.pathEdgeIds) {
      return state.pathEdgeIds.has(link.edge_id)
        ? rgba(PAPER.forest, 0.85)
        : rgba(PAPER.ink, 0.04);
    }
    if (state.mode === 'observability') return rgba(PAPER.ink, 0.05);
    const hover = hoverRef.current;
    if (hover) {
      const source = typeof link.source === 'object' ? link.source.id : link.source;
      const target = typeof link.target === 'object' ? link.target.id : link.target;
      if (source === hover.id || target === hover.id) return rgba(PAPER.forest, 0.5);
      return rgba(PAPER.ink, 0.045);
    }
    // Sole-source edges read slightly stronger at rest. They are the edges
    // that make a supplier irreplaceable, so they are worth seeing before
    // anyone clicks anything.
    return link.is_single_source === true ? rgba(PAPER.ink, 0.16) : rgba(PAPER.ink, 0.055);
  }, [revealOf]);

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
        linkDirectionalArrowLength={((link: GraphLink) =>
          live.current.mode === 'focus' && live.current.pathEdgeIds?.has(link.edge_id) ? 4 : 0) as any}
        linkDirectionalArrowRelPos={1}
        linkDirectionalArrowColor={(() => rgba(PAPER.forest, 0.85)) as any}
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
          // Release the horizontal pin only. `fy` is the node's tier and is
          // not the user's to move — a dragged node that keeps a hand-placed
          // row would put a tier-3 supplier in the anchor's stratum.
          delete (node as any).fx;
          (node as any).fy = bandY(node.tier) + subRowOffset(node.node_id, tierSizeRef.current.get(node.tier) ?? 1);
        }}
      />
    </div>
  );
}
