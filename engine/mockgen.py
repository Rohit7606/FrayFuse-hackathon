"""Synthetic network generator for FrayFuse.

Produces a deterministic mock network.json conforming to the
NetworkInput schema.  Randomness is permitted HERE and NOWHERE ELSE
in the engine — use a local random.Random(seed), never the global module.

Usage:
    python -m engine.mockgen --seed 42 --out data/mock/network.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from engine import config

# ---------------------------------------------------------------------------
# The fixed demo cast — DEMO_SCENARIO.md §2
#
# These six IDs are placed explicitly before any filler is generated, so that
# regenerating the mock network can never move them.  Names, tiers and the
# relationships between them are committed in DEMO_SCENARIO.md and must match.
# ---------------------------------------------------------------------------

PINNED_NODES: tuple[dict[str, Any], ...] = (
    {
        "node_id": "N001",
        "name": "Hindmark Motors India Ltd",
        "tier": 0,
        "sector": "automotive_oem",
        "product_category": "passenger_vehicles",
        "revenue_cr": 18422.60,
        "cash_buffer_days": 214,
        "employees": 11840,
        "is_observable": True,
    },
    {
        "node_id": "N007",
        "name": "Brakecraft Components Ltd",
        "tier": 1,
        "sector": "auto_components",
        "product_category": "brake_systems",
        "revenue_cr": 2969.08,
        "cash_buffer_days": 71,
        "employees": 2340,
        "is_observable": True,
    },
    {
        "node_id": "N042",
        "name": "Sealsworks Rubber Industries Pvt Ltd",
        "tier": 2,
        "sector": "auto_components",
        "product_category": "sealing_systems",
        "revenue_cr": 24.70,
        "cash_buffer_days": 18,
        "employees": 42,
        "is_observable": False,
    },
    {
        "node_id": "N087",
        "name": "Vaayu Thermal Products Pvt Ltd",
        "tier": 2,
        "sector": "auto_components",
        "product_category": "thermal_products",
        "revenue_cr": 61.35,
        "cash_buffer_days": 16,
        "employees": 96,
        "is_observable": False,
    },
    {
        "node_id": "N118",
        "name": "Precision Polymer Works Pvt Ltd",
        "tier": 3,
        "sector": "polymers",
        "product_category": "polymer_compounds",
        "revenue_cr": 9.84,
        "cash_buffer_days": 8,
        "employees": 23,
        "is_observable": False,
    },
    {
        "node_id": "N203",
        "name": "Kalyani Fastener Systems Pvt Ltd",
        "tier": 2,
        "sector": "auto_components",
        "product_category": "fasteners",
        "revenue_cr": 47.12,
        "cash_buffer_days": 34,
        "employees": 78,
        "is_observable": False,
    },
)

# Relationships from DEMO_SCENARIO.md §2-3.  exposure_pct is the fraction of the
# SUPPLIER's revenue that this one buyer accounts for.  N042's 0.7773 against
# N203's 0.61, with only N042 sole-source, is the contrast the ranking rests on.
PINNED_EDGES: tuple[dict[str, Any], ...] = (
    {
        "supplier_id": "N007",
        "buyer_id": "N001",
        "component": "brake_assembly",
        "exposure_pct": 0.4180,
        "is_single_source": False,
    },
    {
        "supplier_id": "N042",
        "buyer_id": "N007",
        "component": "hydraulic_seal_kit",
        "exposure_pct": 0.7773,
        "is_single_source": True,
    },
    {
        "supplier_id": "N203",
        "buyer_id": "N007",
        "component": "fastener_systems",
        "exposure_pct": 0.6100,
        "is_single_source": False,
    },
    {
        "supplier_id": "N087",
        "buyer_id": "N007",
        "component": "thermal_products",
        "exposure_pct": 0.4600,
        "is_single_source": False,
    },
    {
        "supplier_id": "N118",
        "buyer_id": "N042",
        "component": "polymer_compound",
        "exposure_pct": 0.7200,
        "is_single_source": True,
    },
)

# Secondary buyers for the pinned suppliers, so the demo cast are not
# suspiciously single-edge nodes.  Buyer IDs are drawn from the generated
# tier-1 pool at build time; only the exposure split is fixed here.
PINNED_SECONDARY_EXPOSURE: dict[str, tuple[tuple[str, float], ...]] = {
    "N007": (("drivetrain_modules", 0.2140),),
    "N042": (("moulded_seals", 0.1050), ("o_ring_sets", 0.0620)),
    "N203": (("cold_forged_bolts", 0.1800), ("stud_assemblies", 0.1100)),
    "N087": (("radiator_cores", 0.2200), ("heat_shields", 0.1700), ("oil_coolers", 0.1400)),
    "N118": (("masterbatch_compound", 0.1900),),
}

# How many tier-3 suppliers each tier-2 cast member must have beneath it.
#
# Betweenness counts paths THROUGH a node, so a tier-2 firm with one supplier
# sits on almost none and scores as replaceable however exposed it is.  Without
# a supplier base the demo cast is out-ranked by generic filler and
# DEMO_SCENARIO.md §3's contrast never appears in the list.
#
# N203 deliberately gets the LARGEST base.  It is the better-connected node and
# still ranks below N042, which is the sharpest form of the argument: being
# central is not the same as being irreplaceable.  N042 wins on the sole-source
# term alone.
PINNED_TIER2_FANIN: dict[str, int] = {"N042": 6, "N087": 9, "N203": 12}

PINNED_IDS = tuple(n["node_id"] for n in PINNED_NODES)


# ---------------------------------------------------------------------------
# Name generation
#
# Plausibility is not cosmetic here.  A network full of "Company_47" reads as a
# toy and invites a judge to dismiss the whole project, so names are composed
# from realistic Indian manufacturing stems, trades and suffixes.  Every name is
# fictional (DEMO_SCENARIO.md §9); the mock layer is labelled synthetic
# throughout so nothing here can be mistaken for a real filer.
# ---------------------------------------------------------------------------

NAME_STEMS: tuple[str, ...] = (
    "Aarvik", "Adhira", "Amaravati", "Anantham", "Ashwamedh", "Avaneesh",
    "Bhavani", "Chandrika", "Chitrakoot", "Daksha", "Devansh", "Dhruvtara",
    "Girinath", "Harshad", "Indraprast", "Jagriti", "Jyotirmay", "Kaveri",
    "Kesariya", "Kritika", "Lakshmee", "Madhuban", "Mahendra", "Manthan",
    "Meghdoot", "Naganath", "Narmada", "Navrachna", "Nilkanth", "Ojaswi",
    "Panchvati", "Parvati", "Pratapgarh", "Purnima", "Rajhans", "Rameshwar",
    "Ratnadeep", "Rudraksh", "Sahyadri", "Samarth", "Sanchita", "Saptagiri",
    "Sarvodaya", "Shivneri", "Shreeyash", "Siddhivin", "Somnath", "Suryakant",
    "Tejaswini", "Trishul", "Udaygiri", "Vaikunth", "Vajrapani", "Vasundhara",
    "Vidyut", "Vindhyachal", "Virajpet", "Vishwakarm", "Yashodhan", "Zorawar",
)

NAME_TRADES: tuple[str, ...] = (
    "Auto", "Autotech", "Castings", "Engineering", "Forgings", "Industries",
    "Metalworks", "Moulders", "Polymers", "Precision", "Rubber", "Springs",
    "Stampings", "Toolings", "Treatments", "Turned Parts",
)

NAME_KINDS: tuple[str, ...] = (
    "Components", "Engineering", "Enterprises", "Industries", "Products",
    "Systems", "Works",
)

# Suffixes by tier — deep-tier firms are private limited, anchors are listed.
NAME_SUFFIX_BY_TIER: dict[int, tuple[str, ...]] = {
    0: ("India Ltd", "Motors India Ltd", "Ltd"),
    1: ("Ltd", "India Ltd", "Industries Ltd"),
    2: ("Pvt Ltd", "Private Ltd", "Pvt Ltd"),
    3: ("Pvt Ltd", "Udyog Pvt Ltd", "Pvt Ltd"),
}

SECTOR_BY_TIER: dict[int, tuple[str, ...]] = {
    0: ("automotive_oem",),
    1: ("auto_components", "auto_electricals"),
    2: ("auto_components", "metal_forming", "polymers", "auto_electricals"),
    3: ("metal_forming", "polymers", "surface_treatment", "raw_materials"),
}

PRODUCT_BY_SECTOR: dict[str, tuple[str, ...]] = {
    "automotive_oem": ("passenger_vehicles", "commercial_vehicles"),
    "auto_components": (
        "brake_systems", "sealing_systems", "fasteners", "thermal_products",
        "transmission_parts", "suspension_parts", "steering_assemblies",
    ),
    "auto_electricals": ("wiring_harness", "starter_motors", "sensor_modules", "lighting_assemblies"),
    "metal_forming": ("precision_machining", "forgings", "castings", "sheet_metal", "cold_forming"),
    "polymers": ("polymer_compounds", "injection_moulding", "rubber_moulding", "sealing_compounds"),
    "surface_treatment": ("electroplating", "heat_treatment", "powder_coating"),
    "raw_materials": ("alloy_steel", "aluminium_billets", "synthetic_rubber", "engineering_plastics"),
}

# Revenue in ₹ crore by tier, as (lognormal mu, lognormal sigma, floor, cap).
# Heavily skewed on purpose: a few large firms, a long tail of tiny ones.
REVENUE_SHAPE_BY_TIER: dict[int, tuple[float, float, float, float]] = {
    0: (9.30, 0.35, 6000.0, 26000.0),
    1: (6.60, 0.80, 240.0, 4200.0),
    2: (3.70, 0.75, 6.0, 180.0),
    3: (2.30, 0.70, 1.2, 34.0),
}

# Days of operating cost each tier can survive unpaid.
#
# Tier 1 is EMPIRICAL.  Collection measured cash_buffer_days across 29 verified
# company-years of listed Indian tier-1 manufacturers: median 12 days, quartiles
# 4 and 30.5, maximum 266.  The previous 60–100 band was roughly 5x too generous
# and put every real tier-1 below the mock's floor.  See data/real/findings.md.
#
# Tiers 0, 2 and 3 are STATED ASSUMPTIONS, not measurements.  The collected
# cohort is entirely listed manufacturers, so there is no observation of an OEM
# anchor or of an unlisted deep-tier supplier.  Do not describe them as measured.
#
# Note also that a real uniform draw is wrong: the observed distribution is
# heavily right-skewed (median 12, max 266).  These ranges bracket the observed
# IQR rather than reproducing the tail.
#
# The tier gradient is deliberately shallower than before.  Collection showed
# buffer does not separate distress from healthy companies at all (AUC 0.569
# over 44 company-years), so it is no longer the mechanism that makes deep tiers
# fail first — exposure concentration is.  See engine/config.py
# MAX_BUFFER_STRENGTH.
BUFFER_RANGE_BY_TIER: dict[int, tuple[int, int]] = {
    0: (60, 200),  # assumption — OEM anchors hold real cash, but none observed
    1: (3, 45),    # empirical — brackets observed q1=4 to q3=30 with headroom
    2: (2, 30),    # assumption — unobserved
    3: (1, 20),    # assumption — unobserved
}

# Revenue in ₹ crore per employee, used to derive a plausible headcount.
REVENUE_PER_EMPLOYEE_CR = 0.42


def _draw_revenue(rng: random.Random, tier: int) -> float:
    """Draw a revenue inside the tier's range without clamping to its bounds.

    Clamping a lognormal draw piles nodes onto the exact cap, producing a run of
    identical round figures.  Nothing says "generated" faster, so out-of-range
    draws are resampled and only a jittered fallback ever touches the bound.
    """
    mu, sigma, floor, cap = REVENUE_SHAPE_BY_TIER[tier]
    for _ in range(50):
        revenue = rng.lognormvariate(mu, sigma)
        if floor <= revenue <= cap:
            return revenue
    return rng.uniform(floor, cap)


def _compose_name(rng: random.Random, tier: int, used: set[str]) -> str:
    """Compose a unique, plausible company name for the given tier."""
    for _ in range(200):
        parts = [rng.choice(NAME_STEMS)]
        kind = rng.choice(NAME_KINDS)
        if rng.random() < 0.55:
            trade = rng.choice(NAME_TRADES)
            # "Toolings Engineering Works" reads like a generated string; a real
            # firm names its trade or its kind, not both when they overlap.
            if trade != kind:
                parts.append(trade)
        parts.append(kind)
        parts.append(rng.choice(NAME_SUFFIX_BY_TIER[tier]))
        # The trade-vs-kind guard above misses the suffix, which carries its own
        # leading word: kind "Industries" plus suffix "Industries Ltd" produced
        # "Chandrika Stampings Industries Industries Ltd".  Collapsed after
        # assembly rather than by redrawing, so the RNG stream — and therefore
        # every number in the committed network — is untouched.
        words = " ".join(parts).split()
        name = " ".join(
            word for index, word in enumerate(words)
            if index == 0 or word.lower() != words[index - 1].lower()
        )
        if name not in used:
            used.add(name)
            return name
    raise RuntimeError("exhausted the name pool — widen NAME_STEMS")


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def _node_id(index: int) -> str:
    return f"N{index:03d}"


def _assign_tiers(rng: random.Random) -> dict[str, int]:
    """Map every node_id to a tier, with the demo cast pinned to theirs.

    The demo IDs are not contiguous by tier (N118 is tier 3 and sits between two
    tier-2 nodes), so tiers cannot simply be ID ranges.  Pinned tiers are placed
    first and the remainder drawn from a shuffled bag sized by MOCK_TIER_PLAN.
    """
    tiers = {n["node_id"]: n["tier"] for n in PINNED_NODES}

    bag: list[int] = []
    for tier, count in sorted(config.MOCK_TIER_PLAN.items()):
        pinned_in_tier = sum(1 for t in tiers.values() if t == tier)
        bag.extend([tier] * (count - pinned_in_tier))
    rng.shuffle(bag)

    remaining = [
        _node_id(i)
        for i in range(1, config.MOCK_NODE_COUNT + 1)
        if _node_id(i) not in tiers
    ]
    if len(bag) != len(remaining):
        raise RuntimeError("MOCK_TIER_PLAN does not sum to MOCK_NODE_COUNT")

    for node_id, tier in zip(remaining, bag):
        tiers[node_id] = tier
    return tiers


def _generate_nodes(rng: random.Random) -> list[dict[str, Any]]:
    """Build all nodes, pinned cast first, then plausible filler."""
    tiers = _assign_tiers(rng)
    used_names = {n["name"] for n in PINNED_NODES}
    pinned_by_id = {n["node_id"]: n for n in PINNED_NODES}
    nodes: list[dict[str, Any]] = []

    for index in range(1, config.MOCK_NODE_COUNT + 1):
        node_id = _node_id(index)
        tier = tiers[node_id]

        if node_id in pinned_by_id:
            node = dict(pinned_by_id[node_id])
        else:
            sector = rng.choice(SECTOR_BY_TIER[tier])
            revenue = _draw_revenue(rng, tier)
            low, high = BUFFER_RANGE_BY_TIER[tier]
            node = {
                "node_id": node_id,
                "name": _compose_name(rng, tier, used_names),
                "tier": tier,
                "sector": sector,
                "product_category": rng.choice(PRODUCT_BY_SECTOR[sector]),
                "revenue_cr": round(revenue, 2),
                "cash_buffer_days": rng.randint(low, high),
                "employees": max(4, int(revenue / REVENUE_PER_EMPLOYEE_CR)),
                "is_observable": False,
            }

        # The mock layer is synthetic end to end.  is_observable marks a node
        # whose disclosures we model; data_source stays honest either way, so
        # the UI can never present a generated firm as a real filer.
        node["data_source"] = "synthetic"
        node["cin"] = None
        nodes.append(node)

    return nodes


# ---------------------------------------------------------------------------
# Edges
#
# Edges run supplier -> buyer, matching goods flow.  Stress will later propagate
# against this direction (SCHEMA.md §2.2).  exposure_pct is always a fraction of
# the SUPPLIER's revenue, so a supplier's outgoing exposures must not exceed 1.0.
# ---------------------------------------------------------------------------

# Fraction of a supplier's revenue accounted for by its disclosed relationships.
# Never the full 1.0 — every firm has some business outside the modelled graph.
EXPOSURE_COVERAGE_RANGE = (0.45, 0.92)

EXTRA_CHOKEPOINT_COUNT = 3  # beyond the two pinned ones, giving 5 genuine single-source nodes


def _tier_pools(nodes: list[dict[str, Any]]) -> dict[int, list[str]]:
    pools: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: []}
    for node in nodes:
        pools[node["tier"]].append(node["node_id"])
    for pool in pools.values():
        pool.sort()
    return pools


def _component_for(product_category: str) -> str:
    """A supplier ships something named after what it makes."""
    return product_category


def _build_pairs(
    rng: random.Random, nodes: list[dict[str, Any]]
) -> tuple[list[tuple[str, str]], dict[tuple[str, str], dict[str, Any]]]:
    """Choose which supplier -> buyer relationships exist, pinned ones first.

    Returns the pair list plus the exposures that are fixed by DEMO_SCENARIO.md
    and must not be reallocated by the random split.
    """
    pools = _tier_pools(nodes)
    pairs: list[tuple[str, str]] = []
    fixed: dict[tuple[str, str], dict[str, Any]] = {}

    for edge in PINNED_EDGES:
        key = (edge["supplier_id"], edge["buyer_id"])
        pairs.append(key)
        fixed[key] = {
            "component": edge["component"],
            "exposure_pct": edge["exposure_pct"],
            "is_single_source": edge["is_single_source"],
        }

    # Secondary buyers for the pinned cast, drawn from the tier above them.
    secondary_pool = {
        "N007": [n for n in pools[0] if n != "N001"],
        "N042": [n for n in pools[1] if n != "N007"],
        "N203": [n for n in pools[1] if n != "N007"],
        "N087": [n for n in pools[1] if n != "N007"],
        "N118": [n for n in pools[2] if n != "N042"],
    }
    for supplier_id in sorted(PINNED_SECONDARY_EXPOSURE):
        secondaries = PINNED_SECONDARY_EXPOSURE[supplier_id]
        buyers = rng.sample(secondary_pool[supplier_id], len(secondaries))
        for buyer_id, (component, exposure) in zip(sorted(buyers), secondaries):
            key = (supplier_id, buyer_id)
            pairs.append(key)
            fixed[key] = {
                "component": component,
                "exposure_pct": exposure,
                "is_single_source": False,
            }

    # Pinned suppliers are exposure-locked: their outgoing edges are fully
    # specified above, so they are excluded from random selection below.
    locked = set(PINNED_SECONDARY_EXPOSURE)
    seen = set(pairs)

    def add(supplier_id: str, buyer_id: str) -> None:
        if supplier_id in locked or supplier_id == buyer_id:
            return
        if (supplier_id, buyer_id) not in seen:
            seen.add((supplier_id, buyer_id))
            pairs.append((supplier_id, buyer_id))

    # Tier 1 -> tier 0: each tier-1 firm supplies one or two anchors.
    for supplier_id in pools[1]:
        count = min(rng.randint(*config.MOCK_TIER0_FANOUT), len(pools[0]))
        for buyer_id in rng.sample(pools[0], count):
            add(supplier_id, buyer_id)

    # Tier 2 -> tier 1: a real Tier-1 has dozens of suppliers, not three.
    free_tier2 = [n for n in pools[2] if n not in locked]
    for buyer_id in pools[1]:
        count = min(rng.randint(*config.MOCK_TIER1_FANOUT), len(free_tier2))
        for supplier_id in rng.sample(free_tier2, count):
            add(supplier_id, buyer_id)

    # Tier 3 -> tier 2.
    free_tier3 = [n for n in pools[3] if n not in locked]
    for buyer_id in pools[2]:
        count = min(rng.randint(*config.MOCK_TIER2_FANOUT), len(free_tier3))
        for supplier_id in rng.sample(free_tier3, count):
            add(supplier_id, buyer_id)

    # The demo cast needs a real supplier base beneath it — see
    # PINNED_TIER2_FANIN for why betweenness collapses without one.
    for buyer_id in sorted(PINNED_TIER2_FANIN):
        shortfall = PINNED_TIER2_FANIN[buyer_id] - sum(1 for _, b in pairs if b == buyer_id)
        if shortfall <= 0:
            continue
        candidates = [n for n in free_tier3 if (n, buyer_id) not in seen]
        for supplier_id in sorted(rng.sample(candidates, min(shortfall, len(candidates)))):
            add(supplier_id, buyer_id)

    # Nobody is left stranded: a supplier with no buyer would sit outside the
    # graph entirely and could never carry or receive stress.
    has_buyer = {supplier_id for supplier_id, _ in pairs}
    for tier in (1, 2, 3):
        for supplier_id in pools[tier]:
            if supplier_id not in has_buyer and supplier_id not in locked:
                add(supplier_id, rng.choice(pools[tier - 1]))

    return pairs, fixed


def _generate_edges(
    rng: random.Random, nodes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build all edges and allocate each supplier's exposure across its buyers."""
    by_id = {n["node_id"]: n for n in nodes}
    pairs, fixed = _build_pairs(rng, nodes)

    buyers_of: dict[str, list[str]] = {}
    for supplier_id, buyer_id in pairs:
        buyers_of.setdefault(supplier_id, []).append(buyer_id)

    edges: list[dict[str, Any]] = []
    for supplier_id in sorted(buyers_of):
        buyers = sorted(buyers_of[supplier_id])
        supplier = by_id[supplier_id]

        preset = {b: fixed[(supplier_id, b)] for b in buyers if (supplier_id, b) in fixed}
        free = [b for b in buyers if b not in preset]

        headroom = config.MOCK_MAX_EXPOSURE_SUM - sum(
            p["exposure_pct"] for p in preset.values()
        )
        coverage = min(rng.uniform(*EXPOSURE_COVERAGE_RANGE), max(headroom, 0.0))

        # Skewed split: most suppliers have one or two dominant customers and a
        # tail of small ones, which is what creates real concentration risk.
        weights = [rng.expovariate(1.0) + 0.05 for _ in free]
        total_weight = sum(weights) or 1.0
        shares = {b: coverage * w / total_weight for b, w in zip(free, weights)}

        for buyer_id in buyers:
            if buyer_id in preset:
                spec = preset[buyer_id]
                exposure = spec["exposure_pct"]
                component = spec["component"]
                single_source = spec["is_single_source"]
            else:
                exposure = round(shares[buyer_id], 4)
                component = _component_for(supplier["product_category"])
                single_source = False
            if exposure <= 0.0:
                continue
            edges.append(
                {
                    "supplier_id": supplier_id,
                    "buyer_id": buyer_id,
                    "component": component,
                    "annual_value_cr": round(exposure * supplier["revenue_cr"], 2),
                    "exposure_pct": exposure,
                    "is_single_source": single_source,
                    "data_source": "synthetic",
                }
            )

    _add_extra_chokepoints(rng, edges)

    # Sorted before IDs are assigned, so edge_id is stable across regenerations.
    edges.sort(key=lambda e: (e["supplier_id"], e["buyer_id"]))
    for index, edge in enumerate(edges, start=1):
        edge["edge_id"] = f"E{index:03d}"
    return [
        {
            "edge_id": e["edge_id"],
            "supplier_id": e["supplier_id"],
            "buyer_id": e["buyer_id"],
            "component": e["component"],
            "annual_value_cr": e["annual_value_cr"],
            "exposure_pct": e["exposure_pct"],
            "is_single_source": e["is_single_source"],
            "confidence": "confirmed",
            "edge_provenance": "synthetic",
            "data_source": e["data_source"],
        }
        for e in edges
    ]


