"""
Safety cage rules.

Each rule is implemented as a separate module and exposes:
    - a class with .evaluate(state, raw_action, prev_action, ctx) method
    - returns CageDecision(fire: bool, safe_action, reason: str, metadata: dict)

The cage_node imports them in deterministic order and chains their evaluation
according to the protocol defined in docs/04_cage_specification.md.
"""

from .c01_lane_boundary import LaneBoundaryRule
from .c02_heading_limit import HeadingLimitRule
from .c03_ttlc import TTLCRule
from .c04_speed_ceiling import SpeedCeilingRule
from .c05_emergency import EmergencyRule
from .c06_rate_limiter import RateLimiterRule

__all__ = [
    "LaneBoundaryRule",
    "HeadingLimitRule",
    "TTLCRule",
    "SpeedCeilingRule",
    "EmergencyRule",
    "RateLimiterRule",
]
