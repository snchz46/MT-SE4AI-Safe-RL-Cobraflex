"""
Unit tests for C-01 — Lane boundary hard limit.

Coverage:
    - within bounds: no fire
    - exceed activation threshold: fire, correction toward centre
    - sign of correction (positive offset → negative steering and vice versa)
    - hysteresis: stays active in band until N cycles below d_deactivate
    - saturation: correction clipped to [-1, 1]
    - disabled rule: no fire
"""

from pathlib import Path

import pytest
import yaml

from cage.rules import LaneBoundaryRule, State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def c01_params():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]["c01_lane_boundary"]


@pytest.fixture
def rule(c01_params):
    return LaneBoundaryRule(c01_params)


def test_within_bounds_no_fire(rule):
    result = rule.evaluate(state=State(lateral_offset=0.0), raw_action=(0.0, 0.5))
    assert result.fire is False
    assert result.safe_action is None


def test_below_deactivate_no_fire(rule, c01_params):
    d = c01_params["d_max_m"] - 2.5 * c01_params["h_d_m"]
    result = rule.evaluate(state=State(lateral_offset=d), raw_action=(0.0, 0.5))
    assert result.fire is False


def test_exceeds_activation_positive_offset(rule, c01_params):
    d = c01_params["d_max_m"]  # at d_max, well above d_activate
    result = rule.evaluate(state=State(lateral_offset=d), raw_action=(0.0, 0.5))
    assert result.fire is True
    steering_safe, _ = result.safe_action
    assert steering_safe < 0.0  # correction steers toward negative (centre, since d>0)


def test_exceeds_activation_negative_offset(rule, c01_params):
    d = -c01_params["d_max_m"]
    result = rule.evaluate(state=State(lateral_offset=d), raw_action=(0.0, 0.5))
    assert result.fire is True
    steering_safe, _ = result.safe_action
    assert steering_safe > 0.0


def test_hysteresis_persists_in_band(rule, c01_params):
    d_band = c01_params["d_max_m"] - 1.5 * c01_params["h_d_m"]  # inside hysteresis band
    # Trigger first
    trigger = c01_params["d_max_m"]
    r1 = rule.evaluate(state=State(lateral_offset=trigger), raw_action=(0.0, 0.5))
    assert r1.fire is True
    # Now drop into band — should remain active
    r2 = rule.evaluate(state=State(lateral_offset=d_band), raw_action=(0.0, 0.5))
    assert r2.fire is True
    assert r2.metadata["active"] is True


def test_hysteresis_deactivates_after_two_cycles_below(rule, c01_params):
    trigger = c01_params["d_max_m"]
    below = c01_params["d_max_m"] - 3.0 * c01_params["h_d_m"]  # well below d_deactivate
    rule.evaluate(state=State(lateral_offset=trigger), raw_action=(0.0, 0.5))
    r1 = rule.evaluate(state=State(lateral_offset=below), raw_action=(0.0, 0.5))
    # First cycle below: not yet deactivated
    assert r1.metadata["active"] is True
    r2 = rule.evaluate(state=State(lateral_offset=below), raw_action=(0.0, 0.5))
    # Second cycle below: now deactivated
    assert r2.metadata["active"] is False
    assert r2.fire is False


def test_correction_saturated_to_unit_range(rule, c01_params):
    # Push with a huge offset; correction would be very large but must saturate
    big_d = 10.0 * c01_params["d_max_m"]
    result = rule.evaluate(state=State(lateral_offset=big_d), raw_action=(0.0, 0.5))
    steering_safe, _ = result.safe_action
    assert -1.0 <= steering_safe <= 1.0


def test_throttle_passes_through_unchanged(rule, c01_params):
    d = c01_params["d_max_m"]
    raw_throttle = 0.7
    result = rule.evaluate(state=State(lateral_offset=d), raw_action=(0.2, raw_throttle))
    _, throttle_safe = result.safe_action
    assert throttle_safe == pytest.approx(raw_throttle)


def test_disabled_rule_passes_through(c01_params):
    params = dict(c01_params)
    params["enabled"] = False
    rule = LaneBoundaryRule(params)
    result = rule.evaluate(state=State(lateral_offset=10.0), raw_action=(0.0, 0.5))
    assert result.fire is False
    assert result.safe_action is None
