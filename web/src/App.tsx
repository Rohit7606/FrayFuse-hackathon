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
    // In a real app we'd fetch apiClient.simulate(scenario) here
    // For demo, we just wait a bit to simulate the animation, then switch to 'cascaded'
    setTimeout(() => {
      setSimulationState('cascaded');
    }, 2500);
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
              <circle cx="14" cy="14" r="12" stroke="#60a5fa" strokeWidth="1.5" opacity="0.3"/>
              <circle cx="14" cy="14" r="7" stroke="#60a5fa" strokeWidth="1.5" opacity="0.6"/>
              <circle cx="14" cy="14" r="3" fill="#60a5fa"/>
              <line x1="14" y1="2" x2="14" y2="7" stroke="#60a5fa" strokeWidth="1" opacity="0.4"/>
              <line x1="14" y1="21" x2="14" y2="26" stroke="#60a5fa" strokeWidth="1" opacity="0.4"/>
              <line x1="2" y1="14" x2="7" y2="14" stroke="#60a5fa" strokeWidth="1" opacity="0.4"/>
              <line x1="21" y1="14" x2="26" y2="14" stroke="#60a5fa" strokeWidth="1" opacity="0.4"/>
            </svg>
          </div>
          <div className="nav-brand-name">Chain<span>Watch</span></div>
        </div>
        <div className="nav-links">
          <button className="nav-link active">Network</button>
          <button className="nav-link">Signals</button>
          <button className="nav-link">History</button>
        </div>
        <div className="nav-stakeholder-switcher">
          <button className="stakeholder-btn active">Anchor Treasury</button>
          <button className="stakeholder-btn">Bank / NBFC</button>
          <button className="stakeholder-btn">MSME Supplier</button>
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
            <NetworkGraph data={graphData} simulationState={simulationState} />
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
              <div className="stakeholder-context-title">Anchor Treasury</div>
              <div className="stakeholder-context-desc">
                You see your Tier-1 vendors and a payment calendar. Everything below Tier-1 is invisible to you today.
              </div>
            </div>
          </div>

          <div className="panel-section">
            <div className="panel-section-title">Fragile & Critical Suppliers</div>
            {loading ? (
              <div style={{ color: 'var(--text-secondary)' }}>Loading...</div>
            ) : (
              <RankedList scores={simulationState === 'intervened' ? interveneData?.after?.scores : atRiskData?.scores} />
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
