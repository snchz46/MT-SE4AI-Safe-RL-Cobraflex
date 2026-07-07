"""Unit tests for the pass-mode split in tools/campaign_e_failure_modes.py:
since D-45 dropped ``emergency == False`` from the adverse pass criteria, a
per-run PASS is either 'clean' (overcame the stressor, no emergency) or
'with_emergency' (the cage flagged emergency with the safety limits held)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import campaign_e_failure_modes as fm  # noqa: E402


def _run(verdict, emergency, sid="SC-PERT-04", mode="enforcement", ms1=0.05,
         edge=False):
    return {
        "scenario_id": sid,
        "mode": mode,
        "verdict": verdict,
        "_run_id": f"{sid}_{mode}",
        "campaign": {"values": {"M-S1": ms1, "emergency": emergency,
                                "road_edge_contact": edge}},
    }


def test_classify_pass_modes():
    assert fm._classify_pass({"emergency": True}) == "with_emergency"
    assert fm._classify_pass({"emergency": False}) == "clean"
    assert fm._classify_pass({}) == "clean"  # absent flag -> no emergency seen


def test_analyse_splits_pass_by_emergency():
    runs = [
        _run(True, False),               # overcame the perturbation, kept driving
        _run(True, True),                # D-45 controlled stop, limits held: a pass
        _run(True, True),
        _run(False, True, ms1=0.20),     # real M-S1 breach -> fail, not a pass mode
        _run(None, False),               # indeterminate -> neither pass bucket
    ]
    rep = fm.analyse(runs)
    g = next(g for g in rep["per_group"]
             if g["scenario"] == "SC-PERT-04" and g["mode"] == "enforcement")
    assert g["pass"] == 3
    assert g["pass_with_emergency"] == 2
    assert g["pass_clean"] == 1
    assert g["pass_clean"] + g["pass_with_emergency"] == g["pass"]
    assert g["fail"] == 1 and g["fail_ms1_breach"] == 1
    assert g["indet"] == 1


def test_analyse_pass_modes_split_per_mode():
    # The split is per (scenario, mode): a monitoring 'with_emergency' pass is the
    # shadow cage's un-enforced request, kept separate from the enforcement stop.
    runs = [
        _run(True, True, mode="enforcement"),
        _run(True, False, mode="monitoring"),
        _run(True, True, mode="monitoring"),
    ]
    rep = fm.analyse(runs)
    by_mode = {g["mode"]: g for g in rep["per_group"]}
    assert by_mode["enforcement"]["pass_with_emergency"] == 1
    assert by_mode["enforcement"]["pass_clean"] == 0
    assert by_mode["monitoring"]["pass_with_emergency"] == 1
    assert by_mode["monitoring"]["pass_clean"] == 1
