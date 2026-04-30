"""
C-03 — Predictive lane departure / TTLC.

Implements: SR-003
Mitigates: H-01 (primarily), H-02 (partially)
Type: Predictive

Specification: docs/04_cage_specification.md (section C-03).
Parameters: cage/cage.yaml (key: cage.c03_ttlc).
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class CageDecision:
    fire: bool
    safe_action: Optional[tuple] = None
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class TTLCRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.t_min = params["t_min_s"]
        self.horizon = params["horizon_s"]
        self.urgency_gain_max = params["urgency_gain_max"]

    def compute_ttlc(self, state) -> float:
        """
        Project the current trajectory under zero corrective action.
        Return the time at which |lateral_offset| would equal d_max.
        Return float('inf') if no crossing within horizon.

        PHASE 2 IMPLEMENTATION PENDING.
        """
        return float("inf")

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        # PHASE 2 IMPLEMENTATION PENDING
        return CageDecision(fire=False, reason="stub", metadata={"rule": "C-03"})
