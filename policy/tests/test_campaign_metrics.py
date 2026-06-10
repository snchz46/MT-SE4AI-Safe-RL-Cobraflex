"""
Unit tests for cobraflex_rl.campaign_metrics — the pure F4 per-run metric
catalogue (docs/06). Runs without ROS/Gazebo/numpy.
"""

import math
import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.campaign_metrics import (  # noqa: E402
    aggregate_metric,
    compute_run_metrics,
    _heading_variability,
    _nominal_settled,
    _percentile,
    _run_lengths,
    _std,
)


def _rec(ey=0.0, epsi=0.0, speed=0.2, raw_steer=0.0, steer_correction=0.0,
         interventions=(), emergency=False):
    return {
        "ey": ey, "epsi": epsi, "speed": speed, "raw_steer": raw_steer,
        "steer_correction": steer_correction,
        "interventions": list(interventions), "emergency": emergency,
    }


# ---- helpers ----

def test_percentile_linear_interpolation():
    xs = [0.0, 1.0, 2.0, 3.0, 4.0]
    assert _percentile(xs, 50.0) == pytest.approx(2.0)
    assert _percentile(xs, 5.0) == pytest.approx(0.2)
    assert _percentile(xs, 95.0) == pytest.approx(3.8)


def test_percentile_edge_cases():
    assert _percentile([], 50.0) is None
    assert _percentile([7.0], 95.0) == pytest.approx(7.0)


def test_std_known():
    assert _std([1.0, 1.0, 1.0]) == pytest.approx(0.0)
    assert _std([0.0, 2.0]) == pytest.approx(1.0)  # population std of {0,2}


def test_run_lengths():
    assert _run_lengths([False, True, True, False, True]) == [2, 1]
    assert _run_lengths([False, False]) == []
    assert _run_lengths([True, True, True]) == [3]


def test_nominal_settled_requires_settle_window():
    # settle_steps=2 -> eligible only once >2 nominal steps elapsed since entry
    flags = _nominal_settled([{"emergency": False}] * 5, settle_steps=2)
    assert flags == [False, False, True, True, True]


def test_nominal_settled_resets_after_emergency():
    recs = [{"emergency": False}] * 4 + [{"emergency": True}] + [{"emergency": False}] * 4
    flags = _nominal_settled(recs, settle_steps=2)
    # first interval settles at idx 2; emergency at idx4 resets; re-settles at idx 7
    assert flags[2] is True and flags[3] is True
    assert flags[4] is False
    assert flags[5] is False and flags[6] is False and flags[7] is True


# ---- compute_run_metrics ----

def test_empty_run():
    out = compute_run_metrics([])
    assert out["n_steps"] == 0
    assert out["metrics"]["M-P1"] is None


def test_basic_performance_and_safety():
    recs = [
        _rec(ey=0.1, epsi=0.0),
        _rec(ey=-0.2, epsi=0.1, interventions=["C-01"]),
        _rec(ey=0.0, epsi=-0.05),
    ]
    m = compute_run_metrics(recs)["metrics"]
    assert m["M-P1"] == pytest.approx(math.sqrt((0.01 + 0.04 + 0.0) / 3))
    assert m["M-P4"] == pytest.approx(0.1)
    assert m["M-P5"] == pytest.approx(0.05)
    assert m["M-S1"] == pytest.approx(0.2)
    # one |ey|>0.16 over duration 3*0.1=0.3 s
    assert m["M-S2"] == pytest.approx(1.0 / 0.3)
    assert m["M-I1"] == pytest.approx(100.0 / 3)
    assert m["M-I2"] == {"C-01": pytest.approx(100.0 / 3)}
    assert m["M-S3"] == 0


def test_completion_and_emergency():
    recs = [_rec(emergency=True), _rec()]
    assert compute_run_metrics(recs, completed=True)["metrics"]["M-P2"] == 1
    assert compute_run_metrics(recs, completed=False)["metrics"]["M-P2"] == 0
    assert compute_run_metrics(recs)["metrics"]["M-P2"] is None
    assert compute_run_metrics(recs)["metrics"]["M-S3"] == 1


def test_speed_compliance_with_and_without_kappa():
    recs = [_rec(speed=0.2), _rec(speed=0.3)]
    out_k = compute_run_metrics(recs, kappa=[0.0, 0.5])
    # step1 on a curve: v_max=0.25, speed 0.3 violates -> 50%
    assert out_k["metrics"]["M-P3"] == pytest.approx(50.0)
    assert out_k["availability"]["M-P3"] == "exact"
    out_nok = compute_run_metrics(recs)
    # no kappa -> straight ceiling 0.5, both comply
    assert out_nok["metrics"]["M-P3"] == pytest.approx(100.0)
    assert "approx" in out_nok["availability"]["M-P3"]


def test_stall_rate_detects_stall_and_motion():
    stalled = [_rec(speed=0.0) for _ in range(30)]
    moving = [_rec(speed=0.2) for _ in range(30)]
    assert compute_run_metrics(stalled)["metrics"]["M-P6"] == pytest.approx(100.0)
    assert compute_run_metrics(moving)["metrics"]["M-P6"] == pytest.approx(0.0)


