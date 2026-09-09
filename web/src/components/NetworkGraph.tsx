import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface NetworkGraphProps {
  data: any; // { nodes, edges, scores }
  simulationState?: 'idle' | 'cascading' | 'cascaded' | 'intervened';
}

export default function NetworkGraph({ data, simulationState = 'idle' }: NetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const graphRef = useRef<any>(null);

  // Use a ref for hover state — avoids React re-renders on every mouse move.
  // The canvas redraws at ~60fps via requestAnimationFrame, so the ref value
  // is picked up on the next frame without needing a state update.
  const hoverNodeRef = useRef<any>(null);

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (graphRef.current && data?.nodes?.length > 0) {
      setTimeout(() => {
        graphRef.current.zoomToFit(400, 50);
      }, 300);
    }
  }, [data]);

  // Memoise the graph data object itself so the reference is stable
  const graphData = useMemo(() => {
    if (!data || !data.nodes || !data.edges) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n: any) => ({ ...n, id: n.node_id })),
      links: data.edges.map((e: any) => ({ ...e, source: e.source_id, target: e.target_id }))
    };
  }, [data]);

  const getRiskColor = useCallback((nodeId: string, baseStress: number = 0) => {
    const scoreObj = data?.scores?.find((s: any) => s.node_id === nodeId);

    let stress = baseStress;
    let riskBand = 'stable';

    if (scoreObj) {
      stress = scoreObj.own_stress || baseStress;
      riskBand = scoreObj.risk_band || 'stable';
    }

    if (simulationState === 'idle') return '#3b82f6';

    if (simulationState === 'intervened' && scoreObj && scoreObj.intervention_cost_cr > 0 && riskBand === 'stable') {
      return '#10b981';
    }

    if (riskBand === 'critical' || stress >= 0.7) return '#ef4444';
    if (riskBand === 'watch' || stress >= 0.4) return '#f59e0b';
    if (riskBand === 'stable') return '#10b981';

    return '#3b82f6';
  }, [data?.scores, simulationState]);

  if (!data || !data.nodes || !data.edges) {
    return <div style={{ color: 'white', padding: '20px' }}>Loading network...</div>;
  }

  /** Extracts a stable node id from a link endpoint (string before init, object after). */
  const linkNodeId = (endpoint: any): string =>
    typeof endpoint === 'object' ? endpoint.id : endpoint;

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeRelSize={6}
        nodeLabel={() => ''}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        onNodeHover={(node: any) => { hoverNodeRef.current = node || null; }}
        linkColor={(link: any) => {
          const hover = hoverNodeRef.current;
          if (hover) {
            const connected =
              linkNodeId(link.source) === hover.id ||
              linkNodeId(link.target) === hover.id;
            return connected
              ? 'rgba(255, 255, 255, 0.8)'
              : 'rgba(255, 255, 255, 0.05)';
          }
          return 'rgba(255, 255, 255, 0.2)';
        }}
        linkWidth={(link: any) => {
          const hover = hoverNodeRef.current;
          if (hover) {
            const connected =
              linkNodeId(link.source) === hover.id ||
              linkNodeId(link.target) === hover.id;
            return connected ? 2 : 0.5;
          }
          return 1;
        }}
        nodeCanvasObjectMode={() => 'replace'}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const hover = hoverNodeRef.current;
          const isHovered = hover?.id === node.id;

          // Check if this node is a direct neighbour of the hovered node
          let isNeighbour = false;
          if (hover && !isHovered) {
            const gLinks = graphRef.current?.graphData()?.links || [];
            isNeighbour = gLinks.some((l: any) => {
              const src = linkNodeId(l.source);
              const tgt = linkNodeId(l.target);
              return (src === hover.id && tgt === node.id) ||
                     (tgt === hover.id && src === node.id);
            });
          }

          const isFaded = hover && !isHovered && !isNeighbour;
          const color = getRiskColor(node.id, node.stress_level || 0);
          const radius = isHovered ? 8 : 6;

          // --- Draw circle ---
          ctx.save();

          if (isFaded) {
            ctx.globalAlpha = 0.15;
          } else if (isHovered) {
            ctx.shadowColor = color;
            ctx.shadowBlur = 18;
          }

          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.restore();

          // --- Draw label ---
          const fontSize = 12 / globalScale;

          if (isHovered) {
            const nodeName = node.name || node.id;
            ctx.font = `600 ${fontSize * 1.3}px Inter, Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            // Background pill
            const tw = ctx.measureText(nodeName).width;
            const px = fontSize * 0.5;
            const py = fontSize * 0.35;
            ctx.fillStyle = 'rgba(0,0,0,0.85)';
            ctx.beginPath();
            // Simple rounded rect
            const rx = node.x - tw / 2 - px;
            const ry = node.y + radius + 4 - py;
            const rw = tw + px * 2;
            const rh = fontSize + py * 2;
            if (ctx.roundRect) {
              ctx.roundRect(rx, ry, rw, rh, 3);
            } else {
              ctx.rect(rx, ry, rw, rh);
            }
            ctx.fill();

            ctx.fillStyle = '#fff';
            ctx.fillText(nodeName, node.x, node.y + radius + 4 + fontSize * 0.5 - py);
          } else if (globalScale > 1.8 && !isFaded) {
            ctx.font = `${fontSize}px Inter, Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = 'rgba(255,255,255,0.6)';
            ctx.fillText(node.id, node.x, node.y + radius + 4);
          }
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          // Invisible hit area for hover detection — must match or exceed the drawn radius
          ctx.beginPath();
          ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
      />
    </div>
  );
}
