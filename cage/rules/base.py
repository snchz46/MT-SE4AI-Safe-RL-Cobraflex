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
    # Defaults keep test fixtures and partial-state construction ergonomic;
    # production code instantiates with all fields populated by Perception.
    lateral_offset: float = 0.0     # m, positive to the left of centreline
    heading_error: float = 0.0      # rad, positive for leftward error
    speed: float = 0.0              # m/s, longitudinal
    curvature_ahead: float = 0.0    # 1/m, estimated ahead
    distance_left: float = 0.0      # m, distance to left boundary
    distance_right: float = 0.0     # m, distance to right boundary
    state_valid: bool = True        # false if any field is unreliable
    timestamp: float = 0.0          # sim time in seconds (mirrors Header.stamp)
