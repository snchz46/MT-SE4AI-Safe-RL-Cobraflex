"""
C-03 — Predictive lane departure / TTLC.

Implements: SR-003
Mitigates: H-01 (primarily), H-02 (partially)
Type: Predictive

Specification: docs/04_cage_specification.md (section C-03).
Parameters: cage/cage.yaml (key: cage.c03_ttlc).

Evaluation position: fourth in the sequential chain
(C-06 → C-04 → C-02 → C-03 → C-01 → C-05). Acts as predictive guard
before the reactive C-01 fires; together they implement defence in
depth on H-01.
"""

import math
from typing import Any

from .base import CageDecision


class TTLCRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.t_min = params["t_min_s"]
        self.horizon = params["horizon_s"]
        self.urgency_gain_max = params["urgency_gain_max"]
        self.d_max = params["d_max_m"]
        self.v_min_estimate = params["v_min_estimate_mps"]

    def compute_ttlc(self, state) -> float:
        """
        Time at which the heading-constant projection of |lateral_offset|
        would equal d_max. Returns inf when there is no crossing within
        the configured horizon or when speed is below the kinematic floor.
        """
        d = state.lateral_offset
        psi = state.heading_error
        v = state.speed
        if abs(v) < self.v_min_estimate:
            return float("inf")
        v_lat = v * math.sin(psi)
        if abs(v_lat) < 1e-9:
            return float("inf")
        if v_lat > 0:
            ttlc = (self.d_max - d) / v_lat
        else:
            ttlc = (-self.d_max - d) / v_lat
        if ttlc < 0 or ttlc > self.horizon:
            return float("inf")
        return ttlc

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        meta = {"rule": "C-03"}
        if not self.enabled:
            return CageDecision(fire=False, reason="disabled", metadata=meta)

        ttlc = self.compute_ttlc(state)
        meta["ttlc_s"] = ttlc

        if ttlc >= self.t_min:
            return CageDecision(fire=False, reason="ttlc-safe", metadata=meta)

        ttlc_clamped = max(0.0, ttlc)
        urgency = self.urgency_gain_max * (1.0 - ttlc_clamped / self.t_min)
        meta["urgency"] = urgency

        d = state.lateral_offset
        if abs(d) > 1e-9:
            correction = -math.copysign(urgency, d)
        elif abs(state.heading_error) > 1e-9:
            correction = -math.copysign(urgency, state.heading_error)
        else:
            correction = 0.0

        steering_raw, throttle_raw = raw_action
        steering_safe = max(-1.0, min(1.0, correction))

        meta["correction_raw"] = correction
        meta["steering_raw"] = steering_raw
        meta["steering_applied"] = steering_safe

        return CageDecision(
            fire=True,
            safe_action=(steering_safe, throttle_raw),
            reason="ttlc-predictive",
            metadata=meta,
        )
