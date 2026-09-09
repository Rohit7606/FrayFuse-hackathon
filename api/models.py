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


class BandCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical: Annotated[int, Field(ge=0)]
    high: Annotated[int, Field(ge=0)]
    watch: Annotated[int, Field(ge=0)]
    stable: Annotated[int, Field(ge=0)]


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
    own_stress: float


class Intervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NodeId
    amount_cr: float


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stress_overrides: list[StressOverride] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: Scenario


class InterveneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interventions: list[Intervention]
    baseline_scenario: Scenario | None = None


class NetworkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    nodes: list[Node]
    edges: list[Edge]


class AtRiskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    ranking: list[str]
    scores: list[Score]
    summary: Summary


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
