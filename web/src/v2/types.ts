/**
 * The slice of SCHEMA.md the console actually reads.
 *
 * Deliberately not a full transcription of the contract — api/models.py is
 * already a second copy of it and SCHEMA.md §6 warns about a third drifting.
 * Everything here is a field the UI renders, so a missing one shows up as a
 * blank in the interface rather than as a silently wrong number.
 */

export type RiskBand = 'stable' | 'watch' | 'high' | 'critical';
export type DataSource = 'real' | 'synthetic' | 'derived' | 'estimated';

export interface Node {
  node_id: string;
  name: string;
  tier: number;
  sector: string;
  product_category: string;
  revenue_cr: number | null;
  cash_buffer_days: number | null;
  employees: number | null;
  is_observable: boolean;
  data_source: DataSource;
  cin: string | null;
  substituted?: string[];
  observation_completeness?: number | null;
}

export interface Edge {
  edge_id: string;
  supplier_id: string;
  buyer_id: string;
  component: string;
  annual_value_cr: number;
  exposure_pct: number;
  data_source: DataSource;
  /** null means UNKNOWN — no filing stated sole-source status. Never coerce. */
  is_single_source: boolean | null;
  confidence?: string;
  edge_provenance?: string | null;
}

/** One published ageing / MSMED row, exactly as filed. */
export interface StressSignal {
  node_id: string;
  fy: string;
  has_not_due_column: boolean;
  basis: 'standalone' | 'consolidated';
  data_source: DataSource;
  ageing_basis: string;
  msme_unbilled_cr: number | null;
  msme_not_due_cr: number | null;
  msme_under_1yr_cr: number | null;
  msme_1_2yr_cr: number | null;
  msme_2_3yr_cr: number | null;
  msme_over_3yr_cr: number | null;
  msme_total_cr: number | null;
  nonmsme_total_cr: number | null;
  total_trade_payables_cr: number | null;
  msmed_principal_unpaid_year_end_cr: number | null;
  msmed_principal_paid_beyond_appointed_day_cr: number | null;
  msmed_interest_accrued_unpaid_cr: number | null;
  msmed_interest_due_unpaid_cr?: number | null;
  msmed_interest_due_on_payments_beyond_appointed_day_cr?: number | null;
  revenue_cr: number | null;
  cost_of_materials_cr: number | null;
  trade_payables_turnover_ratio: number | null;
  msme_book_material?: boolean | null;
  series_break?: string | null;
  liquidity_quality?: string | null;
}

export interface ReasonFactor {
  kind: string;
  detail: string;
  weight: number;
}

/** One alternative supplier who could take over one relationship. */
export interface SubstitutionCandidate {
  node_id: string;
  name: string;
  component: string;
  replaces_edge_id: string;
  fitness: number;
  fragility: number;
  /** null means the candidate's revenue is undisclosed — unknown headroom, not zero. */
  capacity_headroom_cr: number | null;
  reason_text: string;
}

export interface Score {
  node_id: string;
  own_stress: number;
  inherited_stress: number;
  fragility: number;
  criticality: number;
  final_score: number;
  risk_band: RiskBand;
  propagation_depth: number;
  rank: number | null;
  reason_text?: string;
  reason_factors?: ReasonFactor[];
  intervention_cost_cr: number;
  estimated_exposure_cr: number;
  /** Supply-disruption layer (schema 1.2) — failure travelling back up. */
  halt_risk?: number;
  supply_disruption?: number;
  disruption_band?: RiskBand;
  disrupted_inflow_cr?: number;
  disruption_reason?: string;
  /**
   * Substitution, schema 1.3. THREE states, and they are three different facts
   * (SCHEMA.md §4.6):
   *   undefined / null — not considered: too critical, a confirmed sole source,
   *                      sole-source status undisclosed, or supplies nobody
   *   []               — considered, and nobody qualified
   *   non-empty        — up to three alternatives, best fitness first
   */
  substitution_candidates?: SubstitutionCandidate[] | null;
}

export interface AnchorDisruption {
  node_id: string;
  supply_disruption: number;
  disruption_band: RiskBand;
  disrupted_inflow_cr: number;
  stopped_by: string | null;
}

export interface Summary {
  total_nodes: number;
  at_risk_count: number;
  band_counts: Partial<Record<RiskBand, number>>;
  total_intervention_cost_cr: number;
  total_estimated_exposure_cr: number;
  iterations_to_converge: number;
  stressed_origin_nodes: string[];
  max_propagation_depth: number;
  anchor_disruption?: AnchorDisruption[];
  disruption_iterations_to_converge?: number;
}

export interface Meta {
  schema_version: string;
  node_count: number;
  edge_count: number;
  observable_node_count?: number;
  currency_unit: string;
  generator?: string;
  seed?: number | null;
}

export interface NetworkPayload {
  meta: Meta;
  nodes: Node[];
  edges: Edge[];
  /** Optional and additive in schema 1.2. Absent on an older backend. */
  stress_signals?: StressSignal[];
}

export interface ScoredNetwork {
  meta: Meta;
  nodes?: Node[];
  edges?: Edge[];
  scores: Score[];
  ranking: string[];
  summary: Summary;
}

/** What an upload contained and what was made of it. A demo asset. */
export interface IngestReport {
  files_seen: string[];
  files_used: Record<string, string>;
  files_ignored: string[];
  rows_parsed: Record<string, number>;
  companies_read: number;
  nodes_built: number;
  edges_built: number;
  generated_nodes: number;
  observable_nodes: number;
  fields_present: number;
  fields_null: number;
  warnings: string[];
}

export interface IngestResponse extends ScoredNetwork {
  nodes: Node[];
  edges: Edge[];
  stress_signals: StressSignal[];
  ingest_report: IngestReport;
}

export interface PerNodeDelta {
  node_id: string;
  fragility_before: number;
  fragility_after: number;
  band_before: RiskBand;
  band_after: RiskBand;
}

export interface Delta {
  nodes_improved: number;
  nodes_worsened: number;
  total_exposure_reduced_cr: number;
  total_intervention_cost_cr: number;
  per_node: PerNodeDelta[];
}

export interface InterveneResponse {
  before: ScoredNetwork;
  after: ScoredNetwork;
  delta: Delta;
}

export interface Intervention {
  node_id: string;
  amount_cr: number;
}

export interface DemoScenario {
  scenario_id: string;
  description: string;
  trigger_node: string;
  expected_ranking: string[];
  intervention: Intervention;
  counterfactual_anchor: string;
}
