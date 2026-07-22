"""
Unit tests for the D-50 extensions of GazeboLaneEnv — the 2-D action
(steering + throttle) and the multi-circuit per-episode track sampling — with
the real SafetyCageNode/cage.yaml in the loop, driven against a pure-python
fake of the simulator interface (no Gazebo, no Isaac, no ROS).

The fake implements the duck-typed surface the env calls (the same contract
RosGazeboInterface and IsaacSimInterface satisfy) with a trivial unicycle
integrator, so cage arbitration (C-04 attenuation, C-06 rate limiting), the
actuation mapping and the circuit selection are all exercised end-to-end.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# The env lives in the colcon `cobraflex_rl` package (under src/, not on the
# default path). Its __init__ is lazy and the env module imports without
# rclpy/cv2, so the package imports on any host.
_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

gym = pytest.importorskip("gymnasium")

from cobraflex_rl.gazebo_lane_env import GazeboLaneEnv  # noqa: E402


class _Logger:
    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    warn = warning
    error = warning
    debug = warning


class FakeInterface:
    """Minimal in-memory sim: unicycle kinematics, ground-truth pose."""

    def __init__(self):
        self.x = self.y = self.yaw = 0.0
        self._cmd = (0.0, 0.0)  # (angular_z, linear_x) as sent by the env
        self.t = 0.0
        self.sent = []          # log of every send_action(steer, speed)
        self._logger = _Logger()

    # --- lifecycle / logging ---
    def get_logger(self):
        return self._logger

    def reset_world(self):
        pass

    # --- actuation / stepping ---
    def send_action(self, steer, speed):
        self._cmd = (float(steer), float(speed))
        self.sent.append((float(steer), float(speed)))

    def step_ros(self, duration):
        steer, speed = self._cmd
        self.yaw += steer * duration
        self.x += speed * math.cos(self.yaw) * duration
        self.y += speed * math.sin(self.yaw) * duration
        self.t += duration

    def spin_wall(self, duration):
        self.t += duration  # command unchanged; stationary unless commanded

    def wait_for_initial_data(self, timeout_sec=10.0):
        return True

    # --- reset / teleport ---
    def set_vehicle_pose(self, x, y, yaw):
        self.x, self.y, self.yaw = float(x), float(y), float(yaw)

    def calibrate_pose_offset(self, *args):
        return None

    # --- sensing ---
    def get_pose(self):
        return self.x, self.y, self.yaw

    def get_speed(self):
        return abs(self._cmd[1])

    def sim_now(self):
        return float(self.t)

    def clear_camera_frame(self):
        pass

    def get_camera_frame(self):
        return None


def _circle(radius=5.0, n=120, center=(0.0, 0.0)):
    ang = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return np.stack(
        [center[0] + radius * np.cos(ang), center[1] + radius * np.sin(ang)], axis=1
    )


def _cfg(action_type="steer_throttle"):
    cfg = {
        "fixed_speed": 0.2,
        "control_dt": 0.1,
        "max_episode_steps": 50,
        "observation": {"type": "state"},
        "cage": {"enabled": True, "mode": "enforcement", "yaml_path": ""},
        "spawn_perturbation": {"enabled": False},
        "reward": {
            "lateral_error": 2.5,
            "heading_error": 0.75,
            "steer_delta": 0.20,
            "throttle_delta": 0.10,
            "forward_progress": 1.0,
            "termination": 25.0,
        },
    }
    if action_type is not None:
        cfg["action"] = {
            "type": action_type,
            "max_speed_mps": 0.5,
            "throttle_deadband": 0.05,
        }
    return cfg


def _env(action_type="steer_throttle", **kwargs):
    return GazeboLaneEnv(
        ros_interface=FakeInterface(),
        centerline=_circle(),
        lane_width=0.245,
        road_width=0.52,
        cfg=_cfg(action_type),
        **kwargs,
    )


# --- action space contract ------------------------------------------------------


def test_2d_action_space():
    env = _env()
    assert env.action_space.shape == (2,)
    assert np.allclose(env.action_space.low, [-1.0, -1.0])
    assert np.allclose(env.action_space.high, [1.0, 1.0])


def test_default_config_keeps_the_frozen_1d_contract():
    # No `action:` block (every F/E-track config) -> steering-only Box(1).
    env = GazeboLaneEnv(
        ros_interface=FakeInterface(),
        centerline=_circle(),
        lane_width=0.245,
        road_width=0.52,
        cfg={k: v for k, v in _cfg(None).items()},
    )
    assert env.action_space.shape == (1,)


def test_unknown_action_type_rejected():
    with pytest.raises(ValueError):
        _env(action_type="steer_brake_gears")


# --- throttle authority through the cage ----------------------------------------


def test_full_throttle_actuates_max_speed():
    env = _env()
    env.reset(seed=0)
    env.step(np.array([0.0, 1.0], dtype=np.float32))
    steer, speed = env.ros_interface.sent[-1]
    # first cycle: no prev action (C-06 quiet), observed speed 0 (C-04 quiet)
    assert speed == pytest.approx(0.5)
    assert steer == pytest.approx(0.0)


def test_neutral_throttle_actuates_half_speed():
    env = _env()
    env.reset(seed=0)
    env.step(np.array([0.0, 0.0], dtype=np.float32))
    assert env.ros_interface.sent[-1][1] == pytest.approx(0.25)


def test_full_brake_is_a_true_stop():
    # The policy can command inaction — the stall/liveness (SR-009, M-P6)
    # sub-mode is well-posed on this action space (D-49 -> D-50).
    env = _env()
    env.reset(seed=0)
    _, _, _, _, info = env.step(np.array([0.0, -1.0], dtype=np.float32))
    assert env.ros_interface.sent[-1][1] == 0.0
    assert info["raw_throttle"] == pytest.approx(0.0)


def test_c06_rate_limits_the_policy_throttle():
    env = _env()
    env.reset(seed=0)
    env.step(np.array([0.0, -1.0], dtype=np.float32))   # u=0 (committed)
    _, _, _, _, info = env.step(np.array([0.0, 1.0], dtype=np.float32))  # u=1
    # C-06 clips the throttle jump to delta_max_throttle_per_cycle = 0.10
    assert "C-06" in info["cage_interventions"]
    assert info["safe_throttle"] == pytest.approx(0.10)
    assert env.ros_interface.sent[-1][1] == pytest.approx(0.10 * 0.5)


def test_c04_attenuates_overspeed_for_real():
    # Cycle 1 commits full throttle (0.5 m/s actuated); on cycle 2 the observed
    # speed 0.5 exceeds the curvature ceiling (circle R=5 -> kappa 0.2 ->
    # v_max = 0.5 - 0.3*0.2 = 0.44) and C-04 attenuates the throttle — the
    # structurally-latent-in-1-D speed rule genuinely fires on this action space.
    env = _env()
    env.reset(seed=0)
    env.step(np.array([0.0, 1.0], dtype=np.float32))
    _, _, _, _, info = env.step(np.array([0.0, 1.0], dtype=np.float32))
    assert "C-04" in info["cage_interventions"]
    assert info["safe_throttle"] < info["raw_throttle"]
    assert env.ros_interface.sent[-1][1] < 0.5


def test_2d_info_carries_the_throttle_stream():
    env = _env()
    env.reset(seed=0)
    _, _, _, _, info = env.step(np.array([0.0, 0.5], dtype=np.float32))
    assert info["raw_throttle"] == pytest.approx(0.75)  # (0.5+1)/2
    assert "safe_throttle" in info and "throttle_correction" in info
    assert info["throttle_correction"] == pytest.approx(
        info["safe_throttle"] - info["raw_throttle"]
    )


def test_1d_path_actuation_unchanged():
    # Legacy contract: steering-only action, fixed cruise actuation (0.2 m/s
    # at the nominal throttle) — bit-compatible with the frozen F/E runs.
    env = _env(action_type=None)
    env.reset(seed=0)
    _, _, _, _, info = env.step(np.array([0.3], dtype=np.float32))
    assert env.ros_interface.sent[-1][1] == pytest.approx(0.2)
    assert info["raw_throttle"] == pytest.approx(0.5)  # the fixed nominal


def test_calibration_mode_observes_stop_without_changing_default_termination():
    outcomes = []
    for calibration_mode in (False, True):
        env = _env(action_type=None, calibration_mode=calibration_mode)
        env.reset(seed=0)
        env.ros_interface.yaw += 0.55
        env.last_track_state = env._compute_track_state()
        _, _, terminated, _, info = env.step(
            np.array([0.0], dtype=np.float32)
        )
        assert info["cage_emergency"]
        outcomes.append(terminated)
    assert outcomes == [True, False]


def test_heading_injector_is_unavailable_outside_calibration():
    env = _env(action_type=None)
    with pytest.raises(RuntimeError, match="calibration_mode"):
        env.inject_heading_fault_for_calibration(0.48)


# --- multi-circuit sampling (D-50) ----------------------------------------------


def _two_circuit_env():
    return GazeboLaneEnv(
        ros_interface=FakeInterface(),
        cfg=_cfg(),
        circuits=[
            {
                "name": "near",
                "centerline": _circle(center=(0.0, 0.0)),
                "lane_width": 0.245,
                "road_width": 0.52,
            },
            {
                "name": "far",
                "centerline": _circle(center=(30.0, 0.0)),
                "lane_width": 0.245,
                "road_width": 0.52,
            },
        ],
    )


def test_multi_circuit_sampling_covers_all_circuits():
    env = _two_circuit_env()
    seen = set()
    for seed in range(8):
        _, info = env.reset(seed=seed)
        seen.add(info["circuit_index"])
    assert seen == {0, 1}


def test_multi_circuit_reset_is_seed_reproducible():
    env = _two_circuit_env()
    first = [env.reset(seed=s)[1]["circuit_index"] for s in range(6)]
    second = [env.reset(seed=s)[1]["circuit_index"] for s in range(6)]
    assert first == second


def test_circuit_index_option_pins_the_circuit():
    env = _two_circuit_env()
    _, info = env.reset(seed=0, options={"circuit_index": 1})
    assert info["circuit_index"] == 1
    assert info["circuit_name"] == "far"
    # the spawn actually landed on the far circuit (centred at x=30)
    assert env.ros_interface.x > 20.0
    _, info = env.reset(seed=0, options={"circuit_index": 0})
    assert info["circuit_index"] == 0
    assert env.ros_interface.x < 20.0


def test_multi_circuit_episode_runs_on_the_selected_geometry():
    env = _two_circuit_env()
    env.reset(seed=0, options={"circuit_index": 1})
    _, reward, terminated, truncated, info = env.step(
        np.array([0.0, 1.0], dtype=np.float32)
    )
    assert not terminated and not truncated
    assert info["circuit_name"] == "far"
    # ey measured against the far circuit, not the near one (spawn is on-lane)
    assert abs(info["ey"]) < 0.05


def test_single_circuit_env_has_no_circuit_info_keys():
    env = _env()
    _, info = env.reset(seed=0)
    assert "circuit_index" not in info


# --- SB3 compatibility ------------------------------------------------------------


def test_sb3_check_env_passes_on_the_2d_env():
    check_env = pytest.importorskip(
        "stable_baselines3.common.env_checker"
    ).check_env
    check_env(_env(), warn=True, skip_render_check=True)
