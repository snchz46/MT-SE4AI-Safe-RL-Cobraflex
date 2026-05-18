"""
C-04 — Speed ceiling.

Implements: SR-004
Mitigates: H-03
Type: Reactive (direct safety, parameterised by curvature)

Specification: docs/04_cage_specification.md (section C-04).
Parameters: cage/cage.yaml (key: cage.c04_speed_ceiling).

Evaluation position: second in the sequential chain
(C-06 → C-04 → C-02 → C-03 → C-01 → C-05). Acts on throttle only;
steering is left untouched.
"""

from typing import Any

from .base import CageDecision


class SpeedCeilingRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.v_max_straight = params["v_max_straight_mps"]
        self.v_max_curve = params["v_max_curve_mps"]
        self.curvature_threshold = params["curvature_threshold_inv_m"]
        self.k_kappa = params["k_kappa_mps_per_curvature"]
        self.kappa_window_s = params["curvature_estimation_window_s"]
        self.k_throttle = params["k_throttle_per_mps"]

    def compute_v_max(self, kappa: float) -> float:
        return max(self.v_max_curve, self.v_max_straight - self.k_kappa * abs(kappa))

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        meta = {"rule": "C-04"}
        if not self.enabled:
            return CageDecision(fire=False, reason="disabled", metadata=meta)

        v = state.speed
        kappa = state.curvature_ahead
        v_max = self.compute_v_max(kappa)
        meta["v_observed"] = v
        meta["v_max"] = v_max
        meta["kappa"] = kappa

        if v <= v_max:
            return CageDecision(fire=False, reason="within-ceiling", metadata=meta)

        steering_raw, throttle_raw = raw_action
        excess = v - v_max
        throttle_safe = max(0.0, throttle_raw - self.k_throttle * excess)

        meta["speed_excess_mps"] = excess
        meta["throttle_raw"] = throttle_raw
        meta["throttle_applied"] = throttle_safe

        return CageDecision(
            fire=True,
            safe_action=(steering_raw, throttle_safe),
            reason="speed-exceeds-ceiling",
            metadata=meta,
        )
