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
def _result(sid, verdict, n=50):
    """Build a ScenarioResult with a three-valued verdict. ``verdict=None`` makes
    every run indeterminate (n_pass=n_fail=0, all in n_indeterminate)."""
    if verdict is None:
        return rc.ScenarioResult(sid, "enforcement", n, 0, 0, n, None)
    n_pass = n if verdict else 0
    n_fail = 0 if verdict else n
    return rc.ScenarioResult(sid, "enforcement", n, n_pass, n_fail, 0, verdict)


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
    assert sr.status == "failed" and sr.verdict is False


def test_sr006_scored_out_of_band_does_not_inherit_scenario_fails():
    """SR-006 (D-39) is scored out-of-band, so it never inherits the unrelated
    per-scenario fails its ``ALL`` mapping would otherwise pull in."""
    assert "SR-006" in rc.OUT_OF_BAND_SRS
    objs = {"SC-NOM-01": _scen("SC-NOM-01"), "SC-EDGE-02": _scen("SC-EDGE-02")}
    results = {"SC-NOM-01": _result("SC-NOM-01", True),
               "SC-EDGE-02": _result("SC-EDGE-02", False)}  # a failing scenario
    runs = {"SC-NOM-01": 50, "SC-EDGE-02": 50}
    sr = rc.aggregate_sr("SR-006", "SR-CL-B", ["SC-NOM-01", "SC-EDGE-02"],
                         objs, results, runs)
    assert sr.status == "scored_out_of_band"
    assert sr.verdict is None          # neither pass nor fail
    assert sr.failing_scenarios == []  # no inherited fails


# ----- three-valued / indeterminate handling (D-38 reconciliation) --------- #
def test_aggregate_scenario_excludes_indeterminate_from_fraction():
    # 24 pass + 1 indeterminate -> fraction over *evaluable* = 1.0, verdict True.
    scen = _scen("SC-NOM-01", per_scen="fraction_pass >= 0.95")
    res = rc.aggregate_scenario(scen, "enforcement", [True] * 24 + [None])
    assert (res.n_pass, res.n_fail, res.n_indeterminate) == (24, 0, 1)
    assert res.evaluable == 24 and res.fraction_pass == 1.0 and res.verdict is True


def test_aggregate_scenario_all_indeterminate_is_none_not_fail():
    # Mirrors SC-EDGE-05 / SC-PERT-03 in the F4 campaign: every run is None
    # (instrumentation gap). The scenario verdict must be None, not False.
    scen = _scen("SC-EDGE-05", per_scen="fraction_pass >= 0.95")
    res = rc.aggregate_scenario(scen, "enforcement", [None] * 100)
    assert res.n_indeterminate == 100 and res.evaluable == 0
    assert res.fraction_pass is None and res.verdict is None


def test_sr_indeterminate_scenario_is_insufficient_not_failed():
    # Mirrors SR-010: SC-EDGE-04 passes, SC-EDGE-05 is all-indeterminate. The SR
    # must read insufficient_evidence (a gap), never failed.
    objs = {"SC-EDGE-04": _scen("SC-EDGE-04"), "SC-EDGE-05": _scen("SC-EDGE-05")}
    results = {"SC-EDGE-04": _result("SC-EDGE-04", True),
               "SC-EDGE-05": _result("SC-EDGE-05", None, n=100)}
    runs = {"SC-EDGE-04": 30, "SC-EDGE-05": 100}
    sr = rc.aggregate_sr("SR-010", "SR-CL-B", ["SC-EDGE-04", "SC-EDGE-05"], objs, results, runs)
    assert sr.status == "insufficient_evidence" and sr.verdict is None
    assert sr.failing_scenarios == [] and sr.indeterminate_scenarios == ["SC-EDGE-05"]


def test_sr_real_failure_dominates_indeterminate():
    # failed has precedence over insufficient: a genuine fraction failure wins.
    objs = {"SC-NOM-01": _scen("SC-NOM-01"), "SC-EDGE-05": _scen("SC-EDGE-05")}
    results = {"SC-NOM-01": _result("SC-NOM-01", False),
               "SC-EDGE-05": _result("SC-EDGE-05", None, n=100)}
    runs = {"SC-NOM-01": 50, "SC-EDGE-05": 100}
    sr = rc.aggregate_sr("SR-009", "SR-CL-B", ["SC-NOM-01", "SC-EDGE-05"], objs, results, runs)
    assert sr.status == "failed" and sr.verdict is False


