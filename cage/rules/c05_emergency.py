"""
C-05 — Emergency mode.

Implements: SR-005, SR-007 (partial), SR-008 (partial)
Mitigates: H-04, H-06, H-07
Type: Trigger-based (procedural safety)

Specification: docs/04_cage_specification.md (section C-05).
Parameters: cage/cage.yaml (key: cage.c05_emergency).

Evaluation position: last in the sequential chain
(C-06 → C-04 → C-02 → C-03 → C-01 → C-05). When C-05 fires it overrides
every upstream correction with the controlled-stop action.

Triggers implemented in this F2 first cut:
    1. Compound state (|theta| > theta_warning AND |d| > d_warning,
       sustained for delta_t_max)
    3. Invalid state field (state.state_valid is False)
    4. Stale state (current_time - state.timestamp > staleness_max,
       only when current_time is provided via ctx)
    5. External stop (ctx["external_stop"] is truthy)

Not yet implemented (deferred): missing-state counter (Trigger 5 in spec,
needs cage_node-level counter), high-energy compound trigger, joint-
envelope assertion (SR-010 wiring).

Exit: only via explicit reset (`reset()` method or ctx["reset"]=True)
combined with the trigger condition having cleared. This implements the
asymmetric exit policy with `require_explicit_reset=True` in cage.yaml.
"""

from typing import Any, Optional

from .base import CageDecision

_EMERGENCY_BRAKE_THROTTLE = -0.5  # placeholder until M-3 calibrates a_min → throttle map


class EmergencyRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.theta_warning = params["theta_warning_rad"]
        self.d_warning = params["d_warning_m"]
        self.delta_t_max = params["delta_t_max_s"]
        self.a_min = params["a_min_mps2"]
        self.freeze_steering = params["freeze_steering"]
        self.require_explicit_reset = params["require_explicit_reset"]
        self.staleness_max = params.get("staleness_max_s", 0.2)
        # Internal state
        self._compound_state_start_t: Optional[float] = None
        self._active = False
        self._steering_at_activation: Optional[float] = None
        self._reset_requested = False

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        meta = {"rule": "C-05"}
        if not self.enabled:
            return CageDecision(fire=False, reason="disabled", metadata=meta)

        ctx = ctx or {}
        current_t = ctx.get("current_time")
        external_stop = bool(ctx.get("external_stop", False))
        if ctx.get("reset", False):
            self._reset_requested = True

        triggers = self._evaluate_triggers(state, current_t, external_stop)
        meta["triggers"] = triggers

        if self._active:
            cleared = not triggers["any"]
            can_exit = cleared and (self._reset_requested or not self.require_explicit_reset)
            if can_exit:
                self._active = False
                self._compound_state_start_t = None
                self._steering_at_activation = None
                self._reset_requested = False
                meta["active"] = False
                return CageDecision(fire=False, reason="emergency-cleared", metadata=meta)
            return self._emergency_action(meta, "active-persists")

        if triggers["compound"]:
            if current_t is None:
                self._activate(raw_action)
                return self._emergency_action(meta, "triggered-compound-no-time")
            if self._compound_state_start_t is None:
                self._compound_state_start_t = current_t
            elif (current_t - self._compound_state_start_t) >= self.delta_t_max:
                self._activate(raw_action)
                return self._emergency_action(meta, "triggered-compound")
        else:
            self._compound_state_start_t = None

        if triggers["invalid"]:
            self._activate(raw_action)
            return self._emergency_action(meta, "triggered-invalid-state")
        if triggers["stale"]:
            self._activate(raw_action)
            return self._emergency_action(meta, "triggered-stale-state")
        if triggers["external"]:
            self._activate(raw_action)
            return self._emergency_action(meta, "triggered-external-stop")

        meta["active"] = False
        return CageDecision(fire=False, reason="no-trigger", metadata=meta)

    def _evaluate_triggers(self, state, current_t, external_stop) -> dict:
        abs_theta = abs(state.heading_error)
        abs_d = abs(state.lateral_offset)
        compound = abs_theta > self.theta_warning and abs_d > self.d_warning
        invalid = not state.state_valid
        if current_t is not None and state.timestamp > 0:
            stale = (current_t - state.timestamp) > self.staleness_max
        else:
            stale = False
        return {
            "compound": compound,
            "invalid": invalid,
            "stale": stale,
            "external": external_stop,
            "any": compound or invalid or stale or external_stop,
        }

    def _activate(self, raw_action) -> None:
        self._active = True
        self._steering_at_activation = raw_action[0]
        self._reset_requested = False

    def _emergency_action(self, meta: dict, reason: str) -> CageDecision:
        if self.freeze_steering and self._steering_at_activation is not None:
            steering_safe = self._steering_at_activation
        else:
            steering_safe = 0.0
        throttle_safe = _EMERGENCY_BRAKE_THROTTLE
        meta["active"] = True
        meta["steering_frozen"] = self._steering_at_activation
        meta["throttle_applied"] = throttle_safe
        return CageDecision(
            fire=True,
            safe_action=(steering_safe, throttle_safe),
            reason=reason,
            metadata=meta,
        )

    def reset(self) -> None:
        """Imperative reset entry (e.g., wired to /cage_reset topic).

        Sets the request flag; the actual clearance happens in the next
        evaluate() call iff the trigger condition has also cleared.
        """
        self._reset_requested = True
