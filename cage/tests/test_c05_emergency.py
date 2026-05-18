"""
Unit tests for C-05 — Emergency mode.

Coverage:
    - no trigger: no fire, no active
    - compound trigger requires persistence (delta_t_max)
    - compound trigger fires after persistence
    - invalid state fires immediately
    - external stop via ctx fires immediately
    - stale state fires when ctx provides current_time
    - active emergency persists with require_explicit_reset=True until reset
    - reset alone is not enough — trigger must also have cleared
    - reset + cleared trigger → exit
    - steering frozen at activation value when freeze_steering=True
    - emergency throttle is negative (brake)
    - disabled rule: no fire
"""

from pathlib import Path

import pytest
import yaml

from cage.rules import EmergencyRule, State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def c05_params():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]["c05_emergency"]


@pytest.fixture
def rule(c05_params):
    return EmergencyRule(c05_params)


def _compound_state(c05_params):
    return State(
        lateral_offset=c05_params["d_warning_m"] + 0.01,
        heading_error=c05_params["theta_warning_rad"] + 0.01,
        state_valid=True,
    )


def test_no_trigger_no_fire(rule):
    result = rule.evaluate(state=State(), raw_action=(0.0, 0.5))
    assert result.fire is False
    assert result.metadata["active"] is False


def test_compound_trigger_requires_persistence(rule, c05_params):
    state = _compound_state(c05_params)
    # First detection at t=0: starts the persistence timer, does not fire
    r0 = rule.evaluate(state=state, raw_action=(0.1, 0.5), ctx={"current_time": 0.0})
    assert r0.fire is False
    # Within delta_t_max: still no fire
    t_short = c05_params["delta_t_max_s"] / 2.0
    r1 = rule.evaluate(state=state, raw_action=(0.1, 0.5), ctx={"current_time": t_short})
    assert r1.fire is False


def test_compound_trigger_fires_after_persistence(rule, c05_params):
    state = _compound_state(c05_params)
    rule.evaluate(state=state, raw_action=(0.1, 0.5), ctx={"current_time": 0.0})
    t_after = c05_params["delta_t_max_s"] + 0.01
    r = rule.evaluate(state=state, raw_action=(0.1, 0.5), ctx={"current_time": t_after})
    assert r.fire is True
    assert "compound" in r.reason


def test_compound_trigger_resets_when_state_clears(rule, c05_params):
    state_bad = _compound_state(c05_params)
    state_ok = State()
    rule.evaluate(state=state_bad, raw_action=(0.1, 0.5), ctx={"current_time": 0.0})
    # State clears before persistence elapses
    rule.evaluate(state=state_ok, raw_action=(0.0, 0.5), ctx={"current_time": 0.05})
    # Re-introducing the compound state must restart the timer, not fire immediately
    rule.evaluate(state=state_bad, raw_action=(0.0, 0.5), ctx={"current_time": 0.10})
    r = rule.evaluate(
        state=state_bad,
        raw_action=(0.0, 0.5),
        ctx={"current_time": 0.10 + c05_params["delta_t_max_s"] / 2.0},
    )
    assert r.fire is False


def test_invalid_state_fires_immediately(rule):
    state = State(state_valid=False)
    r = rule.evaluate(state=state, raw_action=(0.0, 0.5))
    assert r.fire is True
    assert "invalid-state" in r.reason


def test_external_stop_fires_immediately(rule):
    r = rule.evaluate(state=State(), raw_action=(0.0, 0.5), ctx={"external_stop": True})
    assert r.fire is True
    assert "external-stop" in r.reason


def test_stale_state_fires_when_current_time_provided(rule, c05_params):
    state = State(timestamp=1.0)
    current = 1.0 + c05_params.get("staleness_max_s", 0.2) + 0.5
    r = rule.evaluate(state=state, raw_action=(0.0, 0.5), ctx={"current_time": current})
    assert r.fire is True
    assert "stale" in r.reason


def test_active_persists_until_reset(rule):
    # Trigger via invalid state
    rule.evaluate(state=State(state_valid=False), raw_action=(0.2, 0.5))
    # Even with valid state, must stay active until reset
    r = rule.evaluate(state=State(state_valid=True), raw_action=(0.0, 0.5))
    assert r.fire is True
    assert "active-persists" in r.reason


def test_reset_alone_does_not_clear_if_trigger_persists(rule):
    rule.evaluate(state=State(state_valid=False), raw_action=(0.2, 0.5))
    r = rule.evaluate(
        state=State(state_valid=False),  # still invalid
        raw_action=(0.0, 0.5),
        ctx={"reset": True},
    )
    assert r.fire is True


def test_reset_plus_cleared_trigger_exits(rule):
    rule.evaluate(state=State(state_valid=False), raw_action=(0.2, 0.5))
    r = rule.evaluate(
        state=State(state_valid=True),
        raw_action=(0.0, 0.5),
        ctx={"reset": True},
    )
    assert r.fire is False
    assert "cleared" in r.reason


def test_steering_frozen_at_activation_value(rule):
    raw_steering_at_trigger = 0.42
    rule.evaluate(state=State(state_valid=False), raw_action=(raw_steering_at_trigger, 0.5))
    r = rule.evaluate(state=State(state_valid=False), raw_action=(0.0, 0.5))
    steering_safe, _ = r.safe_action
    assert steering_safe == pytest.approx(raw_steering_at_trigger)


def test_emergency_throttle_is_brake(rule):
    rule.evaluate(state=State(state_valid=False), raw_action=(0.0, 0.8))
    r = rule.evaluate(state=State(state_valid=False), raw_action=(0.0, 0.8))
    _, throttle_safe = r.safe_action
    assert throttle_safe < 0.0


def test_disabled_rule_passes_through(c05_params):
    params = dict(c05_params)
    params["enabled"] = False
    rule = EmergencyRule(params)
    r = rule.evaluate(state=State(state_valid=False), raw_action=(0.0, 0.5))
    assert r.fire is False
    assert r.safe_action is None
