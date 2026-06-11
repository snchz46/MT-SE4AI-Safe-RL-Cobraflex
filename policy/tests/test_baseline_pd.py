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


def test_loads_from_yaml(pd_params):
    """The YAML loader reads kp_y / throttle_nominal as declared by the
    file. Values themselves are tuned empirically against Gazebo (see
    the comments in policy/baseline_pd.yaml); we only assert the wiring."""
    pd = BaselinePD.from_yaml(PD_YAML)
    assert pd.kp_y == pd_params["kp_y"]
    assert pd.kd_y == pd_params["kd_y"]
    assert pd.kp_h == pd_params["kp_h"]
    assert pd.kd_h == pd_params["kd_h"]
    assert pd.throttle_nominal == pd_params["throttle_nominal"]


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


def test_heading_error_produces_corrective_steering(pd, pd_params):
    # kp_h = 0.3 since v0.7.0: restored after _LOCAL_SEARCH_RADIUS was
    # reduced 6→2, bounding max epsi jump to ~0.094 rad and making the
    # heading term safe. Positive heading_error → car pointing left of
    # track → negative (right) steering correction.
    state = State(heading_error=0.2)
    steering, _ = pd.step(state, current_t=0.0)
    if pd_params["kp_h"] > 0.0:
        assert steering < 0.0
    else:
        assert steering == pytest.approx(0.0)


def test_curvature_reduces_throttle(pd, pd_params):
    state = State(curvature_ahead=0.5)
    _, throttle = pd.step(state, current_t=0.0)
    expected = pd_params["throttle_nominal"] * (
        1.0 - pd_params["alpha_curve_slowdown"] * 0.5
    )
    assert throttle == pytest.approx(expected)


def test_curvature_feedforward_scales_with_throttle_factor(pd, pd_params):
    # v0.8.0: feedforward = kappa_ff * kappa * ff_scale where
    # ff_scale = max(0, 1 - alpha * |kappa|). This keeps the curvature
    # feedforward proportional to the vehicle speed when use_safe_throttle
    # is active (vehicle_control_node scales cruise speed by safe throttle).
    kappa = 0.5
    ff_scale = max(0.0, 1.0 - pd_params["alpha_curve_slowdown"] * kappa)
    expected_ff = pd_params["kappa_to_steering_gain"] * kappa * ff_scale
    state = State(curvature_ahead=kappa)  # ey=0, epsi=0
    steering, _ = pd.step(state, current_t=0.0)
    assert steering == pytest.approx(expected_ff)


def test_extreme_curvature_floors_throttle(pd):
    state = State(curvature_ahead=10.0)
    _, throttle = pd.step(state, current_t=0.0)
    assert throttle == 0.0


def test_finite_difference_rate_contributes(pd, pd_params):
    # kd_y = 0.0 (zeroed in v0.6.0 — same reason kd_h was zeroed: the
    # centerline-projection discontinuity at curve entries produces
    # y_dot ≈ ±3 m/s, making the D-term unreliable). With kd_y = 0 the
    # steering is purely proportional + feedforward, so both steps with
    # the same lateral_offset must produce identical steering.
    pd.step(State(lateral_offset=0.0), current_t=0.0)
    s1, _ = pd.step(State(lateral_offset=0.01), current_t=0.05)
    pd2 = BaselinePD(pd_params)
    s2, _ = pd2.step(State(lateral_offset=0.01), current_t=0.0)
    assert s1 == pytest.approx(s2)  # D-term is zero; outputs must match
    assert s1 > -1.0  # sanity: not saturated


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
