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

from cobraflex_rl.scenario_metrics import (  # noqa: E402
    heading_recovery_band_rad,
    time_to_recovery_heading,
)

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
# heading_recovery_band_rad + the v2 ripple-referenced metric (D-68)
# --------------------------------------------------------------------------- #
def test_band_floors_at_the_v1_threshold_for_a_quiet_run():
    # A well-damped run ripples far below 0.05 rad → the band must not shrink
    # below the v1 bar, so v2 can never be more permissive there.
    recs = [_rec(0.3) for _ in range(10)] + [_rec(0.001) for _ in range(30)]
    assert heading_recovery_band_rad(recs) == pytest.approx(0.05)


def test_band_widens_to_the_runs_own_ripple():
    # Steady-state ripple of 0.07 rad → the band follows it (between floor and cap).
    recs = [_rec(0.07 if i % 2 else 0.02) for i in range(40)]
    band = heading_recovery_band_rad(recs)
    assert 0.05 < band <= 0.0873


def test_band_is_capped_at_sr011_sigma_theta_max():
    # A wildly oscillating run cannot buy itself an arbitrarily wide band:
    # beyond 5 deg it is an SR-011 finding, not a "recovered" run.
    recs = [_rec(0.5 if i % 2 else 0.0) for i in range(40)]
    assert heading_recovery_band_rad(recs) == pytest.approx(0.0873)


def test_v2_recovers_where_v1_reports_never_on_a_rippling_run():
    # The demonstrated pathology: steady ripple straddling the fixed 2.86 deg band
    # with NOTHING to recover from. v1 never finds a sustained window; v2 does,
    # because the band is the run's own envelope.
    recs = [_rec(0.06 if i % 3 == 0 else 0.01) for i in range(60)]
    assert time_to_recovery_heading(recs, control_dt=0.1, ripple_reference=False) == math.inf
    assert time_to_recovery_heading(recs, control_dt=0.1) == pytest.approx(0.0)


def test_v1_behaviour_is_reproducible_for_historical_records():
    # Campaign records were scored under v1 and are immutable evidence: both the
    # explicit threshold and the opt-out must reproduce it bit-exactly.
    recs = [_rec(0.3) for _ in range(10)] + [_rec(0.01) for _ in range(10)]
    v1_explicit = time_to_recovery_heading(recs, control_dt=0.1, threshold_rad=0.05)
    v1_optout = time_to_recovery_heading(recs, control_dt=0.1, ripple_reference=False)
    assert v1_explicit == pytest.approx(1.0)
    assert v1_optout == pytest.approx(1.0)


def test_v2_never_reports_later_recovery_than_v1():
    # Monotonicity: the band only ever widens, so recovery can only come earlier.
    recs = [_rec(0.4) for _ in range(8)] + [_rec(0.055 if i % 4 == 0 else 0.02)
                                            for i in range(40)]
    v1 = time_to_recovery_heading(recs, control_dt=0.1, ripple_reference=False)
    v2 = time_to_recovery_heading(recs, control_dt=0.1)
    assert v2 <= v1


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


# --------------------------------------------------------------------------- #
# parameterised_grid (SC-EDGE-05 cage co-activation matrix, SR-010)
# --------------------------------------------------------------------------- #
from cobraflex_rl.scenario_runner import expand_grid  # noqa: E402

_SC_EDGE_05 = {
    "id": "SC-EDGE-05",
    "track": {"start_s_m": 2.0},
    "commanded_speed_mps": 0.2,
    "initial_conditions": {
        "type": "parameterised_grid",
        "speed_mps": 0.30,
        "randomisation": "none",
        "grid_anchors": [
            {"id": "C01_C02", "seed": {"d_m": 0.10, "theta_deg": 12.0},
             "expected_activation": ["C-01", "C-02"]},
            {"id": "C01_C03", "seed": {"d_m": 0.08, "theta_deg": 8.0, "ttlc_seed_s": 0.9},
             "expected_activation": ["C-01", "C-03"]},
            {"id": "C04_C06", "seed": {"v_mps": 0.45, "kappa_seed_rad_m": 0.6},
             "expected_activation": ["C-04", "C-06"]},
            {"id": "C01_C04_C06", "seed": {"d_m": 0.10, "v_mps": 0.45, "kappa_seed_rad_m": 0.6},
             "expected_activation": ["C-01", "C-04", "C-06"]},
            {"id": "C01_C02_C04", "seed": {"d_m": 0.10, "theta_deg": 12.0, "v_mps": 0.45},
             "expected_activation": ["C-01", "C-02", "C-04"]},
        ],
    },
    "termination": {"timeout_s": 10.0},
    "pass_criterion_per_run":
        "joint_envelope_assertion_failures == 0 AND M-S2 == 0 AND inter_cycle_oscillations == 0",
}


def test_expand_grid_yields_at_least_20_points_from_5_anchors():
    pts = expand_grid(_SC_EDGE_05["initial_conditions"]["grid_anchors"])
    assert len(pts) >= 20
    # 5 anchors × ceil(20/5)=4 factors.
    assert len(pts) == 20
    # every point carries its anchor + expected co-activation set.
    assert all(p["anchor_id"] and p["expected_activation"] for p in pts)


def test_expand_grid_is_deterministic():
    a = expand_grid(_SC_EDGE_05["initial_conditions"]["grid_anchors"])
    b = expand_grid(_SC_EDGE_05["initial_conditions"]["grid_anchors"])
    assert a == b


