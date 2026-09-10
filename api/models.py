"""
Pydantic v2 models mirroring the runtime contract.
"""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

NodeId = Annotated[str, Field(pattern=r"^N[0-9]{3,}$")]
EdgeId = Annotated[str, Field(pattern=r"^E[0-9]{3,}$")]

DataSource = Literal["real", "synthetic"]
RiskBand = Literal["critical", "high", "watch", "stable"]
AgeingBasis = Literal["due_date", "transaction_date"]
EdgeConfidence = Literal["confirmed", "probable", "concentration_only"]
EdgeProvenance = Literal[
    "related_party_note", "related_party", "mdna", "segment_note", "rating_agency",
    "awards_page", "press", "auditor_note", "contingent_liability_note", "synthetic",
]
ObservationCompleteness = Literal["observed", "partially_observed", "not_observed"]


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0", "1.1"]
    generated_at: datetime
    generator: Literal["mockgen", "transform"]
    currency_unit: Literal["INR_crore"]
    node_count: Annotated[int, Field(ge=0)]
    edge_count: Annotated[int, Field(ge=0)]
    seed: int | None = None
    observable_node_count: int | None = None
    source_units_note: str | None = None


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    name: Annotated[str, Field(min_length=3)]
    tier: Annotated[int, Field(ge=0, le=3)]
    sector: str
    product_category: str
    is_observable: bool
    data_source: DataSource
    # Nullable since schema 1.1: a real company whose filings do not disclose the
    # figure carries null and names the field in `substituted`, rather than
    # having a number invented for it (DATA_DICTIONARY.md §3b).
    revenue_cr: Annotated[float | None, Field(ge=0.0)] = None
    cash_buffer_days: Annotated[int | None, Field(ge=0)] = None
    substituted: list[str] = Field(default_factory=list)
    employees: Annotated[int | None, Field(ge=0)] = None
    cin: str | None = None
    observation_completeness: ObservationCompleteness | None = None


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: EdgeId
    supplier_id: NodeId
    buyer_id: NodeId
    component: str
    annual_value_cr: float
    exposure_pct: Annotated[float, Field(ge=0.0, le=1.0)]
    data_source: DataSource
    # null means UNKNOWN — no filing stated sole-source status. `false` is
    # itself a claim that alternatives exist. Never coerce one to the other.
    is_single_source: bool | None = None
    confidence: EdgeConfidence = "confirmed"
    edge_provenance: EdgeProvenance | None = None


class StressSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    fy: Annotated[str, Field(pattern=r"^FY[0-9]{2}$")]
    has_not_due_column: bool
    basis: Literal["standalone", "consolidated"]
    data_source: DataSource
    ageing_basis: AgeingBasis = "due_date"
    msme_unbilled_cr: float | None = None
    msme_not_due_cr: float | None = None
    msme_under_1yr_cr: float | None = None
    msme_1_2yr_cr: float | None = None
    msme_2_3yr_cr: float | None = None
    msme_over_3yr_cr: float | None = None
    msme_total_cr: float | None = None
    nonmsme_total_cr: float | None = None
    total_trade_payables_cr: float | None = None
    msmed_principal_unpaid_year_end_cr: float | None = None
    msmed_principal_paid_beyond_appointed_day_cr: float | None = None
    msmed_interest_accrued_unpaid_cr: float | None = None
    revenue_cr: float | None = None
    cost_of_materials_cr: float | None = None
    trade_payables_turnover_ratio: float | None = None
    msmed_interest_due_unpaid_cr: float | None = None
    msmed_interest_due_on_payments_beyond_appointed_day_cr: float | None = None
    undrawn_credit_facilities_cr: float | None = None
    undrawn_type: str | None = None
    msme_book_material: bool | None = None
    series_break: str | None = None
    liquidity_quality: str | None = None


class NetworkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    nodes: list[Node]
    edges: list[Edge]
    stress_signals: list[StressSignal]


class ReasonFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    detail: str
    weight: float


class SubstitutionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    name: str
    component: str
    replaces_edge_id: EdgeId
    fitness: Annotated[float, Field(ge=0.0, le=1.0)]
    fragility: Annotated[float, Field(ge=0.0, le=1.0)]
    # null means the candidate's revenue is undisclosed, which is unknown
    # headroom and not zero headroom. Never coerce one to the other.
    capacity_headroom_cr: Annotated[float, Field(ge=0.0)] | None = None
    reason_text: str


