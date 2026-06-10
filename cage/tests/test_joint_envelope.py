"""SR-010 Part 1 — joint-envelope assertion and C-05 Trigger 7.

Each rule exposes ``safe_envelope_predicate_holds(state, action, prev_action)``
which captures the rule's end-of-cycle invariant. After the cage chain runs,
``SafetyCageNode.step`` evaluates the conjunction of the six predicates on
the post-chain action and, if any rule's predicate is False, fires C-05
Trigger 7 and overrides the safe action with a controlled stop.

These tests cover:
    (a) the per-rule predicates in isolation, against synthetic states;
    (b) the cage-level integration: trigger 7 firing, emergency flag, action
        override, intervention metadata;
    (c) a regression that the predicates do not interfere with the
        nominal-driving path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cage.cage_node import SafetyCageNode, _NEUTRAL_SAFE_STOP
from cage.rules import State
from cage.rules.c01_lane_boundary import LaneBoundaryRule
from cage.rules.c02_heading_limit import HeadingLimitRule
from cage.rules.c03_ttlc import TTLCRule
from cage.rules.c04_speed_ceiling import SpeedCeilingRule
from cage.rules.c05_emergency import EmergencyRule
from cage.rules.c06_rate_limiter import RateLimiterRule

REPO_ROOT = Path(__file__).resolve().parents[2]
CAGE_YAML = REPO_ROOT / "cage" / "cage.yaml"


def _nominal_state(**overrides) -> State:
    defaults = dict(
        lateral_offset=0.0,
        heading_error=0.0,
        speed=0.2,
        curvature_ahead=0.0,
        distance_left=0.13,
        distance_right=0.13,
        state_valid=True,
        timestamp=0.0,
    )
    defaults.update(overrides)
    return State(**defaults)


# --------------------------------------------------------------------------
# (a) Per-rule predicates
# --------------------------------------------------------------------------


def test_c01_predicate_holds_inside_band():
    rule = LaneBoundaryRule({
        "enabled": True, "d_max_m": 0.16, "h_d_m": 0.02, "correction_gain": 1.5,
    })
    assert rule.safe_envelope_predicate_holds(_nominal_state(lateral_offset=0.10), (0.0, 0.5))


def test_c01_predicate_fails_beyond_d_max():
    rule = LaneBoundaryRule({
        "enabled": True, "d_max_m": 0.16, "h_d_m": 0.02, "correction_gain": 1.5,
    })
    assert not rule.safe_envelope_predicate_holds(
        _nominal_state(lateral_offset=0.20), (0.0, 0.5)
    )


def test_c02_predicate_fails_beyond_theta_max():
    rule = HeadingLimitRule({
        "enabled": True, "theta_max_rad": 0.4363, "h_theta_rad": 0.0349, "correction_gain": 1.0,
    })
    assert rule.safe_envelope_predicate_holds(_nominal_state(heading_error=0.20), (0, 0))
    assert not rule.safe_envelope_predicate_holds(_nominal_state(heading_error=0.50), (0, 0))


def test_c03_predicate_deferred():
    """SR-010 Part 1 for C-03 is deferred: the predicate always returns True so
    C-03 never contributes to joint_envelope_violated. C-03's reactive
    correction in evaluate() still handles TTLC violations in-chain."""
    rule = TTLCRule({
        "enabled": True, "t_min_s": 1.0, "horizon_s": 3.0,
        "urgency_gain_max": 2.0, "d_max_m": 0.16, "v_min_estimate_mps": 0.05,
    })
    # Always returns True regardless of TTLC.
    assert rule.safe_envelope_predicate_holds(_nominal_state(speed=0.4, heading_error=0.0), (0, 0))
    assert rule.safe_envelope_predicate_holds(
        _nominal_state(lateral_offset=0.10, heading_error=0.5, speed=0.4), (0, 0)
    )


def test_c04_predicate_uses_curvature_aware_ceiling():
    rule = SpeedCeilingRule({
        "enabled": True,
        "v_max_straight_mps": 0.5,
        "v_max_curve_mps": 0.25,
        "curvature_threshold_inv_m": 0.05,
        "k_kappa_mps_per_curvature": 0.3,
        "curvature_estimation_window_s": 0.5,
        "k_throttle_per_mps": 5.0,
    })
    # Below straight cap.
    assert rule.safe_envelope_predicate_holds(_nominal_state(speed=0.4), (0, 0.5))
    # Above straight cap.
    assert not rule.safe_envelope_predicate_holds(_nominal_state(speed=0.6), (0, 0.5))
    # Above curve-attenuated cap.
    assert not rule.safe_envelope_predicate_holds(
        _nominal_state(speed=0.4, curvature_ahead=1.0), (0, 0.5)
    )


def test_c05_predicate_always_holds():
    rule = EmergencyRule({
        "enabled": True,
        "theta_warning_rad": 0.3491,
        "d_warning_m": 0.12,
        "delta_t_max_s": 0.2,
        "v_warning_mps": 0.4,
        "delta_t_max_fast_s": 0.1,
        "a_min_mps2": 0.3,
        "freeze_steering": True,
        "require_explicit_reset": True,
    })
    # C-05 is the responder, not a constraint; predicate always True.
    assert rule.safe_envelope_predicate_holds(_nominal_state(), (0, 0))
    assert rule.safe_envelope_predicate_holds(_nominal_state(lateral_offset=0.5), (0, 0))


def test_c06_predicate_skips_when_no_prev_action():
    rule = RateLimiterRule({
        "enabled": True,
        "delta_max_steering_per_cycle": 0.15,
        "delta_max_throttle_per_cycle": 0.10,
    })
    # First cycle has no previous action; predicate must hold (cannot judge).
    assert rule.safe_envelope_predicate_holds(_nominal_state(), (1.0, 1.0), prev_action=None)


def test_c06_predicate_fails_when_delta_too_large():
    rule = RateLimiterRule({
        "enabled": True,
        "delta_max_steering_per_cycle": 0.15,
        "delta_max_throttle_per_cycle": 0.10,
    })
    # Steering jump of 0.5 from 0.0 -> way over delta_max=0.15.
    assert not rule.safe_envelope_predicate_holds(
        _nominal_state(), (0.5, 0.5), prev_action=(0.0, 0.5)
    )
    # Throttle jump of 0.5 from 0.0 -> over delta_max_throttle=0.10.
    assert not rule.safe_envelope_predicate_holds(
        _nominal_state(), (0.0, 0.5), prev_action=(0.0, 0.0)
    )


# --------------------------------------------------------------------------
# (b) Cage-level Trigger 7 integration
# --------------------------------------------------------------------------


def test_nominal_state_does_not_fire_trigger_7():
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    state = _nominal_state(speed=0.2)
    result = node.step(state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    assert result["joint_envelope_violated"] is False
    assert all(result["joint_envelope_predicates"].values())
    # No emergency from Trigger 7 in nominal driving.
    trigger_7s = [iv for iv in result["interventions"]
                  if iv.get("rule") == "C-05"
                  and iv.get("metadata", {}).get("trigger") == 7]
    assert trigger_7s == []


def test_lateral_offset_beyond_d_max_fires_trigger_7():
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    state = _nominal_state(lateral_offset=0.25, speed=0.2)  # d_max=0.16
    result = node.step(state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    assert result["joint_envelope_violated"] is True
    assert "C-01" in result["joint_envelope_predicates"]
    assert result["joint_envelope_predicates"]["C-01"] is False
    # Trigger 7 routes through C-05's state machine; the C-05 intervention
    # carries trigger=7 in its metadata and lists the failing rules.
    trigger_7s = [iv for iv in result["interventions"]
                  if iv.get("rule") == "C-05"
                  and iv.get("metadata", {}).get("trigger") == 7]
    assert len(trigger_7s) == 1
    assert "C-01" in trigger_7s[0]["metadata"]["failing_rules"]
    assert result["emergency"] is True
    # Safe action is the C-05 emergency action (freeze steering + brake).
    assert result["safe_action"][1] == -0.5


def test_excess_speed_fires_trigger_7():
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    state = _nominal_state(speed=1.0, curvature_ahead=0.0)  # > 0.5 straight cap
    result = node.step(state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    assert result["joint_envelope_violated"] is True
    assert "C-04" in [
        rid for rid, ok in result["joint_envelope_predicates"].items() if not ok
    ]


def test_monitoring_mode_logs_violation_but_does_not_override():
    node = SafetyCageNode(CAGE_YAML, mode="monitoring")
    state = _nominal_state(lateral_offset=0.25, speed=0.2)
    raw = (0.3, 0.5)
    result = node.step(state, raw_action=raw, ctx={"current_time": 0.0})
    assert result["joint_envelope_violated"] is True
    # In monitoring mode the action is NOT overridden; safe == raw.
    assert result["safe_action"] == raw
    # But the intervention is still logged.
    trigger_7s = [iv for iv in result["interventions"]
                  if iv.get("rule") == "C-05"
                  and iv.get("metadata", {}).get("trigger") == 7]
    assert len(trigger_7s) == 1


def test_multiple_failing_predicates_listed_in_metadata():
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    state = _nominal_state(
        lateral_offset=0.25,            # fails C-01
        heading_error=0.6,              # fails C-02
        speed=1.0,                      # fails C-04 straight cap
        curvature_ahead=0.0,
    )
    result = node.step(state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    failing = next(
        iv["metadata"]["failing_rules"] for iv in result["interventions"]
        if iv.get("rule") == "C-05"
        and iv.get("metadata", {}).get("trigger") == 7
    )
    assert {"C-01", "C-02", "C-04"}.issubset(set(failing))


def test_trigger_7_latches_across_cycles():
    """Once Trigger 7 fires, C-05 must stay active across subsequent cycles
    even if the joint envelope predicate transiently recovers, until an
    explicit /cage_reset is delivered. This prevents the emergency-toggle
    judder we observed in the first Gazebo run."""
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    # Cycle 1: state out of envelope -> Trigger 7 fires, C-05 latches active.
    out_state = _nominal_state(lateral_offset=0.25, speed=0.2, timestamp=0.0)
    r1 = node.step(out_state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    assert r1["emergency"] is True
    # Cycle 2: state recovered (|d| < d_max) but C-05 must remain active
    # because require_explicit_reset is True in cage.yaml.
    in_state = _nominal_state(lateral_offset=0.05, speed=0.2, timestamp=0.05)
    r2 = node.step(in_state, raw_action=(0.0, 0.5), ctx={"current_time": 0.05})
    assert r2["emergency"] is True, (
        "C-05 should latch via require_explicit_reset, not clear on recovery"
    )
    # Cycle 3: send reset AND state still inside -> C-05 clears.
    r3 = node.step(in_state, raw_action=(0.0, 0.5), ctx={"current_time": 0.10, "reset": True})
    assert r3["emergency"] is False
