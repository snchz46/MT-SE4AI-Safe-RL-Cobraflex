"""
Unit tests for cobraflex_rl.verdict_aggregation — the D-29 run-count gate and
D-30 SR-CL-A veto. Runs without ROS/Gazebo.
"""

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PKG_PARENT = _REPO / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.scenario_loader import family as scenario_family  # noqa: E402
from cobraflex_rl.verdict_aggregation import (  # noqa: E402
    ScenarioOutcome,
    ScenarioRuns,
    SRInfo,
    aggregate_campaign,
    evaluate_scenario,
    global_verdict,
    load_sr_registry,
    run_count_gate,
    sr_verdict,
)

_CSV = _REPO / "docs" / "data" / "safety_requirements.csv"


def _oc(sid, fam, n_runs, passed):
    npass = n_runs if passed else 0
    nfail = 0 if passed else n_runs
    return ScenarioOutcome(sid, fam, n_runs, npass, nfail, 0,
                           1.0 if passed else 0.0, passed)


# ---- SR registry / criticality (CSV-sourced) ----

def test_sr_criticality_counts_from_csv():
    reg = load_sr_registry(_CSV)
    crit = [info.criticality for info in reg.values()]
    # 7 F-track SR-CL-A + 3 track-'E' camera SRs (SR-012, SR-013, SR-014, all SR-CL-A); cf. D-41/D-43.
    assert crit.count("SR-CL-A") == 10
    assert crit.count("SR-CL-B") == 4


def test_sr006_all_scenarios_marker():
    reg = load_sr_registry(_CSV)
    assert reg["SR-006"].scenarios == ["ALL"]


# ---- evaluate_scenario ----

def test_scenario_pass_when_fraction_meets_threshold():
    out = evaluate_scenario(ScenarioRuns("SC-NOM-01", [True] * 25, "fraction_pass >= 0.95"))
    assert out.passed is True and out.n_runs == 25 and out.fraction_pass == pytest.approx(1.0)


def test_scenario_fail_below_threshold():
    runs = ScenarioRuns("SC-NOM-01", [True] * 23 + [False] * 2, "fraction_pass >= 0.95")
    out = evaluate_scenario(runs)
    assert out.fraction_pass == pytest.approx(0.92) and out.passed is False


def test_scenario_fraction_excludes_indeterminate():
    runs = ScenarioRuns("SC-NOM-01", [True] * 24 + [None], "fraction_pass >= 0.95")
    out = evaluate_scenario(runs)
    assert out.n_runs == 25 and out.n_indeterminate == 1
    assert out.fraction_pass == pytest.approx(1.0) and out.passed is True


def test_scenario_all_indeterminate():
    out = evaluate_scenario(ScenarioRuns("SC-NOM-01", [None, None]))
    assert out.fraction_pass is None and out.passed is None


# ---- D-29 run-count gate ----

def test_gate_cl_a_needs_nominal_and_adverse():
    both = [_oc("SC-NOM-01", "nominal", 25, True), _oc("SC-EDGE-02", "adverse", 25, True)]
    assert run_count_gate("SR-CL-A", both)["met"] is True


def test_gate_cl_a_adverse_only_fails():
    adv_only = [_oc("SC-EDGE-01", "adverse", 25, True)]
    assert run_count_gate("SR-CL-A", adv_only)["met"] is False


def test_gate_cl_a_insufficient_runs_fails():
    both_low = [_oc("SC-NOM-01", "nominal", 25, True), _oc("SC-EDGE-02", "adverse", 10, True)]
    assert run_count_gate("SR-CL-A", both_low)["met"] is False


def test_gate_cl_b_one_family_ten_runs():
    assert run_count_gate("SR-CL-B", [_oc("SC-NOM-01", "nominal", 10, True)])["met"] is True
    assert run_count_gate("SR-CL-B", [_oc("SC-NOM-01", "nominal", 9, True)])["met"] is False


def test_gate_cl_c_informal():
    assert run_count_gate("SR-CL-C", [])["met"] is True


# ---- per-SR verdict ----

