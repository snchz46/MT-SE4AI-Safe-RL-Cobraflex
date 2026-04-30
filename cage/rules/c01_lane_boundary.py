"""
C-01 — Lane boundary hard limit.

Implements: SR-001
Mitigates: H-01
Type: Reactive (direct safety)

Specification: docs/04_cage_specification.md (section C-01).
Parameters: cage/cage.yaml (key: cage.c01_lane_boundary).
Unit tests: cage/tests/test_c01_lane_boundary.py.

Phase status: Phase 2 implementation pending. This file is a stub.
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class CageDecision:
    fire: bool
    safe_action: Optional[tuple] = None
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class LaneBoundaryRule:
    """
    Reactive rule on lateral offset d.

    Logic:
        if abs(d) > (d_max - h_d) and policy_action_increases_abs_d():
            correction = bounded_steering_toward_centre(...)
            fire = True
        elif abs(d) < (d_max - 2*h_d) for last 2 cycles:
            fire = False
    """

    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.d_max = params["d_max_m"]
        self.h_d = params["h_d_m"]
        self.gain = params["correction_gain"]
        self._below_threshold_cycles = 0

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        # PHASE 2 IMPLEMENTATION PENDING
        return CageDecision(fire=False, reason="stub", metadata={"rule": "C-01"})
