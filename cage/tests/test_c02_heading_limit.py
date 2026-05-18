"""
Unit tests for C-02 — Heading error limit.

Coverage:
    - within bounds: no fire
    - exceed theta_activate: fire, correction opposite to heading
    - hysteresis activation and deactivation (2 cycles below)
    - correction saturated to [-1, 1]
    - disabled rule: no fire
"""

from pathlib import Path

import pytest
import yaml

from cage.rules import HeadingLimitRule, State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def c02_params():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]["c02_heading_limit"]


@pytest.fixture
def rule(c02_params):
    return HeadingLimitRule(c02_params)


def test_within_bounds_no_fire(rule):
    result = rule.evaluate(state=State(heading_error=0.0), raw_action=(0.0, 0.5))
    assert result.fire is False
    assert result.safe_action is None


def test_exceeds_activation_positive_heading(rule, c02_params):
    theta = c02_params["theta_max_rad"]
    result = rule.evaluate(state=State(heading_error=theta), raw_action=(0.0, 0.5))
    assert result.fire is True
    steering_safe, _ = result.safe_action
    assert steering_safe < 0.0


def test_exceeds_activation_negative_heading(rule, c02_params):
    theta = -c02_params["theta_max_rad"]
    result = rule.evaluate(state=State(heading_error=theta), raw_action=(0.0, 0.5))
    assert result.fire is True
    steering_safe, _ = result.safe_action
    assert steering_safe > 0.0


def test_hysteresis_deactivates_after_two_cycles_below(rule, c02_params):
    trigger = c02_params["theta_max_rad"]
    below = c02_params["theta_max_rad"] - 3.0 * c02_params["h_theta_rad"]
    rule.evaluate(state=State(heading_error=trigger), raw_action=(0.0, 0.5))
    r1 = rule.evaluate(state=State(heading_error=below), raw_action=(0.0, 0.5))
    assert r1.metadata["active"] is True
    r2 = rule.evaluate(state=State(heading_error=below), raw_action=(0.0, 0.5))
    assert r2.metadata["active"] is False
    assert r2.fire is False


def test_correction_saturated_to_unit_range(rule, c02_params):
    big_theta = 10.0 * c02_params["theta_max_rad"]
    result = rule.evaluate(state=State(heading_error=big_theta), raw_action=(0.0, 0.5))
    steering_safe, _ = result.safe_action
    assert -1.0 <= steering_safe <= 1.0


def test_throttle_passes_through(rule, c02_params):
    theta = c02_params["theta_max_rad"]
    result = rule.evaluate(state=State(heading_error=theta), raw_action=(0.0, 0.9))
    _, throttle_safe = result.safe_action
    assert throttle_safe == pytest.approx(0.9)


def test_disabled_rule_passes_through(c02_params):
    params = dict(c02_params)
    params["enabled"] = False
    rule = HeadingLimitRule(params)
    result = rule.evaluate(state=State(heading_error=10.0), raw_action=(0.0, 0.5))
    assert result.fire is False
    assert result.safe_action is None
