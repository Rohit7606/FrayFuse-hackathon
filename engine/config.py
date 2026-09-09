"""All tunable constants for the FrayFuse engine, in one place.

Every constant has a one-line comment explaining what it means and why
it has that value.  No magic numbers elsewhere in the codebase.
"""

# ---------------------------------------------------------------------------
# Randomness (mockgen only)
# ---------------------------------------------------------------------------

MOCK_SEED = 42  # default seed for deterministic mock generation

# ---------------------------------------------------------------------------
# Graph construction  (engine/graph.py)
# ---------------------------------------------------------------------------

# Which evidential levels may carry stress.  schema_change_request.md §1 asks
# that only edges a company named in its own filing propagate automatically:
# "probable" is inference from a third party and must not be given the standing
# of disclosure.  The mock network is entirely "confirmed", so this is a no-op
# there and only bites when the real dataset lands.
PROPAGATING_EDGE_CONFIDENCE = frozenset({"confirmed"})

MAX_EXPOSURE_SUM_TOLERANCE = 1.02  # a supplier's outgoing exposure may exceed 1.0 only by rounding

# ---------------------------------------------------------------------------
# Stress detection  (engine/stress.py)
# ---------------------------------------------------------------------------

# Signal ladder, ordered by control-tested discriminating power.  Evidence for
# every weight is in data/real/DATA_DICTIONARY.md §6 and findings.md §5.
#
# The original spec weighted "late-payment intensity" at 0.65, computed from
# msmed_principal_paid_beyond_appointed_day.  Collection found that field
# disclosed in 3 of 46 company-years, all belonging to a single control
# company.  It cannot carry the model and is now the last rung.
#
# Availability varies enormously between filers, so weights are RENORMALISED
# over whichever rungs are computable for a given company: a company with only
# rung 1 available scores on rung 1 at full weight.  Never substitute a default
# for an unavailable signal — see AGENTS.md §3.6 on null vs zero.

W_INTEREST_DIRECTION = 0.45  # MSMED interest rose YoY — pre-event 6/8, controls 0/7; needs no Not Due column
W_MIGRATION = 0.25           # Not Due → overdue share rose >20pp — clean separation, but only n=2 events
W_PAYABLES_REVENUE = 0.20    # payables ÷ revenue rising — distress +4.0/+5.2pp vs controls −1.8/−2.2pp
W_NONMSME_AGEING = 0.10      # non-MSME aged-bucket growth — fallback where the MSME book is immaterial

# RETIRED — MSME balance growth.  Control Bharat Gears posted +629% in a year
# CARE upgraded it, against distress case Nectar's +583%.  Does not
# discriminate; suspected s.43B(h) reclassification, not payment behaviour.
# Do not reinstate without re-testing against the control cohort.

MIGRATION_THRESHOLD_PP = 20.0  # rung 2 fires above +20pp; 18 measured no-event transitions top out at +15.5

MIN_SECTOR_SAMPLE = 3  # minimum sector peers for z-score; below this, fall back to global stats

EPSILON = 1e-6  # floor for standard-deviation denominators to prevent division by zero

# ---------------------------------------------------------------------------
# Contagion  (engine/contagion.py)
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 10     # upper bound on propagation iterations; convergence usually happens in 4–5
CONVERGENCE_THRESHOLD = 0.001  # max absolute change across all nodes to declare convergence
DAMPING = 0.75          # each hop transmits 75% of upstream fragility; prevents long-chain blowup
BUFFER_REF_DAYS = 90    # cash-buffer reference: 90 days ≈ a well-buffered mid-tier firm

# Cap on how far cash buffer can damp inherited stress.  Was 0.9, which let the
# buffer term swing per-hop transmission by 10x and made it the dominant force
# in propagation.  Collection measured cash_buffer_days across 44 verified
# company-years — 22 distress, 22 control — and it does not separate them:
# AUC 0.569 against a 0.500 coin flip.  The lowest buffers in the set belong to
# an investment-grade control (Balrampur Chini, 0 days) and the highest to a
# company that collapsed months later (Gensol, 351 days, cash later found not
# to be what the balance sheet claimed).
#
# Buffer is kept because absorbing a payment delay for longer is mechanically
# real, but a measurement this noisy must nudge rather than decide.  At 0.35 the
# per-hop swing is 1.54x instead of 10x.  Prefer undrawn committed facilities
# over reported cash once that field is populated — see schema_change_request.md
# gap 6 (liquidity quality).
MAX_BUFFER_STRENGTH = 0.35

# ---------------------------------------------------------------------------
# Criticality  (engine/criticality.py)
# ---------------------------------------------------------------------------

# Normalise betweenness and flow share within tier rather than across the whole
# network.  Both are size-correlated by construction, so a network-wide maximum
# hands both to the tier-1 hub: measured on the mock at seed 42, the hub took
# betweenness 0.875 and flow share 1.000 while a genuine sole-source tier-2
# chokepoint scored 0.137 and 0.012.  That made 0.65 of criticality a proxy for
# revenue and filled the ranked list with large stressed companies instead of the
# small irreplaceable ones the product exists to find.  Within tier, the same
# chokepoint scores 0.475 against a comparably stressed non-sole-source peer's
# 0.178 — the 2.7x separation DEMO_SCENARIO.md §3 rests its argument on.
# Set false to restore the original network-wide behaviour.
NORMALISE_CRITICALITY_WITHIN_TIER = True

W_BETWEENNESS = 0.45    # graph position — how many paths pass through this node
W_SINGLE_SOURCE = 0.35  # irreplaceability — sole-source edges have outsized supply-chain impact
W_FLOW_SHARE = 0.20     # share of total network trade flowing through this node

# ---------------------------------------------------------------------------
# Risk bands  (engine/ranking.py)
# ---------------------------------------------------------------------------

# Recalibrated to the score distribution the model actually produces.
#
# final_score is the product of two sub-1 factors, and fragility is damped twice
# on the way down the chain (once by DAMPING, once by the buffer term), so the
# realistic range is far narrower than the original 0.50/0.30/0.15 assumed.  On
# the mock at seed 42 the whole non-origin population fits under 0.21, and the
# original thresholds banded every deep-tier supplier "stable" — including the
# sole-source chokepoint the demo is built around.
#
# These are a calibration to an observed distribution, not a claim about the
# world.  What carries meaning is the ORDERING and the separation between bands,
# not the absolute numbers: the headline finding sits at 0.204 against the next
# node's 0.090, a 2.3x gap.  Say that plainly rather than implying 0.20 is a
# measured threshold for corporate distress.  Re-derive them if DAMPING,
# MAX_BUFFER_STRENGTH or the criticality weights change.
BAND_CRITICAL = 0.20   # final_score >= 0.20 -> "critical"
BAND_HIGH = 0.06       # 0.06 - 0.20 -> "high"
BAND_WATCH = 0.012     # 0.012 - 0.06 -> "watch"
# below 0.012 -> "stable"

# ---------------------------------------------------------------------------
# Intervention  (engine/intervention.py)
# ---------------------------------------------------------------------------

# Below this many days of cash, a node's buffer is worth calling out in its
# reason text.  Presentation only — it does not enter any score.  Chosen from
# the collected tier-1 median of 12-15 days: a fortnight of cover against a
# stretched payment cycle is the point where the buffer stops being a cushion.
THIN_BUFFER_DAYS = 21

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