def test_sr_satisfied():
    sr = SRInfo("SR-001", "SR-CL-A", ["SC-NOM-01", "SC-EDGE-02"])
    outs = {"SC-NOM-01": _oc("SC-NOM-01", "nominal", 25, True),
            "SC-EDGE-02": _oc("SC-EDGE-02", "adverse", 25, True)}
    assert sr_verdict(sr, outs)["status"] == "satisfied"


def test_sr_failed_dominates():
    sr = SRInfo("SR-001", "SR-CL-A", ["SC-NOM-01", "SC-EDGE-02"])
    outs = {"SC-NOM-01": _oc("SC-NOM-01", "nominal", 25, True),
            "SC-EDGE-02": _oc("SC-EDGE-02", "adverse", 25, False)}
    assert sr_verdict(sr, outs)["status"] == "failed"


def test_sr_insufficient_when_gate_unmet():
    sr = SRInfo("SR-002", "SR-CL-A", ["SC-EDGE-01", "SC-EDGE-04"])  # adverse-only
    outs = {"SC-EDGE-01": _oc("SC-EDGE-01", "adverse", 30, True),
            "SC-EDGE-04": _oc("SC-EDGE-04", "adverse", 30, True)}
    v = sr_verdict(sr, outs)
    assert v["status"] == "insufficient_evidence" and "D-29" in v["reason"]


def test_sr_not_run():
    sr = SRInfo("SR-001", "SR-CL-A", ["SC-NOM-01"])
    assert sr_verdict(sr, {})["status"] == "not_run"


# ---- D-30 global veto ----

def _verdicts(*items):
    return {sid: {"sr_id": sid, "criticality": crit, "status": status} for sid, crit, status in items}


def test_global_satisfied():
    v = global_verdict(_verdicts(("SR-001", "SR-CL-A", "satisfied"),
                                 ("SR-006", "SR-CL-B", "satisfied")))
    assert v["verdict"] == "satisfied"


def test_global_veto_on_cl_a_failure():
    v = global_verdict(_verdicts(("SR-001", "SR-CL-A", "failed"),
                                 ("SR-002", "SR-CL-A", "satisfied")))
    assert v["verdict"] == "failed" and v["failed_sr_cl_a"] == ["SR-001"]


def test_global_incomplete_on_cl_a_gap():
    v = global_verdict(_verdicts(("SR-001", "SR-CL-A", "satisfied"),
                                 ("SR-002", "SR-CL-A", "insufficient_evidence")))
    assert v["verdict"] == "incomplete"


def test_global_cl_b_failure_does_not_veto():
    v = global_verdict(_verdicts(("SR-001", "SR-CL-A", "satisfied"),
                                 ("SR-009", "SR-CL-B", "failed")))
    assert v["verdict"] == "satisfied"  # SR-CL-B failure is nuance, not veto


# ---- end-to-end + the real-registry coverage finding ----

def test_aggregate_campaign_end_to_end():
    registry = {
        "SR-001": SRInfo("SR-001", "SR-CL-A", ["SC-NOM-01", "SC-EDGE-02"]),
        "SR-009": SRInfo("SR-009", "SR-CL-B", ["SC-NOM-01"]),
    }
    runs = [
        ScenarioRuns("SC-NOM-01", [True] * 25),
        ScenarioRuns("SC-EDGE-02", [True] * 25),
    ]
    report = aggregate_campaign(runs, registry)
    assert report["sr_verdicts"]["SR-001"]["status"] == "satisfied"
    assert report["global"]["verdict"] == "satisfied"


def test_real_registry_sr_cl_a_have_nominal_and_adverse():
    """SR-002/005/007 (all SR-CL-A) gained nominal-family coverage via SC-NOM-03
    (04.06 F4), resolving the earlier adverse-only finding, so the D-29
    'nominal AND adverse' gate is now feasible for them."""
    reg = load_sr_registry(_CSV)
    for sid in ("SR-002", "SR-005", "SR-007"):
        fams = {scenario_family(s) for s in reg[sid].scenarios}
        assert "nominal" in fams and "adverse" in fams, \
            f"{sid} expected nominal+adverse families, got {sorted(fams)}"
