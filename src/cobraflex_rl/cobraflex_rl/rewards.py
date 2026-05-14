from __future__ import annotations

from typing import Any, Mapping

from .polyline_tracker import TrackState


def compute_reward(
    track_state: TrackState,
    speed: float,
    steer: float,
    prev_steer: float,
    done: bool,
    cfg: Mapping[str, Any],
) -> float:
    reward_cfg = cfg.get("reward", cfg)

    lateral_penalty = float(reward_cfg.get("lateral_error", 1.0)) * abs(track_state.ey)
    heading_penalty = float(reward_cfg.get("heading_error", 0.5)) * abs(
        track_state.epsi
    )
    steer_penalty = float(reward_cfg.get("steer_delta", 0.1)) * abs(
        float(steer) - float(prev_steer)
    )
    forward_reward = float(reward_cfg.get("forward_progress", 1.0)) * max(
        float(speed), 0.0
    )

    reward = forward_reward - lateral_penalty - heading_penalty - steer_penalty
    if done:
        reward -= float(reward_cfg.get("termination", 10.0))

    return float(reward)
