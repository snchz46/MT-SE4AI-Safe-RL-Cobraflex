"""
Unit tests for cobraflex_rl.scenario_perturbations — the pure (ROS-free) runtime
perturbation injection used by the F4 campaign (SC-PERT-01/02, SC-EDGE-03).
Run without ROS/Gazebo.
"""
import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

np = pytest.importorskip("numpy")
from cobraflex_rl.scenario_perturbations import (  # noqa: E402
    NONE,
    ScenarioPerturbation,
    resolve_perturbation,
)

# --------------------------------------------------------------------------- #
# observation_noise (SC-PERT-01)
# --------------------------------------------------------------------------- #
_OBS = {
    "type": "observation_noise",
    "channel": "lateral_offset",
    "sigma_levels_m": [0.01, 0.03, 0.05],
}


def test_obs_noise_level_selected_round_robin_by_rep():
    assert resolve_perturbation(_OBS, 0).obs_noise_sigma_m == pytest.approx(0.01)
    assert resolve_perturbation(_OBS, 1).obs_noise_sigma_m == pytest.approx(0.03)
    assert resolve_perturbation(_OBS, 2).obs_noise_sigma_m == pytest.approx(0.05)
    assert resolve_perturbation(_OBS, 3).obs_noise_sigma_m == pytest.approx(0.01)  # wraps
    assert resolve_perturbation(_OBS, 5).obs_noise_sigma_m == pytest.approx(0.05)


def test_obs_noise_is_zero_mean_with_requested_sigma():
    p = resolve_perturbation(_OBS, 1)  # sigma = 0.03
    rng = np.random.default_rng(0)
    deltas = [p.perceive_lateral(0.10, rng) - 0.10 for _ in range(20000)]
    assert abs(float(np.mean(deltas))) < 0.002
    assert float(np.std(deltas)) == pytest.approx(0.03, rel=0.1)


def test_obs_noise_only_touches_its_channel():
    p = ScenarioPerturbation(
        kind="observation_noise", obs_noise_sigma_m=0.03, obs_noise_channel="speed"
    )
    rng = np.random.default_rng(0)
    assert p.perceive_lateral(0.1, rng) == 0.1  # lateral untouched when channel != lateral_offset


# --------------------------------------------------------------------------- #
# actuation_latency (SC-PERT-02)
# --------------------------------------------------------------------------- #
_LAT = {"type": "actuation_latency", "latency_levels_ms": [50, 100]}


def test_latency_steps_and_10hz_granularity():
    # At 10 Hz (dt=0.1) the realizable granularity is one control period: 50 ms is
    # sub-cycle (rounds to 0), 100 ms = 1 step. Documented limitation.
    assert resolve_perturbation(_LAT, 0, control_dt=0.1).latency_steps == 0
    assert resolve_perturbation(_LAT, 1, control_dt=0.1).latency_steps == 1
    assert resolve_perturbation(_LAT, 2, control_dt=0.1).latency_steps == 0  # round-robin
    # A faster control period resolves the levels distinctly.
    assert resolve_perturbation(_LAT, 1, control_dt=0.05).latency_steps == 2  # 100 ms @ 20 Hz


# --------------------------------------------------------------------------- #
# throttle_override (SC-EDGE-03)
# --------------------------------------------------------------------------- #
_THR = {"type": "throttle_override", "at_time_s": 5.0, "duration_s": 0.2, "throttle": 1.0}


def test_throttle_override_window_half_open():
    p = resolve_perturbation(_THR, 0)
    assert p.throttle_override(4.99) is None
    assert p.throttle_override(5.0) == pytest.approx(1.0)   # start inclusive
    assert p.throttle_override(5.19) == pytest.approx(1.0)
    assert p.throttle_override(5.2) is None                 # end exclusive
    assert p.pulse_throttle == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# none / non-runtime blocks → NONE singleton, inert
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "block",
    [
        None,
        "none",
        {},
        {"type": "parameterised_grid"},        # SC-EDGE-05 (initial-condition mechanism)
        {"type": "pre_run_policy_finetune"},   # SC-PERT-03 (pre-run policy swap)
        {"type": "observation_noise"},         # missing sigma_levels_m
        {"type": "actuation_latency"},         # missing latency_levels_ms
    ],
)
def test_non_runtime_blocks_resolve_to_none(block):
    assert resolve_perturbation(block, 0) is NONE


def test_none_is_inert():
    rng = np.random.default_rng(0)
    assert not NONE.active
    assert NONE.perceive_lateral(0.123, rng) == 0.123
    assert NONE.throttle_override(5.0) is None
