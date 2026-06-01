"""
Unit tests for cobraflex_rl.cage_bridge — the in-process glue that routes RL
actions through the safety cage (D-34, F3 task TS-01).

Coverage:
    - throttle -> speed mapping mirrors vehicle_control_node
    - safe (steering, throttle) -> /cmd_vel mapping, incl. emergency stop
    - State assembly mirrors lane_perception_node (boundary distances, signs)
    - integration: a lane-boundary violation drives C-01 to correct steering
"""

import sys
from pathlib import Path

import pytest

# cage_bridge lives in the colcon `cobraflex_rl` package, which pytest does not
# import from the repo root (src/ is in norecursedirs). The module is
# deliberately ROS-free, so import it by file path — no rclpy / ROS toolchain
# required.
_BRIDGE_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl" / "cobraflex_rl"
)
if str(_BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_DIR))

cage_bridge = pytest.importorskip("cage_bridge")


FIXED_SPEED = 0.2
THROTTLE_NOMINAL = 0.5
MIN_SPEED_SCALE = 0.35
YAW_GAIN = 0.8


def _speed(throttle):
    return cage_bridge.target_speed_from_throttle(
        throttle, FIXED_SPEED, THROTTLE_NOMINAL, MIN_SPEED_SCALE
    )


def test_target_speed_nominal_throttle_gives_cruise():
    assert _speed(0.5) == pytest.approx(0.2)


def test_target_speed_zero_throttle_stops():
    assert _speed(0.0) == 0.0


def test_target_speed_half_throttle_scales():
    # scale = 0.25/0.5 = 0.5 (within [0.35, 1.0]) -> 0.2 * 0.5
    assert _speed(0.25) == pytest.approx(0.1)


def test_target_speed_clamps_to_min_scale():
    # scale = 0.05/0.5 = 0.1 -> clamped up to min_speed_scale 0.35
    assert _speed(0.05) == pytest.approx(0.2 * 0.35)


def test_target_speed_clamps_throttle_above_nominal():
    # throttle 1.0 is clamped to throttle_nominal -> scale 1.0 -> cruise
    assert _speed(1.0) == pytest.approx(0.2)


def test_safe_action_to_cmd_emergency_is_full_stop():
    linear, angular = cage_bridge.safe_action_to_cmd(
        0.7,
        0.5,
        True,
        fixed_speed=FIXED_SPEED,
        throttle_nominal=THROTTLE_NOMINAL,
        min_speed_scale=MIN_SPEED_SCALE,
        yaw_gain=YAW_GAIN,
    )
    assert (linear, angular) == (0.0, 0.0)


def test_safe_action_to_cmd_applies_yaw_gain_and_throttle():
    linear, angular = cage_bridge.safe_action_to_cmd(
        0.5,
        0.5,
        False,
        fixed_speed=FIXED_SPEED,
        throttle_nominal=THROTTLE_NOMINAL,
        min_speed_scale=MIN_SPEED_SCALE,
        yaw_gain=YAW_GAIN,
    )
    assert linear == pytest.approx(0.2)
    assert angular == pytest.approx(0.5 * 0.8)


def test_build_cage_state_boundary_distances():
    state = cage_bridge.build_cage_state(
        lateral_offset=0.05,
        heading_error=0.1,
        speed=0.2,
        road_width=0.5,
        curvature_ahead=0.0,
        timestamp=1.0,
    )
    assert state.lateral_offset == pytest.approx(0.05)
    assert state.heading_error == pytest.approx(0.1)
    assert state.distance_left == pytest.approx(0.20)  # 0.25 - 0.05
    assert state.distance_right == pytest.approx(0.30)  # 0.25 + 0.05
    assert state.state_valid is True


def test_build_cage_state_clamps_distance_at_zero():
    state = cage_bridge.build_cage_state(
        lateral_offset=0.30,
        heading_error=0.0,
        speed=0.0,
        road_width=0.5,
        curvature_ahead=0.0,
        timestamp=0.0,
    )
    assert state.distance_left == 0.0  # max(0, 0.25 - 0.30)
    assert state.distance_right == pytest.approx(0.55)


def test_lane_violation_triggers_c01_correction():
    """End-to-end: a lateral offset beyond C-01's d_max drives the cage to
    correct the steering, using the same SafetyCageNode + cage.yaml as
    deployment."""
    cage = cage_bridge.SafetyCageNode(
        cage_bridge.resolve_cage_yaml(""), mode="enforcement"
    )
    # ey beyond C-01 d_max (0.16 m); speed below v_min_estimate so C-03/C-04
    # stay quiet and the correction is attributable to the lane-boundary rule.
    state = cage_bridge.build_cage_state(
        lateral_offset=0.18,
        heading_error=0.0,
        speed=0.0,
        road_width=0.5,
        curvature_ahead=0.0,
        timestamp=0.0,
    )
    result = cage.step(
        state, (0.0, 0.5), {"current_time": 0.0, "external_stop": False}
    )
    rules = [iv["rule"] for iv in result["interventions"]]
    safe_steer, _ = result["safe_action"]

    assert "C-01" in rules
    # Positive offset (left of centre) -> corrective steering to the right (<0),
    # matching the PD sign convention (test_baseline_pd).
    assert safe_steer < 0.0
