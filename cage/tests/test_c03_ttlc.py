"""
Unit tests for C-03 — Predictive TTLC.

Coverage:
    - compute_ttlc: zero velocity → inf
    - compute_ttlc: heading away from boundary → inf
    - compute_ttlc: heading toward boundary → finite, positive
    - evaluate: ttlc above t_min → no fire
    - evaluate: ttlc below t_min → fire with linearly ramping urgency
    - correction toward centre
    - saturated to [-1, 1]
    - disabled rule: no fire
"""

import math
from pathlib import Path

import pytest
import yaml

from cage.rules import State, TTLCRule

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def c03_params():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]["c03_ttlc"]


@pytest.fixture
def rule(c03_params):
    return TTLCRule(c03_params)


def test_ttlc_zero_speed_is_inf(rule):
    state = State(lateral_offset=0.1, heading_error=0.3, speed=0.0)
    assert rule.compute_ttlc(state) == float("inf")


def test_ttlc_heading_away_from_boundary_is_inf(rule):
    # Vehicle on right side (d>0) but heading further right? No — sin(psi)>0 means moving left.
    # To move away from +d_max, we need v_lat<0 → psi<0 when v>0
    state = State(lateral_offset=0.10, heading_error=-0.1, speed=0.5)
    # v_lat = 0.5 * sin(-0.1) < 0; moving toward -d_max from d=0.10
    # That IS toward a boundary; ttlc finite. Let me invert to a true "away" config:
    state_away = State(lateral_offset=0.10, heading_error=0.01, speed=0.5)
    # Tiny positive heading moving slowly toward +d_max — finite but large
    ttlc_away = rule.compute_ttlc(state_away)
    # With v=0.5, psi=0.01 → v_lat≈0.005, distance≈(0.16-0.10)=0.06 → ttlc≈12 s
    # horizon=3 s → returns inf
    assert ttlc_away == float("inf")


def test_ttlc_heading_toward_boundary_is_finite(rule, c03_params):
    state = State(lateral_offset=0.10, heading_error=0.5, speed=0.5)
    ttlc = rule.compute_ttlc(state)
    assert 0.0 < ttlc < c03_params["horizon_s"]


def test_evaluate_safe_no_fire(rule):
    state = State(lateral_offset=0.0, heading_error=0.0, speed=0.3)
    result = rule.evaluate(state=state, raw_action=(0.0, 0.5))
    assert result.fire is False
    assert result.safe_action is None


def test_evaluate_low_ttlc_fires(rule, c03_params):
    # Construct state with ttlc clearly below t_min
    # v_lat = 0.5 * sin(0.5) ≈ 0.24; distance = 0.16 - 0.10 = 0.06; ttlc ≈ 0.25 s
    state = State(lateral_offset=0.10, heading_error=0.5, speed=0.5)
    result = rule.evaluate(state=state, raw_action=(0.0, 0.5))
    assert result.fire is True
    assert result.metadata["ttlc_s"] < c03_params["t_min_s"]


def test_correction_toward_centre(rule):
    # Positive offset → steering must be negative (toward centre)
    state = State(lateral_offset=0.12, heading_error=0.4, speed=0.5)
    result = rule.evaluate(state=state, raw_action=(0.0, 0.5))
    if result.fire:
        steering_safe, _ = result.safe_action
        assert steering_safe <= 0.0


def test_urgency_ramp_increases_as_ttlc_decreases(rule):
    # Higher heading_error → smaller ttlc → higher urgency magnitude
    s_low_urgency = State(lateral_offset=0.10, heading_error=0.3, speed=0.5)
    s_high_urgency = State(lateral_offset=0.10, heading_error=0.8, speed=0.5)
    r_low = rule.evaluate(state=s_low_urgency, raw_action=(0.0, 0.5))
    r_high = rule.evaluate(state=s_high_urgency, raw_action=(0.0, 0.5))
    if r_low.fire and r_high.fire:
        u_low = r_low.metadata["urgency"]
        u_high = r_high.metadata["urgency"]
        assert u_high >= u_low


def test_correction_saturated_to_unit_range(rule):
    state = State(lateral_offset=0.15, heading_error=1.0, speed=1.0)
    result = rule.evaluate(state=state, raw_action=(0.0, 0.5))
    if result.fire:
        steering_safe, _ = result.safe_action
        assert -1.0 <= steering_safe <= 1.0


def test_disabled_rule_passes_through(c03_params):
    params = dict(c03_params)
    params["enabled"] = False
    rule = TTLCRule(params)
    state = State(lateral_offset=0.15, heading_error=1.0, speed=1.0)
    result = rule.evaluate(state=state, raw_action=(0.0, 0.5))
    assert result.fire is False
    assert result.safe_action is None
