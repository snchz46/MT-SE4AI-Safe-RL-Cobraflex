"""
Unit tests for cobraflex_rl.cage_perception — the track-'E' supervisor that
composes the CV lane-estimator with the SR-013 health monitor and the SR-014
plausibility check into the cage's state + C-05 Trigger 8 contract (D-40).

Uses the same synthetic ground-truth rendering as test_cv_lane_estimator.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from cobraflex_rl.camera_geometry import CameraModel  # noqa: E402
from cobraflex_rl.cage_perception import CagePerceptionSupervisor  # noqa: E402
from cobraflex_rl.cv_lane_estimator import CvLaneEstimator  # noqa: E402
from cobraflex_rl.perception_health import PerceptionHealthMonitor  # noqa: E402

from test_cv_lane_estimator import centered_lane, render_lane  # noqa: E402

CAM = CameraModel()
DT = 0.1


def make_supervisor(**health_kwargs):
    health = PerceptionHealthMonitor(**health_kwargs) if health_kwargs else None
    return CagePerceptionSupervisor(
        estimator=CvLaneEstimator(CAM), health=health
    )


def good_frame(ey=0.0, yaw=0.0):
    return render_lane(CAM, centered_lane(ey=ey, yaw=yaw))


def blank_frame():
    return np.full((CAM.height_px, CAM.width_px, 3), 40, dtype=np.uint8)


def run_cycles(sup, frames, t0=0.0, speed=0.2):
    results = []
    t = t0
    for f in frames:
        results.append(
            sup.update(f, frame_timestamp_s=t, now_s=t, speed_mps=speed)
        )
        t += DT
    return results


def test_nominal_frames_give_state_no_trigger():
    sup = make_supervisor()
    results = run_cycles(sup, [good_frame()] * 5)
    last = results[-1]
    assert last.state_available
    assert not last.perception_invalid
    assert last.estimate.ey == pytest.approx(0.0, abs=0.015)


def test_lost_lane_raises_trigger_after_persistence():
    sup = make_supervisor()
    run_cycles(sup, [good_frame()] * 3)
    results = run_cycles(sup, [blank_frame()] * 3, t0=0.3)
    assert not results[0].state_available
    # min_invalid_cycles=2 default: by the second blank cycle the trigger fires.
    assert results[1].perception_invalid
    assert "features" in results[1].health_reason or "confidence" in results[1].health_reason


def test_dropped_frames_raise_trigger():
    sup = make_supervisor()
    run_cycles(sup, [good_frame()] * 2)
    # No frame for 3 cycles: staleness (default 0.2 s) → emergency.
    results = []
    for i in range(3):
        results.append(
            sup.update(
                None,
                frame_timestamp_s=0.1,  # last real frame stamp
                now_s=0.2 + (i + 1) * DT,
                speed_mps=0.2,
            )
        )
    assert results[-1].perception_invalid
    assert "stale" in results[-1].health_reason


def test_false_jump_rejected_by_plausibility():
    sup = make_supervisor()
    run_cycles(sup, [good_frame()] * 3)
    # A sudden 0.2 m lateral jump (vehicle moves 0.02 m per cycle): implausible.
    jump = [good_frame(ey=0.20)] * 3
    results = run_cycles(sup, jump, t0=0.3)
    assert not results[0].state_available  # implausible from the first jump frame
    assert results[1].perception_invalid   # persistence (2 cycles) → reject
    assert "jump" in results[1].plausibility_reason


def test_recovery_clears_flag():
    sup = make_supervisor()
    run_cycles(sup, [good_frame()] * 2)
    run_cycles(sup, [blank_frame()] * 3, t0=0.2)
    results = run_cycles(sup, [good_frame()] * 2, t0=0.5)
    assert results[-1].state_available
    assert not results[-1].perception_invalid


def test_reset_clears_counters():
    sup = make_supervisor()
    run_cycles(sup, [blank_frame()] * 5)
    sup.reset()
    results = run_cycles(sup, [blank_frame()], t0=1.0)
    # One bad cycle after reset: not yet persistent → no trigger.
    assert not results[0].perception_invalid
