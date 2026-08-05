"""Host-side unit tests for the pure logic of rl_policy_node (Phase-5 deploy).

The ROS wiring needs rclpy + hardware; these tests cover the parts that must be
provably correct before any bring-up: the 2-D action → Twist-field mapping and the
k=4 frame-stack layout (which must match the trained observation exactly)."""
import numpy as np
import pytest

from cobraflex_rl import cage_bridge
from cobraflex_rl.rl_policy_node import action_to_twist_fields, _FrameStacker


def test_action_to_twist_2d_maps_throttle_into_the_cage_domain():
    # /raw_action.linear.x is the cage's u in [0, 1], not the policy's a in
    # [-1, 1]: the node must apply the same policy_throttle_to_cage the sim
    # applies before the cage (u = (a+1)/2).
    steer, throttle = action_to_twist_fields(np.array([0.4, -0.7]))
    assert steer == pytest.approx(0.4)       # angular.z, unmapped
    assert throttle == pytest.approx(0.15)   # linear.x = (-0.7 + 1)/2


def test_action_to_twist_matches_the_sim_bridge_across_the_range():
    for a in (-1.0, -0.5, 0.0, 0.22, 1.0):
        _, throttle = action_to_twist_fields(np.array([0.0, a]))
        assert throttle == pytest.approx(cage_bridge.policy_throttle_to_cage(a))


def test_action_to_twist_clips_to_unit_range():
    steer, throttle = action_to_twist_fields(np.array([2.0, -3.0]))
    assert steer == pytest.approx(1.0)
    assert throttle == pytest.approx(0.0)   # a = -1 → u = 0 (full stop)


def test_action_to_twist_raw_map_is_the_legacy_passthrough():
    steer, throttle = action_to_twist_fields(
        np.array([0.4, -0.7]), throttle_map="raw"
    )
    assert steer == pytest.approx(0.4)
    assert throttle == pytest.approx(-0.7)


def test_action_to_twist_rejects_an_unknown_map():
    with pytest.raises(ValueError):
        action_to_twist_fields(np.array([0.0, 0.0]), throttle_map="linear")


def test_action_to_twist_1d_falls_back_to_the_cruise_nominal():
    # A steering-only (1-D) checkpoint has no throttle axis; the sim's
    # _apply_cage substitutes the fixed cruise nominal there, so the node must
    # publish that same value — 0.0 would read as a commanded stop.
    steer, throttle = action_to_twist_fields(np.array([0.25]))
    assert steer == pytest.approx(0.25)
    assert throttle == pytest.approx(0.5)
    _, throttle = action_to_twist_fields(np.array([0.25]), throttle_nominal=0.4)
    assert throttle == pytest.approx(0.4)


def test_deployed_chain_speed_equals_the_sim_speed():
    """End-to-end domain check of the deploy chain against the sim.

    Sim:    a --policy_throttle_to_cage--> u --cage--> u' --target_speed_2d--> v
    Deploy: a --action_to_twist_fields--> /raw_action.linear.x --cage--> /safe_action
            --vehicle_control_node(speed_map=linear_2d)--> v

    With the cage passing the throttle through (no C-04/C-06 correction) the two
    must agree at every point of the action range — that equality is what the
    launch's `throttle_map` + `speed_map` defaults buy, and what the old
    cruise-scaling path broke (it saturated at a = 0 and floored at 0.35·max).
    """
    max_speed, deadband = 0.22, 0.05
    for a in (-1.0, -0.9, -0.5, -0.1, 0.0, 0.3, 0.7, 1.0):
        sim_v = cage_bridge.target_speed_from_throttle_2d(
            cage_bridge.policy_throttle_to_cage(a), max_speed, deadband
        )
        _, raw_throttle = action_to_twist_fields(np.array([0.0, a]))
        deploy_v = cage_bridge.target_speed_from_throttle_2d(
            raw_throttle, max_speed, deadband
        )
        assert deploy_v == pytest.approx(sim_v), f"action {a}"
    # And the property the 1-D cruise map cannot express: a stop is commandable.
    _, raw_throttle = action_to_twist_fields(np.array([0.0, -1.0]))
    assert cage_bridge.target_speed_from_throttle_2d(
        raw_throttle, max_speed, deadband) == 0.0


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
