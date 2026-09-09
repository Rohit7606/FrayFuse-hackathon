import { useEffect, useRef, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface NetworkGraphProps {
  data: any; // { nodes, edges, scores }
  simulationState?: 'idle' | 'cascading' | 'cascaded' | 'intervened';
}

export default function NetworkGraph({ data, simulationState = 'idle' }: NetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const graphRef = useRef<any>(null);
  
  const [hoverNode, setHoverNode] = useState<any>(null);

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
    // Zoom to fit when data changes
    if (graphRef.current && data?.nodes?.length > 0) {
      setTimeout(() => {
        graphRef.current.zoomToFit(400, 50);
      }, 100);
    }
  }, [data]);

  const { nodes, links } = useMemo(() => {
    if (!data || !data.nodes || !data.edges) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n: any) => ({ ...n, id: n.node_id })),
      links: data.edges.map((e: any) => ({ ...e, source: e.source_id, target: e.target_id }))
    };
  }, [data]);

  if (!data || !data.nodes || !data.edges) return <div style={{ color: 'white', padding: '20px' }}>Loading network...</div>;

  const getRiskColor = (nodeId: string, baseStress: number = 0) => {
    // Find if we have a score for this node
    const scoreObj = data?.scores?.find((s: any) => s.node_id === nodeId);
    
    let stress = baseStress;
    let riskBand = 'stable';
    
    if (scoreObj) {
      stress = scoreObj.own_stress || baseStress;
      riskBand = scoreObj.risk_band || 'stable';
    }

    if (simulationState === 'idle') {
      // In idle state, mostly dim unless it's a base anchor/tier1
      return '#3b82f6'; 
    }

    if (simulationState === 'intervened' && scoreObj && scoreObj.intervention_cost_cr > 0 && riskBand === 'stable') {
      return '#10b981'; // Solved node
    }

    if (riskBand === 'critical' || stress >= 0.7) return '#ef4444'; // critical
    if (riskBand === 'watch' || stress >= 0.4) return '#f59e0b'; // watch
    if (riskBand === 'stable') return '#10b981'; // stable

    return '#3b82f6';
  };

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', cursor: hoverNode ? 'pointer' : 'default' }}>
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={{ nodes, links }}
        nodeColor={(node: any) => getRiskColor(node.id, node.stress_level || 0)}
        nodeRelSize={6}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        linkColor={(link: any) => {
          if (hoverNode) {
            const isConnected = link.source.id === hoverNode.id || link.target.id === hoverNode.id;
            return isConnected ? 'rgba(255, 255, 255, 0.8)' : 'rgba(255, 255, 255, 0.05)';
          }
          return 'rgba(255, 255, 255, 0.2)';
        }}
        linkWidth={(link: any) => {
           if (hoverNode) {
             return link.source.id === hoverNode.id || link.target.id === hoverNode.id ? 2 : 1;
           }
           return 1;
        }}
        onNodeHover={setHoverNode}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const isHovered = hoverNode === node;
          const isConnected = hoverNode && links.some((l: any) => 
            (l.source.id === hoverNode.id && l.target.id === node.id) ||
            (l.target.id === hoverNode.id && l.source.id === node.id)
          );
          
          const isFaded = hoverNode && !isHovered && !isConnected;

          const label = node.id;
          const fontSize = 12/globalScale;
          const color = getRiskColor(node.id, node.stress_level || 0);
          
          // Draw Node Circle
          ctx.beginPath();
          ctx.arc(node.x, node.y, isHovered ? 8 : 6, 0, 2 * Math.PI, false);
          ctx.fillStyle = color;
          
          if (isFaded) {
             ctx.globalAlpha = 0.2;
          } else if (isHovered) {
             ctx.shadowColor = color;
             ctx.shadowBlur = 15;
          }
          
          ctx.fill();
          
          // Reset shadow/alpha
          ctx.shadowBlur = 0;
          ctx.globalAlpha = 1;
          
          // Draw Label
          if (globalScale > 1.5 || isHovered) {
            ctx.font = `${isHovered ? fontSize * 1.2 : fontSize}px Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = isFaded ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.9)';
            
            // Draw background pill for hovered label
            if (isHovered) {
              const textWidth = ctx.measureText(label).width;
              const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.8);
              ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
              ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y + 10 - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
              ctx.fillStyle = 'rgba(255, 255, 255, 1)';
            }
            
            ctx.fillText(label, node.x, node.y + 10);
          }
        }}
      />
    </div>
  );
}
