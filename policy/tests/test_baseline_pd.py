"""
Unit tests for the BaselinePD controller.

Coverage:
    - construction from the YAML works
    - centred, straight, at rest → zero steering, nominal throttle
    - positive lateral offset → negative (corrective) steering
    - positive heading error → negative steering
    - curvature reduces throttle
    - rates derived by finite difference contribute to steering
    - reset clears the previous-state history
    - actuator saturation
"""

from pathlib import Path

import pytest
import yaml

from cage.rules import State
from policy.baseline_pd import BaselinePD

PD_YAML = Path(__file__).resolve().parent.parent / "baseline_pd.yaml"


@pytest.fixture(scope="module")
def pd_params():
    with PD_YAML.open() as f:
        return yaml.safe_load(f)["baseline_pd"]


@pytest.fixture
def pd(pd_params):
    return BaselinePD(pd_params)


def test_loads_from_yaml():
    pd = BaselinePD.from_yaml(PD_YAML)
    assert pd.kp_y == 12.0
    assert pd.throttle_nominal == 0.5


def test_centred_straight_at_rest_no_steering(pd, pd_params):
    state = State()
    steering, throttle = pd.step(state, current_t=0.0)
    assert steering == pytest.approx(0.0)
    assert throttle == pytest.approx(pd_params["throttle_nominal"])


def test_positive_offset_produces_negative_steering(pd):
    state = State(lateral_offset=0.05)
    steering, _ = pd.step(state, current_t=0.0)
    assert steering < 0.0


def test_negative_offset_produces_positive_steering(pd):
    state = State(lateral_offset=-0.05)
    steering, _ = pd.step(state, current_t=0.0)
    assert steering > 0.0


def test_positive_heading_produces_negative_steering(pd):
    state = State(heading_error=0.2)
    steering, _ = pd.step(state, current_t=0.0)
    assert steering < 0.0


def test_curvature_reduces_throttle(pd, pd_params):
    state = State(curvature_ahead=0.5)
    _, throttle = pd.step(state, current_t=0.0)
    expected = pd_params["throttle_nominal"] * (
        1.0 - pd_params["alpha_curve_slowdown"] * 0.5
    )
    assert throttle == pytest.approx(expected)


def test_extreme_curvature_floors_throttle(pd):
    state = State(curvature_ahead=10.0)
    _, throttle = pd.step(state, current_t=0.0)
    assert throttle == 0.0


def test_finite_difference_rate_contributes(pd, pd_params):
    # Small magnitudes to stay clear of actuator saturation.
    # First step at t=0 → no rate accumulated
    pd.step(State(lateral_offset=0.0), current_t=0.0)
    # Second step at t=0.05 with offset jump → positive lateral_rate → extra negative steering
    s1, _ = pd.step(State(lateral_offset=0.01), current_t=0.05)
    # Compare against a fresh PD given the same offset but no rate
    pd2 = BaselinePD(pd_params)
    s2, _ = pd2.step(State(lateral_offset=0.01), current_t=0.0)
    assert s1 < s2  # the rate term should add more corrective steering
    assert s1 > -1.0  # sanity: not just saturated


def test_reset_clears_history(pd):
    pd.step(State(lateral_offset=0.05), current_t=0.0)
    pd.reset()
    # After reset, the next step must not see any prior history (rate = 0)
    s_after_reset, _ = pd.step(State(lateral_offset=0.05), current_t=0.1)
    pd2 = BaselinePD({
        "kp_y": pd.kp_y, "kd_y": pd.kd_y, "kp_h": pd.kp_h, "kd_h": pd.kd_h,
        "throttle_nominal": pd.throttle_nominal,
        "alpha_curve_slowdown": pd.alpha,
    })
    s_fresh, _ = pd2.step(State(lateral_offset=0.05), current_t=0.1)
    assert s_after_reset == pytest.approx(s_fresh)


def test_saturation_within_unit_range(pd):
    state = State(lateral_offset=10.0, heading_error=10.0)
    steering, throttle = pd.step(state, current_t=0.0)
    assert -1.0 <= steering <= 1.0
    assert 0.0 <= throttle <= 1.0