def _add_extra_chokepoints(rng: random.Random, edges: list[dict[str, Any]]) -> None:
    """Flag a few more genuine sole-source relationships.

    Criticality needs real chokepoints to find.  A network where only the demo
    node is single-source would make the ranking look rigged.
    """
    candidates = sorted(
        (
            e
            for e in edges
            if not e["is_single_source"]
            and e["exposure_pct"] > 0.5
            and e["supplier_id"] not in PINNED_IDS
        ),
        key=lambda e: (e["supplier_id"], e["buyer_id"]),
    )
    for edge in rng.sample(candidates, min(EXTRA_CHOKEPOINT_COUNT, len(candidates))):
        edge["is_single_source"] = True


# ---------------------------------------------------------------------------
# Stress signals
#
# Shaped like real Schedule III disclosures.  N007 carries the pattern the whole
# demo turns on: an ageing table that looks clean beside an MSMED note showing
# late payments doubling — both from the same filing (DEMO_SCENARIO.md step 3).
# ---------------------------------------------------------------------------

FY_YEARS = ("FY23", "FY24")
OBSERVABLE_COUNT = 8  # a handful of listed filers; everything below them is dark

# Positions in the observable list whose disclosures deteriorate year on year.
#
# Empty by design.  DEMO_SCENARIO.md §5 specifies a single stressed origin,
# N007, and the cascade story is that one trigger reaching four suppliers.  A
# second deteriorating peer creates a parallel stress branch whose suppliers
# interleave with the demo cast in the ranked list, so the list stops being "what
# N007 did" and the narration no longer matches the screen.
#
# The peers still matter: they are the quiet control cohort that makes N007's
# deterioration legible as a signal rather than as the only thing measured.
DETERIORATING_POSITIONS: frozenset[int] = frozenset()

