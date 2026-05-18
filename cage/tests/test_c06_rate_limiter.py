"""
Unit tests for C-06 — Actuator rate limiter.

Coverage:
    - first cycle (no prev_action) → pass-through
    - within limits → no fire
    - steering clipped (positive direction)
    - steering clipped (negative direction)
    - throttle clipped
    - both components clipped simultaneously
    - exact boundary (strict inequality)
    - disabled rule → pass-through
    - metadata exposes rule ID and applied deltas
"""

from pathlib import Path

import pytest
import yaml

from cage.rules import RateLimiterRule

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def c06_params():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]["c06_rate_limiter"]


@pytest.fixture
def rule(c06_params):
    return RateLimiterRule(c06_params)


def test_no_prev_action_passes_through(rule):
    result = rule.evaluate(state=None, raw_action=(0.5, 0.8), prev_action=None)
    assert result.fire is False
    assert result.safe_action is None
    assert "no-prev" in result.reason


def test_within_limits_does_not_fire(rule, c06_params):
    prev = (0.0, 0.5)
    delta_s = c06_params["delta_max_steering_per_cycle"] - 0.01
    delta_t = c06_params["delta_max_throttle_per_cycle"] - 0.01
    raw = (prev[0] + delta_s, prev[1] + delta_t)
    result = rule.evaluate(state=None, raw_action=raw, prev_action=prev)
    assert result.fire is False
    assert result.safe_action is None
    assert result.reason == "within-limits"


def test_steering_exceeds_positive(rule, c06_params):
    prev = (0.0, 0.5)
    delta_max = c06_params["delta_max_steering_per_cycle"]
    raw = (prev[0] + 2.0 * delta_max, prev[1])
    result = rule.evaluate(state=None, raw_action=raw, prev_action=prev)
    assert result.fire is True
    s_safe, t_safe = result.safe_action
    assert s_safe == pytest.approx(prev[0] + delta_max)
    assert t_safe == pytest.approx(prev[1])


def test_steering_exceeds_negative(rule, c06_params):
    prev = (0.5, 0.5)
    delta_max = c06_params["delta_max_steering_per_cycle"]
    raw = (prev[0] - 2.0 * delta_max, prev[1])
    result = rule.evaluate(state=None, raw_action=raw, prev_action=prev)
    assert result.fire is True
    s_safe, _ = result.safe_action
    assert s_safe == pytest.approx(prev[0] - delta_max)


def test_throttle_exceeds(rule, c06_params):
    prev = (0.0, 0.3)
    delta_max = c06_params["delta_max_throttle_per_cycle"]
    raw = (prev[0], prev[1] + 2.0 * delta_max)
    result = rule.evaluate(state=None, raw_action=raw, prev_action=prev)
    assert result.fire is True
    _, t_safe = result.safe_action
    assert t_safe == pytest.approx(prev[1] + delta_max)


def test_both_components_clipped(rule, c06_params):
    prev = (0.0, 0.5)
    raw = (prev[0] + 1.0, prev[1] + 1.0)
    result = rule.evaluate(state=None, raw_action=raw, prev_action=prev)
    assert result.fire is True
    s_safe, t_safe = result.safe_action
    assert s_safe == pytest.approx(prev[0] + c06_params["delta_max_steering_per_cycle"])
    assert t_safe == pytest.approx(prev[1] + c06_params["delta_max_throttle_per_cycle"])


def test_at_exact_boundary_does_not_fire(rule, c06_params):
    """Strict inequality: delta == max should not trigger clipping."""
    prev = (0.0, 0.5)
    raw = (prev[0] + c06_params["delta_max_steering_per_cycle"], prev[1])
    result = rule.evaluate(state=None, raw_action=raw, prev_action=prev)
    assert result.fire is False


def test_disabled_rule_passes_through(c06_params):
    params = dict(c06_params)
    params["enabled"] = False
    rule = RateLimiterRule(params)
    result = rule.evaluate(state=None, raw_action=(1.0, 1.0), prev_action=(0.0, 0.0))
    assert result.fire is False
    assert result.safe_action is None
    assert result.reason == "disabled"


def test_metadata_contains_rule_id_and_deltas(rule, c06_params):
    prev = (0.0, 0.5)
    delta_max = c06_params["delta_max_steering_per_cycle"]
    raw = (prev[0] + 3.0 * delta_max, prev[1])
    result = rule.evaluate(state=None, raw_action=raw, prev_action=prev)
    assert result.metadata["rule"] == "C-06"
    assert result.metadata["delta_steering_raw"] == pytest.approx(3.0 * delta_max)
    assert result.metadata["delta_steering_applied"] == pytest.approx(delta_max)
