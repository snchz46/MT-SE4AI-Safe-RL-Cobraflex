"""
Unit tests for C-04 — Speed ceiling.

Coverage:
    - compute_v_max: floors at v_max_curve, decreases with |kappa|
    - speed below ceiling: no fire
    - speed above ceiling: fire, throttle reduced
    - throttle saturated to ≥ 0
    - steering pass-through
    - disabled rule: no fire
"""

from pathlib import Path

import pytest
import yaml

from cage.rules import SpeedCeilingRule, State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def c04_params():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]["c04_speed_ceiling"]


@pytest.fixture
def rule(c04_params):
    return SpeedCeilingRule(c04_params)


def test_v_max_straight_at_zero_curvature(rule, c04_params):
    assert rule.compute_v_max(0.0) == pytest.approx(c04_params["v_max_straight_mps"])


def test_v_max_floors_at_v_curve(rule, c04_params):
    big_kappa = 100.0
    assert rule.compute_v_max(big_kappa) == pytest.approx(c04_params["v_max_curve_mps"])


def test_v_max_monotonically_decreases_with_curvature(rule):
    v0 = rule.compute_v_max(0.0)
    v_small = rule.compute_v_max(0.1)
    v_large = rule.compute_v_max(0.5)
    assert v0 >= v_small >= v_large


def test_speed_below_ceiling_no_fire(rule, c04_params):
    state = State(speed=c04_params["v_max_straight_mps"] - 0.1)
    result = rule.evaluate(state=state, raw_action=(0.0, 0.8))
    assert result.fire is False
    assert result.safe_action is None


def test_speed_above_ceiling_fires(rule, c04_params):
    state = State(speed=c04_params["v_max_straight_mps"] + 0.05)
    result = rule.evaluate(state=state, raw_action=(0.0, 0.8))
    assert result.fire is True
    _, throttle_safe = result.safe_action
    assert throttle_safe < 0.8


def test_throttle_saturates_at_zero(rule, c04_params):
    state = State(speed=c04_params["v_max_straight_mps"] + 1.0)  # big excess
    result = rule.evaluate(state=state, raw_action=(0.0, 0.5))
    _, throttle_safe = result.safe_action
    assert throttle_safe >= 0.0


def test_steering_passes_through(rule, c04_params):
    state = State(speed=c04_params["v_max_straight_mps"] + 0.05)
    raw_steering = 0.3
    result = rule.evaluate(state=state, raw_action=(raw_steering, 0.8))
    steering_safe, _ = result.safe_action
    assert steering_safe == pytest.approx(raw_steering)


def test_curvature_lowers_ceiling(rule, c04_params):
    # At zero curvature, v=0.4 is under v_max_straight=0.5 → no fire
    no_curve = State(speed=0.4, curvature_ahead=0.0)
    r_flat = rule.evaluate(state=no_curve, raw_action=(0.0, 0.5))
    assert r_flat.fire is False
    # At high curvature, v_max drops; same speed may trigger
    high_curve = State(speed=0.4, curvature_ahead=1.0)
    r_curve = rule.evaluate(state=high_curve, raw_action=(0.0, 0.5))
    # With k_kappa=0.3, v_max = max(0.25, 0.5 - 0.3*1.0) = max(0.25, 0.2) = 0.25
    # speed 0.4 > 0.25 → fires
    assert r_curve.fire is True


def test_disabled_rule_passes_through(c04_params):
    params = dict(c04_params)
    params["enabled"] = False
    rule = SpeedCeilingRule(params)
    state = State(speed=10.0)
    result = rule.evaluate(state=state, raw_action=(0.0, 1.0))
    assert result.fire is False
    assert result.safe_action is None
