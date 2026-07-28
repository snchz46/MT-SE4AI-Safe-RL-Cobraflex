"""Host-side unit tests for the pure logic of rl_policy_node (Phase-5 deploy).

The ROS wiring needs rclpy + hardware; these tests cover the parts that must be
provably correct before any bring-up: the 2-D action → Twist-field mapping and the
k=4 frame-stack layout (which must match the trained observation exactly)."""
import numpy as np
import pytest

from cobraflex_rl.rl_policy_node import action_to_twist_fields, _FrameStacker


def test_action_to_twist_2d_maps_steer_and_throttle():
    steer, throttle = action_to_twist_fields(np.array([0.4, -0.7]))
    assert steer == pytest.approx(0.4)      # angular.z
    assert throttle == pytest.approx(-0.7)  # linear.x


def test_action_to_twist_clips_to_unit_range():
    steer, throttle = action_to_twist_fields(np.array([2.0, -3.0]))
    assert steer == pytest.approx(1.0)
    assert throttle == pytest.approx(-1.0)


def test_action_to_twist_1d_falls_back_to_zero_throttle():
    # A steering-only (1-D) checkpoint → throttle 0 (cruise nominal applied downstream).
    steer, throttle = action_to_twist_fields(np.array([0.25]))
    assert steer == pytest.approx(0.25)
    assert throttle == pytest.approx(0.0)


def test_frame_stack_reset_replicates_first_frame():
    st = _FrameStacker(4)
    f = np.full((84, 84, 1), 7, dtype=np.uint8)
    obs = st.reset(f)
    assert obs.shape == (84, 84, 4)           # k=4 on the channel axis
    assert np.all(obs == 7)


def test_frame_stack_step_keeps_last_k_newest_last():
    st = _FrameStacker(4)
    st.reset(np.zeros((84, 84, 1), dtype=np.uint8))
    for v in (1, 2, 3, 4):
        obs = st.step(np.full((84, 84, 1), v, dtype=np.uint8))
    # after 4 steps the window holds frames 1,2,3,4 (newest last)
    assert obs.shape == (84, 84, 4)
    assert [int(obs[0, 0, c]) for c in range(4)] == [1, 2, 3, 4]
