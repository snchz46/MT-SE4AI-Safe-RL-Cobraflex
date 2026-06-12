"""
C-06 — Actuator rate limiter.

Implements: SR-006
Mitigates: H-05
Type: Bounded derivative (always evaluated)

Specification: docs/04_cage_specification.md (section C-06).
Parameters: cage/cage.yaml (key: cage.c06_rate_limiter).

Evaluation position: first in the sequential chain
(C-06 → C-04 → C-02 → C-03 → C-01 → C-05). The plan rationale
(`docs/.phases/Fase 2/fase_2_detallada.md` §2.1) is that C-06 sanitises
the policy's raw action into a physically realisable command before any
downstream rule applies its correction, so subsequent rules operate on
a feasible baseline.
"""

import math
from typing import Any

from .base import CageDecision


class RateLimiterRule:
    """Bounded-derivative rule: clips per-cycle steering/throttle deltas (stateless)."""

    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.delta_max_steering = params["delta_max_steering_per_cycle"]
        self.delta_max_throttle = params["delta_max_throttle_per_cycle"]

    def safe_envelope_predicate_holds(
        self, state: Any, action: tuple, prev_action=None
    ) -> bool:
        """SR-010 Part 1: end-of-cycle assertion that the committed
        action does not exceed the per-cycle rate envelope relative to
        the action emitted in the previous cycle. The check skips the
        first cycle (``prev_action is None``) by returning True, matching
        the per-cycle semantics of ``evaluate``."""
        if not self.enabled:
            return True
        if prev_action is None:
            return True
        d_steer = action[0] - prev_action[0]
        d_throttle = action[1] - prev_action[1]
        if abs(d_steer) > self.delta_max_steering + 1e-9:
            return False
        if abs(d_throttle) > self.delta_max_throttle + 1e-9:
            return False
        return True

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        """
        Clip the change in steering and throttle commands between consecutive cycles.

        Contract:
            - `fire=True` iff at least one component was actually clipped.
            - `safe_action` is set only when `fire=True`; otherwise None
              (pass-through convention: the downstream chain uses raw_action).
        """
        meta = {"rule": "C-06"}

        if not self.enabled:
            return CageDecision(fire=False, reason="disabled", metadata=meta)

        if prev_action is None:
            return CageDecision(fire=False, reason="no-prev-action", metadata=meta)

        steering_raw, throttle_raw = raw_action
        steering_prev, throttle_prev = prev_action

        d_steer = steering_raw - steering_prev
        d_throttle = throttle_raw - throttle_prev

        steering_safe = steering_raw
        throttle_safe = throttle_raw
        fired = False

        if abs(d_steer) > self.delta_max_steering:
            steering_safe = steering_prev + math.copysign(self.delta_max_steering, d_steer)
            fired = True

        if abs(d_throttle) > self.delta_max_throttle:
            throttle_safe = throttle_prev + math.copysign(self.delta_max_throttle, d_throttle)
            fired = True

        if not fired:
            return CageDecision(fire=False, reason="within-limits", metadata=meta)

        meta.update({
            "delta_steering_raw": d_steer,
            "delta_throttle_raw": d_throttle,
            "delta_steering_applied": steering_safe - steering_prev,
            "delta_throttle_applied": throttle_safe - throttle_prev,
        })
        return CageDecision(
            fire=True,
            safe_action=(steering_safe, throttle_safe),
            reason="rate-clipped",
            metadata=meta,
        )
