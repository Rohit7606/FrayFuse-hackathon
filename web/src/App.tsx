import { useEffect, useState } from 'react';
import { apiClient } from './api/client';
import NetworkGraph from './components/NetworkGraph';
import RankedList from './components/RankedList';
import './index.css';

function App() {
  const [networkData, setNetworkData] = useState<any>(null);
  const [atRiskData, setAtRiskData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

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

  return (
    <div className="app-container">
      <header className="header">
        <h1>FrayFuse</h1>
      </header>

      <main className="main-content">
        {loading ? (
          <div style={{ padding: '5rem', color: 'var(--text-secondary)' }}>Initializing FrayFuse Engine...</div>
        ) : (
          <NetworkGraph data={networkData} />
        )}
      </main>

      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>At-Risk Suppliers</h2>
        </div>
        <div className="sidebar-content">
          {loading ? (
            <div style={{ color: 'var(--text-secondary)' }}>Loading...</div>
          ) : (
            <RankedList scores={atRiskData?.scores || []} />
          )}
        </div>
      </aside>
    </div>
  );
}

export default App;
