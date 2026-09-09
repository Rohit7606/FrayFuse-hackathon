"""All tunable constants for the FrayFuse engine, in one place.

Every constant has a one-line comment explaining what it means and why
it has that value.  No magic numbers elsewhere in the codebase.
"""

# ---------------------------------------------------------------------------
# Randomness (mockgen only)
# ---------------------------------------------------------------------------

MOCK_SEED = 42  # default seed for deterministic mock generation

# ---------------------------------------------------------------------------
# Stress detection  (engine/stress.py)
# ---------------------------------------------------------------------------

W_MIGRATION = 0.35  # weight of migration-ratio signal — lower because ageing table can be window-dressed
W_LATE = 0.65       # weight of late-payment intensity — primary signal; whole-year flow cannot be tidied

MIN_SECTOR_SAMPLE = 3  # minimum sector peers for z-score; below this, fall back to global stats

EPSILON = 1e-6  # floor for standard-deviation denominators to prevent division by zero

# ---------------------------------------------------------------------------
# Contagion  (engine/contagion.py)
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 10     # upper bound on propagation iterations; convergence usually happens in 4–5
CONVERGENCE_THRESHOLD = 0.001  # max absolute change across all nodes to declare convergence
DAMPING = 0.75          # each hop transmits 75% of upstream fragility; prevents long-chain blowup
BUFFER_REF_DAYS = 90    # cash-buffer reference: 90 days ≈ a well-buffered mid-tier firm
MAX_BUFFER_STRENGTH = 0.9  # nobody is fully immune — cap at 0.9 so even large firms carry some risk

# ---------------------------------------------------------------------------
# Criticality  (engine/criticality.py)
# ---------------------------------------------------------------------------

W_BETWEENNESS = 0.45    # graph position — how many paths pass through this node
W_SINGLE_SOURCE = 0.35  # irreplaceability — sole-source edges have outsized supply-chain impact
W_FLOW_SHARE = 0.20     # share of total network trade flowing through this node

# ---------------------------------------------------------------------------
# Risk bands  (engine/ranking.py)
# ---------------------------------------------------------------------------

BAND_CRITICAL = 0.50  # final_score ≥ 0.50 → "critical"
BAND_HIGH = 0.30      # 0.30 – 0.50 → "high"
BAND_WATCH = 0.15     # 0.15 – 0.30 → "watch"
# below 0.15 → "stable"

# ---------------------------------------------------------------------------
# Intervention  (engine/intervention.py)
# ---------------------------------------------------------------------------

DISRUPTION_MONTHS = 3  # assumed disruption window for exposure calculation — a stated assumption, not measured

# ---------------------------------------------------------------------------
# Mock generation build-time constants  (engine/mockgen.py)
# ---------------------------------------------------------------------------

MOCK_GENERATED_AT = "2026-08-27T00:00:00Z"  # fixed, not now() — same seed must give a byte-identical file
MOCK_NODE_COUNT = 412  # total nodes in the mock network; ~400 per the brief
MOCK_TIER_PLAN = {0: 3, 1: 28, 2: 130, 3: 251}  # nodes per tier; sums to MOCK_NODE_COUNT
MOCK_TIER1_FANOUT = (20, 42)  # suppliers per tier-1 buyer — real Tier-1s have dozens, not three
MOCK_TIER2_FANOUT = (1, 4)    # tier-3 suppliers per tier-2 buyer
MOCK_TIER0_FANOUT = (1, 2)    # anchors each tier-1 supplies
MOCK_MAX_EXPOSURE_SUM = 1.0   # a supplier's outgoing exposure_pct may not exceed its whole revenue
