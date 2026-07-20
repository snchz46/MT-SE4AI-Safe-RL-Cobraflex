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

# Weights (Training Spec §7.2.3): forward driver v1.1, steer_delta v1.2
# (0.10 -> 0.20, now on the RAW policy delta; §7.2.5 / §7.5.2). Values are
# [provisional, M-P1..M-P4]; the formula tests below pin the maths, not the tuning.
WEIGHTS = {
    "forward_progress": 1.0,
    "lateral_error": 2.5,
    "heading_error": 0.75,
    "steer_delta": 0.20,
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
    # only the change in steering is penalised (steer/prev_steer are the RAW
    # policy commands; the env feeds raw, not post-cage, deltas — §7.2.5)
    assert _reward(steer=0.5, prev_steer=0.0) == pytest.approx(NOMINAL - 0.20 * 0.5)
    # holding the same steering costs nothing
    assert _reward(steer=0.5, prev_steer=0.5) == pytest.approx(NOMINAL)


def test_raw_bang_bang_costs_more_than_smooth_ramp():
    # A sign flip (raw bang-bang, |Δ|=2.0) must cost far more than a gradual ramp
    # within C-06's rate limit (|Δ|=0.15). This is the whole point of measuring
    # the RAW delta (reward v1.2, §7.5.2): the policy now pays for jerk that C-06
    # would otherwise absorb for free.
    flip = _reward(steer=1.0, prev_steer=-1.0)
    ramp = _reward(steer=0.15, prev_steer=0.0)
    assert (NOMINAL - flip) == pytest.approx(0.20 * 2.0)
    assert (NOMINAL - ramp) == pytest.approx(0.20 * 0.15)
    assert flip < ramp


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
    expected = 1.0 * 1.0 - 2.5 * 0.1 - 0.75 * 0.2 - 0.20 * 0.5
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


# --- 2-D action: raw-throttle smoothness term (D-50) ---------------------------

ISAAC_2D_YAML = _PKG_PARENT / "config" / "train_isaac_2d.yaml"


def test_throttle_args_are_inert_without_weight():
    # Passing throttle/prev_throttle with no `throttle_delta` weight in the
    # config must not change the return (weight defaults to 0.0) — the frozen
    # 1-D configs stay bit-identical even if a caller supplies throttle.
    assert compute_reward(
        track_state=_ts(), progress=NOMINAL, steer=0.0, prev_steer=0.0,
        done=False, cfg=CFG, throttle=1.0, prev_throttle=0.0,
    ) == pytest.approx(_reward())


def test_throttle_none_is_the_default_legacy_path():
    # Omitting the args entirely (every existing call site) is the 1-D path.
    assert _reward() == pytest.approx(1.0 * NOMINAL)


def test_throttle_delta_penalises_change_not_magnitude():
    cfg = {"reward": dict(WEIGHTS, throttle_delta=0.10)}
    kw = dict(track_state=_ts(), progress=NOMINAL, steer=0.0, prev_steer=0.0,
              done=False, cfg=cfg)
    # a full-range jump (0 -> 1 on the cage scale) costs w_dt * 1.0
    assert compute_reward(**kw, throttle=1.0, prev_throttle=0.0) == pytest.approx(
        NOMINAL - 0.10 * 1.0
    )
    # holding the same throttle costs nothing
    assert compute_reward(**kw, throttle=0.7, prev_throttle=0.7) == pytest.approx(
        NOMINAL
    )


def test_isaac_2d_yaml_reward_block_extends_v12_with_throttle_delta():
    with ISAAC_2D_YAML.open(encoding="utf-8") as handle:
        reward_cfg = yaml.safe_load(handle)["reward"]
    # v1.2 base + throttle_delta (D-50) + stall_penalty/stall_progress_min (D-56).
    assert set(reward_cfg) == set(WEIGHTS) | {
        "throttle_delta", "stall_penalty", "stall_progress_min"
    }
    assert all(float(v) > 0.0 for v in reward_cfg.values())


def test_stall_penalty_inert_by_default():
    # No stall_penalty key (every pre-D-56 config): parked progress just earns
    # zero forward reward — bit-identical returns.
    assert _reward(progress=0.0) == pytest.approx(0.0)


def test_stall_penalty_fires_below_progress_threshold():
    cfg = {"reward": dict(WEIGHTS, stall_penalty=0.5, stall_progress_min=0.25)}
    kw = dict(track_state=_ts(), steer=0.0, prev_steer=0.0, done=False, cfg=cfg)
    # Parked (progress 0): pay the stall penalty every step.
    assert compute_reward(progress=0.0, **kw) == pytest.approx(-0.5)
    # Semi-stall crawl below the threshold still pays.
    assert compute_reward(progress=0.1, **kw) == pytest.approx(0.1 - 0.5)


def test_stall_penalty_not_charged_while_driving():
    cfg = {"reward": dict(WEIGHTS, stall_penalty=0.5, stall_progress_min=0.25)}
    kw = dict(track_state=_ts(), steer=0.0, prev_steer=0.0, done=False, cfg=cfg)
    # Slow-but-driving (progress 0.6 = 0.12 m/s at cruise 0.2) is NOT a stall.
    assert compute_reward(progress=0.6, **kw) == pytest.approx(0.6)
    assert compute_reward(progress=NOMINAL, **kw) == pytest.approx(NOMINAL)


def test_sc_pert_03_lambda_stall_is_inert_by_default_and_penalises_throttle():
    kw = dict(
        track_state=_ts(), progress=NOMINAL, steer=0.0, prev_steer=0.0,
        done=False, throttle=0.4, prev_throttle=0.4,
    )
    base = compute_reward(cfg={"reward": WEIGHTS}, **kw)
    injected = compute_reward(
        cfg={"reward": dict(WEIGHTS, lambda_stall=4.0)}, **kw
    )
    assert base - injected == pytest.approx(4.0 * 0.4)


def test_sc_pert_03_lambda_stall_does_not_affect_legacy_1d_action():
    kw = dict(
        track_state=_ts(), progress=NOMINAL, steer=0.0, prev_steer=0.0,
        done=False,
    )
    assert compute_reward(
        cfg={"reward": dict(WEIGHTS, lambda_stall=4.0)}, **kw
    ) == pytest.approx(compute_reward(cfg={"reward": WEIGHTS}, **kw))