# N007, both years, hand-built.  FY24 matches the worked example in SCHEMA.md
# §3.4 exactly; FY23 is its prior year, giving a 2.1x rise in the MSMED flow
# figure against an ageing table that barely moves.
N007_SIGNALS: tuple[dict[str, Any], ...] = (
    {
        "fy": "FY23",
        "msme_unbilled_cr": None,
        "msme_not_due_cr": 49.87,
        "msme_under_1yr_cr": 2.71,
        "msme_1_2yr_cr": 0.09,
        "msme_2_3yr_cr": 0.03,
        "msme_over_3yr_cr": 0.04,
        "msme_total_cr": 52.74,
        "nonmsme_total_cr": 331.44,
        "total_trade_payables_cr": 448.90,
        "msmed_principal_unpaid_year_end_cr": 31.20,
        "msmed_principal_paid_beyond_appointed_day_cr": 183.86,
        "msmed_interest_accrued_unpaid_cr": 0.94,
        "revenue_cr": 2784.31,
        "cost_of_materials_cr": 1798.20,
        "trade_payables_turnover_ratio": 5.62,
    },
    {
        "fy": "FY24",
        "msme_unbilled_cr": None,
        "msme_not_due_cr": 53.42,
        "msme_under_1yr_cr": 3.08,
        "msme_1_2yr_cr": 0.12,
        "msme_2_3yr_cr": 0.02,
        "msme_over_3yr_cr": 0.05,
        "msme_total_cr": 56.69,
        "nonmsme_total_cr": 360.20,
        "total_trade_payables_cr": 489.18,
        "msmed_principal_unpaid_year_end_cr": 50.63,
        "msmed_principal_paid_beyond_appointed_day_cr": 386.11,
        "msmed_interest_accrued_unpaid_cr": 2.02,
        "revenue_cr": 2969.08,
        "cost_of_materials_cr": 1904.55,
        "trade_payables_turnover_ratio": 5.41,
    },
)


