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

# Runtime fill for a real company whose filings do not disclose a buffer.
#
# 41 of 46 collected company-years have no cash_buffer_days, so the alternative
# to substituting is dropping most real nodes from the graph.  The tier-1 value
# is the measured median across 29 verified company-years; the others are stated
# assumptions with no observation behind them, because the collected cohort is
# entirely listed manufacturers.  Nodes filled this way carry the field in their
# `substituted` list so the UI can label it — DATA_DICTIONARY.md §3b requires
# the substitution to be visible rather than frozen into the data.
SUBSTITUTE_BUFFER_DAYS_BY_TIER: dict[int, int] = {0: 60, 1: 12, 2: 10, 3: 8}
DEFAULT_SUBSTITUTE_BUFFER_DAYS = 12

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
# Substitution  (engine/substitution.py)
# ---------------------------------------------------------------------------

# The criticality at or below which a supplier is treated as replaceable enough
# to be worth suggesting alternatives for.
#
# Calibrated to the distribution this model actually produces, not to a claim
# about the world.  On data/mock/network.json at seed 42 criticality runs
# lower quartile 0.0370, median 0.0805, upper decile 0.2975; 0.04 sits just
# above the lower quartile, so roughly the bottom quarter of the network is in
# scope and 109 of 412 nodes qualify.  On data/real/network.json the quartile
# is lower still (0.0183) and 124 nodes fall under the same threshold, so the
# constant is not tuned to one dataset's shape.
#
# Raise it and the suggestions start reaching nodes the ranked list is warning
# about, which is a contradiction on one screen.  Re-derive it if the
# criticality weights or NORMALISE_CRITICALITY_WITHIN_TIER change.
SUBSTITUTION_CRITICALITY_MAX = 0.04

# Fitness weights.  Health leads because a replacement that is itself failing is
# not a replacement at any capacity, whereas a healthy supplier that is a little
# tight can usually stretch.  They sum to 1.0; a candidate whose revenue is
# undisclosed drops the capacity term and renormalises onto health.
W_SUB_HEALTH = 0.60     # 1 - fragility of the candidate
W_SUB_CAPACITY = 0.40   # spare revenue against the volume being taken on, normalised within tier

# Suggestions kept per supplier.  Three is a decision aid; a full list is a
# search result, and nobody reads past the third row on a slide anyway.
SUBSTITUTION_MAX_CANDIDATES = 3

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
# Supply-disruption bands  (engine/disruption.py, banded in engine/ranking.py)
# ---------------------------------------------------------------------------

# supply_disruption is a different quantity from final_score — the chance a
# node's line stops for want of an input, not fragility x criticality — so it
# gets its own thresholds rather than borrowing the ones above.
#
# They currently hold the SAME values, and that is an observation, not a
# shortcut: measured on the mock at seed 42 the two distributions have
# comparable shape.  Disruption tops out at 0.5916 (the tier-1 that cannot
# source its sole-sourced seal kit), the next node sits at 0.2514, the two
# anchors at 0.1076 and 0.1073, and the 90th percentile of the 124 nodes with
# any disruption at all is 0.0423.
#
# Deliberately NOT calibrated to put the demo's anchor in the top band.  At
# these thresholds N001 bands "high" at baseline and drops to "watch" once N042
# is funded.  A DISRUPTION_BAND_CRITICAL of 0.10 would make it "critical"
# instead, and it would be reverse-engineering a threshold to fit one node —
# the gap between 0.1076 and the 0.0980 below it is 9%, which is not a break
# the distribution supports.  Change these only with a reason that is about the
# distribution, not about the demo.
DISRUPTION_BAND_CRITICAL = 0.20  # supply_disruption >= 0.20 -> "critical"
DISRUPTION_BAND_HIGH = 0.06      # 0.06 - 0.20 -> "high"
DISRUPTION_BAND_WATCH = 0.012    # 0.012 - 0.06 -> "watch"
# below 0.012 -> "stable"

# ---------------------------------------------------------------------------
# Ingestion  (engine/ingest.py) — added for the judged demo, AGENTS.md §1.5
# ---------------------------------------------------------------------------

# Caps that make a hostile zip a 422 rather than an outage.  A zip bomb is a
# small file that expands without limit, so the guard has to be on the declared
# uncompressed size and the member count, checked BEFORE anything is written.
#
# The collection set this was sized against is five CSVs totalling under 2 MB,
# so both caps sit an order of magnitude above anything a real upload needs.
INGEST_MAX_MEMBERS = 200            # files in the archive
INGEST_MAX_UNCOMPRESSED_BYTES = 64 * 1024 * 1024   # 64 MB expanded
INGEST_MAX_UPLOAD_BYTES = 16 * 1024 * 1024         # 16 MB on the wire

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
# Transform build-time constants  (engine/transform.py)
# ---------------------------------------------------------------------------

# Fixed, not now().  Set at data-build time so the same CSVs always produce a
# byte-identical network.json — AGENTS.md §3.1.
TRANSFORM_GENERATED_AT = "2026-09-09T00:00:00Z"

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


# ---------------------------------------------------------------------------
# Synthetic deep tier for the real dataset  (engine/mockgen.py, called by
# engine/transform.py)
# ---------------------------------------------------------------------------

# The collected cohort is 43 nodes that bottom out at 3-node chains, so nothing
# propagates: the real network scores 0 at-risk and converges in 1 iteration.
# SCHEMA.md §7.1 step 5 always intended a generated tier-2/tier-3 layer beneath
# the real tier-0/1 companies; this is that layer's shape.
DEEP_TIER_SEED = 42  # fixed, so the same CSVs always produce a byte-identical network.json

# Synthetic tier-2 suppliers per real tier-1 buyer, and tier-3 per tier-2.
# Lower than MOCK_TIER1_FANOUT (20-42) because the real cohort has 11 tier-1
# companies rather than 28, and a 400-node layer under a 43-node real graph
# would make the synthetic tail visibly the whole product.
# Sized against the pool rather than guessed.  9 of the 11 real tier-1 companies
# are auto ancillaries, as are all 14 real tier-2s, so essentially the whole
# demand lands on the pool's auto_components bucket (264 of 358 names).  At an
# average fanout of 9 the generated auto layer needs ~190 of those 264, which
# leaves headroom for the draw to vary.  Raise this and the pool runs dry —
# synthesise_deep_tier raises rather than reusing a name.
DEEP_TIER1_FANOUT = (6, 12)   # tier-2 suppliers each real tier-1 buys from
DEEP_TIER2_FANOUT = (1, 3)    # tier-3 suppliers each tier-2 buys from

# Sole-source edges are placed ONLY where the BUYER is synthetic.  An edge
# saying "this supplier is the sole source for <real company>" is a fabricated
# claim about a real company's sourcing arrangements, which DATA_DICTIONARY.md
# §3b forbids outright.  Confining chokepoints to synthetic buyers keeps the
# claim inside the generated layer, and costs the demo nothing: the product's
# thesis is that the irreplaceable supplier sits deep in the chain anyway.
DEEP_TIER_CHOKEPOINTS = 5  # genuine sole-source relationships in the generated layer
