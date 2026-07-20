"""Unit tests for tools/run_campaign — the pure (ROS-free) orchestration and
verdict-aggregation core of the Phase-4 campaign runner (D-29 run counts,
D-30 SR-CL-A veto). The Gazebo executor is out of scope here."""

import json
import sys
from pathlib import Path

import pytest

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
    # M-P6 is expressed in percentage points (0..100), not a 0..1 fraction.
    assert rc.evaluate_criterion("M-P6 > 50.0", {"M-P6": 70.0}) is True
    assert rc.evaluate_criterion("M-P6 > 50.0", {"M-P6": 20.0}) is False
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


def test_build_matrix_splits_preregistered_policy_arms_symmetrically():
    scen = _scen("SC-PERT-03", n_enf=40, n_mon=40)
    scen.perturbations = {
        "type": "pre_run_policy_finetune",
        "arms": [
            {"id": "released", "runs_per_mode": 20},
            {"id": "stall_variant", "runs_per_mode": 20},
        ],
    }
    matrix = rc.build_matrix(
        {scen.id: scen}, ["rl"], [2024], ["enforcement", "monitoring"]
    )
    assert len(matrix) == 80
    assert {
        (r.mode, r.arm): sum(
            1 for x in matrix if (x.mode, x.arm) == (r.mode, r.arm)
        )
        for r in matrix
    } == {
        ("enforcement", "released"): 20,
        ("enforcement", "stall_variant"): 20,
        ("monitoring", "released"): 20,
        ("monitoring", "stall_variant"): 20,
    }


def test_build_matrix_rejects_arm_counts_that_do_not_sum_to_scenario_budget():
    scen = _scen("SC-PERT-03", n_enf=40, n_mon=40)
    scen.perturbations = {
        "type": "pre_run_policy_finetune",
        "arms": [
            {"id": "released", "runs_per_mode": 20},
            {"id": "stall_variant", "runs_per_mode": 19},
        ],
    }
    with pytest.raises(ValueError, match="sum to"):
        rc.build_matrix({scen.id: scen}, ["rl"], [2024], ["enforcement"])


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


def test_aggregate_campaign_splits_passes_by_emergency():
    # D-45: a safe controlled stop passes the adverse criteria, so the per-scenario
    # report splits n_pass into emergency-stop passes vs overcame-the-scenario passes.
    scens = {"SC-PERT-01": _scen("SC-PERT-01", n_enf=2, n_mon=0, srs=["SR-012"],
                                 per_scen="fraction_pass >= 0.90")}
    srs = {"SR-012": {"criticality": "SR-CL-B", "scenarios": ["SC-PERT-01"]}}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])
    emergency_by_rep = {0: True, 1: False}

    def _exec(run_spec, scenario, *, output_root, **kw):
        return {"verdict": True, "scenario_id": run_spec.scenario_id,
                "campaign": {"values": {"emergency": emergency_by_rep[run_spec.rep]}}}

    outcomes = rc.run_matrix(matrix, scens, Path("/tmp/x"), executor=_exec)
    rep = rc.aggregate_campaign(outcomes, scens, srs)
    row = next(s for s in rep["per_scenario"] if s["scenario"] == "SC-PERT-01")
    assert row["n_pass"] == 2 and row["n_pass_emergency"] == 1


def test_write_report_emits_json_and_csv(tmp_path):
    scens = {"SC-NOM-01": _scen("SC-NOM-01", n_enf=2, n_mon=0, srs=["SR-001"])}
    srs = {"SR-001": {"criticality": "SR-CL-B", "scenarios": ["SC-NOM-01"]}}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])
    outcomes = rc.run_matrix(matrix, scens, tmp_path, executor=_stub_executor({"SC-NOM-01": True}))
    report = rc.aggregate_campaign(outcomes, scens, srs)
    rc.write_report(report, outcomes, tmp_path)
    assert (tmp_path / "campaign_report.json").is_file()
    csv_lines = (tmp_path / "campaign_runs.csv").read_text().splitlines()
    assert csv_lines[0] == "scenario,mode,arm,controller,seed,rep,verdict,emergency,error"


