"""
Unit tests for cobraflex_rl.cage_perception — the track-'E' supervisor that
composes the CV lane-estimator with the SR-013 health monitor and the SR-014
plausibility check into the cage's state + C-05 Trigger 8 contract (D-43).

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
    # Supervisor persistence is 4 cycles (0.4 s at 10 Hz — bridges the
    # measured ~2-cycle dash-gap blind stretches at the oval curve apex,
    # inside the cage's 5-cycle missing-state budget).
    results = run_cycles(sup, [blank_frame()] * 5, t0=0.3)
    assert not results[0].state_available
    assert not results[2].perception_invalid  # 3 bad cycles: not yet
    assert results[3].perception_invalid      # 4th consecutive: trigger
    assert "features" in results[3].health_reason or "confidence" in results[3].health_reason


def test_dropped_frames_raise_trigger():
    sup = make_supervisor()
    run_cycles(sup, [good_frame()] * 2)
    # No frame for 5 cycles: staleness (default 0.2 s) + 4-cycle persistence.
    results = []
    for i in range(5):
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


# --------------------------------------------------------------------------
# D-77 — SR-014's inter-frame lateral gate is configurable, and the deployed
# default is deliberately NOT the frozen one.
# --------------------------------------------------------------------------

def test_jump_tol_defaults_to_the_frozen_value_so_the_verdict_path_is_unchanged():
    """The D-69 verdict was scored with LanePlausibilityCheck's own 0.10 m.
    Omitting the override must leave it exactly there — the Gazebo path stays
    bit-identical and no re-run is owed."""
    sup = CagePerceptionSupervisor()
    assert sup.plausibility.jump_tol_m == pytest.approx(0.10)


def test_jump_tol_override_reaches_the_checker():
    sup = CagePerceptionSupervisor(jump_tol_m=0.05)
    assert sup.plausibility.jump_tol_m == pytest.approx(0.05)


def test_overriding_jump_tol_preserves_the_E2_lane_width_INVARIANT():
    """The SR-014 width window must stay equal to the estimator's own pair
    acceptance window; decoupling them re-creates the E2 dead zone that
    deadlocked the cage into its no-state path."""
    sup = CagePerceptionSupervisor(jump_tol_m=0.05)
    cfg = sup.estimator.config
    assert sup.plausibility.lane_width_lo == pytest.approx(
        cfg.lane_width_nominal_m - cfg.lane_width_tol_m)
    assert sup.plausibility.lane_width_hi == pytest.approx(
        cfg.lane_width_nominal_m + cfg.lane_width_tol_m)


def test_a_relocation_the_frozen_gate_admits_is_caught_by_the_tightened_one():
    """The measured failure: at 0.22 m/s and a 50 ms cycle the physical lateral
    motion is 11 mm, so the frozen 0.10 m tolerance admits a 111 mm jump as
    temporally consistent. 90 mm is such a relocation — inside the frozen gate,
    outside the tightened one. Suppression, not emergency: one bad frame must
    not raise C-05 (that needs min_implausible_cycles)."""
    from cobraflex_rl.lane_plausibility import LaneEstimate, LanePlausibilityCheck

    def probe(tol):
        chk = LanePlausibilityCheck(lane_width_range=(0.145, 0.345),
                                    curvature_max=3.0, jump_tol_m=tol)
        good = LaneEstimate(ey=0.0, heading=0.0, lane_width=0.245,
                            curvature=0.0, timestamp_s=100.0)
        chk.update(good, speed_mps=0.22, now_s=100.0)
        jumped = LaneEstimate(ey=0.090, heading=0.0, lane_width=0.245,
                              curvature=0.0, timestamp_s=100.05)
        return chk.update(jumped, speed_mps=0.22, now_s=100.05)

    frozen, tightened = probe(0.10), probe(0.05)
    assert frozen.plausible, "the frozen gate admits the 90 mm relocation"
    assert not tightened.plausible, "the tightened gate must catch it"
    assert not tightened.reject, "one frame suppresses state; it must not raise C-05"
