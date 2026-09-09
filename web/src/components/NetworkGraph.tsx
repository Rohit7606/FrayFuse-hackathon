import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface NetworkGraphProps {
  data: any; // { nodes, edges, scores }
  simulationState?: 'idle' | 'cascading' | 'cascaded' | 'intervened';
  currentWave?: number;
}

/**
 * Get the radius for a node based on its revenue, log-scaled.
 * PERSON_C.md §5.1: "Node size: revenue_cr, log-scaled.
 * Otherwise the anchor is a planet and Tier-3 is invisible."
 */
function getNodeRadius(revenueCr: number): number {
  if (!revenueCr || revenueCr <= 0) return 4;
  // Log-scale: ensures N001 (125,000 cr) is large but not overwhelming,
  // and N118 (8.5 cr) is still visible
  return Math.max(3, Math.log10(revenueCr + 1) * 3);
}

/**
 * Get edge width based on annual_value_cr, log-scaled.
 * PERSON_C.md §5.1: "Edge thickness: annual_value_cr, log-scaled"
 */
function getEdgeWidth(annualValueCr: number): number {
  if (!annualValueCr || annualValueCr <= 0) return 0.5;
  return Math.max(0.5, Math.log10(annualValueCr + 1) * 0.8);
}

export default function NetworkGraph({ data, simulationState = 'idle', currentWave = 0 }: NetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const graphRef = useRef<any>(null);
  const hoverNodeRef = useRef<any>(null);
  const [, forceRender] = useState(0);
  const hasSettled = useRef(false);

  // Resize observer
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

  // Zoom to fit after data loads
  useEffect(() => {
    if (graphRef.current && data?.nodes?.length > 0) {
      hasSettled.current = false;
      setTimeout(() => {
        graphRef.current?.zoomToFit?.(400, 60);
      }, 500);
    }
  }, [data]);

  // Build a lookup map from node_id → node data for fast access
  const nodeMap = useMemo(() => {
    if (!data?.nodes) return new Map();
    const map = new Map();
    data.nodes.forEach((n: any) => map.set(n.node_id, n));
    return map;
  }, [data?.nodes]);

  // Build a lookup map from node_id → score data
  const scoreMap = useMemo(() => {
    if (!data?.scores) return new Map();
    const map = new Map();
    data.scores.forEach((s: any) => map.set(s.node_id, s));
    return map;
  }, [data?.scores]);

  const graphData = useMemo(() => {
    if (!data || !data.nodes || !data.edges) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n: any) => ({
        ...n,
        id: n.node_id,
        // Pre-compute radius for consistent use in drawing and hit detection
        _radius: getNodeRadius(n.revenue_cr),
      })),
      links: data.edges.map((e: any) => ({
        ...e,
        source: e.supplier_id,
        target: e.buyer_id,
        _width: getEdgeWidth(e.annual_value_cr),
      }))
    };
  }, [data]);

  /**
   * Map risk_band to colour.
   * PERSON_C.md §5.1: "Node colour: risk_band — critical / high / watch / stable"
   */
  const getRiskColor = useCallback((nodeId: string): string => {
    const scoreObj = scoreMap.get(nodeId);

    // If we're cascading and this node's propagation depth hasn't been reached yet,
    // force it to look 'idle'.
    let treatAsIdle = false;
    if (simulationState === 'cascading') {
      const nodeDepth = scoreObj?.propagation_depth ?? Infinity;
      if (nodeDepth > currentWave) {
        treatAsIdle = true;
      }
    }

    if (simulationState === 'idle' || treatAsIdle) {
      // In idle state, show muted colours based on tier for structure visibility
      const node = nodeMap.get(nodeId);
      const tier = node?.tier ?? 1;
      // Subtle blue tones differentiated by tier
      if (tier === 0) return '#60a5fa'; // anchor — brighter blue
      if (tier === 1) return '#4a8fe0';
      if (tier === 2) return '#3a7bc8';
      return '#2b68b0'; // tier 3+
    }

    if (!scoreObj) return '#3b7cc8';

    const riskBand = scoreObj.risk_band || 'stable';

    if (simulationState === 'intervened' && scoreObj.intervention_cost_cr > 0 && riskBand === 'stable') {
      return '#10b981'; // green — intervention resolved this node
    }

    if (riskBand === 'critical') return '#ef4444';
    if (riskBand === 'high') return '#f59e0b';
    if (riskBand === 'watch') return '#60a5fa';
    if (riskBand === 'stable') return '#10b981';

    return '#3b7cc8';
  }, [scoreMap, nodeMap, simulationState, currentWave]);

  const linkNodeId = (endpoint: any): string => {
    if (!endpoint) return '';
    return typeof endpoint === 'object' ? String(endpoint.id || '') : String(endpoint);
  };

  // Callback to force a canvas repaint when hover changes
  const setHoverNode = useCallback((node: any) => {
    hoverNodeRef.current = node || null;
    // Force canvas repaint by triggering a state update
    forceRender(c => c + 1);
  }, []);

  // Pre-compute adjacency for fast neighbour lookups during canvas draw
  // Avoids calling graphRef.current.graphData() which can fail before graph is ready
  const adjacency = useMemo(() => {
    const map = new Map<string, Set<string>>();
    if (!data?.edges) return map;
    data.edges.forEach((e: any) => {
      const sid = e.supplier_id;
      const bid = e.buyer_id;
      if (!map.has(sid)) map.set(sid, new Set());
      if (!map.has(bid)) map.set(bid, new Set());
      map.get(sid)!.add(bid);
      map.get(bid)!.add(sid);
    });
    return map;
  }, [data?.edges]);

  if (!data || !data.nodes || !data.edges) {
    return <div style={{ color: 'white', padding: '20px' }}>Loading network...</div>;
  }

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative', cursor: 'grab' }}>
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeRelSize={1}
        nodeVal={(node: any) => node._radius * node._radius}
        nodeLabel={() => ''}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        // --- LAYOUT: Radial force by tier ---
        // Use d3 forces to create radial tier layout
        // PERSON_C.md §5.1: "radial by tier — anchor at centre, tiers moving outward"
        d3AlphaDecay={0.035}
        d3VelocityDecay={0.3}
        cooldownTicks={200}
        warmupTicks={80}
        onEngineStop={() => {
          hasSettled.current = true;
        }}
        // --- HOVER ---
        onNodeHover={(node: any) => {
          setHoverNode(node);
          if (containerRef.current) {
            containerRef.current.style.cursor = node ? 'pointer' : 'grab';
          }
        }}
        // --- DRAG ---
        onNodeDrag={() => {
          if (containerRef.current) containerRef.current.style.cursor = 'grabbing';
        }}
        onNodeDragEnd={(node: any) => {
          if (containerRef.current) containerRef.current.style.cursor = 'grab';
          // Fix the node position after drag so it stays put (physics is cooled down)
          node.fx = node.x;
          node.fy = node.y;
        }}
        // --- EDGE STYLING ---
        linkColor={(link: any) => {
          try {
            const hover = hoverNodeRef.current;
            if (hover) {
              const connected =
                linkNodeId(link.source) === hover.id ||
                linkNodeId(link.target) === hover.id;
              return connected
                ? 'rgba(255, 255, 255, 0.7)'
                : 'rgba(255, 255, 255, 0.04)';
            }
            return 'rgba(255, 255, 255, 0.12)';
          } catch (_) {
            return 'rgba(255, 255, 255, 0.12)';
          }
        }}
        linkWidth={(link: any) => {
          try {
            const hover = hoverNodeRef.current;
            if (hover) {
              const connected =
                linkNodeId(link.source) === hover.id ||
                linkNodeId(link.target) === hover.id;
              return connected ? (link._width || 1) * 2.5 : 0.3;
            }
            return link._width || 1;
          } catch (_) {
            return 1;
          }
        }}
        // --- THE FUSE: PARTICLES ---
        linkDirectionalParticles={(link: any) => {
          if (simulationState !== 'cascading') return 0;
          
          const sourceId = linkNodeId(link.source);
          const targetId = linkNodeId(link.target);
          const sourceScore = scoreMap.get(sourceId);
          const targetScore = scoreMap.get(targetId);
          
          if (!sourceScore || !targetScore) return 0;
          
          const sourceDepth = sourceScore.propagation_depth ?? Infinity;
          const targetDepth = targetScore.propagation_depth ?? Infinity;
          
          // Only show particles flowing from an already infected node to the next victim
          if (sourceDepth <= currentWave && targetDepth === currentWave + 1) {
            return 3; 
          }
          return 0;
        }}
        linkDirectionalParticleWidth={(link: any) => (link._width || 1) * 2.5}
        linkDirectionalParticleColor={(link: any) => {
          const targetId = linkNodeId(link.target);
          const targetScore = scoreMap.get(targetId);
          const riskBand = targetScore?.risk_band || 'critical';
          if (riskBand === 'critical') return '#ef4444';
          if (riskBand === 'high') return '#f59e0b';
          return '#ef4444';
        }}
        linkDirectionalParticleSpeed={() => 0.006} // Slow travel
        // --- NODE DRAWING ---
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          if (!node || typeof node.x !== 'number' || typeof node.y !== 'number') return;

          try {
            const hover = hoverNodeRef.current;
            const isHovered = hover?.id === node.id;

            let isNeighbour = false;
            if (hover && !isHovered) {
              const neighbours = adjacency.get(hover.id);
              isNeighbour = !!neighbours && neighbours.has(node.id);
            }

            const isFaded = hover && !isHovered && !isNeighbour;
            const color = getRiskColor(node.id);
            const radius = isHovered ? node._radius * 1.4 : node._radius;

            ctx.save();

            if (isFaded) {
              ctx.globalAlpha = 0.12;
            }

            // --- Glow effect for hovered or critical nodes ---
            if (isHovered) {
              ctx.shadowColor = color;
              ctx.shadowBlur = 20;
            } else if (simulationState !== 'idle' && !isFaded) {
              const scoreObj = scoreMap.get(node.id);
              let treatAsIdle = false;
              if (simulationState === 'cascading') {
                const nodeDepth = scoreObj?.propagation_depth ?? Infinity;
                if (nodeDepth > currentWave) treatAsIdle = true;
              }
              if (scoreObj?.risk_band === 'critical' && (!treatAsIdle)) {
                ctx.shadowColor = '#ef4444';
                ctx.shadowBlur = 12;
              }
            }

            // --- THE SHOCKWAVE (PULSE) ---
            if (simulationState === 'cascading') {
              const scoreObj = scoreMap.get(node.id);
              const nodeDepth = scoreObj?.propagation_depth ?? Infinity;
              
              if (nodeDepth === currentWave) {
                 ctx.save();
                 // Inner strong aura
                 ctx.beginPath();
                 ctx.arc(node.x, node.y, radius * 1.8, 0, 2 * Math.PI);
                 ctx.fillStyle = color;
                 ctx.globalAlpha = 0.25;
                 ctx.fill();
                 
                 // Outer ripple ring
                 ctx.beginPath();
                 ctx.arc(node.x, node.y, radius * 3.0, 0, 2 * Math.PI);
                 ctx.strokeStyle = color;
                 ctx.globalAlpha = 0.15;
                 ctx.lineWidth = 1.5 / globalScale;
                 ctx.stroke();
                 ctx.restore();
                 
                 // Intensify the core glow
                 ctx.shadowColor = color;
                 ctx.shadowBlur = 30;
              }
            }

            // --- Draw the filled circle ---
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();

            // --- Ring: dashed for synthetic, solid for real ---
            // PERSON_C.md §5.1: "Dashed outline for data_source: 'synthetic', solid for 'real'"
            ctx.shadowBlur = 0; // turn off glow for ring
            ctx.lineWidth = isHovered ? 2 / globalScale : 1.2 / globalScale;

            if (node.data_source === 'real') {
              ctx.strokeStyle = isFaded ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.7)';
              ctx.setLineDash([]);
              ctx.stroke();
            } else {
              ctx.strokeStyle = isFaded ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.25)';
              ctx.setLineDash([2 / globalScale, 2 / globalScale]);
              ctx.stroke();
              ctx.setLineDash([]); // reset
            }

            ctx.restore();

            // --- Labels ---
            const fontSize = Math.max(11 / globalScale, 1.8);

            if (isHovered) {
              // HOVER TOOLTIP: Show detailed info card
              ctx.save();
              const nodeName = String(node.name || node.id);
              const scoreObj = scoreMap.get(node.id);
              const tierText = `Tier ${node.tier}`;
              const revenueText = `₹${node.revenue_cr >= 1 ? node.revenue_cr.toFixed(1) : (node.revenue_cr * 100).toFixed(0) + 'L'} cr`;
              const dataSourceText = node.data_source === 'real' ? '● REAL' : '○ SYNTH';
              const riskBand = scoreObj?.risk_band || 'stable';

              const tooltipFontSize = Math.max(12 / globalScale, 2.2);
              const smallFont = tooltipFontSize * 0.8;
              const lineHeight = tooltipFontSize * 1.6;
              const padX = tooltipFontSize * 0.8;
              const padY = tooltipFontSize * 0.5;

              // Measure text widths
              ctx.font = `700 ${tooltipFontSize}px Inter, sans-serif`;
              const nameWidth = ctx.measureText(nodeName).width;
              ctx.font = `500 ${smallFont}px Inter, sans-serif`;
              const detailWidth = Math.max(
                ctx.measureText(`${tierText}  •  ${revenueText}`).width,
                ctx.measureText(`${riskBand.toUpperCase()}  •  ${dataSourceText}`).width
              );
              const tooltipWidth = Math.max(nameWidth, detailWidth) + padX * 2;
              const tooltipHeight = lineHeight * 3 + padY * 2;

              const tx = node.x - tooltipWidth / 2;
              const ty = node.y + radius + 6 / globalScale;

              // Background
              ctx.fillStyle = 'rgba(10, 11, 15, 0.92)';
              ctx.beginPath();
              if (ctx.roundRect) {
                ctx.roundRect(tx, ty, tooltipWidth, tooltipHeight, 4 / globalScale);
              } else {
                ctx.rect(tx, ty, tooltipWidth, tooltipHeight);
              }
              ctx.fill();

              // Border
              ctx.strokeStyle = 'rgba(255,255,255,0.12)';
              ctx.lineWidth = 0.8 / globalScale;
              ctx.stroke();

              // Name
              ctx.font = `700 ${tooltipFontSize}px Inter, sans-serif`;
              ctx.textAlign = 'left';
              ctx.textBaseline = 'top';
              ctx.fillStyle = '#e8eaed';
              ctx.fillText(nodeName, tx + padX, ty + padY);

              // Tier + Revenue
              ctx.font = `500 ${smallFont}px Inter, sans-serif`;
              ctx.fillStyle = '#9aa0b0';
              ctx.fillText(`${tierText}  •  ${revenueText}`, tx + padX, ty + padY + lineHeight);

              // Risk band + Data source
              const bandColors: Record<string, string> = {
                critical: '#ef4444',
                high: '#f59e0b',
                watch: '#60a5fa',
                stable: '#10b981',
              };
              ctx.fillStyle = bandColors[riskBand] || '#9aa0b0';
              ctx.fillText(riskBand.toUpperCase(), tx + padX, ty + padY + lineHeight * 2);

              // Data source badge
              ctx.fillStyle = node.data_source === 'real' ? '#60a5fa' : '#6b7185';
              const bandTextWidth = ctx.measureText(riskBand.toUpperCase() + '  •  ').width;
              ctx.fillText(`•  ${dataSourceText}`, tx + padX + bandTextWidth, ty + padY + lineHeight * 2);

              ctx.restore();
            } else if (globalScale > 0.8 && !isFaded) {
              // Always show truncated name at reasonable zoom
              ctx.save();
              ctx.font = `500 ${fontSize}px Inter, sans-serif`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'top';

              const name = String(node.name || node.id);
              const displayName = name.length > 18 ? name.substring(0, 16) + '…' : name;
              ctx.fillStyle = 'rgba(255,255,255,0.45)';
              ctx.fillText(displayName, node.x, node.y + radius + 2);
              ctx.restore();
            }
          } catch (err) {
            // Silently ignore render errors to prevent canvas crash
          }
        }}
        // --- HIT AREA: generous for all nodes, not just hovered ---
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          if (!node || typeof node.x !== 'number' || typeof node.y !== 'number') return;
          // Use a generous hit area: node radius + padding
          // This ensures hover detection works reliably for ALL nodes
          const hitRadius = (node._radius || 6) + 8;
          ctx.beginPath();
          ctx.arc(node.x, node.y, hitRadius, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
      />

      {/* LEGEND — always visible per PERSON_C.md §6: "Legend always visible" */}
      <div className="graph-legend">
        <div className="legend-group">
          <div className="legend-group-title">Risk Band</div>
          <div className="legend-items">
            <div className="legend-item">
              <div className="legend-dot" style={{ background: '#ef4444', boxShadow: '0 0 6px rgba(239,68,68,0.4)' }}></div>
              <span>Critical</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: '#f59e0b' }}></div>
              <span>High</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: '#60a5fa' }}></div>
              <span>Watch</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: '#10b981' }}></div>
              <span>Stable</span>
            </div>
          </div>
        </div>
        <div className="legend-divider"></div>
        <div className="legend-group">
          <div className="legend-group-title">Data Source</div>
          <div className="legend-items">
            <div className="legend-item">
              <div className="legend-dot" style={{ background: '#60a5fa', border: '1.5px solid rgba(255,255,255,0.7)' }}></div>
              <span>Real</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: '#3a7bc8', border: '1.5px dashed rgba(255,255,255,0.3)' }}></div>
              <span>Synthetic</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
