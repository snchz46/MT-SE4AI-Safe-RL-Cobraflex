"""
C-01 — Lane boundary hard limit.

Implements: SR-001
Mitigates: H-01
Type: Reactive (direct safety)

Specification: docs/04_cage_specification.md (section C-01).
Parameters: cage/cage.yaml (key: cage.c01_lane_boundary).
Unit tests: cage/tests/test_c01_lane_boundary.py.

Evaluation position: fifth in the sequential chain
(C-06 → C-04 → C-02 → C-03 → C-01 → C-05). C-01 is the final reactive
guard on lateral offset before emergency mode takes over.
"""

import math
from typing import Any

from .base import CageDecision

_CYCLES_TO_DEACTIVATE = 2


class LaneBoundaryRule:
    """
    Reactive rule on lateral offset `d`.

    Hysteresis state machine:
        activate   when |d| > d_max - h_d
        deactivate after |d| < d_max - 2*h_d for `_CYCLES_TO_DEACTIVATE` cycles

    Once active, the rule overrides steering with a proportional correction
    toward the centreline. Throttle is left unchanged.
    """

    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.d_max = params["d_max_m"]
        self.h_d = params["h_d_m"]
        self.gain = params["correction_gain"]
        self.d_activate = self.d_max - self.h_d
        self.d_deactivate = self.d_max - 2.0 * self.h_d
        self._active = False
        self._below_threshold_cycles = 0

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        meta = {"rule": "C-01"}
        if not self.enabled:
            return CageDecision(fire=False, reason="disabled", metadata=meta)

        d = state.lateral_offset
        abs_d = abs(d)
        meta["lateral_offset"] = d

        if abs_d > self.d_activate:
            self._active = True
            self._below_threshold_cycles = 0
        elif abs_d < self.d_deactivate:
            self._below_threshold_cycles += 1
            if self._below_threshold_cycles >= _CYCLES_TO_DEACTIVATE:
                self._active = False
        else:
            self._below_threshold_cycles = 0

        meta["active"] = self._active

        if not self._active:
            return CageDecision(fire=False, reason="within-bounds", metadata=meta)

        steering_raw, throttle_raw = raw_action
        excess = max(0.0, abs_d - self.d_deactivate)
        correction = -math.copysign(self.gain * excess, d)
        steering_safe = max(-1.0, min(1.0, correction))

        meta["correction_raw"] = correction
        meta["steering_raw"] = steering_raw
        meta["steering_applied"] = steering_safe

        return CageDecision(
            fire=True,
            safe_action=(steering_safe, throttle_raw),
            reason="lane-boundary-correction",
            metadata=meta,
        )
