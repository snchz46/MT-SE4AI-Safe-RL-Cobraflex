"""
Unit tests for GazeboLaneEnv's mirror augmentation (sim-to-real, D-71 follow-up).

complex_b is driven counter-clockwise and is 6.5:1 left-dominant, and a policy
trained only on it learns a constant left-steer prior — measured at +0.112...+0.120
mean raw steering, flat across the 285k-step sim-to-real fine-tune, with the
lane-independent probe bias unmoved (+0.122 -> +0.124). Mirroring half the
episodes balances the distribution instead of correcting the policy.

The augmentation is only sound if it is applied *consistently*: the frame flip
must reach the policy observation and the cage's CV estimator together (they
share one pipeline call), and the steering must be negated back exactly once, at
the actuator. These tests pin both, plus the RNG discipline and the rule that a
scenario-driven episode never mirrors.

Driven against a pure-python fake interface — no Gazebo, no ROS.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

pytest.importorskip("gymnasium")
cv2 = pytest.importorskip("cv2")

from cobraflex_rl.gazebo_lane_env import GazeboLaneEnv  # noqa: E402


class _Logger:
    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    warn = warning
    error = warning


class CameraFakeInterface:
    """Unicycle fake that also serves a deterministic, LEFT-RIGHT ASYMMETRIC
    camera frame, so a flip is detectable rather than a no-op."""

    def __init__(self):
        self.x = self.y = self.yaw = 0.0
        self._cmd = (0.0, 0.0)
        self.t = 0.0
        self.sent = []
        self._logger = _Logger()
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        frame[200:360, 40:120] = 255       # a bright bar, left of centre only
        frame[250:300, 500:560] = 128
        self.frame = frame

    def get_logger(self):
        return self._logger

    def reset_world(self):
        pass

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
        self.t += duration

    def wait_for_initial_data(self, timeout_sec=10.0):
        return True

    def set_vehicle_pose(self, x, y, yaw):
        self.x, self.y, self.yaw = float(x), float(y), float(yaw)

    def calibrate_pose_offset(self, *args):
        return None

    def get_pose(self):
        return self.x, self.y, self.yaw

    def get_speed(self):
        return abs(self._cmd[1])

    def sim_now(self):
        return float(self.t)

    def clear_camera_frame(self):
        pass

    def get_camera_frame(self):
        return self.frame, float(self.t)


def _circle(radius=5.0, n=120):
    ang = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return np.stack([radius * np.cos(ang), radius * np.sin(ang)], axis=1)


def _cfg(**overrides):
    cfg = {
        "fixed_speed": 0.2,
        "control_dt": 0.1,
        "max_episode_steps": 50,
        "observation": {
            "type": "camera",
            "camera": {"width": 84, "height": 84, "grayscale": True, "frame_stack": 4},
        },
        "action": {"type": "steer_throttle", "max_speed_mps": 0.22},
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
    cfg.update(overrides)
    return cfg


def _env(**overrides):
    return GazeboLaneEnv(
        ros_interface=CameraFakeInterface(),
        centerline=_circle(),
        lane_width=0.245,
        road_width=0.52,
        cfg=_cfg(**overrides),
    )


# --- gating and RNG discipline ----------------------------------------------


def test_absent_block_never_mirrors_and_consumes_no_rng():
    env = _env()
    assert env.mirror_enabled is False
    rng = env.np_random
    before = rng.bit_generator.state
    for _ in range(50):
        assert env._resolve_visual_injector({}) is None
        assert env._mirror is False
    assert rng.bit_generator.state == before


def test_p_one_always_mirrors_and_p_zero_never_does():
    for p, expected in ((1.0, True), (0.0, False)):
        env = _env(mirror_augmentation={"enabled": True, "p": p})
        for _ in range(20):
            env._resolve_visual_injector({})
            assert env._mirror is expected


def test_draw_is_roughly_balanced_at_p_half():
    env = _env(mirror_augmentation={"enabled": True, "p": 0.5})
    env.reset(seed=2024)
    draws = []
    for _ in range(2000):
        env._resolve_visual_injector({})
        draws.append(env._mirror)
    assert 0.45 < np.mean(draws) < 0.55


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError, match="mirror_augmentation.p"):
        _env(mirror_augmentation={"enabled": True, "p": 1.4})


# --- the flip itself --------------------------------------------------------


def test_injector_flips_the_frame_horizontally():
    env = _env(mirror_augmentation={"enabled": True, "p": 1.0})
    injector = env._resolve_visual_injector({})
    frame = env.ros_interface.frame
    assert np.array_equal(injector(frame), frame[:, ::-1])


def test_flip_reaches_the_policy_obs_and_the_cage_frame_together():
    """One pipeline call feeds both consumers, so they cannot disagree about
    which way round the world is."""
    env = _env(mirror_augmentation={"enabled": True, "p": 1.0})
    env.reset(seed=0)
    assert env._mirror is True
    raw = env.ros_interface.frame
    # The retained native frame (what the CV estimator reads) is the flipped one
    assert np.array_equal(env._cam_frame, raw[:, ::-1])
    # ...and the policy observation is the downsample of that same frame
    from cobraflex_rl.camera_pipeline import to_observation

    assert np.array_equal(env._last_obs_img, to_observation(raw[:, ::-1]))


def test_chain_order_is_mirror_then_geometry_then_photometry():
    """The physical order: the scene is mirrored (a convention over the whole
    world), the optics see that scene, the sensor's photometry happens last."""
    env = _env(
        mirror_augmentation={"enabled": True, "p": 1.0},
        geometric_randomization={"enabled": True, "p_pose": 1.0},
        domain_randomization={
            "enabled": True,
            "p_degrade": 1.0,
            "modes": ["low_contrast"],
            "level_range": [0.8, 0.8],
        },
    )
    injector = env._resolve_visual_injector({})
    frame = env.ros_interface.frame
    expected = frame[:, ::-1]
    expected = env.geometric_randomizer.apply(
        np.ascontiguousarray(expected), env._geom_spec
    )
    expected = env.domain_randomizer.apply(expected, env._dr_spec)
    assert np.array_equal(injector(frame), expected)


