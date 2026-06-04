"""Unit tests for tools/run_campaign — the pure (ROS-free) orchestration and
verdict-aggregation core of the Phase-4 campaign runner (D-29 run counts,
D-30 SR-CL-A veto). The Gazebo executor is out of scope here."""

import sys
from pathlib import Path

# run_campaign lives in tools/; import it by file path (it is ROS-free, needs
# only PyYAML + stdlib), mirroring the cage_bridge/training_metrics test pattern.
_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import run_campaign as rc  # noqa: E402


def _scen(sid, n_enf=50, n_mon=50, stub=False, srs=None, per_scen="fraction_pass >= 0.95"):
    return rc.Scenario(
        id=sid,
        category={"SC-NOM": "nominal", "SC-EDGE": "edge", "SC-PERT": "perturbed"}[sid.rsplit("-", 1)[0]],
        is_stub=stub,
        references_SR=srs or [],
        pass_criterion_per_run="M-P1 < 0.05 AND M-P2 == 1 AND emergency == False",
        pass_criterion_per_scenario=per_scen,
        n_runs={"enforcement": n_enf, "monitoring": n_mon},
    )


# ----- evaluate_criterion -------------------------------------------------- #
def test_criterion_per_run_pass_and_fail():
    expr = "M-P1 < 0.05 AND M-P2 == 1 AND emergency == False"
    assert rc.evaluate_criterion(expr, {"M-P1": 0.01, "M-P2": 1, "emergency": False}) is True
    assert rc.evaluate_criterion(expr, {"M-P1": 0.10, "M-P2": 1, "emergency": False}) is False
    assert rc.evaluate_criterion(expr, {"M-P1": 0.01, "M-P2": 1, "emergency": True}) is False


def test_criterion_or_and_thresholds():
    assert rc.evaluate_criterion("M-P6 > 0.50", {"M-P6": 0.7}) is True
    assert rc.evaluate_criterion("M-P6 > 0.50", {"M-P6": 0.2}) is False
    assert rc.evaluate_criterion("fraction_pass >= 0.95", {"fraction_pass": 0.96}) is True
    assert rc.evaluate_criterion("fraction_pass >= 0.95", {"fraction_pass": 0.90}) is False


def test_criterion_is_sandboxed():
    # No builtins available inside the sandbox.
    try:
        rc.evaluate_criterion("__import__('os')", {})
    except Exception:
        return
    raise AssertionError("sandbox should block __import__")


# ----- build_matrix -------------------------------------------------------- #
def test_build_matrix_counts_and_seed_axis():
    scenarios = {"SC-NOM-01": _scen("SC-NOM-01", n_enf=50, n_mon=50)}
    matrix = rc.build_matrix(scenarios, controllers=["rl", "pd"],
                             seeds=[42, 123, 2024], modes=["enforcement", "monitoring"])
    # per mode: rl = 3 seeds * 50 + pd = 1 * 50 = 200; two modes -> 400.
    assert len(matrix) == 400
    pd_runs = [r for r in matrix if r.controller == "pd"]
    assert all(r.seed is None for r in pd_runs)
    assert len({r.seed for r in matrix if r.controller == "rl"}) == 3


def test_build_matrix_skips_stubs():
    scenarios = {
        "SC-NOM-01": _scen("SC-NOM-01"),
        "SC-NOM-02": _scen("SC-NOM-02", stub=True),
    }
    matrix = rc.build_matrix(scenarios, ["rl"], [42], ["enforcement"])
    assert {r.scenario_id for r in matrix} == {"SC-NOM-01"}


# ----- aggregate_scenario -------------------------------------------------- #
def test_aggregate_scenario_threshold():
    scen = _scen("SC-NOM-01", per_scen="fraction_pass >= 0.95")
    passing = rc.aggregate_scenario(scen, "enforcement", [True] * 96 + [False] * 4)
    assert passing.verdict is True and passing.fraction_pass == 0.96
    failing = rc.aggregate_scenario(scen, "enforcement", [True] * 90 + [False] * 10)
    assert failing.verdict is False


# ----- aggregate_sr (D-29) ------------------------------------------------- #
def _result(sid, verdict):
    return rc.ScenarioResult(sid, "enforcement", 50, 50 if verdict else 0, verdict)


