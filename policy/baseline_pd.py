"""
BaselinePD — pure-Python PD controller for the F2 pipeline validation.

The PD is the baseline policy that exercises the safety cage end-to-end
during Phase 2 (Milestone M1 demo) and reappears in Phase 8 as the
comparison baseline against the trained RL policy. It is deliberately
simple: PD on lateral_offset, PD on heading_error, curve-aware throttle.

Per Phase 2 plan §10.2 plus a curvature feedforward added in v0.4.0:
    steering = kappa_ff · κ_ahead
               -kp_y · y  - kd_y · ẏ
               -kp_h · ψ  - kd_h · ψ̇
    throttle = throttle_nominal · max(0, 1 - alpha · |κ_ahead|)

The feedforward eliminates the steady-state lateral offset that a
proportional-only outer loop otherwise needs to hold a curve, which
in turn removes the high-gain operating point where any small
perturbation (segment-boundary jitter, wheel slip) saturates the
steering and triggers a C-05 latch.

Lateral and heading rates are finite-differenced from the previous
state observation. `reset()` clears the history, e.g. on lap reset.

The ROS2 node that wires this controller to /state_obs and /raw_action
will live under `src/cobraflex` (Phase 2 D31); this file is the pure-
Python logic so the controller can be unit-tested without ROS2.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import yaml

from cage.rules import Action, State


def _wrap_angle(angle: float) -> float:
    """Wrap to (-pi, pi]. Used to compute the shortest-arc heading delta
    when finite-differencing psi across the ±pi seam."""
    return math.atan2(math.sin(angle), math.cos(angle))


class BaselinePD:
    def __init__(self, params: dict):
        self.kp_y = params["kp_y"]
        self.kd_y = params["kd_y"]
        self.kp_h = params["kp_h"]
        self.kd_h = params["kd_h"]
        self.kappa_ff = params.get("kappa_to_steering_gain", 0.0)
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
                # Shortest-arc heading delta. A raw subtraction across the
                # ±pi seam (e.g. prev = +3.10, now = -3.10) yields ~6.2 rad
                # instead of the true ~0.08 rad delta, which at dt=0.05 s
                # becomes a 120 rad/s spurious derivative that saturates
                # steering and triggers C-05. Latent while kd_h == 0; this
                # guard makes reactivating kd_h safe.
                psi_dot = _wrap_angle(psi - self._prev_psi) / dt

        # Throttle and feedforward share the same speed-reduction factor so
        # the curvature feedforward stays consistent when vehicle_control_node
        # scales the cruise speed by the safe throttle (use_safe_throttle=True).
        # Without this, kappa_ff (calibrated at v_nominal=0.2 m/s) is ~3×
        # too large at the curve entry speed (0.07 m/s), causing oversteer
        # that builds up ey/epsi until C-05 latches.
        ff_scale = max(0.0, 1.0 - self.alpha * abs(kappa))
        steering = (
            self.kappa_ff * kappa * ff_scale
            - self.kp_y * y
            - self.kd_y * y_dot
            - self.kp_h * psi
            - self.kd_h * psi_dot
        )
        throttle = self.throttle_nominal * ff_scale

        self._prev_y = y
        self._prev_psi = psi
        self._prev_t = current_t

        steering_safe = max(-self.steering_limit, min(self.steering_limit, steering))
        throttle_safe = max(self.throttle_min, min(self.throttle_max, throttle))
        return (steering_safe, throttle_safe)