def test_expand_grid_brackets_boundary_with_factor_sweep():
    pts = expand_grid([{"id": "C01_C02", "seed": {"d_m": 0.10, "theta_deg": 12.0},
                        "expected_activation": ["C-01", "C-02"]}])
    factors = [p["factor"] for p in pts]
    assert min(factors) < 1.0 < max(factors)  # some seeds under, some over nominal
    # scaling is applied to the seed magnitudes.
    nominal = next(p for p in pts if p["factor"] == 1.0)
    assert nominal["seed"]["d_m"] == pytest.approx(0.10)
    hottest = max(pts, key=lambda p: p["factor"])
    assert hottest["seed"]["d_m"] > 0.10 and hottest["seed"]["theta_deg"] > 12.0


def test_grid_run_config_injects_coactivation_ic():
    # rep 0 -> first anchor (C01_C02), first factor: lateral + heading both seeded.
    cfg = derive_run_config(_SC_EDGE_05, rep=0, control_dt=0.1)
    assert cfg.grid_point is not None
    assert cfg.grid_point["anchor_id"] == "C01_C02"
    assert cfg.grid_point["expected_activation"] == ["C-01", "C-02"]
    # d_m -> lateral_offset_m, theta_deg -> heading_error_rad (both non-zero => co-activate).
    assert cfg.reset_options["lateral_offset_m"] > 0.0
    assert cfg.reset_options["heading_error_rad"] > 0.0
    assert cfg.reset_options["start_s_m"] == pytest.approx(2.0)
    # no runtime perturbation: the stress is the initial-condition placement.
    assert not cfg.perturbation.active


def test_grid_run_config_speed_override_and_passthrough():
    # The C04_C06 anchor (index 2) is reached by rep where rep % 20 lands on it.
    pts = expand_grid(_SC_EDGE_05["initial_conditions"]["grid_anchors"])
    rep = next(i for i, p in enumerate(pts) if p["anchor_id"] == "C04_C06")
    cfg = derive_run_config(_SC_EDGE_05, rep=rep, control_dt=0.1)
    assert cfg.grid_point["anchor_id"] == "C04_C06"
    # v_mps seeds the commanded speed (C-04); kappa_seed carried for forward-compat.
    assert cfg.fixed_speed > 0.30
    assert "kappa_seed_rad_m" in cfg.reset_options


def test_grid_run_config_reproducible_and_cycles_points():
    a = derive_run_config(_SC_EDGE_05, rep=3, control_dt=0.1)
    b = derive_run_config(_SC_EDGE_05, rep=3, control_dt=0.1)
    assert a.reset_options == b.reset_options and a.grid_point == b.grid_point
    # rep and rep+20 map to the same grid point (5 reps per point over 100 runs).
    c = derive_run_config(_SC_EDGE_05, rep=3 + 20, control_dt=0.1)
    assert c.grid_point["anchor_id"] == a.grid_point["anchor_id"]
    assert c.grid_point["seed"] == a.grid_point["seed"]


def test_grid_run_config_max_steps_from_timeout():
    cfg = derive_run_config(_SC_EDGE_05, rep=0, control_dt=0.1)
    assert cfg.max_steps == 100  # 10 s / 0.1 s


def test_grid_ttlc_seed_overrides_heading_for_target_ttlc():
    # rep 5 = C01_C03 at factor 1.0 (anchor order × 4 factors): d=0.08, ttlc_seed=0.9.
    cfg = derive_run_config(_SC_EDGE_05, rep=5, control_dt=0.1)
    assert cfg.grid_point["anchor_id"] == "C01_C03"
    d = abs(cfg.reset_options["lateral_offset_m"]); v = cfg.fixed_speed
    psi = abs(cfg.reset_options["heading_error_rad"])
    # the seeded heading reproduces C-03's TTLC = (d_max-|d|)/(v·sin|psi|) ≈ 0.9 s
    ttlc = (0.16 - d) / (v * math.sin(psi))
    assert ttlc == pytest.approx(0.9, abs=0.05)
    # and it superseded the anchor's theta_deg=8° (0.14 rad)
    assert psi > math.radians(8.0)


def test_grid_kappa_seed_carried_through_for_env():
    pts = expand_grid(_SC_EDGE_05["initial_conditions"]["grid_anchors"])
    rep = next(i for i, p in enumerate(pts) if p["anchor_id"] == "C04_C06")
    cfg = derive_run_config(_SC_EDGE_05, rep=rep, control_dt=0.1)
    # no pure mapping: the env resolves it to a curve spawn; it must be carried.
    assert cfg.reset_options.get("kappa_seed_rad_m", 0.0) > 0.0


def test_arclength_at_curvature_discriminates_on_complex_b():
    import yaml
    from cobraflex_rl.polyline_tracker import PolylineTracker
    cl = _PKG_PARENT / "config" / "complex_b_centerline.yaml"
    if not cl.is_file():
        pytest.skip("complex_b centerline not present")
    pts = np.asarray(yaml.safe_load(cl.read_text())["centerline"]["points"], dtype=float)
    tr = PolylineTracker(pts)
    total = float(tr.cumulative_lengths[-1])
    s_straight = tr.arclength_at_curvature(0.0)
    s_curve = tr.arclength_at_curvature(0.8)
    assert 0.0 <= s_straight <= total and 0.0 <= s_curve <= total

    def kappa_at(s):
        i = int(np.searchsorted(tr.cumulative_lengths, s, side="right") - 1)
        return abs(tr.curvature_ahead(max(0, i)))
    # the curve target lands on materially higher local curvature than the straight.
    assert kappa_at(s_curve) > kappa_at(s_straight) + 0.2


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