def test_two_arm_aggregation_requires_each_arm_to_meet_fraction():
    scen = _scen(
        "SC-PERT-03", n_enf=40, n_mon=0, srs=["SR-009"],
        per_scen="fraction_pass >= 0.90",
    )
    scen.perturbations = {
        "type": "pre_run_policy_finetune",
        "arms": [
            {"id": "released", "runs_per_mode": 20},
            {"id": "stall_variant", "runs_per_mode": 20},
        ],
    }
    scens = {scen.id: scen}
    matrix = rc.build_matrix(scens, ["rl"], [2024], ["enforcement"])

    def _exec(run_spec, scenario, *, output_root, **kw):
        # released=20/20, stall=16/20. Pooling would be 36/40=90% and pass;
        # correct arm-wise conjunction must fail the scenario.
        verdict = run_spec.arm == "released" or run_spec.rep < 16
        return {"verdict": verdict, "scenario_id": scenario.id}

    outcomes = rc.run_matrix(matrix, scens, Path("/tmp/x"), executor=_exec)
    report = rc.aggregate_campaign(
        outcomes,
        scens,
        {"SR-009": {"criticality": "SR-CL-B", "scenarios": [scen.id]}},
    )
    rows = report["per_scenario"]
    assert {(row["arm"], row["fraction_pass"]) for row in rows} == {
        ("released", 1.0), ("stall_variant", 0.8)
    }
    sr = report["per_sr"][0]
    assert sr["status"] == "failed" and sr["failing_scenarios"] == [scen.id]


def test_run_id_for_is_deterministic_and_unique():
    a = rc.RunSpec("SC-EDGE-01", "enforcement", "rl", 2024, 3)
    b = rc.RunSpec("SC-EDGE-01", "monitoring", "rl", 2024, 3)
    assert rc.run_id_for(a) == rc.run_id_for(a)
    assert rc.run_id_for(a) != rc.run_id_for(b)
    assert "rep03" in rc.run_id_for(a)
    arm_a = rc.RunSpec("SC-PERT-03", "enforcement", "rl", 2024, 3, "released")
    arm_b = rc.RunSpec("SC-PERT-03", "enforcement", "rl", 2024, 3, "stall_variant")
    assert rc.run_id_for(arm_a) != rc.run_id_for(arm_b)
    assert rc.run_id_for(arm_a, "a" * 64) != rc.run_id_for(arm_a, "b" * 64)


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


def test_execute_run_selects_arm_checkpoint_config_and_manifest(tmp_path, monkeypatch):
    import subprocess

    rs = rc.RunSpec(
        "SC-PERT-03", "enforcement", "rl", 2024, 0, "stall_variant"
    )
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text("id: SC-PERT-03\n", encoding="utf-8")
    scen = _scen("SC-PERT-03")
    scen.path = scenario_path
    checkpoint = tmp_path / "stall.zip"
    checkpoint.write_bytes(b"checkpoint")
    config = tmp_path / "stall.yaml"
    config.write_text("algorithm: sac\n", encoding="utf-8")
    manifest = tmp_path / "protocol_manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    run_dir = tmp_path / rc.run_id_for(rs, rc._file_sha256(manifest))
    run_dir.mkdir()
    (run_dir / "summary.json").write_text(
        '{"verdict": true, "criterion_arm": "stall_variant"}', encoding="utf-8"
    )
    calls = []

    class Result:
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd) or Result())
    monkeypatch.setattr(rc, "_reap_orphan_gazebo", lambda: 0)
    result = rc.execute_run(
        rs, scen, output_root=tmp_path,
        model_paths_by_arm={"stall_variant": checkpoint},
        train_configs_by_arm={"stall_variant": config},
        protocol_manifest=manifest,
    )
    assert result["verdict"] is True
    command = calls[0]
    assert f"model_path:={checkpoint}" in command
    assert f"train_config:={config}" in command
    assert "criterion_arm:=stall_variant" in command
    assert f"protocol_manifest:={manifest}" in command


# ----- posterior D-43 execution gate -------------------------------------- #
def _write_d43_report(tmp_path, *, checkpoint_hash, config_hash,
                      aggregate_verdict="PASS", input_verdict="PASS",
                      provenance_valid=True):
    path = tmp_path / "d43.json"
    path.write_text(json.dumps({
        "schema_version": "d43-preflight/v1",
        "verdict": aggregate_verdict,
        "invalid_reasons": [],
        "inputs": [{
            "path": "runs/nominal/cage_status.csv",
            "sha256": "c" * 64,
            "verdict": input_verdict,
            "provenance": {
                "valid": provenance_valid,
                "metadata_sha256": "m" * 64,
                "policy_checkpoint_hash": checkpoint_hash,
                "train_config_hash": config_hash,
                "scenario_id": "SC-NOM-01",
                "mode": "enforcement",
                "status": "completed",
            },
        }],
    }), encoding="utf-8")
    return path


