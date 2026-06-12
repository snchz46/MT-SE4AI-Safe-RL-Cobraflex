"""Reward function for the lane-following RL task (reward v1.2).

Single entry point :func:`compute_reward`; the weights come from the
``reward:`` section of the training config so reward shaping is recorded in
the run's reproducibility metadata. Authoritative spec: docs/10_reward_function.md
and Training Spec Ch.7 §7.2.3.
"""

from __future__ import annotations

from typing import Any, Mapping

from .polyline_tracker import TrackState


def compute_reward(
    track_state: TrackState,
    progress: float,
    steer: float,
    prev_steer: float,
    done: bool,
    cfg: Mapping[str, Any],
) -> float:
    """One control-cycle reward (Training Spec §7.2.3).

        r = w_fwd·max(progress, 0) − w_ey·|ey| − w_eps·|epsi|
            − w_ds·|Δsteer| − w_term·[done]

    ``progress`` is the *normalised* advance along the lane centerline this cycle
    (≈1.0 at nominal cruise; the env handles the closed-loop arc-length wrap),
    NOT instantaneous speed. Rewarding real progress instead of the (cage-fixed,
    near-constant) speed makes the return discriminate policy behaviour — a policy
    that survives and advances farther scores strictly higher — and keeps each
    on-track step net-positive, so ending early (e.g. via a penalty-free C-05
    emergency) is never preferable to continuing (closes the perverse-incentive
    interaction noted in D-34's F3 first-run refinements).

    ``steer``/``prev_steer`` are the **raw policy** steering of this and the
    previous cycle — NOT the post-cage applied steering. This is a deliberate
    exception to the otherwise reward-on-safe-action convention (D-34, §7.2.5):
    the smoothness term exists to shape the *policy's own* actuation, and the
    rate-limiter C-06 absorbs raw bang-bang into a near-identical smoothed signal,
    so measuring the post-cage delta makes the penalty toothless (the F3 eval saw
    the policy drive C-06 to its limit ~89% of steps for free; §7.5.2). Penalising
    the raw delta makes the policy pay for its own jerk. All other terms stay on
    the safe action / resulting state."""
    reward_cfg = cfg.get("reward", cfg)

    lateral_penalty = float(reward_cfg.get("lateral_error", 1.0)) * abs(track_state.ey)
    heading_penalty = float(reward_cfg.get("heading_error", 0.5)) * abs(
        track_state.epsi
    )
    steer_penalty = float(reward_cfg.get("steer_delta", 0.1)) * abs(
        float(steer) - float(prev_steer)
    )
    forward_reward = float(reward_cfg.get("forward_progress", 1.0)) * max(
        float(progress), 0.0
    )

    reward = forward_reward - lateral_penalty - heading_penalty - steer_penalty
    if done:
        reward -= float(reward_cfg.get("termination", 10.0))

    return float(reward)
