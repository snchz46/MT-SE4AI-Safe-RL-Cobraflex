"""
cage_node.py
------------
ROS2 node implementing the safety cage.

Subscribes to:
    /raw_action     (from policy node)
    /state_obs      (from perception node)
    /external_stop  (external trigger)
    /cage_reset     (to clear emergency mode)

Publishes:
    /safe_action    (corrected or substituted command)
    /cage_status    (per-cycle log entry)
    /emergency      (signal when emergency mode active)

Configuration: cage/cage.yaml (loaded at launch).

Phase status: Phase 2 implementation pending. This is a structural stub.
"""

from __future__ import annotations

from pathlib import Path
import yaml

from cage.rules import (
    LaneBoundaryRule,
    HeadingLimitRule,
    TTLCRule,
    SpeedCeilingRule,
    EmergencyRule,
    RateLimiterRule,
)


class SafetyCageNode:
    """
    The cage node combines six rules in a deterministic evaluation order:

        1. C-05 (emergency) first; if activated, short-circuit the rest.
        2. C-01 + C-02 in parallel on steering.
        3. C-03 may further bias steering; worst-case envelope with C-01/C-02.
        4. C-04 on throttle.
        5. C-06 (rate limiter) last, on the final command.

    Operating modes:
        enforcement: corrections are applied to /safe_action.
        monitoring:  corrections are computed and logged but not applied;
                     /safe_action == /raw_action.
    """

    def __init__(self, config_path: str | Path, mode: str = "enforcement"):
        self.config_path = Path(config_path)
        with self.config_path.open() as f:
            cfg = yaml.safe_load(f)["cage"]

        self.mode = mode
        self.cfg = cfg
        self.version = cfg.get("version", "unknown")

        # Instantiate the six rules
        self.c01 = LaneBoundaryRule(cfg["c01_lane_boundary"])
        self.c02 = HeadingLimitRule(cfg["c02_heading_limit"])
        self.c03 = TTLCRule(cfg["c03_ttlc"])
        self.c04 = SpeedCeilingRule(cfg["c04_speed_ceiling"])
        self.c05 = EmergencyRule(cfg["c05_emergency"])
        self.c06 = RateLimiterRule(cfg["c06_rate_limiter"])

        self._prev_action = None  # for rate limiter

    def step(self, state, raw_action, ctx=None) -> dict:
        """
        Execute one control cycle.

        Returns a dict with:
            safe_action: (steering, throttle) tuple to publish.
            interventions: list of CageDecision objects from rules that fired.
            emergency: bool, whether emergency mode active.
            mode: "enforcement" or "monitoring".
        """
        # PHASE 2 IMPLEMENTATION PENDING.
        # This stub passes through raw_action without modification.
        return {
            "safe_action": raw_action,
            "interventions": [],
            "emergency": False,
            "mode": self.mode,
            "cage_version": self.version,
        }

    def reset_emergency(self) -> None:
        """Clear the emergency mode flag (only if conditions cleared)."""
        self.c05.reset()
