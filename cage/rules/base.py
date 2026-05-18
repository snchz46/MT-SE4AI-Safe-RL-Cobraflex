"""
Shared types for the cage rules.

These types are imported by every rule under `cage/rules/` and by
`cage_node.py`. Keeping them here avoids duplication and ensures the
six rules share a single contract.

`State` mirrors the ROS2 message `StateObservation.msg` defined in
`docs/.phases/Fase 2/fase_2_detallada.md` §8.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


Action = Tuple[float, float]


@dataclass
class CageDecision:
    fire: bool
    safe_action: Optional[Action] = None
    reason: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class State:
    lateral_offset: float       # m, positive to the left of centreline
    heading_error: float        # rad, positive for leftward error
    speed: float                # m/s, longitudinal
    curvature_ahead: float      # 1/m, estimated ahead
    distance_left: float        # m, distance to left boundary
    distance_right: float       # m, distance to right boundary
    state_valid: bool           # false if any field is unreliable
    timestamp: float            # sim time in seconds (mirrors Header.stamp)
