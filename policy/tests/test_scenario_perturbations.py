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


# --------------------------------------------------------------------------- #
# visual_degradation / perception_loss / false_lane (track 'E', SC-PERT-04..08)
# --------------------------------------------------------------------------- #
def test_visual_degradation_levels_round_robin():
    block = {"type": "visual_degradation", "mode": "glare_overexposure",
             "level_levels": [0.3, 0.6]}
    p0 = resolve_perturbation(block, 0)
    p1 = resolve_perturbation(block, 1)
    p2 = resolve_perturbation(block, 2)
    assert p0.kind == "visual_degradation" and p0.visual_mode == "glare_overexposure"
    assert (p0.visual_level, p1.visual_level, p2.visual_level) == (0.3, 0.6, 0.3)


def test_visual_degradation_onset_window():
    block = {"type": "perception_loss", "mode": "occlusion",
             "level_levels": [1.0], "at_time_s": 5.0}
    p = resolve_perturbation(block, 0)
    assert p.visual_degradation_at(4.9) is None       # nominal lead-in clean
    assert p.visual_degradation_at(5.0) == ("occlusion", 1.0)
    assert p.visual_degradation_at(12.0) == ("occlusion", 1.0)


def test_scenario_mode_aliases_resolve_to_primitives():
    p7 = resolve_perturbation(
        {"type": "perception_loss", "mode": "occlusion_or_dropout",
         "level_levels": [1.0]}, 0)
    assert p7.visual_mode == "occlusion"
    p8 = resolve_perturbation(
        {"type": "false_lane", "mode": "misleading_markings",
         "level_levels": [0.8], "at_time_s": 5.0}, 0)
    assert p8.visual_mode == "false_lane"
    assert p8.visual_degradation_at(6.0) == ("false_lane", 0.8)


def test_visual_modes_exist_in_degradation_catalogue():
    # The strings this module emits must be real visual_degradation modes.
    from cobraflex_rl.visual_degradation import ALL_MODES
    for block in (
        {"type": "visual_degradation", "mode": "glare_overexposure", "level_levels": [0.3]},
        {"type": "visual_degradation", "mode": "low_light_underexposure", "level_levels": [0.2]},
        {"type": "visual_degradation", "mode": "motion_blur", "level_levels": [0.4]},
        {"type": "perception_loss", "mode": "occlusion_or_dropout", "level_levels": [1.0]},
        {"type": "false_lane", "mode": "misleading_markings", "level_levels": [0.8]},
    ):
        p = resolve_perturbation(block, 0)
        assert p.visual_mode in ALL_MODES


def test_none_has_no_visual_degradation():
    assert NONE.visual_degradation_at(0.0) is None


def test_visual_degradation_level_index_round_robin():
    """The resolved perturbation records its level index (rep % n_levels) so a
    single-run evaluator can pick the matching arm of a labelled criterion
    (SC-PERT-05 low/high)."""
    block = {"type": "visual_degradation", "mode": "low_light_underexposure",
             "level_levels": [0.2, 0.5]}
    assert resolve_perturbation(block, 0).level_index == 0
    assert resolve_perturbation(block, 1).level_index == 1
    assert resolve_perturbation(block, 2).level_index == 0
