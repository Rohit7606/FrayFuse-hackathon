"""Transform tests — the CSV to network.json handoff.

The two failure modes these guard are the ones PERSON_A.md §5 names as able to
corrupt the model silently rather than crash it: units, and defaulting
`has_not_due_column`.
"""

from __future__ import annotations

import json

import pytest

from engine import transform
from engine.graph import build_graph
from engine.pipeline import score_network
from tests.engine.conftest import REPO_ROOT, validator_for

REAL_DIR = REPO_ROOT / "data" / "real"


@pytest.fixture(scope="module")
def real_network():
    if not (REAL_DIR / "companies.csv").exists():
        pytest.skip("collection CSVs not present")
    network, _ = transform.transform(REAL_DIR)
    return network


def test_transform_output_validates(real_network, schema):
    """transform output validates against NetworkInput, same as mockgen's."""
    errors = sorted(
        validator_for(schema, "NetworkInput").iter_errors(real_network),
        key=lambda e: list(e.path),
    )
    assert errors == [], [f"{list(e.path)}: {e.message}" for e in errors[:5]]


def test_transform_is_deterministic(real_network):
    """The same CSVs always produce a byte-identical network."""
    again, _ = transform.transform(REAL_DIR)
    assert json.dumps(real_network, sort_keys=True) == json.dumps(again, sort_keys=True)


def test_figures_are_not_converted_twice(real_network):
    """financials.csv is already in rupees crore; units_as_reported is provenance.

    These three are quoted in findings.md with their as-printed source figures,
    and each is a different source unit. Re-dividing by units_as_reported would
    put Nectar at 152 crore and Balrampur at 48 — plausible-looking numbers that
    are wrong by a factor of ten or a hundred.
    """
    revenue = {n["name"]: n["revenue_cr"] for n in real_network["nodes"]}
    expected = {
        "Nectar Lifesciences Limited": 1669.97,  # source printed millions
        "Balrampur Chini Mills Limited": 5415.38,  # source printed lakhs
        "Bajaj Hindusthan Sugar Limited": 6076.56,  # source printed crore
    }
    for name, value in expected.items():
        assert revenue[name] == pytest.approx(value, rel=1e-6), name


def test_has_not_due_column_is_never_defaulted(real_network):
    """Both values survive the transform — 19 of 46 collected rows are false.

    Defaulting to true would make a filer who omits the column look badly
    overdue, because its under_1yr silently includes amounts not yet due.
    """
    values = {s["has_not_due_column"] for s in real_network["stress_signals"]}
    assert values == {True, False}


def test_real_company_missing_field_is_null_not_invented(real_network):
    """A real company with an undisclosed figure carries null and says so."""
    substituted = [n for n in real_network["nodes"] if n.get("substituted")]
    assert substituted, "the collected set has companies with no financials at all"
    for node in substituted:
        for field in node["substituted"]:
            assert node[field] is None, f"{node['node_id']}.{field} was invented"
            assert node["data_source"] == "real"


def test_sole_source_is_never_inferred(real_network):
    """No filing in the collected set states sole-source status.

    Inferring `false` from the sparsity of our own edge collection would
    manufacture the product's headline finding out of our own ignorance.

    Scoped to REAL edges since the synthetic deep tier landed. Generated edges
    carry a generated flag on purpose — DATA_DICTIONARY.md §3b puts
    `is_single_source` on synthetic edges in the "should be synthetic" list.
    """
    real_edges = [e for e in real_network["edges"] if e["data_source"] == "real"]
    assert real_edges, "the collected set should contribute edges"
    assert all(e["is_single_source"] is None for e in real_edges)


def test_no_sole_source_claim_against_a_real_company(real_network):
    """The generated layer must never call anybody real single-sourced.

    DATA_DICTIONARY.md §3b: "any statement that a real company is a sole
    source" is on the never-synthetic-under-any-circumstances list. An edge
    flagged `is_single_source` whose BUYER is real asserts that real company
    single-sources the part, which is a fabricated claim about its supply
    chain. Chokepoints are therefore confined to synthetic buyers.
    """
    real_ids = {n["node_id"] for n in real_network["nodes"] if n["data_source"] == "real"}
    offenders = [
        e["edge_id"]
        for e in real_network["edges"]
        if e["is_single_source"] is True and e["buyer_id"] in real_ids
    ]
    assert offenders == [], f"sole-source claim against a real buyer: {offenders}"


