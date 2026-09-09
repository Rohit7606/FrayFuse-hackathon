import { useEffect, useState, useMemo } from 'react';
import { apiClient } from './api/client';
import NetworkGraph from './components/NetworkGraph';
import RankedList from './components/RankedList';
import HeaderBar from './components/HeaderBar';
import InterventionCard from './components/InterventionCard';
import './index.css';

function App() {
  const [networkData, setNetworkData] = useState<any>(null);
  const [atRiskData, setAtRiskData] = useState<any>(null);
  const [interveneData, setInterveneData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  type SimState = 'idle' | 'cascading' | 'cascaded' | 'intervened';
  const [simulationState, setSimulationState] = useState<SimState>('idle');
  const [currentWave, setCurrentWave] = useState(0);

  useEffect(() => {
    async function loadData() {
      try {
        const [network, atRisk] = await Promise.all([
          apiClient.getNetwork(),
          apiClient.getAtRisk()
        ]);
        setNetworkData(network);
        setAtRiskData(atRisk);
      } catch (err) {
        console.error("Failed to load initial data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleRunCascade = async () => {
    setSimulationState('cascading');
    setCurrentWave(0);
    
    // Find the max propagation depth from the scores
    const maxDepth = atRiskData?.scores?.reduce((max: number, score: any) => {
      return Math.max(max, score.propagation_depth || 0);
    }, 0) || 0;

    let wave = 0;
    const interval = setInterval(() => {
      if (wave >= maxDepth) {
        clearInterval(interval);
        setSimulationState('cascaded');
      } else {
        wave += 1;
        setCurrentWave(wave);
      }
    }, 1500); // 1500ms per wave for dramatic effect
  };

  const handleIntervene = async () => {
    try {
      const data = await apiClient.intervene({}, []);
      setInterveneData(data);
      setSimulationState('intervened');
    } catch (err) {
      console.error(err);
    }
  };

  const handleReset = () => {
    setSimulationState('idle');
    setInterveneData(null);
    setCurrentWave(0);
  };

  const stats = useMemo(() => {
    if (!networkData?.nodes) return { healthy: 0, stressed: 0, critical: 0 };
    
    // If we have intervene data and state is intervened, use after.scores, else atRiskData.scores
    const activeScores = (simulationState === 'intervened' && interveneData?.after?.scores) 
      ? interveneData.after.scores 
      : atRiskData?.scores || [];
      
    // Count from the active scores
    let critical = 0;
    let stressed = 0;
    
    activeScores.forEach((s: any) => {
      if (s.final_score > 0.6) critical++;
      else if (s.final_score > 0.3) stressed++;
    });
    
    const healthy = networkData.nodes.length - critical - stressed;
    return { healthy, stressed, critical };
  }, [networkData, atRiskData, interveneData, simulationState]);

  // Determine which data to pass to the graph
  const graphData = useMemo(() => {
    if (!networkData) return null;
    if (simulationState === 'intervened' && interveneData?.after) {
      // In intervened state, the nodes/edges might be identical but we want the updated scores
      return {
        ...networkData,
        scores: interveneData.after.scores
      };
    }
    return {
      ...networkData,
      scores: atRiskData?.scores || []
    };
  }, [networkData, atRiskData, interveneData, simulationState]);

  return (
    <div className="app">
      <nav className="nav">
        <div className="nav-brand">
          <div className="nav-logo">
            <svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Network graph icon — nodes connected by edges */}
              <circle cx="14" cy="6" r="3" fill="#f87171" opacity="0.9"/>
              <circle cx="6" cy="18" r="2.5" fill="#fbbf24" opacity="0.8"/>
              <circle cx="22" cy="18" r="2.5" fill="#fbbf24" opacity="0.8"/>
              <circle cx="14" cy="24" r="2" fill="#34d399" opacity="0.7"/>
              <line x1="14" y1="9" x2="6" y2="15.5" stroke="#60a5fa" strokeWidth="1.2" opacity="0.5"/>
              <line x1="14" y1="9" x2="22" y2="15.5" stroke="#60a5fa" strokeWidth="1.2" opacity="0.5"/>
              <line x1="6" y1="20.5" x2="14" y2="22" stroke="#60a5fa" strokeWidth="1" opacity="0.3"/>
              <line x1="22" y1="20.5" x2="14" y2="22" stroke="#60a5fa" strokeWidth="1" opacity="0.3"/>
            </svg>
          </div>
          <div className="nav-brand-name">Fray<span>Fuse</span></div>
        </div>
        <div className="nav-stakeholder-switcher">
          <button className="stakeholder-btn active">Anchor</button>
          <button className="stakeholder-btn">Bank / NBFC</button>
          <button className="stakeholder-btn">Supplier</button>
        </div>
      </nav>

      <div className="dashboard">
        <HeaderBar 
          stats={stats} 
          simulationState={simulationState} 
          onRunCascade={handleRunCascade}
          onIntervene={handleIntervene}
          onReset={handleReset}
        />

        <div className="graph-panel">
          {loading ? (
            <div style={{ padding: '5rem', color: 'var(--text-secondary)' }}>Initializing FrayFuse Engine...</div>
          ) : (
            <NetworkGraph data={graphData} simulationState={simulationState} currentWave={currentWave} />
          )}
          
          {simulationState === 'cascading' && (
            <div className="cascade-status active">
              <div className="pulse"></div>
              <span>Propagating stress wave...</span>
            </div>
          )}
          {simulationState === 'intervened' && (
            <div className="cascade-status active resolved">
              <div className="pulse"></div>
              <span>Intervention applied — Risk contained</span>
            </div>
          )}
        </div>

        <aside className="side-panel">
          <div className="panel-section">
            <div className="panel-section-title">Stakeholder View</div>
            <div className="stakeholder-context">
              <div className="stakeholder-context-title">Anchor View</div>
              <div className="stakeholder-context-desc">
                Full network, ranked list, intervention controls, and total exposure across all tiers.
              </div>
            </div>
          </div>

          <div className="panel-section">
            <div className="panel-section-title">Fragile & Critical Suppliers</div>
            {loading ? (
              <div style={{ color: 'var(--text-secondary)' }}>Loading...</div>
            ) : (
              <RankedList 
                scores={simulationState === 'intervened' ? interveneData?.after?.scores : atRiskData?.scores} 
                nodes={networkData?.nodes} 
                simulationState={simulationState}
                currentWave={currentWave}
              />
            )}
          </div>

          {simulationState === 'intervened' && interveneData?.delta && (
            <InterventionCard 
              delta={interveneData.delta} 
              onCounterfactual={() => setSimulationState('cascaded')}
            />
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
