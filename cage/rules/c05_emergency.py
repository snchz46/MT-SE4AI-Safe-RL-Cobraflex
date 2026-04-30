"""
C-05 — Emergency mode.

Implements: SR-005, SR-007, SR-008
Mitigates: H-04, H-06, H-07
Type: Trigger-based (procedural safety)

Specification: docs/04_cage_specification.md (section C-05).
Parameters: cage/cage.yaml (key: cage.c05_emergency).

This rule has the highest priority in the evaluation order: if it activates,
all subsequent rules are short-circuited for the current cycle.
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class CageDecision:
    fire: bool
    safe_action: Optional[tuple] = None
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class EmergencyRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        # Compound-state trigger
        self.theta_warning = params["theta_warning_rad"]
        self.d_warning = params["d_warning_m"]
        self.delta_t_max = params["delta_t_max_s"]
        # Emergency response
        self.a_min = params["a_min_mps2"]
        self.freeze_steering = params["freeze_steering"]
        # Reset policy
        self.require_explicit_reset = params["require_explicit_reset"]
        # Internal state
        self._compound_state_start_t: Optional[float] = None
        self._active = False
        self._steering_at_activation: Optional[float] = None

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        # PHASE 2 IMPLEMENTATION PENDING
        # Triggers to implement:
        # 1. Compound state (theta + d sustained for delta_t_max)
        # 2. Stale state observation
        # 3. Invalid state field
        # 4. Missing state for N consecutive cycles
        # 5. External stop signal (from ctx)
        return CageDecision(fire=False, reason="stub", metadata={"rule": "C-05"})

    def reset(self) -> None:
        """Explicit reset; clears active flag if conditions have cleared."""
        self._active = False
        self._compound_state_start_t = None
        self._steering_at_activation = None
