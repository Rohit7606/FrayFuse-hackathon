interface RankedListProps {
  scores: any[];
}

export default function RankedList({ scores }: RankedListProps) {
  if (!scores || scores.length === 0) {
    return <div style={{ color: 'var(--text-secondary)' }}>No at-risk suppliers detected.</div>;
  }

  // Ensure we sort by rank (nulls at the bottom if any)
  const sortedScores = [...scores].sort((a, b) => {
    if (a.rank === null) return 1;
    if (b.rank === null) return -1;
    return a.rank - b.rank;
  });

  return (
    <div className="ranked-list">
      {sortedScores.map((score) => (
        <div key={score.node_id} className="ranked-item">
          <div className="ranked-item-header">
            <span className="ranked-item-title">{score.node_id}</span>
            <span className={`badge ${score.risk_band}`}>
              {score.risk_band}
            </span>
          </div>
          <div className="ranked-item-score">
            Rank: {score.rank || 'N/A'} • Score: {score.final_score.toFixed(4)}
          </div>
          <div className="ranked-item-reason">
            {score.reason_text}
          </div>
        </div>
      ))}
    </div>
  );
}
