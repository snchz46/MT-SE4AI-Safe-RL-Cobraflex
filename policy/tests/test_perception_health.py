"""
Unit tests for cobraflex_rl.perception_health — the track-'E' perception-health
monitor (D-38/D-39; H-11, SR-013, SC-PERT-07).

The monitor is the external supervisor's pure decision logic: when camera
perception is invalid it raises the cage's C-05 perception-health trigger. Pure
logic, host-testable (no ROS); ``cobraflex_rl/__init__`` is lazy so the submodule
imports without the ROS toolchain (same pattern as test_rewards.py).
"""
import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.perception_health import (  # noqa: E402
    PerceptionHealthMonitor,
    PerceptionSample,
)


def _good(ts: float) -> PerceptionSample:
    return PerceptionSample(timestamp_s=ts, frame_received=True, confidence=0.9, feature_count=3)


def test_valid_sample_is_not_emergency():
    mon = PerceptionHealthMonitor()
    res = mon.update(_good(0.0), now_s=0.0)
    assert res.valid is True
    assert res.emergency is False
    assert res.reason == "ok"


def test_low_confidence_raises_emergency_after_persistence():
    mon = PerceptionHealthMonitor(min_confidence=0.3, min_invalid_cycles=2)
    s1 = PerceptionSample(0.0, True, confidence=0.1, feature_count=3)
    r1 = mon.update(s1, now_s=0.0)
    assert r1.valid is False and r1.emergency is False  # first invalid cycle: not yet
    s2 = PerceptionSample(0.1, True, confidence=0.1, feature_count=3)
    r2 = mon.update(s2, now_s=0.1)
    assert r2.emergency is True
    assert "low_confidence" in r2.reason


def test_single_glitch_does_not_trip():
    mon = PerceptionHealthMonitor(min_invalid_cycles=2)
    mon.update(PerceptionSample(0.0, True, 0.1, 3), now_s=0.0)   # one invalid cycle
    r = mon.update(_good(0.1), now_s=0.1)                        # recovers
    assert r.valid is True and r.emergency is False


def test_frame_dropout_beyond_staleness_raises_emergency():
    mon = PerceptionHealthMonitor(staleness_max_s=0.2, min_invalid_cycles=2)
    mon.update(_good(0.0), now_s=0.0)                            # last good frame at t=0
    drop = PerceptionSample(0.0, frame_received=False, confidence=0.0, feature_count=0)
    r1 = mon.update(drop, now_s=0.3)                             # 0.3 > 0.2 -> stale
    assert r1.valid is False and r1.emergency is False
    r2 = mon.update(drop, now_s=0.4)
    assert r2.emergency is True
    assert "stale_or_dropped_frame" in r2.reason


def test_missing_single_frame_within_budget_is_ok():
    mon = PerceptionHealthMonitor(staleness_max_s=0.2)
    mon.update(_good(0.0), now_s=0.0)
    # a frame is briefly missing but we are still within the staleness budget
    r = mon.update(PerceptionSample(0.0, False, 0.0, 0), now_s=0.1)
    assert r.valid is True and r.emergency is False


def test_insufficient_features_is_invalid():
    mon = PerceptionHealthMonitor(min_features=1, min_invalid_cycles=1)
    r = mon.update(PerceptionSample(0.0, True, confidence=0.9, feature_count=0), now_s=0.0)
    assert r.valid is False and r.emergency is True
    assert "insufficient_features" in r.reason


def test_recovery_clears_emergency():
    mon = PerceptionHealthMonitor(min_invalid_cycles=2)
    mon.update(PerceptionSample(0.0, True, 0.1, 3), now_s=0.0)
    r_em = mon.update(PerceptionSample(0.1, True, 0.1, 3), now_s=0.1)
    assert r_em.emergency is True
    r_ok = mon.update(_good(0.2), now_s=0.2)
    assert r_ok.valid is True and r_ok.emergency is False


def test_reset_clears_state():
    mon = PerceptionHealthMonitor(min_invalid_cycles=2)
    mon.update(PerceptionSample(0.0, True, 0.1, 3), now_s=0.0)
    mon.reset()
    # after reset the previous invalid cycle is forgotten: one new invalid is not emergency
    r = mon.update(PerceptionSample(0.1, True, 0.1, 3), now_s=0.1)
    assert r.emergency is False


@pytest.mark.parametrize("kwargs", [
    {"staleness_max_s": 0.0},
    {"min_confidence": 1.5},
    {"min_features": -1},
    {"min_invalid_cycles": 0},
])
def test_constructor_validation(kwargs):
    with pytest.raises(ValueError):
        PerceptionHealthMonitor(**kwargs)
