"""
Unit tests for cobraflex_rl.eval_metrics — the pure aggregation behind the §7.5
evaluation harness (laps, cage intervention rate, emergencies, tracking error).
Runs without ROS/Gazebo.
"""

import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.eval_metrics import forward_delta, summarize_eval  # noqa: E402


def _rec(ep, s, ey=0.0, epsi=0.0, interventions=(), emergency=False):
    return {
        "episode": ep,
        "s": s,
        "ey": ey,
        "epsi": epsi,
        "interventions": list(interventions),
        "emergency": emergency,
    }


def test_forward_delta_normal():
    assert forward_delta(1.0, 1.5, 10.0) == pytest.approx(0.5)


def test_forward_delta_wrap_at_finish_line():
    # 9.9 -> 0.1 on a 10 m loop is a +0.2 forward crossing of s=0
    assert forward_delta(9.9, 0.1, 10.0) == pytest.approx(0.2)


def test_forward_delta_small_backward_not_treated_as_wrap():
    assert forward_delta(1.0, 0.9, 10.0) == pytest.approx(-0.1)


def test_summarize_empty():
    out = summarize_eval([], perimeter=10.0, cycle_dt_s=0.1)
    assert out["total_steps"] == 0
    assert out["completed_laps"] == 0.0
    assert out["interventions_per_rule"] == {}


def test_summarize_laps_single_episode_full_loop():
    recs = [_rec(0, s) for s in [0.0, 2.5, 5.0, 7.5, 9.9, 0.1]]
    out = summarize_eval(recs, perimeter=10.0, cycle_dt_s=0.1)
    # progress 2.5+2.5+2.5+2.4+0.2 = 10.1 -> 1.01 laps
    assert out["completed_laps"] == pytest.approx(10.1 / 10.0)
    assert out["episodes"] == 1
    assert out["total_steps"] == 6


def test_summarize_resets_progress_between_episodes():
    recs = [_rec(0, 0.0), _rec(0, 5.0), _rec(1, 9.0), _rec(1, 9.5)]
    out = summarize_eval(recs, perimeter=10.0, cycle_dt_s=0.1)
    # ep0 contributes +5.0; ep1 contributes +0.5; the 9.0 at ep1 start is a
    # reference, not progress carried over from ep0.
    assert out["completed_laps"] == pytest.approx(5.5 / 10.0)
    assert out["episodes"] == 2


def test_summarize_interventions_and_emergencies():
    recs = [
        _rec(0, 0.0, ey=0.10, interventions=["C-01"]),
        _rec(0, 1.0, ey=-0.20, interventions=["C-01", "C-05"], emergency=True),
        _rec(0, 2.0, ey=0.0),
        _rec(0, 3.0, ey=0.0),
    ]
    out = summarize_eval(recs, perimeter=10.0, cycle_dt_s=0.1)
    assert out["intervention_steps"] == 2
    assert out["intervention_rate_pct"] == pytest.approx(50.0)
    assert out["emergency_steps"] == 1
    assert out["interventions_per_rule"] == {"C-01": 2, "C-05": 1}
    assert out["max_abs_ey_m"] == pytest.approx(0.20)
    assert out["mean_ey_m"] == pytest.approx((0.10 - 0.20) / 4)
    assert out["duration_s"] == pytest.approx(0.4)