def test_sr_cl_a_needs_nominal_and_adverse_coverage():
    objs = {"SC-NOM-01": _scen("SC-NOM-01"), "SC-EDGE-02": _scen("SC-EDGE-02")}
    results = {"SC-NOM-01": _result("SC-NOM-01", True), "SC-EDGE-02": _result("SC-EDGE-02", True)}
    runs = {"SC-NOM-01": 50, "SC-EDGE-02": 30}
    ok = rc.aggregate_sr("SR-001", "SR-CL-A", ["SC-NOM-01", "SC-EDGE-02"], objs, results, runs)
    assert ok.verdict is True and ok.run_count_ok is True
    assert set(ok.families_covered) == {"nominal", "adverse"}

    # Only nominal coverage -> D-29 not met for SR-CL-A.
    only_nom = rc.aggregate_sr("SR-001", "SR-CL-A", ["SC-NOM-01"], objs, results,
                               {"SC-NOM-01": 50})
    assert only_nom.run_count_ok is False


def test_sr_cl_a_run_count_threshold_and_stub():
    objs = {"SC-NOM-01": _scen("SC-NOM-01"), "SC-EDGE-02": _scen("SC-EDGE-02")}
    results = {"SC-NOM-01": _result("SC-NOM-01", True), "SC-EDGE-02": _result("SC-EDGE-02", True)}
    # adverse family has only 20 runs (< 25) -> D-29 not met.
    low = rc.aggregate_sr("SR-001", "SR-CL-A", ["SC-NOM-01", "SC-EDGE-02"], objs, results,
                          {"SC-NOM-01": 50, "SC-EDGE-02": 20})
    assert low.run_count_ok is False

    # A stub among the SR's scenarios blocks sufficiency.
    objs2 = dict(objs, **{"SC-PERT-01": _scen("SC-PERT-01", stub=True)})
    stub = rc.aggregate_sr("SR-001", "SR-CL-A", ["SC-NOM-01", "SC-PERT-01"], objs2,
                           {"SC-NOM-01": _result("SC-NOM-01", True)}, {"SC-NOM-01": 50})
    assert stub.run_count_ok is False


def test_sr_failed_scenario_fails_verdict():
    objs = {"SC-NOM-01": _scen("SC-NOM-01"), "SC-EDGE-02": _scen("SC-EDGE-02")}
    results = {"SC-NOM-01": _result("SC-NOM-01", True), "SC-EDGE-02": _result("SC-EDGE-02", False)}
    runs = {"SC-NOM-01": 50, "SC-EDGE-02": 50}
    sr = rc.aggregate_sr("SR-001", "SR-CL-A", ["SC-NOM-01", "SC-EDGE-02"], objs, results, runs)
    assert sr.verdict is False


# ----- global_verdict (D-30 veto) ------------------------------------------ #
def test_global_verdict_veto():
    good_a = rc.SRResult("SR-001", "SR-CL-A", verdict=True, run_count_ok=True, families_covered=["nominal", "adverse"])
    bad_a = rc.SRResult("SR-002", "SR-CL-A", verdict=False, run_count_ok=True, families_covered=["nominal", "adverse"])
    nuance_b = rc.SRResult("SR-006", "SR-CL-B", verdict=False, run_count_ok=True, families_covered=["nominal"])

    assert rc.global_verdict([good_a, nuance_b])["verdict"] == "SATISFIED"  # B failure does not veto
    out = rc.global_verdict([good_a, bad_a])
    assert out["verdict"] == "NOT SATISFIED" and out["blocking_sr_cl_a"] == ["SR-002"]
    # An SR-CL-A that passes but lacks D-29 sufficiency also blocks.
    insufficient = rc.SRResult("SR-003", "SR-CL-A", verdict=True, run_count_ok=False, families_covered=["nominal"])
    assert rc.global_verdict([good_a, insufficient])["verdict"] == "NOT SATISFIED"


# ----- loaders smoke (real repo files) ------------------------------------- #
def test_load_scenarios_and_srs_real_files():
    scenarios = rc.load_scenarios()
    assert "SC-NOM-01" in scenarios
    nom01 = scenarios["SC-NOM-01"]
    assert nom01.track.get("world") == "lane_following_oval.world"
    assert nom01.is_stub is False
    srs = rc.load_srs()
    assert srs["SR-001"]["criticality"] == "SR-CL-A"
    assert "SC-NOM-01" in srs["SR-001"]["scenarios"]
