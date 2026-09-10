/**
 * The slice of SCHEMA.md the console actually reads.
 *
 * Deliberately not a full transcription of the contract — api/models.py is
 * already a second copy of it and SCHEMA.md §6 warns about a third drifting.
 * Everything here is a field the UI renders, so a missing one shows up as a
 * blank in the interface rather than as a silently wrong number.
 */

export type RiskBand = 'stable' | 'watch' | 'high' | 'critical';

/**
 * Which queue a supplier belongs in — a DECISION, not a score (SCHEMA.md 4.7).
 *
 * Not derivable from risk_band on this side: fragility 0.35 x criticality 0.20
 * and fragility 0.10 x criticality 0.70 are the same final_score and the
 * opposite response. The engine reads the two factors apart; the UI reads the
 * queue it produced and never re-derives it here.
 */
export type TriageQueue = 'fund_now' | 'derisk' | 'monitor' | 'clear' | 'origin';
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
  /** Triage, schema 1.4. Absent on an older backend. */
  triage_queue?: TriageQueue | null;
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

/** One of the two readings behind a queue, stated separately. */
export interface TriageStatus {
  kind: 'fragility' | 'replaceability';
  verdict: 'fragile' | 'holding' | 'irreplaceable' | 'replaceable';
  detail: string;
}

/** A threshold that, once crossed, moves a watched supplier to the funding queue. */
export interface ReviewTrigger {
  metric: 'fragility' | 'criticality' | 'alternatives' | 'buyer_own_stress';
  current: number;
  threshold: number;
  detail: string;
}

export interface PlanDependency {
  buyer_id: string;
  buyer_name: string;
  edge_id: string;
  component: string;
  exposure_pct: number;
  annual_value_cr: number;
  buyer_is_stressed_origin: boolean;
  buyer_own_stress: number;
  buyer_fragility: number;
}

export interface RecommendedAction {
  kind: 'fund' | 'derisk' | 'monitor' | 'none';
  label: string;
  /** null where money is not the answer — a different fact from ₹0.00 cr. */
  amount_cr?: number | null;
}

export interface DeriskPlan {
  node_id: string;
  name: string;
  tier: number;
  queue: TriageQueue;
  queue_label: string;
  headline: string;
  fragility: number;
  criticality: number;
  final_score: number;
  risk_band: RiskBand;
  status: TriageStatus[];
  exposure_at_risk_cr: number;
  stabilisation_cost_cr: number;
  inherited_share: number;
  /** null means substitution was not considered; 0 means it was and nobody qualified. */
  alternatives_found?: number | null;
  dependency?: PlanDependency | null;
  review_triggers: ReviewTrigger[];
  actions: string[];
  recommended_action: RecommendedAction;
}

/** One supplier's share of a budget, and what it bought. */
export interface Allocation {
  node_id: string;
  name: string;
  rank?: number | null;
  amount_cr: number;
  cost_cr: number;
  coverage: number;
  /**
   * Measured with this supplier funded ALONE. Suppliers on one chain each get
   * credit for relieving it, so these can sum to more than
   * `objective.reduced_cr` — which is the joint figure and the one to show.
   */
  measured_benefit_cr: number;
  efficiency: number;
  exposure_at_risk_cr: number;
  fragility_before: number;
  fragility_after: number;
  band_before: RiskBand;
  band_after: RiskBand;
}

export interface AllocationObjective {
  metric: 'anchor_inflow_at_risk_cr';
  before_cr: number;
  after_cr: number;
  reduced_cr: number;
}

export interface AllocateResponse {
  budget_cr: number;
  allocated_cr: number;
  unallocated_cr: number;
  objective: AllocationObjective;
  allocations: Allocation[];
  candidates_considered: string[];
  scoring_runs: number;
  note: string;
  delta: Delta;
  summary_before: Summary;
  summary_after: Summary;
}
