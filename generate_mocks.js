const fs = require('fs');

const network = JSON.parse(fs.readFileSync('web/src/mocks/network.json'));
const atRisk = JSON.parse(fs.readFileSync('web/src/mocks/at-risk.json'));

const baseScore = {
  own_stress: 0.0,
  inherited_stress: 0.0,
  fragility: 0.0,
  criticality: 0.1,
  final_score: 0.0,
  risk_band: "stable",
  rank: null,
  reason_text: "Node is stable.",
  reason_factors: [
    { kind: "own_stress", detail: "Stable operations", weight: 1.0 }
  ],
  intervention_cost_cr: 0.0,
  estimated_exposure_cr: 0.0,
  propagation_depth: 0
};

const scores = [...atRisk.scores];
// add N001
scores.push({
  ...baseScore,
  node_id: "N001"
});
// add N007
scores.push({
  ...baseScore,
  node_id: "N007",
  own_stress: 0.85,
  fragility: 0.85,
  criticality: 0.5,
  final_score: 0.425,
  risk_band: "high",
  reason_text: "Own stress is high.",
  reason_factors: [
    { kind: "own_stress", detail: "Late payments", weight: 1.0 }
  ]
});

const simulate = {
  meta: network.meta,
  nodes: network.nodes,
  edges: network.edges,
  scores: scores,
  ranking: atRisk.ranking,
  summary: atRisk.summary
};

fs.writeFileSync('web/src/mocks/simulate.json', JSON.stringify(simulate, null, 2));

const intervene = {
  before: simulate,
  after: {
    ...simulate,
    scores: simulate.scores.map(s => {
      if (s.node_id === "N042") return { ...s, fragility: 0.1102, risk_band: "stable", final_score: 0.1, rank: null };
      if (s.node_id === "N118") return { ...s, fragility: 0.2, risk_band: "watch", final_score: 0.2, rank: 4 };
      return s;
    }),
    ranking: simulate.ranking.filter(id => id !== "N042")
  },
  delta: {
    nodes_improved: 7,
    nodes_worsened: 0,
    total_exposure_reduced_cr: 148.30,
    total_intervention_cost_cr: 4.80,
    per_node: [
      { node_id: "N042", fragility_before: 0.6314, fragility_after: 0.1102, band_before: "critical", band_after: "stable" }
    ]
  }
};

fs.writeFileSync('web/src/mocks/intervene.json', JSON.stringify(intervene, null, 2));

console.log('Mocks generated successfully');
