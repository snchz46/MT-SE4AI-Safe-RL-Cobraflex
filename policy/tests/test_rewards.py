"""
Unit tests for cobraflex_rl.rewards.compute_reward — the PPO reward function
(Training Specification §7.2.3, weights v1.0). Closes F3 day D39
("tests unitarios: reward en estados sintéticos específicos").

The reward in one control cycle is

    r = w_fwd·max(progress, 0) − w_ey·|ey| − w_eps·|epsi| − w_ds·|Δsteer| − w_term·[done]

where ``progress`` is the normalised centerline advance this cycle (≈1.0 at
nominal cruise), not instantaneous speed (§7.2.3, D-34 F3 refinements). Each test
isolates one term on a synthetic TrackState so the contribution is attributable;
the final tests check term composition and the YAML reward block.
"""

import sys
from pathlib import Path

import pytest
import yaml

# rewards lives in the colcon `cobraflex_rl` package (under src/, not on the
# default path). Its __init__ is lazy (importing the package does NOT pull in
# rclpy), so the pure submodule imports without the ROS toolchain.
_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.polyline_tracker import TrackState  # noqa: E402
from cobraflex_rl.rewards import compute_reward  # noqa: E402

TRAIN_YAML = _PKG_PARENT / "config" / "train_ppo.yaml"

# Weights v1.0 (Training Spec §7.2.3). Values are [provisional, M-P1..M-P4];
# the formula tests below pin the maths, not the tuning.
WEIGHTS = {
    "forward_progress": 1.0,
    "lateral_error": 2.5,
    "heading_error": 0.75,
    "steer_delta": 0.10,
    "termination": 25.0,
}
CFG = {"reward": WEIGHTS}
NOMINAL = 1.0  # normalised progress for one nominal cruise step


def _ts(ey=0.0, epsi=0.0):
    """A TrackState carrying the fields compute_reward reads (ey, epsi)."""
    return TrackState(
        ey=ey,
        epsi=epsi,
        s=0.0,
        segment_index=0,
        segment_fraction=0.0,
        track_heading=0.0,
        closest_point=(0.0, 0.0),
    )


def _reward(track_state=None, progress=NOMINAL, steer=0.0, prev_steer=0.0, done=False):
    return compute_reward(
        track_state=track_state if track_state is not None else _ts(),
        progress=progress,
        steer=steer,
        prev_steer=prev_steer,
        done=done,
        cfg=CFG,
    )


def test_centred_straight_cruise_is_forward_progress_only():
    # ey=epsi=0, no steering change, not done -> r = w_fwd * progress
    assert _reward() == pytest.approx(1.0 * NOMINAL)


def test_lateral_error_is_penalised():
    r = _reward(track_state=_ts(ey=0.1))
    assert r == pytest.approx(NOMINAL - 2.5 * 0.1)
    assert r < _reward()  # strictly worse than centred


def test_lateral_penalty_is_symmetric():
    assert _reward(track_state=_ts(ey=0.1)) == pytest.approx(
        _reward(track_state=_ts(ey=-0.1))
    )


def test_heading_error_is_penalised():
    assert _reward(track_state=_ts(epsi=0.2)) == pytest.approx(NOMINAL - 0.75 * 0.2)


def test_steer_delta_penalises_change_not_magnitude():
    # only the change in steering is penalised
    assert _reward(steer=0.5, prev_steer=0.0) == pytest.approx(NOMINAL - 0.10 * 0.5)
    # holding the same steering costs nothing
    assert _reward(steer=0.5, prev_steer=0.5) == pytest.approx(NOMINAL)


def test_termination_applies_fixed_penalty():
    assert _reward(done=True) == pytest.approx(NOMINAL - 25.0)
    # the penalty is exactly w_term, independent of the rest of the state
    assert _reward() - _reward(done=True) == pytest.approx(25.0)


def test_negative_progress_does_not_reward_reverse():
    # forward_progress uses max(progress, 0): going backwards yields no forward reward
    assert _reward(progress=-0.5) == pytest.approx(0.0)


def test_combined_terms_sum_linearly():
    r = _reward(
        track_state=_ts(ey=0.1, epsi=0.2), progress=1.0, steer=0.5, prev_steer=0.0
    )
    expected = 1.0 * 1.0 - 2.5 * 0.1 - 0.75 * 0.2 - 0.10 * 0.5
    assert r == pytest.approx(expected)


def test_lateral_dominates_heading_for_equal_error():
    # w_ey (2.5) is the principal penalty, > w_eps (0.75): an equal-magnitude
    # lateral error must cost more than a heading error (§7.2.3).
    assert _reward(track_state=_ts(ey=0.2)) < _reward(track_state=_ts(epsi=0.2))


def test_train_yaml_has_complete_reward_block():
    with TRAIN_YAML.open(encoding="utf-8") as handle:
        reward_cfg = yaml.safe_load(handle)["reward"]
    # all five v1.0 components present and positive; the values themselves are
    # tuned experimentally ([provisional, M-P1..M-P4], §7.2.3).
    assert set(reward_cfg) == set(WEIGHTS)
    assert all(float(reward_cfg[k]) > 0.0 for k in WEIGHTS)
