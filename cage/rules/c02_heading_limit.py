"""
C-02 — Heading error limit.

Implements: SR-002
Mitigates: H-02
Type: Reactive (direct safety)

Specification: docs/04_cage_specification.md (section C-02).
Parameters: cage/cage.yaml (key: cage.c02_heading_limit).

Evaluation position: third in the sequential chain
(C-06 → C-04 → C-02 → C-03 → C-01 → C-05). Same hysteresis pattern as
C-01 but on heading error.
"""

from typing import Any

from .base import CageDecision

_CYCLES_TO_DEACTIVATE = 2


class HeadingLimitRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.theta_max = params["theta_max_rad"]
        self.h_theta = params["h_theta_rad"]
        self.gain = params["correction_gain"]
        self.theta_activate = self.theta_max - self.h_theta
        self.theta_deactivate = self.theta_max - 2.0 * self.h_theta
        self._active = False
        self._below_threshold_cycles = 0

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        meta = {"rule": "C-02"}
        if not self.enabled:
            return CageDecision(fire=False, reason="disabled", metadata=meta)

        theta = state.heading_error
        abs_theta = abs(theta)
        meta["heading_error"] = theta

        if abs_theta > self.theta_activate:
            self._active = True
            self._below_threshold_cycles = 0
        elif abs_theta < self.theta_deactivate:
            self._below_threshold_cycles += 1
            if self._below_threshold_cycles >= _CYCLES_TO_DEACTIVATE:
                self._active = False
        else:
            self._below_threshold_cycles = 0

        meta["active"] = self._active

        if not self._active:
            return CageDecision(fire=False, reason="within-bounds", metadata=meta)

        steering_raw, throttle_raw = raw_action
        correction = -self.gain * theta
        steering_safe = max(-1.0, min(1.0, correction))

        meta["correction_raw"] = correction
        meta["steering_raw"] = steering_raw
        meta["steering_applied"] = steering_safe

        return CageDecision(
            fire=True,
            safe_action=(steering_safe, throttle_raw),
            reason="heading-limit-correction",
            metadata=meta,
        )
