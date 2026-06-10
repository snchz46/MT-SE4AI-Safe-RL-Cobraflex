"""
Unit tests for the pure F4 scenario-execution helpers:
  * cobraflex_rl.scenario_metrics.time_to_recovery_heading
  * cobraflex_rl.scenario_runner.derive_run_config
Both run without ROS/Gazebo (scenario_runner needs numpy for its seeded RNG).
"""

import math
import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.scenario_metrics import time_to_recovery_heading  # noqa: E402

np = pytest.importorskip("numpy")
from cobraflex_rl.scenario_runner import derive_run_config, run_seed  # noqa: E402


def _rec(epsi):
    return {"epsi": epsi}


# --------------------------------------------------------------------------- #
# time_to_recovery_heading
# --------------------------------------------------------------------------- #
def test_recovery_immediate_when_already_settled():
    # |epsi| below threshold from the start, held → recovery at t=0.
    recs = [_rec(0.01) for _ in range(20)]
    assert time_to_recovery_heading(recs, control_dt=0.1) == pytest.approx(0.0)


def test_recovery_after_decay():
    # Large error for 10 steps, then settled below threshold and held.
    recs = [_rec(0.3) for _ in range(10)] + [_rec(0.01) for _ in range(10)]
    # settle_s=0.5 → 5 steps; first sustained window starts at step 10 → 1.0 s.
    assert time_to_recovery_heading(recs, control_dt=0.1, settle_s=0.5) == pytest.approx(1.0)


def test_no_sustained_recovery_returns_inf():
    # Dips below threshold for only 2 steps, never holds the 5-step settle window.
    recs = [_rec(0.3), _rec(0.01), _rec(0.01), _rec(0.3), _rec(0.3)]
    assert time_to_recovery_heading(recs, control_dt=0.1, settle_s=0.5) == math.inf


def test_empty_run_returns_none():
    assert time_to_recovery_heading([], control_dt=0.1) is None


# --------------------------------------------------------------------------- #
# derive_run_config
# --------------------------------------------------------------------------- #
_SC_EDGE_01 = {
    "id": "SC-EDGE-01",
    "track": {"start_s_m": 0.0},
    "commanded_speed_mps": 0.2,
    "initial_conditions": {"pose": {"x": 0.0, "y": 0.0, "theta_deg": 15.0},
                           "randomisation": "none"},
    "termination": {"timeout_s": 15.0},
    "pass_criterion_per_run": "emergency == False AND M-S1 < 0.16",
}

_SC_EDGE_02 = {
    "id": "SC-EDGE-02",
    "track": {"start_s_m": 0.0},
    "commanded_speed_mps": 0.2,
    "initial_conditions": {
        "pose": {"x": 0.0, "y": 0.12, "theta_deg": 0.0},
        "randomisation": {"lateral_offset_uniform_m": [-0.02, 0.02],
                          "heading_uniform_deg": [-2.0, 2.0]},
    },
    "termination": {"timeout_s": 15.0},
    "pass_criterion_per_run": "M-S1 < 0.16 AND emergency == False",
}


def test_seed_heading_error_no_jitter():
    cfg = derive_run_config(_SC_EDGE_01, rep=0, control_dt=0.1)
    assert cfg.reset_options["heading_error_rad"] == pytest.approx(math.radians(15.0))
    assert cfg.reset_options["lateral_offset_m"] == pytest.approx(0.0)
    assert cfg.reset_options["start_s_m"] == 0.0
    assert cfg.fixed_speed == pytest.approx(0.2)
    assert cfg.max_steps == 150  # 15 s / 0.1 s


def test_lateral_seed_plus_jitter_within_bounds():
    cfg = derive_run_config(_SC_EDGE_02, rep=3, control_dt=0.1)
    # 0.12 seed + jitter in [-0.02, 0.02].
    assert 0.10 <= cfg.reset_options["lateral_offset_m"] <= 0.14
    # heading jitter in [-2, 2] deg.
    assert abs(cfg.reset_options["heading_error_rad"]) <= math.radians(2.0) + 1e-9


def test_jitter_is_reproducible_per_rep():
    a = derive_run_config(_SC_EDGE_02, rep=7, control_dt=0.1).reset_options
    b = derive_run_config(_SC_EDGE_02, rep=7, control_dt=0.1).reset_options
    assert a == b


def test_different_reps_differ():
    a = derive_run_config(_SC_EDGE_02, rep=1, control_dt=0.1).reset_options
    b = derive_run_config(_SC_EDGE_02, rep=2, control_dt=0.1).reset_options
    assert a != b


# --------------------------------------------------------------------------- #
# derive_run_config — perturbation + env_seed (F4 runtime injection)
# --------------------------------------------------------------------------- #
def test_run_config_carries_level_resolved_perturbation():
    sc = {
        **_SC_EDGE_02,
        "perturbations": {"type": "observation_noise", "sigma_levels_m": [0.01, 0.03, 0.05]},
    }
    c0 = derive_run_config(sc, rep=0, control_dt=0.1)
    c1 = derive_run_config(sc, rep=1, control_dt=0.1)
    assert c0.perturbation.kind == "observation_noise"
    assert c0.perturbation.obs_noise_sigma_m == pytest.approx(0.01)
    assert c1.perturbation.obs_noise_sigma_m == pytest.approx(0.03)  # level by rep


def test_run_config_env_seed_reproducible_and_rep_specific():
    c0 = derive_run_config(_SC_EDGE_02, rep=0)
    c0_again = derive_run_config(_SC_EDGE_02, rep=0)
    c1 = derive_run_config(_SC_EDGE_02, rep=1)
    assert c0.env_seed == c0_again.env_seed == run_seed("SC-EDGE-02", 0, 0)
    assert c0.env_seed != c1.env_seed


def test_run_config_without_perturbations_is_inert():
    c = derive_run_config(_SC_EDGE_01, rep=0)  # _SC_EDGE_01 has no perturbations key
    assert c.perturbation.kind == "none"
    assert not c.perturbation.active


def test_run_seed_stable_across_calls():
    assert run_seed("SC-EDGE-02", 5, 0) == run_seed("SC-EDGE-02", 5, 0)
    assert run_seed("SC-EDGE-02", 5, 0) != run_seed("SC-EDGE-02", 6, 0)


# --------------------------------------------------------------------------- #
# frontier / OOD verdict metrics
# --------------------------------------------------------------------------- #
from cobraflex_rl.scenario_metrics import (  # noqa: E402
    max_excursion_m, emergency_triggered, road_edge_contact)


def _recE(ey, emergency=False):
    return {"ey": ey, "epsi": 0.0, "emergency": emergency}


def test_max_excursion_and_contact():
    # Enforcement-like: caught at 0.18 m, road half 0.26 -> no contact.
    enf = [_recE(0.14), _recE(0.18), _recE(0.16)]
    assert max_excursion_m(enf) == pytest.approx(0.18)
    assert road_edge_contact(enf, 0.26) is False
    # Monitoring-like: drove to the road edge -> contact.
    mon = [_recE(0.14), _recE(0.22), _recE(0.27)]
    assert road_edge_contact(mon, 0.26) is True


def test_emergency_triggered():
    assert emergency_triggered([_recE(0.1), _recE(0.18, emergency=True)]) is True
    assert emergency_triggered([_recE(0.1), _recE(0.12)]) is False


def test_frontier_metrics_empty_run():
    assert max_excursion_m([]) is None
    assert road_edge_contact([], 0.26) is None
    assert emergency_triggered([]) is False
