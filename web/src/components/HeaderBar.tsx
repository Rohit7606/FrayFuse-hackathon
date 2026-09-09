interface HeaderBarProps {
  stats: { healthy: number; stressed: number; critical: number };
  simulationState: 'idle' | 'cascading' | 'cascaded' | 'intervened';
  onRunCascade: () => void;
  onIntervene: () => void;
  onReset: () => void;
}

export default function HeaderBar({ stats, simulationState, onRunCascade, onIntervene, onReset }: HeaderBarProps) {
  return (
    <div className="header-bar">
      <div className="header-left">
        <div className="header-title">Auto Manufacturing Supply Chain</div>
        <div className="header-stats">
          <div className="header-stat">
            <div className="dot dot-green"></div>
            <span>{stats.healthy} Healthy</span>
          </div>
          <div className="header-stat">
            <div className="dot dot-amber"></div>
            <span>{stats.stressed} Stressed</span>
          </div>
          <div className="header-stat">
            <div className="dot dot-red"></div>
            <span>{stats.critical} Critical</span>
          </div>
        </div>
      </div>
      <div className="header-right">
        <button 
          className="btn" 
          onClick={onRunCascade}
          disabled={simulationState !== 'idle'}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          Run Cascade
        </button>
        {simulationState === 'cascaded' && (
          <button className="btn btn-success" onClick={onIntervene}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Intervene
          </button>
        )}
        {(simulationState === 'cascaded' || simulationState === 'intervened') && (
          <button className="btn btn-danger" onClick={onReset}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
