"""
C-02 — Heading error limit.

Implements: SR-002
Mitigates: H-02
Type: Reactive (direct safety)

Specification: docs/04_cage_specification.md (section C-02).
Parameters: cage/cage.yaml (key: cage.c02_heading_limit).
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class CageDecision:
    fire: bool
    safe_action: Optional[tuple] = None
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class HeadingLimitRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.theta_max = params["theta_max_rad"]
        self.h_theta = params["h_theta_rad"]
        self.gain = params["correction_gain"]
        self._below_threshold_cycles = 0

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        # PHASE 2 IMPLEMENTATION PENDING
        return CageDecision(fire=False, reason="stub", metadata={"rule": "C-02"})