def test_d43_gate_binds_pass_to_checkpoint_and_config_hashes(tmp_path):
    checkpoint_hash = "a" * 64
    config_hash = "b" * 64
    report = _write_d43_report(
        tmp_path,
        checkpoint_hash=checkpoint_hash,
        config_hash=config_hash,
        # A reference matrix may be BLOCKED by unrelated inputs.  The exact
        # selected checkpoint is nevertheless authorised by its own PASS row.
        aggregate_verdict="BLOCKED",
    )
    result = rc.validate_d43_preflight_report(report, [{
        "label": "released",
        "checkpoint_sha256": checkpoint_hash,
        "train_config_sha256": config_hash,
    }])
    assert result["status"] == "PASS_FOR_SELECTED_CHECKPOINTS"
    assert result["matches"][0]["checkpoint_sha256"] == checkpoint_hash
    assert result["report_sha256"] == rc._file_sha256(report)


@pytest.mark.parametrize(
    ("checkpoint_hash", "config_hash", "input_verdict", "provenance_valid"),
    [
        ("x" * 64, "b" * 64, "PASS", True),
        ("a" * 64, "x" * 64, "PASS", True),
        ("a" * 64, "b" * 64, "BLOCKED", True),
        ("a" * 64, "b" * 64, "PASS", False),
    ],
)
def test_d43_gate_rejects_unmatched_or_invalid_input(
    tmp_path, checkpoint_hash, config_hash, input_verdict, provenance_valid
):
    report = _write_d43_report(
        tmp_path,
        checkpoint_hash=checkpoint_hash,
        config_hash=config_hash,
        input_verdict=input_verdict,
        provenance_valid=provenance_valid,
    )
    with pytest.raises(ValueError, match="no provenance-valid PASS"):
        rc.validate_d43_preflight_report(report, [{
            "label": "released",
            "checkpoint_sha256": "a" * 64,
            "train_config_sha256": "b" * 64,
        }])


def test_d43_gate_rejects_aggregate_invalid_report(tmp_path):
    report = _write_d43_report(
        tmp_path,
        checkpoint_hash="a" * 64,
        config_hash="b" * 64,
        aggregate_verdict="INVALID",
    )
    with pytest.raises(ValueError, match="INVALID"):
        rc.validate_d43_preflight_report(report, [{
            "label": "released",
            "checkpoint_sha256": "a" * 64,
            "train_config_sha256": "b" * 64,
        }])


def test_config_d43_opt_in_is_explicit_and_fail_closed(tmp_path):
    historical = tmp_path / "historical.yaml"
    historical.write_text("algorithm: sac\n", encoding="utf-8")
    assert rc._config_requires_d43_preflight(historical) is False

    opted_in = tmp_path / "posterior.yaml"
    opted_in.write_text(
        "campaign_contract:\n  d43_preflight_required: true\n",
        encoding="utf-8",
    )
    assert rc._config_requires_d43_preflight(opted_in) is True

    opted_in.write_text(
        "campaign_contract:\n  d43_preflight_required: false\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="d43_preflight_required=true"):
        rc._config_requires_d43_preflight(opted_in)


def test_main_blocks_missing_d43_report_before_touching_gazebo(tmp_path, monkeypatch):
    checkpoint = tmp_path / "fresh_margin022.zip"
    checkpoint.write_bytes(b"fresh-policy")
    reaped = []
    monkeypatch.setattr(rc, "_reap_orphan_gazebo", lambda: reaped.append(True))

    result = rc.main([
        "--scenario-dir", str(rc.REPO / "scenarios_complex_b"),
        "--scenarios", "SC-NOM-01",
        "--controllers", "rl",
        "--seeds", "2024",
        "--modes", "enforcement",
        "--reps", "1",
        "--train-config", str(
            rc.REPO
            / "src"
            / "cobraflex_rl"
            / "config"
            / "train_sac_camera_2d_tuned_entfix_margin022.yaml"
        ),
        "--model-path", str(checkpoint),
        "--out", str(tmp_path / "campaign"),
        "--no-frontier-plots",
    ])
    assert result == 2
    assert reaped == []