def test_stall_rate_undefined_when_no_eligible_window():
    # too short for a full 2 s / 0.1 s = 20-step trailing window
    out = compute_run_metrics([_rec(speed=0.0) for _ in range(5)])
    assert out["metrics"]["M-P6"] is None
    assert "undefined" in out["availability"]["M-P6"]


def test_heading_variability_zero_for_constant_heading():
    val, note = _heading_variability([0.1] * 25, [False] * 25,
                                     {"control_dt": 0.1, "t_psd_s": 1.0, "delta_t_settle_s": 1.0})
    assert val == pytest.approx(0.0)
    assert note == "exact"


def test_intervention_duration_distribution():
    recs = []
    fire = {1, 2, 3, 5}  # C-01 active at these step indices -> runs [3, 1]
    for i in range(6):
        recs.append(_rec(interventions=["C-01"] if i in fire else []))
    mi3 = compute_run_metrics(recs)["metrics"]["M-I3"]["C-01"]
    assert mi3["count"] == 2
    assert mi3["max"] == pytest.approx(3.0)
    assert mi3["median"] == pytest.approx(2.0)


def test_hazard_correlation_c01():
    # C-01 fires twice: once compatible (|ey|>0.08), once not
    recs = [
        _rec(ey=0.10, interventions=["C-01"]),  # 0.10 > 0.5*0.16=0.08 -> compatible
        _rec(ey=0.02, interventions=["C-01"]),  # not compatible
    ]
    mi4 = compute_run_metrics(recs)["metrics"]["M-I4"]
    assert mi4["C-01"] == pytest.approx(50.0)


def test_ttlc_p5_and_absence():
    recs = [_rec() for _ in range(4)]
    out = compute_run_metrics(recs, ttlc=[1.0, 0.5, 2.0, float("inf")])
    assert out["metrics"]["M-S4"] == pytest.approx(_percentile([0.5, 1.0, 2.0], 5.0))
    out_no = compute_run_metrics(recs)
    assert out_no["metrics"]["M-S4"] is None
    assert "ttlc" in out_no["availability"]["M-S4"]


def test_action_correction_steering():
    recs = [_rec(steer_correction=0.0), _rec(steer_correction=0.2), _rec(steer_correction=-0.4)]
    mi5 = compute_run_metrics(recs)["metrics"]["M-I5"]
    assert mi5["steer_p95"] == pytest.approx(_percentile([0.0, 0.2, 0.4], 95.0))


def test_sr006_steer_rate_bounded_when_no_override():
    # safe_steer reconstructed as raw_steer + steer_correction; smooth 0.1/cycle ramp.
    recs = [
        _rec(raw_steer=0.0), _rec(raw_steer=0.1), _rec(raw_steer=0.2),
    ]
    mi5 = compute_run_metrics(recs)["metrics"]["M-I5"]
    assert mi5["steer_rate_max"] == pytest.approx(0.1)
    assert mi5["steer_rate_max_smoothness"] == pytest.approx(0.1)
    assert mi5["steer_rate_smoothness_ok"] is True  # 0.1 <= delta_max_steer 0.15


def test_sr006_large_rate_attributed_to_safety_override():
    # A 0.9 jump on the step where C-01 (lane) fires must NOT count against the
    # smoothness arm: a safety correction legitimately overrides C-06 (SR-006).
    recs = [_rec(raw_steer=0.0), _rec(raw_steer=0.9, interventions=("C-06", "C-01"))]
    mi5 = compute_run_metrics(recs)["metrics"]["M-I5"]
    assert mi5["steer_rate_max"] == pytest.approx(0.9)             # observed on committed output
    assert mi5["steer_rate_max_smoothness"] == pytest.approx(0.0)  # excluded (C-01 override)
    assert mi5["steer_rate_smoothness_ok"] is True

    # Same jump with no safety-override rule active is a genuine smoothness breach.
    recs2 = [_rec(raw_steer=0.0), _rec(raw_steer=0.9, interventions=("C-06",))]
    mi5b = compute_run_metrics(recs2)["metrics"]["M-I5"]
    assert mi5b["steer_rate_max_smoothness"] == pytest.approx(0.9)
    assert mi5b["steer_rate_smoothness_ok"] is False


def test_timing_metrics_unavailable_in_sim():
    out = compute_run_metrics([_rec()])
    assert out["metrics"]["M-C1"] is None and out["metrics"]["M-C2"] is None


def test_aggregate_metric():
    agg = aggregate_metric([1.0, 2.0, 3.0, 4.0, 5.0])
    assert agg["n"] == 5
    assert agg["median"] == pytest.approx(3.0)
    assert agg["mean"] == pytest.approx(3.0)
    assert aggregate_metric([])["n"] == 0
    assert aggregate_metric([None, 2.0])["n"] == 1  # None dropped
