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


# --- 2-D action mapping (D-50, Isaac posterior track) --------------------------

MAX_SPEED = 0.5          # = C-04 v_max_straight = ODD-1.V_MAX
DEADBAND = 0.05


def _speed2d(throttle):
    return cage_bridge.target_speed_from_throttle_2d(throttle, MAX_SPEED, DEADBAND)


def test_policy_throttle_maps_symmetric_to_cage_scale():
    # a ∈ [-1, 1] -> u ∈ [0, 1]: -1 -> 0 (stop), 0 -> 0.5, +1 -> 1 (full)
    assert cage_bridge.policy_throttle_to_cage(-1.0) == pytest.approx(0.0)
    assert cage_bridge.policy_throttle_to_cage(0.0) == pytest.approx(0.5)
    assert cage_bridge.policy_throttle_to_cage(1.0) == pytest.approx(1.0)


def test_policy_throttle_clips_out_of_range():
    assert cage_bridge.policy_throttle_to_cage(-3.0) == 0.0
    assert cage_bridge.policy_throttle_to_cage(3.0) == 1.0


def test_speed2d_is_linear_up_to_max_speed():
    assert _speed2d(1.0) == pytest.approx(MAX_SPEED)
    assert _speed2d(0.5) == pytest.approx(0.25)
    # genuine speed authority ABOVE the 1-D cruise cap (0.20) and C-04's curve
    # ceiling (0.25) — the structural change that un-latches the speed rules.
    assert _speed2d(1.0) > 0.25


def test_speed2d_deadband_commands_a_true_stop():
    # below the deadband the command is a full stop (stall must be commandable
    # for SR-009's liveness sub-mode to be well-posed)
    assert _speed2d(0.0) == 0.0
    assert _speed2d(DEADBAND / 2.0) == 0.0
    assert _speed2d(DEADBAND) == pytest.approx(MAX_SPEED * DEADBAND)


def test_speed2d_has_no_lower_speed_clamp():
    # unlike the 1-D deployment map (floor min_speed_scale·cruise = 0.07), the
    # 2-D map lets the cage attenuate speed all the way toward zero
    low = _speed2d(0.10)
    assert low == pytest.approx(0.05)
    assert 0.0 < low < MIN_SPEED_SCALE * FIXED_SPEED


def test_safe_action_to_cmd_2d_emergency_is_full_stop():
    linear, angular = cage_bridge.safe_action_to_cmd_2d(
        0.7, 0.9, True,
        max_speed=MAX_SPEED, throttle_deadband=DEADBAND, yaw_gain=YAW_GAIN,
    )
    assert (linear, angular) == (0.0, 0.0)


def test_safe_action_to_cmd_2d_applies_yaw_gain_and_speed_map():
    linear, angular = cage_bridge.safe_action_to_cmd_2d(
        0.5, 0.8, False,
        max_speed=MAX_SPEED, throttle_deadband=DEADBAND, yaw_gain=YAW_GAIN,
    )
    assert linear == pytest.approx(0.8 * MAX_SPEED)
    assert angular == pytest.approx(0.5 * 0.8)


def test_c06_bounds_2d_commanded_acceleration_to_platform_limit():
    # C-06's throttle rate limit (0.10/cycle) on the 2-D map at 10 Hz bounds
    # commanded acceleration to max_speed * 0.10 / 0.1 s = 0.5 m/s² — within the
    # platform's measured 0.53 m/s² (docs/14 §2.3). Pin the arithmetic so a
    # max_speed change that breaks the alignment fails loudly here.
    delta_max_throttle = 0.10
    control_dt = 0.10
    accel = MAX_SPEED * delta_max_throttle / control_dt
    assert accel == pytest.approx(0.5)
    assert accel <= 0.53


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
