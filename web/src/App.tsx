import { useEffect, useState, useMemo } from 'react';
import { apiClient } from './api/client';
import demoScenario from './mocks/demo-scenario.json';
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
      // DEMO_SCENARIO.md §8: read the node and amount from the fixture rather
      // than hardcoding them here. This sent an EMPTY interventions array,
      // which mock mode hid because it returns a pre-baked intervene.json —
      // against the live API it funded nothing and before/after came back
      // identical.
      const data = await apiClient.intervene(
        { stress_overrides: [], interventions: [] },
        [demoScenario.intervention]
      );
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
    // Read summary.band_counts rather than re-deriving bands from final_score.
    //
    // This used to count `final_score > 0.6` as critical and `> 0.3` as
    // stressed, which were the ORIGINAL thresholds. Schema 1.1 recalibrated
    // them to 0.20 / 0.06 / 0.012 because the model's real range is far
    // narrower — nothing in the network scores above 0.21 — so both counters
    // were permanently zero and the header read "412 Healthy, 0 Stressed,
    // 0 Critical" while the engine was flagging a critical supplier.
    //
    // The engine bands every node from engine/config.py and reports the totals
    // in summary.band_counts. That covers all 412 nodes, where `scores` here
    // holds only the ranked top ten, so this is both correct and complete.
    const summary = (simulationState === 'intervened' && interveneData?.after?.summary)
      ? interveneData.after.summary
      : atRiskData?.summary;

    const counts = summary?.band_counts;
    if (!counts) return { healthy: 0, stressed: 0, critical: 0 };

    return {
      critical: counts.critical ?? 0,
      stressed: (counts.high ?? 0) + (counts.watch ?? 0),
      healthy: counts.stable ?? 0,
    };
  }, [atRiskData, interveneData, simulationState]);

  // The worst-hit anchor before funding, and THE SAME anchor after.
  //
  // summary.anchor_disruption is sorted by disruption descending, and the
  // order changes once the intervention lands: N001 leads at 0.1076 before,
  // but afterwards N251 (0.0394) edges past N001 (0.0392). Taking [0] from
  // each list would pair one anchor's "before" with another's "after" and
  // print a number that belongs to neither.
  const anchorBeat = useMemo(() => {
    const before = interveneData?.before?.summary?.anchor_disruption?.[0];
    if (!before) return {};
    const after = interveneData?.after?.summary?.anchor_disruption
      ?.find((a: any) => a.node_id === before.node_id);
    return after ? { anchorBefore: before, anchorAfter: after } : {};
  }, [interveneData]);

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
              <RankedList scores={simulationState === 'intervened' ? interveneData?.after?.scores : atRiskData?.scores} />
            )}
          </div>

          {simulationState === 'intervened' && interveneData?.delta && (
            <InterventionCard 
              delta={interveneData.delta} 
              {...anchorBeat}
              onCounterfactual={() => setSimulationState('cascaded')}
            />
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
