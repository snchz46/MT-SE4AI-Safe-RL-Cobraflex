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

Phase status: F2 first-cut. The ROS2 wiring is not yet implemented in this
file (it will live under `cage/ros2/`); for now `SafetyCageNode` is the pure
Python composition of the six rules, callable from tests and from the future
ROS2 wrapper alike.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from cage.rules import (
    Action,
    EmergencyRule,
    HeadingLimitRule,
    LaneBoundaryRule,
    RateLimiterRule,
    SpeedCeilingRule,
    TTLCRule,
)


class SafetyCageNode:
    """
    Compose the six rules in the deterministic evaluation order documented
    in the Phase 2 plan (`docs/.phases/Fase 2/fase_2_detallada.md` §2.1):

        C-06 → C-04 → C-02 → C-03 → C-01 → C-05

    Rationale (plan §5.6): C-06 first sanitises the raw policy action into
    a physically realisable command so the downstream rules operate on a
    feasible baseline. C-05 last because, when emergency mode fires, it
    overrides every upstream correction with the controlled-stop action.

    Operating modes:
        enforcement: corrections are applied to /safe_action.
        monitoring:  corrections are computed and logged but not applied;
                     /safe_action == /raw_action. `_prev_action` tracks the
                     raw stream in this mode so C-06's rate computation
                     reflects what was actually emitted.
    """

    def __init__(self, config_path: str | Path, mode: str = "enforcement"):
        self.config_path = Path(config_path)
        with self.config_path.open() as f:
            cfg = yaml.safe_load(f)["cage"]

        self.mode = mode
        self.cfg = cfg
        self.version = cfg.get("version", "unknown")

        self.c01 = LaneBoundaryRule(cfg["c01_lane_boundary"])
        self.c02 = HeadingLimitRule(cfg["c02_heading_limit"])
        self.c03 = TTLCRule(cfg["c03_ttlc"])
        self.c04 = SpeedCeilingRule(cfg["c04_speed_ceiling"])
        self.c05 = EmergencyRule(cfg["c05_emergency"])
        self.c06 = RateLimiterRule(cfg["c06_rate_limiter"])

        self._chain = (
            ("C-06", self.c06),
            ("C-04", self.c04),
            ("C-02", self.c02),
            ("C-03", self.c03),
            ("C-01", self.c01),
            ("C-05", self.c05),
        )

        self._prev_action: Optional[Action] = None

    @property
    def prev_action(self) -> Optional[Action]:
        return self._prev_action

    def step(self, state, raw_action: Action, ctx: Optional[dict] = None) -> dict:
        """
        Run one control cycle through the rule chain.

        Returns:
            safe_action: (steering, throttle) tuple actually emitted.
            interventions: list of dicts {rule, reason, metadata} for each
                rule that fired this cycle, in evaluation order.
            emergency: True if C-05 was active this cycle.
            raw_action: echoed for the logger.
            mode: "enforcement" or "monitoring".
            cage_version: from cage.yaml.
        """
        ctx = ctx or {}
        interventions = []
        current_action = raw_action
        emergency_active = False

        for rule_id, rule in self._chain:
            decision = rule.evaluate(
                state=state,
                raw_action=current_action,
                prev_action=self._prev_action,
                ctx=ctx,
            )
            if decision.fire:
                interventions.append({
                    "rule": rule_id,
                    "reason": decision.reason,
                    "metadata": decision.metadata,
                })
                if decision.safe_action is not None:
                    current_action = decision.safe_action
                if rule_id == "C-05":
                    emergency_active = True

        if self.mode == "monitoring":
            final_action = raw_action
        else:
            final_action = current_action

        self._prev_action = final_action

        return {
            "safe_action": final_action,
            "raw_action": raw_action,
            "interventions": interventions,
            "emergency": emergency_active,
            "mode": self.mode,
            "cage_version": self.version,
        }

    def reset_emergency(self) -> None:
        """Request clearance of emergency mode.

        The clearance only takes effect on the next `step()` if the
        underlying trigger condition has also cleared (see C-05 contract).
        """
        self.c05.reset()
