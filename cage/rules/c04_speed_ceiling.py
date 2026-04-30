"""
C-04 — Speed ceiling.

Implements: SR-004
Mitigates: H-03
Type: Reactive (direct safety, parameterised by curvature)

Specification: docs/04_cage_specification.md (section C-04).
Parameters: cage/cage.yaml (key: cage.c04_speed_ceiling).
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class CageDecision:
    fire: bool
    safe_action: Optional[tuple] = None
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class SpeedCeilingRule:
    def __init__(self, params: dict):
        self.enabled = params.get("enabled", True)
        self.v_max_straight = params["v_max_straight_mps"]
        self.v_max_curve = params["v_max_curve_mps"]
        self.curvature_threshold = params["curvature_threshold_inv_m"]
        self.k_kappa = params["k_kappa_mps_per_curvature"]
        self.kappa_window_s = params["curvature_estimation_window_s"]

    def compute_v_max(self, kappa: float) -> float:
        return max(self.v_max_curve, self.v_max_straight - self.k_kappa * abs(kappa))

    def evaluate(self, state: Any, raw_action: tuple, prev_action=None, ctx=None) -> CageDecision:
        # PHASE 2 IMPLEMENTATION PENDING
        return CageDecision(fire=False, reason="stub", metadata={"rule": "C-04"})
