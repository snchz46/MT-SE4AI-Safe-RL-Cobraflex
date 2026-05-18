"""
BaselinePD — pure-Python PD controller for the F2 pipeline validation.

The PD is the baseline policy that exercises the safety cage end-to-end
during Phase 2 (Milestone M1 demo) and reappears in Phase 8 as the
comparison baseline against the trained RL policy. It is deliberately
simple: PD on lateral_offset, PD on heading_error, curve-aware throttle.

Per Phase 2 plan §10.2:
    steering = -kp_y · y  - kd_y · ẏ
               -kp_h · ψ  - kd_h · ψ̇
    throttle = throttle_nominal · max(0, 1 - alpha · |κ_ahead|)

Lateral and heading rates are finite-differenced from the previous
state observation. `reset()` clears the history, e.g. on lap reset.

The ROS2 node that wires this controller to /state_obs and /raw_action
will live under `src/cobraflex` (Phase 2 D31); this file is the pure-
Python logic so the controller can be unit-tested without ROS2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from cage.rules import Action, State


class BaselinePD:
    def __init__(self, params: dict):
        self.kp_y = params["kp_y"]
        self.kd_y = params["kd_y"]
        self.kp_h = params["kp_h"]
        self.kd_h = params["kd_h"]
        self.throttle_nominal = params["throttle_nominal"]
        self.alpha = params["alpha_curve_slowdown"]
        self.steering_limit = params.get("steering_limit", 1.0)
        self.throttle_min = params.get("throttle_min", 0.0)
        self.throttle_max = params.get("throttle_max", 1.0)
        self._prev_y: Optional[float] = None
        self._prev_psi: Optional[float] = None
        self._prev_t: Optional[float] = None

    @classmethod
    def from_yaml(cls, path) -> "BaselinePD":
        with Path(path).open() as f:
            cfg = yaml.safe_load(f)["baseline_pd"]
        return cls(cfg)

    def reset(self) -> None:
        self._prev_y = None
        self._prev_psi = None
        self._prev_t = None

    def step(self, state: State, current_t: Optional[float] = None) -> Action:
        y = state.lateral_offset
        psi = state.heading_error
        kappa = state.curvature_ahead

        if self._prev_t is None or current_t is None:
            y_dot = 0.0
            psi_dot = 0.0
        else:
            dt = current_t - self._prev_t
            if dt <= 0.0:
                y_dot = 0.0
                psi_dot = 0.0
            else:
                y_dot = (y - self._prev_y) / dt
                psi_dot = (psi - self._prev_psi) / dt

        steering = (
            -self.kp_y * y
            - self.kd_y * y_dot
            - self.kp_h * psi
            - self.kd_h * psi_dot
        )
        throttle = self.throttle_nominal * max(0.0, 1.0 - self.alpha * abs(kappa))

        self._prev_y = y
        self._prev_psi = psi
        self._prev_t = current_t

        steering_safe = max(-self.steering_limit, min(self.steering_limit, steering))
        throttle_safe = max(self.throttle_min, min(self.throttle_max, throttle))
        return (steering_safe, throttle_safe)