def _peer_signals(
    rng: random.Random,
    node: dict[str, Any],
    omit_not_due: bool,
    omit_materials: bool,
    deteriorating: bool = False,
) -> list[dict[str, Any]]:
    """Two years of disclosures for an observable peer.

    The year-on-year direction of every figure the stress ladder reads is set
    deliberately by `deteriorating`, not left to independent draws per year.
    Drawing each year independently makes roughly half of all peers trip rung 1
    by accident, which buries the demo's trigger in noise and — worse — puts a
    stress score on the anchor, which DEMO_SCENARIO.md §2 says pays on time.
    """
    revenue = node["revenue_cr"]
    materials_ratio = rng.uniform(0.58, 0.68)
    late_intensity = rng.uniform(0.06, 0.14)
    migration = rng.uniform(0.03, 0.11)
    growth = rng.uniform(1.02, 1.09)

    # Drift multipliers applied to year two.  A quiet filer's figures hold flat
    # or improve; a deteriorating one's rise, but below N007's 2.1x so the
    # trigger stays the clearest case in the network.
    if deteriorating:
        late_drift = rng.uniform(1.25, 1.60)
        migration_drift = rng.uniform(1.05, 1.20)
        payables_drift = rng.uniform(1.04, 1.10)
        aged_drift = rng.uniform(1.10, 1.35)
    else:
        late_drift = rng.uniform(0.82, 0.97)
        migration_drift = rng.uniform(0.88, 1.02)
        payables_drift = rng.uniform(0.93, 0.99)
        aged_drift = rng.uniform(0.80, 0.96)

    # Every ratio is drawn once, before the year loop, then carried forward by
    # its drift multiplier.  Redrawing inside the loop is what made a filer's
    # direction accidental rather than intended.
    msme_ratio = rng.uniform(0.014, 0.022)
    nonmsme_ratio = rng.uniform(0.09, 0.16)
    aged_1_2_ratio = rng.uniform(0.001, 0.006)
    aged_2_3_ratio = rng.uniform(0.0002, 0.002)
    aged_over_3_ratio = rng.uniform(0.0002, 0.0015)
    unpaid_ratio = rng.uniform(0.5, 0.95)
    interest_ratio = rng.uniform(0.01, 0.05)
    turnover = rng.uniform(4.1, 7.3)

    rows: list[dict[str, Any]] = []
    for year_index, fy in enumerate(FY_YEARS):
        year_revenue = revenue / growth ** (len(FY_YEARS) - 1 - year_index)
        materials = year_revenue * materials_ratio
        year_migration = migration * migration_drift**year_index
        year_late = late_intensity * late_drift**year_index
        year_payables = payables_drift**year_index
        year_aged = aged_drift**year_index

        msme_total = year_revenue * msme_ratio * year_payables
        under_1yr = msme_total * year_migration
        not_due = msme_total - under_1yr
        aged_1_2 = msme_total * aged_1_2_ratio * year_aged
        aged_2_3 = msme_total * aged_2_3_ratio * year_aged
        aged_over_3 = msme_total * aged_over_3_ratio * year_aged
        nonmsme = year_revenue * nonmsme_ratio * year_payables
        interest = msme_total * interest_ratio * late_drift**year_index

        rows.append(
            {
                "fy": fy,
                "msme_unbilled_cr": None,
                # A filer who omits the Not Due column reports a combined figure
                # under_1yr that is NOT comparable with anyone else's.
                "msme_not_due_cr": None if omit_not_due else round(not_due, 2),
                "msme_under_1yr_cr": round(msme_total if omit_not_due else under_1yr, 2),
                "msme_1_2yr_cr": round(aged_1_2, 2),
                "msme_2_3yr_cr": round(aged_2_3, 2),
                "msme_over_3yr_cr": round(aged_over_3, 2),
                "msme_total_cr": round(msme_total + aged_1_2 + aged_2_3 + aged_over_3, 2),
                "nonmsme_total_cr": round(nonmsme, 2),
                "total_trade_payables_cr": round(msme_total + nonmsme, 2),
                "msmed_principal_unpaid_year_end_cr": round(msme_total * unpaid_ratio, 2),
                "msmed_principal_paid_beyond_appointed_day_cr": round(year_late * materials, 2),
                "msmed_interest_accrued_unpaid_cr": round(interest, 2),
                "revenue_cr": round(year_revenue, 2),
                "cost_of_materials_cr": None if omit_materials else round(materials, 2),
                "trade_payables_turnover_ratio": round(turnover, 2),
                "has_not_due_column": not omit_not_due,
            }
        )
    return rows