# --- the actuator -----------------------------------------------------------


def test_actuated_steering_is_negated_exactly_once():
    """Isolated deliberately: the mirror flag is forced on an env whose config
    leaves the augmentation OFF, so the frame is identical in both arms and the
    only difference on the wire is the negation."""
    action = np.array([0.6, 0.4], dtype=np.float32)
    plain = _env()
    plain.reset(seed=1)
    plain.step(action)
    straight = plain.ros_interface.sent[-1]

    mirrored = _env()
    mirrored.reset(seed=1)
    mirrored._mirror = True
    mirrored.step(action)
    flipped = mirrored.ros_interface.sent[-1]

    assert flipped[0] == pytest.approx(-straight[0])
    assert flipped[1] == pytest.approx(straight[1])  # speed is unsigned


def test_ground_truth_metrics_stay_in_the_unmirrored_world():
    """`ey` in info is the oracle, not the policy's view: a mirrored episode
    must not flip the sign of the metric every campaign is scored on."""
    env = _env(mirror_augmentation={"enabled": True, "p": 1.0})
    env.reset(seed=3)
    _, _, _, _, info = env.step(np.array([0.2, 0.3], dtype=np.float32))
    truth = env._compute_track_state()
    assert info["ey"] == pytest.approx(truth.ey)
    assert info["mirrored"] is True


# --- scenarios must never mirror --------------------------------------------


@pytest.mark.parametrize(
    "opts",
    [
        {"visual_injector": lambda f: f},
        {"visual_degradation": {"mode": "glare", "level": 0.5}},
    ],
)
def test_scenario_episodes_never_mirror(opts):
    """SC-* episodes are the verdict-bearing artefacts; the augmentation is a
    training-only device and must be inert whenever a scenario dictates the
    frame."""
    env = _env(mirror_augmentation={"enabled": True, "p": 1.0})
    env._mirror = True  # stale from a previous training episode
    env._resolve_visual_injector(opts)
    assert env._mirror is False


# --- the loop is closed with the RIGHT sign ---------------------------------


def test_a_geometric_controller_issues_the_SAME_physical_command_when_mirrored():
    """The invariant the whole augmentation rests on, end to end on real frames.

    The unit test above pins that the actuator negates a *fixed* policy action.
    That is not the same as the loop being consistent: what must hold is that a
    controller which reacts to what it sees produces the *identical physical*
    command either way round. Otherwise the mirrored half of training would be
    driving into the boundary the cage is trying to keep it off, and five days of
    compute would go into learning from a broken world.

    Composition being checked: the D-43 estimator is antisymmetric under the
    flip, so a sign-linear controller's command negates; the env then negates it
    back at the actuator; the two cancel.

    Uses the 420-frame Gazebo pose set, which carries its true ey in the
    filename, and the shipped pure-pursuit CV controller (docs/12) — geometric,
    no learning, so it has no handedness prior of its own to confound the test.
    """
    frames_dir = (
        Path(__file__).resolve().parents[2]
        / "experiments/sim/runs/cv_probe_weak_sections_20260713T084230Z"
        / "raw_logs/frames"
    )
    paths = sorted(frames_dir.glob("*.png"))
    if len(paths) < 50:
        pytest.skip("Gazebo probe frames not present on this host (gitignored)")

    from cobraflex_rl.cv_lane_controller import CVLaneController

    plain, mirrored = CVLaneController(), CVLaneController()
    compared = 0
    for path in paths[::4]:
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        straight, ok_a = plain.compute(frame)
        flipped, ok_b = mirrored.compute(np.ascontiguousarray(frame[:, ::-1]))
        if not (ok_a and ok_b):
            continue
        # `flipped` is the command in the mirrored convention; the env negates it
        # at the actuator, and the result must be what the unmirrored arm sent.
        # Tolerance from the measured residual, not from taste: the flip is
        # centred on the pixel grid rather than on cx, which costs a CONSTANT
        # 0.075 mm of ey (mean = p95 = max, no outliers) and a bounded 0.0032
        # steering difference. camera_pipeline.mirror_frame documents why the
        # exact correction is worse. A genuine sign error would land here at
        # twice the command, not at 3e-3.
        assert -flipped == pytest.approx(straight, abs=4e-3), path.name
        compared += 1
    assert compared >= 40, f"only {compared} frames yielded a lane estimate both ways"