class Score(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    own_stress: Annotated[float, Field(ge=0.0, le=1.0)]
    inherited_stress: Annotated[float, Field(ge=0.0, le=1.0)]
    fragility: Annotated[float, Field(ge=0.0, le=1.0)]
    criticality: Annotated[float, Field(ge=0.0, le=1.0)]
    final_score: Annotated[float, Field(ge=0.0, le=1.0)]
    risk_band: RiskBand
    reason_text: str
    reason_factors: list[ReasonFactor]
    intervention_cost_cr: float
    estimated_exposure_cr: float
    propagation_depth: int
    rank: int | None = None
    # Supply-disruption layer, schema 1.2. The second propagation, running with
    # goods flow: whose line stops when a supplier stops delivering.
    halt_risk: Annotated[float, Field(ge=0.0, le=1.0)]
    supply_disruption: Annotated[float, Field(ge=0.0, le=1.0)]
    disruption_band: RiskBand
    disrupted_inflow_cr: Annotated[float, Field(ge=0.0)]
    disruption_reason: str
    # Substitution, schema 1.3. ABSENT (None) means substitution was not
    # considered for this node; an EMPTY LIST means it was considered and
    # nobody qualified. Two different facts — see SCHEMA.md §4.6.
    substitution_candidates: list[SubstitutionCandidate] | None = None


class BandCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical: Annotated[int, Field(ge=0)]
    high: Annotated[int, Field(ge=0)]
    watch: Annotated[int, Field(ge=0)]
    stable: Annotated[int, Field(ge=0)]


class AnchorDisruption(BaseModel):
    """One tier-0 anchor's supply-disruption state, lifted out for the UI.

    DEMO_SCENARIO.md §6's closing beat reads these rather than scanning four
    hundred score objects for the three anchors.
    """

    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    supply_disruption: Annotated[float, Field(ge=0.0, le=1.0)]
    disruption_band: RiskBand
    disrupted_inflow_cr: Annotated[float, Field(ge=0.0)]
    stopped_by: NodeId | None = None


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_nodes: int
    at_risk_count: int
    band_counts: BandCounts
    total_intervention_cost_cr: float
    total_estimated_exposure_cr: float
    iterations_to_converge: int
    stressed_origin_nodes: list[str] | None = None
    max_propagation_depth: int | None = None
    anchor_disruption: list[AnchorDisruption] = Field(default_factory=list)
    disruption_iterations_to_converge: int | None = None


class ScoredNetwork(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    nodes: list[Node]
    edges: list[Edge]
    scores: list[Score]
    ranking: list[str]
    summary: Summary


class StressOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    # Bounded, so an out-of-range value is a readable 422 rather than being
    # silently clamped by the engine into something the caller did not ask for.
    own_stress: Annotated[float, Field(ge=0.0, le=1.0)]


class Intervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    # Funding cannot be negative. Unbounded, this reached compute_delta and
    # failed Delta's own ge=0 constraint at *response* construction, which the
    # catch-all turned into a 500 — SCHEMA.md §5.6 forbids a 500 for a bad
    # request. Constrained here, it is a 422 naming the field.
    amount_cr: Annotated[float, Field(ge=0.0)]


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stress_overrides: list[StressOverride] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: Scenario
    # Score THIS network instead of the one the server loaded at startup.
    #
    # Added with ingestion (schema 1.3). The alternative was to keep the
    # uploaded network in server memory and hand back a handle, which is the
    # session state AGENTS.md §3.4 forbids. The client holds the network it
    # ingested and sends it with each scenario, so every request stays a pure
    # function of its own body and two clients can hold two different networks
    # without knowing about each other. Omitted, the default network is scored,
    # so nothing that worked before changes.
    network: NetworkInput | None = None


class InterveneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interventions: list[Intervention]
    baseline_scenario: Scenario | None = None
    # As on SimulateRequest — the client's own network, or the default.
    network: NetworkInput | None = None


class IngestReport(BaseModel):
    """What the upload contained and what was made of it.

    A demo asset rather than debug output: `fields_null` against
    `fields_present` is the number behind "most of this network is dark",
    which is the product's own thesis.
    """

    model_config = ConfigDict(extra="forbid")

    files_seen: list[str]
    files_used: dict[str, str]
    files_ignored: list[str]
    rows_parsed: dict[str, int]
    companies_read: int
    nodes_built: int
    edges_built: int
    generated_nodes: int
    observable_nodes: int
    fields_present: int
    fields_null: int
    warnings: list[str]


class NetworkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    nodes: list[Node]
    edges: list[Edge]
    # The published disclosures the stress ladder reads, passed through
    # unchanged. Additive and optional, so an older client that forbids extras
    # is unaffected and a network file without signals still serves.
    #
    # The evidence panel shows a judge WHERE own_stress came from: the year-end
    # ageing snapshot beside the whole-year MSMED payment lines. Without this
    # the frontend would have to hardcode those rupee figures, which is exactly
    # the fabrication AGENTS.md 3.6 forbids.
    stress_signals: list[StressSignal] = Field(default_factory=list)


class AtRiskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    ranking: list[str]
    scores: list[Score]
    summary: Summary


class IngestResponse(ScoredNetwork):
    """The scored network built from an upload, plus what the upload held.

    Carries `stress_signals` as well as the ScoredNetwork fields, because the
    client needs the whole NetworkInput back: to show the evidence panel, and
    to send it with the scenario requests that follow (see SimulateRequest).
    """

    model_config = ConfigDict(extra="forbid")

    stress_signals: list[StressSignal] = Field(default_factory=list)
    ingest_report: IngestReport


class PerNodeDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    fragility_before: float
    fragility_after: float
    band_before: RiskBand
    band_after: RiskBand


class Delta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes_improved: Annotated[int, Field(ge=0)]
    nodes_worsened: Annotated[int, Field(ge=0)]
    total_exposure_reduced_cr: float
    total_intervention_cost_cr: Annotated[float, Field(ge=0.0)]
    per_node: list[PerNodeDelta]


class InterveneResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before: ScoredNetwork
    after: ScoredNetwork
    delta: Delta


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str
    detail: str
    node_id: str | None = None