def _generate_stress_signals(
    rng: random.Random, nodes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Pick the observable filers and emit two years of disclosures for each.

    Mutates is_observable on the chosen nodes — only these have disclosures to
    read; every deeper node's stress must be inferred by propagation alone.
    """
    by_id = {n["node_id"]: n for n in nodes}
    tier1_pool = sorted(
        n["node_id"] for n in nodes if n["tier"] == 1 and n["node_id"] != "N007"
    )
    chosen = ["N001", "N007"] + sorted(rng.sample(tier1_pool, OBSERVABLE_COUNT - 2))

    signals: list[dict[str, Any]] = []
    for position, node_id in enumerate(chosen):
        node = by_id[node_id]
        node["is_observable"] = True

        if node_id == "N007":
            rows = [dict(r, has_not_due_column=True) for r in N007_SIGNALS]
        else:
            # One peer omits the Not Due column and one omits cost of materials,
            # so both fallback branches are exercised by the committed mock.
            #
            # N001 is the anchor and must read clean: DEMO_SCENARIO.md §2 says it
            # pays on time and has idle cash, and the counterfactual only lands
            # if it starts the demo green.  Two peers deteriorate mildly so the
            # ranked list is not suspiciously short, but none as sharply as N007.
            rows = _peer_signals(
                rng,
                node,
                omit_not_due=position == 2,
                omit_materials=position == 3,
                deteriorating=position in DETERIORATING_POSITIONS,
            )

        for row in rows:
            signals.append(
                {
                    "node_id": node_id,
                    **row,
                    "ageing_basis": "due_date",
                    "basis": "standalone",
                    "data_source": "synthetic",
                }
            )

    signals.sort(key=lambda s: (s["node_id"], s["fy"]))
    return signals


# ---------------------------------------------------------------------------
# Assembly, validation, CLI
# ---------------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"


def build_network(seed: int = config.MOCK_SEED) -> dict[str, Any]:
    """Generate the complete mock network for a seed.

    Deterministic: the same seed always yields an identical dict.  The only
    random.Random in the engine lives here.
    """
    rng = random.Random(seed)
    nodes = _generate_nodes(rng)
    edges = _generate_edges(rng, nodes)
    signals = _generate_stress_signals(rng, nodes)

    nodes.sort(key=lambda n: n["node_id"])
    edges.sort(key=lambda e: e["edge_id"])

    return {
        "meta": {
            "schema_version": "1.0",
            "generated_at": config.MOCK_GENERATED_AT,
            "generator": "mockgen",
            "seed": seed,
            "currency_unit": "INR_crore",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "observable_node_count": sum(1 for n in nodes if n["is_observable"]),
        },
        "nodes": nodes,
        "edges": edges,
        "stress_signals": signals,
    }


def check_invariants(network: dict[str, Any]) -> None:
    """Assert the structural rules schema.json cannot express.

    Raises ValueError on the failures that would silently corrupt the model
    rather than crash it.
    """
    node_ids = {n["node_id"] for n in network["nodes"]}

    for edge in network["edges"]:
        for role in ("supplier_id", "buyer_id"):
            if edge[role] not in node_ids:
                raise ValueError(f"{edge['edge_id']} has dangling {role} {edge[role]}")

    exposure_sum: dict[str, float] = {}
    for edge in network["edges"]:
        exposure_sum[edge["supplier_id"]] = (
            exposure_sum.get(edge["supplier_id"], 0.0) + edge["exposure_pct"]
        )
    for supplier_id, total in sorted(exposure_sum.items()):
        if total > 1.02:
            raise ValueError(f"{supplier_id} outgoing exposure_pct sums to {total:.4f} > 1.02")

    observable = {n["node_id"] for n in network["nodes"] if n["is_observable"]}
    for signal in network["stress_signals"]:
        if signal["node_id"] not in observable:
            raise ValueError(f"stress signal for non-observable node {signal['node_id']}")

    for node_id in PINNED_IDS:
        if node_id not in node_ids:
            raise ValueError(f"demo node {node_id} missing — DEMO_SCENARIO.md §8")


def validate(network: dict[str, Any]) -> None:
    """Validate against the NetworkInput definition in schema.json."""
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(
        instance=network,
        schema={
            "$schema": schema["$schema"],
            "definitions": schema["definitions"],
            "$ref": "#/definitions/NetworkInput",
        },
    )
    check_invariants(network)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the FrayFuse mock network.")
    parser.add_argument("--seed", type=int, default=config.MOCK_SEED)
    parser.add_argument("--out", type=Path, default=Path("data/mock/network.json"))
    args = parser.parse_args()

    network = build_network(args.seed)
    validate(network)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(network, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    meta = network["meta"]
    print(
        f"wrote {args.out}: {meta['node_count']} nodes, {meta['edge_count']} edges, "
        f"{meta['observable_node_count']} observable (seed {meta['seed']})"
    )


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Synthetic deep tier for the real dataset — SCHEMA.md §7.1 step 5
#
# transform.py reads entity_pool.csv and calls synthesise_deep_tier() to hang a
# generated tier-2/tier-3 layer beneath the real tier-0/1 companies.  It lives
# here, not in transform.py, because AGENTS.md §3.1 permits `random` in this
# module and nowhere else.  The seed is fixed in config, so the same CSVs always
# produce a byte-identical network.json.
#
# Everything this function emits is `data_source: "synthetic"` at row level.
# DATA_DICTIONARY.md §3b is explicit that tier-2 and tier-3 nodes, the edges
# below tier-1, and `component` / `is_single_source` / `annual_value_cr` on
# synthetic edges SHOULD be generated — and equally explicit that no rupee
# figure may ever sit next to a real company's name, and that no real company
# may be called a sole source.  Both rules are enforced below.
# ---------------------------------------------------------------------------

# product_category substrings -> sector, most specific first.  Ordered, because
# "solar_junction_box" must not be caught by the generic metal-forming rules.
# Anything unmatched is auto_components, which is both the pool's majority and
# the real cohort's dominant sector.
POOL_SECTOR_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pharmaceuticals", (
        "intermediate", "capsule", "ampoule", "blister", "vial", "excipient",
        "stearate", "croscarmellose", "hydroxypropyl", "enteric", "gelatin",
        "lidding", "tray_pack", "paracetamol", "ibuprofen",
    )),
    ("agrochemicals", (
        "technical", "formulation", "herbicide", "insecticide", "fungicide",
        "wettable", "granule", "coex_bottle", "agrochemical",
    )),
    ("sugar_and_ethanol", (
        "sugar_", "bagasse", "distillery", "ethanol", "calandria", "molasses",
        "centrifuge", "centrifugal_basket",
    )),
    ("cement_and_construction", (
        "cement_", "concrete_", "aggregate", "ready_mix", "kiln", "raw_mill",
        "admixture", "block_mould", "grinding_media",
    )),
    ("solar_ev", ("solar_", "battery_", "busbar", "ev_", "photovoltaic")),
    ("tractor_and_farm_equipment", ("tractor_", "pto_", "harvester", "plough")),
    ("power_tools", ("carbon_brush", "armature_winding")),
)

# Real buyer sector -> the pool sector its suppliers should come from.  An
# unmapped sector falls back to auto_components: the collected cohort is mostly
# auto ancillaries and their OEM customers.
BUYER_SECTOR_TO_POOL: dict[str, str] = {
    "pharmaceuticals": "pharmaceuticals",
    "pharma_brand_owner": "pharmaceuticals",
    "agrochemicals": "agrochemicals",
    "sugar": "sugar_and_ethanol",
    "cement_and_construction": "cement_and_construction",
    "solar_epc_and_ev": "solar_ev",
    "ev_fleet_operator": "solar_ev",
    "tractor_oem": "tractor_and_farm_equipment",
    "agricultural_equipment_oem": "tractor_and_farm_equipment",
    "power_tools_oem": "power_tools",
}


def classify_pool_sector(product_category: str) -> str:
    """Sector for one entity-pool row, from its product_category."""
    lowered = product_category.lower()
    for sector, needles in POOL_SECTOR_RULES:
        if any(needle in lowered for needle in needles):
            return sector
    return "auto_components"


def _pool_sector_for_buyer(buyer_sector: str) -> str:
    return BUYER_SECTOR_TO_POOL.get(buyer_sector, "auto_components")


def synthesise_deep_tier(
    pool_rows: list[dict[str, str]],
    real_nodes: list[dict[str, Any]],
    seed: int = config.DEEP_TIER_SEED,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate a tier-2/tier-3 supplier layer beneath the real companies.

    Args:
        pool_rows:  entity_pool.csv rows — name, source, location, product_category
        real_nodes: the nodes transform.py built from companies.csv
        seed:       fixed in config, so the same CSVs give a byte-identical file

    Returns (synthetic_nodes, synthetic_edges).  Edge ids are left unset; the
    caller assigns them once the real and synthetic edges are merged, so the
    numbering stays contiguous.

    Raises RuntimeError if the pool cannot cover a sector the real graph needs,
    rather than silently reusing a name or substituting a mismatched one.
    """
    rng = random.Random(seed)

    by_sector: dict[str, list[dict[str, str]]] = {}
    for row in sorted(pool_rows, key=lambda r: r["name"]):
        by_sector.setdefault(classify_pool_sector(row["product_category"]), []).append(row)
    for bucket in by_sector.values():
        rng.shuffle(bucket)

    taken_names = {node["name"] for node in real_nodes}
    next_index = max(int(node["node_id"][1:]) for node in real_nodes) + 1

    def draw(sector: str) -> dict[str, str]:
        """Take one unused pool entry, preferring the asked-for sector.

        Falls back to auto_components, then to whatever is left.  A slightly
        off-sector supplier name is a cosmetic blemish; running dry and raising
        mid-build is not, and reusing a name would put one company in the graph
        twice.
        """
        order = [sector, "auto_components", *sorted(by_sector)]
        for candidate_sector in order:
            bucket = by_sector.get(candidate_sector, [])
            while bucket:
                row = bucket.pop()
                if row["name"] not in taken_names:
                    taken_names.add(row["name"])
                    return row
        raise RuntimeError(
            f"entity_pool.csv exhausted for sector {sector!r} - add more rows "
            f"or lower DEEP_TIER1_FANOUT/DEEP_TIER2_FANOUT in config.py"
        )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    def make_node(row: dict[str, str], tier: int) -> dict[str, Any]:
        nonlocal next_index
        revenue = _draw_revenue(rng, tier)
        low, high = BUFFER_RANGE_BY_TIER[tier]
        node = {
            "node_id": _node_id(next_index),
            "name": row["name"],
            "tier": tier,
            "sector": classify_pool_sector(row["product_category"]),
            "product_category": row["product_category"],
            "revenue_cr": round(revenue, 2),
            "cash_buffer_days": rng.randint(low, high),
            "employees": max(4, int(revenue / REVENUE_PER_EMPLOYEE_CR)),
            "is_observable": False,
            # Row-level and never file-level, so the UI can always tell a
            # generated firm from a real filer (DATA_DICTIONARY.md §3b).
            "data_source": "synthetic",
            "cin": None,
            "substituted": [],
        }
        next_index += 1
        nodes.append(node)
        return node

    # Remaining outgoing exposure per supplier.  exposure_pct is a fraction of
    # the SUPPLIER's revenue, so a supplier's outgoing edges must not sum past
    # 1.0 — graph.py raises if they do.
    budget: dict[str, float] = {}

    def connect(supplier: dict[str, Any], buyer: dict[str, Any]) -> None:
        remaining = budget.get(supplier["node_id"], rng.uniform(*EXPOSURE_COVERAGE_RANGE))
        if remaining <= 0.02:
            return
        exposure = round(min(remaining, rng.uniform(0.08, 0.62)), 4)
        budget[supplier["node_id"]] = remaining - exposure
        edges.append({
            "supplier_id": supplier["node_id"],
            "buyer_id": buyer["node_id"],
            "component": supplier["product_category"],
            "annual_value_cr": round(exposure * supplier["revenue_cr"], 2),
            "exposure_pct": exposure,
            # Set below, and only where the buyer is synthetic.
            "is_single_source": False,
            "confidence": "confirmed",
            "edge_provenance": "synthetic",
            "data_source": "synthetic",
        })

    real_by_tier: dict[int, list[dict[str, Any]]] = {}
    for node in sorted(real_nodes, key=lambda n: n["node_id"]):
        real_by_tier.setdefault(node["tier"], []).append(node)

    # Tier 2 beneath every real tier-1.  Suppliers are shared across buyers in
    # the same sector, which is what a real ancillary cluster looks like: one
    # forging shop serves several tier-1s rather than exactly one.
    tier2_by_sector: dict[str, list[dict[str, Any]]] = {}
    for buyer in real_by_tier.get(1, []):
        pool_sector = _pool_sector_for_buyer(buyer["sector"])
        existing = tier2_by_sector.setdefault(pool_sector, [])
        wanted = rng.randint(*config.DEEP_TIER1_FANOUT)

        # Reuse part of an existing cluster before generating more.
        reused = existing[:]
        rng.shuffle(reused)
        reused = reused[: wanted // 3]
        for supplier in reused:
            connect(supplier, buyer)

        for _ in range(wanted - len(reused)):
            supplier = make_node(draw(pool_sector), tier=2)
            existing.append(supplier)
            connect(supplier, buyer)

    # Tier 3 beneath every tier-2, real ones included — a real tier-2 with no
    # suppliers of its own is a leaf, and leaves cannot carry stress onward.
    tier2_all = [n for n in nodes if n["tier"] == 2] + real_by_tier.get(2, [])
    for buyer in sorted(tier2_all, key=lambda n: n["node_id"]):
        pool_sector = _pool_sector_for_buyer(buyer["sector"])
        for _ in range(rng.randint(*config.DEEP_TIER2_FANOUT)):
            connect(make_node(draw(pool_sector), tier=3), buyer)

    _place_deep_tier_chokepoints(rng, edges, {n["node_id"] for n in nodes})

    edges.sort(key=lambda e: (e["supplier_id"], e["buyer_id"]))
    return nodes, edges


def _place_deep_tier_chokepoints(
    rng: random.Random,
    edges: list[dict[str, Any]],
    synthetic_ids: set[str],
) -> None:
    """Flag a few genuine sole-source relationships inside the generated layer.

    Only edges whose BUYER is synthetic are eligible.  Saying a real company
    single-sources a part is a fabricated claim about that company's supply
    chain, which DATA_DICTIONARY.md §3b puts in the "never synthetic under any
    circumstances" list.  Criticality needs real chokepoints to find, and the
    generated layer supplies them without making a claim about anybody real.
    """
    eligible = [
        edge for edge in sorted(edges, key=lambda e: (e["supplier_id"], e["buyer_id"]))
        if edge["buyer_id"] in synthetic_ids and edge["exposure_pct"] >= 0.25
    ]
    for edge in rng.sample(eligible, min(config.DEEP_TIER_CHOKEPOINTS, len(eligible))):
        edge["is_single_source"] = True
