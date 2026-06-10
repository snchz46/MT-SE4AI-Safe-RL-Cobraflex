"""
Unit tests for cobraflex_rl.lane_plausibility — the cage CV lane-estimate plausibility /
temporal-consistency check (track 'E'; SR-014, H-12, D-40).

Pure logic, host-testable; `cobraflex_rl/__init__` is lazy (no rclpy).
"""
import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.lane_plausibility import (  # noqa: E402
    LaneEstimate,
    LanePlausibilityCheck,
)


def _est(ey=0.0, heading=0.0, lane_width=0.5, curvature=0.0, t=0.0):
    return LaneEstimate(ey=ey, heading=heading, lane_width=lane_width, curvature=curvature, timestamp_s=t)


def test_plausible_first_estimate_is_accepted():
    chk = LanePlausibilityCheck()
    r = chk.update(_est(), speed_mps=0.2, now_s=0.0)
    assert r.plausible is True and r.reject is False and r.reason == "ok"


def test_ey_out_of_range_rejects_after_persistence():
    chk = LanePlausibilityCheck(ey_max=0.30, min_implausible_cycles=2)
    r1 = chk.update(_est(ey=0.5, t=0.0), 0.2, 0.0)
    assert r1.plausible is False and r1.reject is False
    r2 = chk.update(_est(ey=0.5, t=0.1), 0.2, 0.1)
    assert r2.reject is True and "ey_out_of_range" in r2.reason


def test_lane_width_implausible():
    chk = LanePlausibilityCheck(lane_width_range=(0.20, 0.80), min_implausible_cycles=1)
    r = chk.update(_est(lane_width=1.2), 0.2, 0.0)
    assert r.plausible is False and "lane_width_implausible" in r.reason


def test_curvature_out_of_range():
    chk = LanePlausibilityCheck(curvature_max=1.5, min_implausible_cycles=1)
    r = chk.update(_est(curvature=3.0), 0.2, 0.0)
    assert r.plausible is False and "curvature_out_of_range" in r.reason


def test_temporal_ey_jump_rejects():
    chk = LanePlausibilityCheck(jump_tol_m=0.10, min_implausible_cycles=2)
    chk.update(_est(ey=0.0, t=0.0), speed_mps=0.2, now_s=0.0)        # trusted reference
    r1 = chk.update(_est(ey=0.5, t=0.1), speed_mps=0.2, now_s=0.1)   # allowed ~0.12 << 0.5
    assert r1.plausible is False and "ey_jump" in r1.reason and r1.reject is False
    r2 = chk.update(_est(ey=0.5, t=0.2), speed_mps=0.2, now_s=0.2)
    assert r2.reject is True


def test_temporal_heading_jump():
    chk = LanePlausibilityCheck(max_heading_rate=6.0, jump_tol_rad=0.30, min_implausible_cycles=1)
    chk.update(_est(heading=0.0, t=0.0), 0.2, 0.0)
    r = chk.update(_est(heading=2.5, t=0.1), 0.2, 0.1)  # allowed ~0.9 << 2.5
    assert r.plausible is False and "heading_jump" in r.reason


def test_single_suspect_frame_does_not_trip_and_reference_holds():
    chk = LanePlausibilityCheck(jump_tol_m=0.10, min_implausible_cycles=2)
    chk.update(_est(ey=0.0, t=0.0), 0.2, 0.0)
    chk.update(_est(ey=0.5, t=0.1), 0.2, 0.1)            # one suspect frame (not accepted)
    r = chk.update(_est(ey=0.02, t=0.2), 0.2, 0.2)       # back near the trusted reference
    assert r.plausible is True and r.reject is False


def test_recovery_resets_counter():
    chk = LanePlausibilityCheck(ey_max=0.30, min_implausible_cycles=2)
    chk.update(_est(ey=0.5, t=0.0), 0.2, 0.0)
    r_rej = chk.update(_est(ey=0.5, t=0.1), 0.2, 0.1)
    assert r_rej.reject is True
    r_ok = chk.update(_est(ey=0.0, t=0.2), 0.2, 0.2)
    assert r_ok.plausible is True and r_ok.reject is False


def test_reset_clears_state():
    chk = LanePlausibilityCheck(ey_max=0.30, min_implausible_cycles=2)
    chk.update(_est(ey=0.5, t=0.0), 0.2, 0.0)
    chk.reset()
    r = chk.update(_est(ey=0.5, t=0.1), 0.2, 0.1)  # first bad after reset → not yet reject
    assert r.reject is False


@pytest.mark.parametrize("kwargs", [
    {"ey_max": 0.0},
    {"lane_width_range": (0.8, 0.2)},
    {"curvature_max": -1.0},
    {"max_heading_rate": 0.0},
    {"min_implausible_cycles": 0},
])
def test_constructor_validation(kwargs):
    with pytest.raises(ValueError):
        LanePlausibilityCheck(**kwargs)