# ----- global_verdict (D-30 veto) ------------------------------------------ #
def test_global_verdict_veto():
    good_a = rc.SRResult("SR-001", "SR-CL-A", "satisfied", run_count_ok=True, families_covered=["nominal", "adverse"])
    bad_a = rc.SRResult("SR-002", "SR-CL-A", "failed", run_count_ok=True, families_covered=["nominal", "adverse"])
    nuance_b = rc.SRResult("SR-006", "SR-CL-B", "failed", run_count_ok=True, families_covered=["nominal"])

    assert rc.global_verdict([good_a, nuance_b])["verdict"] == "SATISFIED"  # B failure does not veto
    out = rc.global_verdict([good_a, bad_a])
    assert out["verdict"] == "NOT SATISFIED" and out["blocking_sr_cl_a"] == ["SR-002"]
    # An SR-CL-A that passes its scenarios but lacks D-29 sufficiency is INCOMPLETE
    # (under-covered), not a failure (D-38): distinct from a real veto.
    insufficient = rc.SRResult("SR-003", "SR-CL-A", "satisfied", run_count_ok=False, families_covered=["nominal"])
    inc = rc.global_verdict([good_a, insufficient])
    assert inc["verdict"] == "INCOMPLETE" and inc["incomplete_sr_cl_a"] == ["SR-003"]
    # An SR-CL-A whose evidence is indeterminate is likewise INCOMPLETE, not failed.
    indet = rc.SRResult("SR-004", "SR-CL-A", "insufficient_evidence", run_count_ok=True, families_covered=["nominal", "adverse"])
    assert rc.global_verdict([good_a, indet])["verdict"] == "INCOMPLETE"


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


# ----- orchestration: run_matrix + aggregate_campaign (stub executor) ------ #
def _stub_executor(verdict_by_scenario):
    """Build an executor that returns a fixed per-run verdict per scenario id,
    writing a deterministic run_id dir read-back is not needed (returns inline)."""
    def _exec(run_spec, scenario, *, output_root, **kw):
        v = verdict_by_scenario.get(run_spec.scenario_id)
        if v == "raise":
            raise RuntimeError("simulated Gazebo failure")
        return {"verdict": v, "scenario_id": run_spec.scenario_id}
    return _exec


def test_run_matrix_collects_verdicts_and_errors():
    scens = {"SC-NOM-01": _scen("SC-NOM-01", n_enf=2, n_mon=0),
             "SC-EDGE-01": _scen("SC-EDGE-01", n_enf=2, n_mon=0)}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])
    execu = _stub_executor({"SC-NOM-01": True, "SC-EDGE-01": "raise"})
    outcomes = rc.run_matrix(matrix, scens, Path("/tmp/none"), executor=execu)
    assert len(outcomes) == 4
    nom = [o for o in outcomes if o.run_spec.scenario_id == "SC-NOM-01"]
    edge = [o for o in outcomes if o.run_spec.scenario_id == "SC-EDGE-01"]
    assert all(o.verdict is True for o in nom)
    assert all(o.verdict is None and o.error for o in edge)


def test_run_matrix_stop_on_error_raises():
    scens = {"SC-NOM-01": _scen("SC-NOM-01", n_enf=2, n_mon=0)}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])
    execu = _stub_executor({"SC-NOM-01": "raise"})
    try:
        rc.run_matrix(matrix, scens, Path("/tmp/none"), executor=execu, continue_on_error=False)
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_aggregate_campaign_global_pass_and_veto():
    # One SR-CL-A (SR-001) covered by a nominal + an adverse scenario, enough runs.
    scens = {
        "SC-NOM-01": _scen("SC-NOM-01", n_enf=25, n_mon=0, srs=["SR-001"], per_scen="fraction_pass >= 0.90"),
        "SC-EDGE-01": _scen("SC-EDGE-01", n_enf=25, n_mon=0, srs=["SR-001"], per_scen="fraction_pass >= 0.90"),
    }
    srs = {"SR-001": {"criticality": "SR-CL-A", "scenarios": ["SC-NOM-01", "SC-EDGE-01"]}}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])

    all_pass = rc.run_matrix(matrix, scens, Path("/tmp/x"), executor=_stub_executor(
        {"SC-NOM-01": True, "SC-EDGE-01": True}))
    rep = rc.aggregate_campaign(all_pass, scens, srs, verdict_mode="enforcement")
    assert rep["global"]["verdict"] == "SATISFIED"

    # An SR-CL-A scenario failing its fraction vetoes the global verdict (D-30).
    edge_fail = rc.run_matrix(matrix, scens, Path("/tmp/x"), executor=_stub_executor(
        {"SC-NOM-01": True, "SC-EDGE-01": False}))
    rep2 = rc.aggregate_campaign(edge_fail, scens, srs, verdict_mode="enforcement")
    assert rep2["global"]["verdict"] == "NOT SATISFIED"
    assert "SR-001" in rep2["global"]["blocking_sr_cl_a"]


