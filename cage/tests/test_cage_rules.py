"""
Tests for cage rule loading from cage.yaml.

These tests verify that:
1. The cage YAML can be loaded and parsed.
2. Each rule class can be instantiated with its corresponding parameter block.
3. Each rule responds to .evaluate() with a CageDecision-shaped object.

These are minimal tests that pass even with the Phase 2 stub implementations.
They will be supplemented by per-rule behavioural tests in Phase 2.
"""

from pathlib import Path
import yaml
import pytest

from cage.rules import (
    LaneBoundaryRule,
    HeadingLimitRule,
    TTLCRule,
    SpeedCeilingRule,
    EmergencyRule,
    RateLimiterRule,
)

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def cage_config():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]


def test_cage_yaml_loads(cage_config):
    assert "version" in cage_config
    assert "default_mode" in cage_config


@pytest.mark.parametrize(
    "rule_class, params_key",
    [
        (LaneBoundaryRule, "c01_lane_boundary"),
        (HeadingLimitRule, "c02_heading_limit"),
        (TTLCRule, "c03_ttlc"),
        (SpeedCeilingRule, "c04_speed_ceiling"),
        (EmergencyRule, "c05_emergency"),
        (RateLimiterRule, "c06_rate_limiter"),
    ],
)
def test_rule_instantiation(cage_config, rule_class, params_key):
    rule = rule_class(cage_config[params_key])
    assert rule.enabled is True


@pytest.mark.parametrize(
    "rule_class, params_key",
    [
        (LaneBoundaryRule, "c01_lane_boundary"),
        (HeadingLimitRule, "c02_heading_limit"),
        (TTLCRule, "c03_ttlc"),
        (SpeedCeilingRule, "c04_speed_ceiling"),
        (EmergencyRule, "c05_emergency"),
        (RateLimiterRule, "c06_rate_limiter"),
    ],
)
def test_rule_evaluate_returns_decision(cage_config, rule_class, params_key):
    rule = rule_class(cage_config[params_key])
    state = {"lateral_offset": 0.0, "heading_error": 0.0, "speed": 0.3}
    raw_action = (0.0, 0.5)
    result = rule.evaluate(state=state, raw_action=raw_action, prev_action=None)
    assert hasattr(result, "fire")
    assert hasattr(result, "metadata")