def test_no_synthetic_rupee_figure_beside_a_real_name(real_network):
    """A real company's node carries only disclosed figures, or null.

    §3b again: no rupee figure may sit next to a real company's name unless it
    came from a filing. The synthetic layer must not have leaked a generated
    revenue onto a real node.
    """
    for node in real_network["nodes"]:
        if node["data_source"] != "real":
            continue
        for field in node.get("substituted", []):
            assert node[field] is None, f"{node['node_id']}.{field} was invented"


def test_synthetic_layer_gives_the_real_graph_depth(real_network):
    """Without the generated tier-2/3 layer nothing propagates.

    The collected graph bottoms out at three-node chains, which is why the real
    network scored 0 at risk and converged in one iteration. This asserts the
    layer is actually present and labelled, not that any particular node is at
    risk — that is the scoring tests' job.
    """
    tiers = {}
    for node in real_network["nodes"]:
        tiers.setdefault(node["tier"], []).append(node)

    assert tiers.get(3), "no tier-3 layer was generated"
    assert len(tiers.get(2, [])) > 20, "tier-2 layer too thin to propagate"

    for tier in (2, 3):
        for node in tiers.get(tier, []):
            if node["data_source"] == "synthetic":
                assert node["is_observable"] is False
                assert node["cin"] is None


def test_unnamed_counterparty_rows_are_not_edges(real_network):
    """concentration_disclosure_unnamed rows are real disclosures, not edges."""
    node_ids = {n["node_id"] for n in real_network["nodes"]}
    for edge in real_network["edges"]:
        assert edge["supplier_id"] in node_ids
        assert edge["buyer_id"] in node_ids


def test_terminated_relationship_is_dropped():
    """A pair whose most recent row ends the relationship is not an edge.

    LOKESH -> MAHINDRA has two rows and the later one is the OFAC sanctions
    termination. Collapsing carelessly either loses the termination or silently
    keeps an edge that no longer exists.
    """
    rows = [
        {"edge_id": "E1", "from_company_id": "A", "to_company_id": "B", "fy": "FY2023",
         "confidence": "confirmed", "relationship_type": "supplies_to", "component": "x"},
        {"edge_id": "E2", "from_company_id": "A", "to_company_id": "B", "fy": "FY2024",
         "confidence": "confirmed", "relationship_type": "relationship_terminated", "component": "x"},
    ]
    assert transform.collapse_edge_rows(rows) == []


def test_collapse_keeps_the_only_disclosed_value():
    """Multi-row pairs carry forward the best non-null value of each field.

    SHIVAM -> HERO has three rows and only one carries a rupee figure. Taking
    everything from the winning row discards it.
    """
    rows = [
        {"edge_id": "E1", "from_company_id": "A", "to_company_id": "B", "fy": "FY2025",
         "confidence": "confirmed", "relationship_type": "supplies_to",
         "component": "", "annual_value_cr": "", "weight_pct": ""},
        {"edge_id": "E2", "from_company_id": "A", "to_company_id": "B", "fy": "FY2025",
         "confidence": "confirmed", "relationship_type": "supplies_to",
         "component": "gears", "annual_value_cr": "181.59", "weight_pct": "40"},
    ]
    collapsed = transform.collapse_edge_rows(rows)
    assert len(collapsed) == 1
    assert collapsed[0]["annual_value_cr"] == "181.59"
    assert collapsed[0]["component"] == "gears"


def test_exposure_ceiling_enforced(real_network):
    """No supplier's outgoing exposure exceeds the whole of its revenue."""
    totals: dict[str, float] = {}
    for edge in real_network["edges"]:
        totals[edge["supplier_id"]] = totals.get(edge["supplier_id"], 0.0) + edge["exposure_pct"]
    for supplier_id, total in totals.items():
        assert total <= 1.02, f"{supplier_id} sums to {total}"


def test_engine_runs_on_the_real_network(real_network):
    """The real dataset flows through the same pipeline as the mock.

    This is the whole point of the handoff: swapping the dataset in is a
    file-path change and nothing else (AGENTS.md §7).
    """
    build_graph(real_network)
    result = score_network(real_network)
    assert len(result["scores"]) == len(real_network["nodes"])
    assert all(0.0 <= s["final_score"] <= 1.0 for s in result["scores"])