def test_aggregate_campaign_all_indeterminate_scenario_is_insufficient():
    # End-to-end: a scenario whose every run is indeterminate (None) must surface
    # as insufficient_evidence at the SR level, with fraction_pass=None at the
    # scenario level — never collapsed to a fail (D-38). SR-CL-B does not veto.
    scens = {
        "SC-NOM-01": _scen("SC-NOM-01", n_enf=25, n_mon=0, srs=["SR-009"], per_scen="fraction_pass >= 0.90"),
        "SC-EDGE-05": _scen("SC-EDGE-05", n_enf=25, n_mon=0, srs=["SR-009"], per_scen="fraction_pass >= 0.90"),
    }
    srs = {"SR-009": {"criticality": "SR-CL-B", "scenarios": ["SC-NOM-01", "SC-EDGE-05"]}}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])
    outcomes = rc.run_matrix(matrix, scens, Path("/tmp/x"), executor=_stub_executor(
        {"SC-NOM-01": True, "SC-EDGE-05": None}))
    rep = rc.aggregate_campaign(outcomes, scens, srs, verdict_mode="enforcement")

    edge = next(s for s in rep["per_scenario"] if s["scenario"] == "SC-EDGE-05")
    assert edge["verdict"] is None and edge["fraction_pass"] is None
    assert edge["n_indeterminate"] == 25 and edge["n_fail"] == 0
    sr = next(r for r in rep["per_sr"] if r["sr"] == "SR-009")
    assert sr["status"] == "insufficient_evidence" and sr["verdict"] is None
    assert sr["indeterminate_scenarios"] == ["SC-EDGE-05"]
    assert rep["global"]["verdict"] == "SATISFIED"  # no SR-CL-A, B does not veto


def test_write_report_emits_json_and_csv(tmp_path):
    scens = {"SC-NOM-01": _scen("SC-NOM-01", n_enf=2, n_mon=0, srs=["SR-001"])}
    srs = {"SR-001": {"criticality": "SR-CL-B", "scenarios": ["SC-NOM-01"]}}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])
    outcomes = rc.run_matrix(matrix, scens, tmp_path, executor=_stub_executor({"SC-NOM-01": True}))
    report = rc.aggregate_campaign(outcomes, scens, srs)
    rc.write_report(report, outcomes, tmp_path)
    assert (tmp_path / "campaign_report.json").is_file()
    assert (tmp_path / "campaign_runs.csv").is_file()


def test_run_id_for_is_deterministic_and_unique():
    a = rc.RunSpec("SC-EDGE-01", "enforcement", "rl", 2024, 3)
    b = rc.RunSpec("SC-EDGE-01", "monitoring", "rl", 2024, 3)
    assert rc.run_id_for(a) == rc.run_id_for(a)
    assert rc.run_id_for(a) != rc.run_id_for(b)
    assert "rep03" in rc.run_id_for(a)


def test_execute_run_resume_reads_cached_summary(tmp_path):
    # With resume=True and an existing summary.json, execute_run must read it back
    # without launching Gazebo (subprocess 'ros2' would fail in this env).
    rs = rc.RunSpec("SC-EDGE-01", "enforcement", "rl", 2024, 0)
    scen = _scen("SC-EDGE-01")
    run_dir = tmp_path / rc.run_id_for(rs)
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text('{"verdict": true, "scenario_id": "SC-EDGE-01"}')
    out = rc.execute_run(rs, scen, output_root=tmp_path, resume=True)
    assert out["verdict"] is True
