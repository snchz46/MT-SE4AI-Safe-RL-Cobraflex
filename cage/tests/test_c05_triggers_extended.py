"""
Extended unit tests for C-05 covering Triggers 2 (high-energy compound)
and 5 (missing-state via ctx flag). The basic Triggers 1, 3, 4, 6 are
covered in test_c05_emergency.py.
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


def _compound_state(c05_params, speed: float):
    return State(
        lateral_offset=c05_params["d_warning_m"] + 0.01,
        heading_error=c05_params["theta_warning_rad"] + 0.01,
        speed=speed,
        state_valid=True,
    )


def test_high_energy_uses_fast_persistence(rule, c05_params):
    high_speed = c05_params["v_warning_mps"] + 0.05
    state = _compound_state(c05_params, speed=high_speed)
    rule.evaluate(state=state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    # Beyond delta_t_max_fast but BELOW delta_t_max — should fire on the fast path
    t_fast = c05_params["delta_t_max_fast_s"] + 0.01
    assert t_fast < c05_params["delta_t_max_s"]  # sanity check on params
    r = rule.evaluate(state=state, raw_action=(0.0, 0.5), ctx={"current_time": t_fast})
    assert r.fire is True
    assert "compound-high" in r.reason


def test_low_energy_does_not_use_fast_persistence(rule, c05_params):
    low_speed = c05_params["v_warning_mps"] - 0.05
    state = _compound_state(c05_params, speed=low_speed)
    rule.evaluate(state=state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    # Just past fast threshold; low-energy must NOT have fired yet
    t_fast = c05_params["delta_t_max_fast_s"] + 0.01
    r = rule.evaluate(state=state, raw_action=(0.0, 0.5), ctx={"current_time": t_fast})
    assert r.fire is False


def test_low_energy_eventually_fires_at_slow_threshold(rule, c05_params):
    low_speed = c05_params["v_warning_mps"] - 0.05
    state = _compound_state(c05_params, speed=low_speed)
    rule.evaluate(state=state, raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    r = rule.evaluate(
        state=state,
        raw_action=(0.0, 0.5),
        ctx={"current_time": c05_params["delta_t_max_s"] + 0.01},
    )
    assert r.fire is True
    assert "compound-low" in r.reason


def test_missing_state_via_ctx_fires_immediately(rule):
    r = rule.evaluate(
        state=State(state_valid=True),
        raw_action=(0.0, 0.5),
        ctx={"missing_state": True},
    )
    assert r.fire is True
    assert "missing-state" in r.reason


def test_missing_state_false_does_not_fire(rule):
    r = rule.evaluate(
        state=State(state_valid=True),
        raw_action=(0.0, 0.5),
        ctx={"missing_state": False},
    )
    assert r.fire is False
