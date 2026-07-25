"""Unit tests for cobraflex_rl.cv_lane_estimator (track 'E', D-43).

Synthetic frames are rendered through the *same* camera model the estimator
uses: for a pitch-only mount each image row v sees one ground distance X(v)
and u maps linearly to lateral Y, so a ground-frame lane (two white lines)
can be drawn exactly. The tests verify the estimator recovers known
ey / epsi / lane width / curvature, and degrades honestly (ok=False with a
reason) when the lane is absent or occluded.
"""
import math

import numpy as np
import pytest

from cobraflex_rl.camera_geometry import CameraModel
from cobraflex_rl.cv_lane_estimator import (
    CvLaneEstimator,
    CvLaneEstimatorConfig,
)

LANE_W = 0.245
LINE_W = 0.02  # painted line width, metres
ROAD_GRAY = 40
LINE_VAL = 230


@pytest.fixture(scope="module")
def cam():
    return CameraModel()


def render_lane(
    cam: CameraModel,
    lines,  # iterable of callables X -> Y (ground frame, metres)
    x_min: float = 0.12,
    x_max: float = 1.5,
) -> np.ndarray:
    """Draw white ground-frame lines on a dark road, row-exactly."""
    img = np.full((cam.height_px, cam.width_px, 3), ROAD_GRAY, dtype=np.uint8)
    for v in range(cam.height_px):
        try:
            x = cam.row_to_distance(float(v))
        except ValueError:
            continue
        if not x_min <= x <= x_max:
            continue
        res = cam.lateral_resolution(float(v))
        for line_fn in lines:
            y = line_fn(x)
            u_c = cam.cx - (y / res)
            half = max(1.0, (LINE_W / 2.0) / res)
            lo = int(round(u_c - half))
            hi = int(round(u_c + half))
            if hi < 0 or lo >= cam.width_px:
                continue
            img[v, max(0, lo): min(cam.width_px, hi + 1)] = LINE_VAL
    return img


def centered_lane(ey: float = 0.0, yaw: float = 0.0, kappa: float = 0.0):
    """Two lane lines for a vehicle at lateral offset ``ey`` (+left of centre)
    and heading error ``yaw`` (+vehicle yawed left of lane direction).

    In the vehicle/ground frame the lane centre then satisfies
    Y_c(X) ≈ -ey + tan(-yaw)·X + kappa/2·X² (small-angle composition), and the
    lines sit ±LANE_W/2 beside it.
    """
    b = math.tan(-yaw)

    def centre(x):
        return -ey + b * x + 0.5 * kappa * x * x

    return (
        lambda x: centre(x) + LANE_W / 2.0,  # left line
        lambda x: centre(x) - LANE_W / 2.0,  # right line
    )


@pytest.fixture(scope="module")
def estimator(cam):
    return CvLaneEstimator(cam)


def test_centered_straight_lane(estimator, cam):
    img = render_lane(cam, centered_lane())
    est = estimator.estimate(img)
    assert est.ok
    assert est.ey == pytest.approx(0.0, abs=0.01)
    assert est.epsi == pytest.approx(0.0, abs=0.02)
    assert est.lane_width == pytest.approx(LANE_W, abs=0.03)
    assert est.confidence > 0.5
    assert est.feature_count >= 10


def test_lateral_offset_recovered(estimator, cam):
    for ey in (-0.08, -0.04, 0.04, 0.08):
        img = render_lane(cam, centered_lane(ey=ey))
        est = estimator.estimate(img)
        assert est.ok, f"ey={ey}: {est.reason}"
        assert est.ey == pytest.approx(ey, abs=0.015), f"ey={ey}"


def test_heading_error_recovered(estimator, cam):
    for yaw in (-0.15, 0.15):
        img = render_lane(cam, centered_lane(yaw=yaw))
        est = estimator.estimate(img)
        assert est.ok, f"yaw={yaw}: {est.reason}"
        assert est.epsi == pytest.approx(yaw, abs=0.03), f"yaw={yaw}"


def test_combined_offset_and_heading(estimator, cam):
    img = render_lane(cam, centered_lane(ey=0.06, yaw=-0.1))
    est = estimator.estimate(img)
    assert est.ok
    assert est.ey == pytest.approx(0.06, abs=0.02)
    assert est.epsi == pytest.approx(-0.1, abs=0.03)


def test_curvature_sign_left_bend(estimator, cam):
    img = render_lane(cam, centered_lane(kappa=0.8))
    est = estimator.estimate(img)
    assert est.ok
    assert est.curvature > 0.2  # left bend → positive


def test_curvature_sign_right_bend(estimator, cam):
    img = render_lane(cam, centered_lane(kappa=-0.8))
    est = estimator.estimate(img)
    assert est.ok
    assert est.curvature < -0.2


def test_centred_on_curve_heading_stays_under_cage_threshold(estimator, cam):
    """A vehicle centred on a curved lane must keep the *reported* heading under
    C-02's theta_max so the cage stays latent on a benign in-ODD curve. Heading
    comes from a short near-field secant: on a *uniformly* curved synthetic
    parabola it carries a small bounded arc bias (≈ κ × window-centroid ≈ 0.27
    at the oval's KAPPA_MAX 1.25); on the real circuit the near band is locally
    straight so it reads even smaller. Either way it must stay under theta_warning
    (0.349) — the apex over-read *past* theta_max was the false emergency
    (cv_ctrl_eval_20260618T182017Z)."""
    for kappa in (0.6, -0.6, 1.25, -1.25):
        img = render_lane(cam, centered_lane(yaw=0.0, kappa=kappa))
        est = estimator.estimate(img)
        assert est.ok, f"kappa={kappa}: {est.reason}"
        assert abs(est.epsi) < 0.349, f"kappa={kappa}: epsi={est.epsi:.3f}"  # < theta_warning
        assert abs(est.ey) < 0.02, f"kappa={kappa}: ey={est.ey:.3f}"


def test_no_lane_on_blank_frame(estimator, cam):
    img = np.full((cam.height_px, cam.width_px, 3), ROAD_GRAY, dtype=np.uint8)
    est = estimator.estimate(img)
    assert not est.ok
    assert est.reason == "no_line_features"
    assert est.confidence == 0.0


def test_single_line_fallback_left_line(cam):
    # One line ~half a lane to the LEFT: the fallback infers the centre from
    # the running lane width (lane_keeper single-side precedent).
    est = CvLaneEstimator(cam).estimate(render_lane(cam, [lambda x: LANE_W / 2.0]))
    assert est.ok
    assert est.reason == "single_line"
    assert est.ey == pytest.approx(0.0, abs=0.02)
    assert est.confidence <= 0.5  # halved confidence


def test_single_line_fallback_right_line(cam):
    est = CvLaneEstimator(cam).estimate(render_lane(cam, [lambda x: -LANE_W / 2.0]))
    assert est.ok
    assert est.reason == "single_line"
    assert est.ey == pytest.approx(0.0, abs=0.02)


def test_single_line_far_from_half_lane_rejected(cam):
    # A lone line 0.4 m out: side assignment too ambiguous -> no estimate.
    est = CvLaneEstimator(cam).estimate(render_lane(cam, [lambda x: 0.4]))
    assert not est.ok
    assert est.reason == "fewer_than_two_lines"


def test_single_line_fallback_can_be_disabled(cam):
    cfg = CvLaneEstimatorConfig(single_line_fallback=False)
    est = CvLaneEstimator(cam, cfg).estimate(
        render_lane(cam, [lambda x: LANE_W / 2.0])
    )
    assert not est.ok


def test_pair_separation_must_be_plausible(estimator, cam):
    # Two lines 0.6 m apart: not a 0.245 m lane.
    img = render_lane(cam, [lambda x: 0.3, lambda x: -0.3])
    est = estimator.estimate(img)
    assert not est.ok
    assert est.reason == "no_plausible_lane_pair"


def test_three_lines_pick_the_driven_lane(estimator, cam):
    # Two-lane road seen from the right lane's centre: right edge at
    # -LANE_W/2, separator at +LANE_W/2, far edge at +3·LANE_W/2. The
    # estimator must pick the pair bracketing the vehicle.
    img = render_lane(
        cam,
        [
            lambda x: -LANE_W / 2.0,
            lambda x: LANE_W / 2.0,
            lambda x: 1.5 * LANE_W,
        ],
    )
    est = estimator.estimate(img)
    assert est.ok
    assert est.n_lines >= 3
    assert est.ey == pytest.approx(0.0, abs=0.015)


def test_occlusion_drops_confidence(estimator, cam):
    img = render_lane(cam, centered_lane())
    clean = estimator.estimate(img)
    # Occlude the bottom 60% of the frame (near field) with a dark patch.
    occluded = img.copy()
    occluded[int(cam.height_px * 0.4):, :] = 15
    occ = estimator.estimate(occluded)
    if occ.ok:
        assert occ.confidence < clean.confidence
    else:
        assert occ.reason in ("no_line_features", "fewer_than_two_lines")


def test_grayscale_input_supported(estimator, cam):
    img = render_lane(cam, centered_lane())
    gray = img[:, :, 0]
    est = estimator.estimate(gray)
    assert est.ok
    assert est.ey == pytest.approx(0.0, abs=0.015)


def test_near_field_slope_ignores_far_curve():
    # A lane bending across the scan band (yc = 0.3·X²): the short near-window
    # secant sees only the locally-flat start, so it reports a slope far below
    # the full-band secant (which is dominated by the far bend).
    est = CvLaneEstimator(config=CvLaneEstimatorConfig())
    xs = np.linspace(0.15, 1.0, 24)
    yc = 0.3 * xs ** 2  # lane-centre y bends with X (right-hand curve)
    right = {"pts": list(zip(xs, yc - LANE_W / 2)), "c0": 0.0, "c1": 0.0, "c2": 0.3}
    left = {"pts": list(zip(xs, yc + LANE_W / 2)), "c0": 0.0, "c1": 0.0, "c2": 0.3}
    full_band = 0.345  # ~ secant slope over the whole band (the biased value)
    near = est._near_field_slope(right, left, full_band)
    assert near < 0.20                       # near band ≪ far-curve secant
    assert near < full_band - 0.1            # clearly below the full-band slope


def test_near_field_slope_disabled_falls_back_to_full_band():
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(heading_window_m=0.0))
    xs = np.linspace(0.15, 1.0, 24)
    right = {"pts": list(zip(xs, 0.3 * xs ** 2)), "c0": 0.0, "c1": 0.0, "c2": 0.0}
    left = {"pts": list(zip(xs, 0.3 * xs ** 2)), "c0": 0.0, "c1": 0.0, "c2": 0.0}
    assert est._near_field_slope(right, left, 0.345) == 0.345


def test_joint_pair_fit_separates_heading_from_shared_curvature(cam):
    """The candidate readout recovers heading without subtracting curvature."""
    cfg = CvLaneEstimatorConfig(heading_fit_mode="joint_pair_quadratic")
    estimator = CvLaneEstimator(cam, cfg)
    for yaw in (-0.48, 0.0, 0.48):
        estimate = estimator.estimate(
            render_lane(cam, centered_lane(yaw=yaw, kappa=1.0))
        )
        assert estimate.ok, estimate.reason
        assert estimate.epsi == pytest.approx(yaw, abs=0.06)


def test_joint_pair_fit_mode_is_explicit_and_validated():
    with pytest.raises(ValueError, match="heading_fit_mode"):
        CvLaneEstimator(config=CvLaneEstimatorConfig(heading_fit_mode="unknown"))


def test_heading_gain_preserves_sign_and_amplifies_real_heading(cam):
    base = CvLaneEstimator(
        cam, CvLaneEstimatorConfig(heading_fit_mode="joint_pair_quadratic")
    )
    gained = CvLaneEstimator(
        cam,
        CvLaneEstimatorConfig(
            heading_fit_mode="joint_pair_quadratic", heading_gain=1.75,
        ),
    )
    for yaw in (-0.30, 0.30):
        image = render_lane(cam, centered_lane(yaw=yaw, kappa=1.0))
        assert gained.estimate(image).epsi == pytest.approx(
            1.75 * base.estimate(image).epsi, abs=1e-6
        )


@pytest.mark.parametrize("gain", [0.0, -1.0, float("inf")])
def test_heading_gain_must_be_positive_and_finite(gain):
    with pytest.raises(ValueError, match="heading_gain"):
        CvLaneEstimator(config=CvLaneEstimatorConfig(heading_gain=gain))


# --------------------------------------------------------------------------
# Temporal heading-consistency gate (T3, D-62). Unit-level tests of
# CvLaneEstimator._temporal_heading_gate: the mechanism that resolves the H-12
# single-frame heading over-read on tight curves. Validated end-to-end offline
# against the held-out D-43/C-02 fault cells and the margin022 nominal trace.
# --------------------------------------------------------------------------
_T3 = dict(
    heading_temporal_window=4,
    heading_temporal_ey_track_m=0.08,
    heading_temporal_ey_drift_m=0.03,
    heading_temporal_kappa_gate=0.30,
    heading_temporal_cap_rad=0.32,
)


def test_t3_disabled_by_default_is_noop():
    """window == 0 (the default) must leave epsi untouched — frozen GE4/G4
    configs stay bit-identical."""
    est = CvLaneEstimator(config=CvLaneEstimatorConfig())
    for _ in range(6):
        assert est._temporal_heading_gate(0.02, -0.44, 0.9) == -0.44


def test_t3_negative_window_rejected():
    with pytest.raises(ValueError, match="heading_temporal_window"):
        CvLaneEstimator(config=CvLaneEstimatorConfig(heading_temporal_window=-1))


def test_t3_caps_confirmed_tracking_over_read():
    """A centred, non-drifting vehicle on a real curve whose CV heading
    over-reads past C-02 gets capped once the window fills (sign preserved)."""
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**_T3))
    out = [est._temporal_heading_gate(0.03, -0.44, 0.8) for _ in range(4)]
    # window not full for the first three frames -> pass-through
    assert out[:3] == [-0.44, -0.44, -0.44]
    # fourth frame: window full, gate holds -> capped to -0.32
    assert out[3] == pytest.approx(-0.32)


def test_t3_never_masks_a_drifting_fault():
    """A genuine heading fault moves the vehicle: once ey drifts past the bound
    the over-read passes through unchanged, whatever the curvature."""
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**_T3))
    for _ in range(4):  # confirm lane-following first (centred, still)
        est._temporal_heading_gate(0.02, -0.20, 0.8)
    # fault onset: ey jumps > drift bound in one cycle, heading spikes
    assert est._temporal_heading_gate(0.09, -0.90, 0.8) == -0.90


def test_t3_does_not_cap_on_a_straight():
    """No real curvature -> no geometric over-read to attribute; pass through
    so a true heading fault on a straight keeps full sensitivity."""
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**_T3))
    out = [est._temporal_heading_gate(0.02, -0.44, 0.05) for _ in range(5)]
    assert all(v == -0.44 for v in out)


def test_t3_reset_clears_window():
    """reset() drops the confirmation history so a new episode starts at full
    sensitivity (no cap until the window refills)."""
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**_T3))
    for _ in range(4):
        est._temporal_heading_gate(0.03, -0.44, 0.8)
    assert est._temporal_heading_gate(0.03, -0.44, 0.8) == pytest.approx(-0.32)
    est.reset()
    # first post-reset frame: window not full again -> pass-through
    assert est._temporal_heading_gate(0.03, -0.44, 0.8) == -0.44


# --------------------------------------------------------------------------
# Pure-pursuit controller (cobraflex_rl.cv_lane_controller). Shares this file's
# synthetic-frame fixtures; verifies the look-ahead law turns the right way and
# by the right amount where the PD law under-steered (the curve regression).
# --------------------------------------------------------------------------
from cobraflex_rl.cv_lane_controller import CVLaneController  # noqa: E402


def test_controller_centred_straight_goes_straight(cam):
    ctrl = CVLaneController(speed=0.2)
    angular, detected = ctrl.compute(render_lane(cam, centered_lane()))
    assert detected
    assert abs(angular) < 0.03


def test_controller_offset_steers_back_to_centre(cam):
    ctrl = CVLaneController(speed=0.2)
    # Car to the LEFT of centre (ey>0) on a straight ⇒ steer right (negative).
    ang_left, _ = ctrl.compute(render_lane(cam, centered_lane(ey=0.08)))
    assert ang_left < -0.02
    # Mirror.
    ang_right, _ = ctrl.compute(render_lane(cam, centered_lane(ey=-0.08)))
    assert ang_right > 0.02


def test_controller_follows_curve_with_feedforward(cam):
    """On a centred curve the law must command ≈ v·κ in the bend direction —
    the turn the PD+curvature law lost on tight arcs (cv_ctrl_eval regression).
    angular = v·κ within tolerance, correct sign, never under-steering to ~0."""
    v = 0.2
    for kappa in (0.6, 1.25):
        ctrl = CVLaneController(speed=v)
        angular, detected = ctrl.compute(render_lane(cam, centered_lane(kappa=kappa)))
        assert detected
        assert angular > 0.05, f"kappa={kappa}: under-steer angular={angular:.3f}"
        # Pure pursuit ≈ v·κ near the vehicle; allow generous tolerance.
        assert abs(angular - v * kappa) < 0.5 * v * kappa + 0.05, \
            f"kappa={kappa}: angular={angular:.3f} vs v*k={v*kappa:.3f}"
    # Right bend ⇒ negative command.
    ctrl = CVLaneController(speed=v)
    ang_r, _ = ctrl.compute(render_lane(cam, centered_lane(kappa=-1.0)))
    assert ang_r < -0.05


def test_controller_no_lane_returns_zero(cam):
    ctrl = CVLaneController(speed=0.2)
    blank = np.full((cam.height_px, cam.width_px, 3), ROAD_GRAY, dtype=np.uint8)
    angular, detected = ctrl.compute(blank)
    assert not detected
    assert angular == 0.0


def test_controller_accepts_legacy_gain_kwargs(cam):
    # The deployment node still passes kp_ey/kd_epsi/kff_curv; must not raise.
    ctrl = CVLaneController(speed=0.2, kp_ey=6.0, kd_epsi=1.6, kff_curv=1.0,
                           max_angular_z=0.9)
    angular, detected = ctrl.compute(render_lane(cam, centered_lane(kappa=0.6)))
    assert detected and angular > 0.05


def _three_line_offcenter(ey: float = 0.14):
    """Vehicle at +``ey`` m left of its lane centre — *past its own left line*
    (ey > LANE_W/2), with the next-left lane's line also in view: the geometry
    that produced the SC-EDGE-02 H-12 under-read (D-48). Three lines: the own
    lane's right/left pair (centre −ey) plus a third line a further lane-width to
    the left, which forms a competing plausible pair whose centre is
    opposite-signed and *nearer* the vehicle, so the legacy nearest-centre rule
    locks onto it and reports the vehicle as centred in the wrong lane."""
    centre = -ey
    return (
        lambda x: centre - LANE_W / 2.0,        # own right line
        lambda x: centre + LANE_W / 2.0,        # own left line
        lambda x: centre + 3.0 * LANE_W / 2.0,  # next-left lane's line
    )


def test_offcenter_conservative_picks_own_lane_not_neighbour(cam):
    """Conservative selection (D-48, opt-in: default OFF after the closed-loop
    regression) reports the true large offset rather than locking onto the centred
    neighbour pair on a straight off-centre frame. This is the narrow case the rule
    handles; it is disabled in production because it mis-fires on heading-skewed
    centred/curve views (see CvLaneEstimatorConfig.conservative_lane_selection)."""
    img = render_lane(cam, _three_line_offcenter(ey=0.14))
    est = CvLaneEstimator(
        cam, CvLaneEstimatorConfig(conservative_lane_selection=True)
    ).estimate(img)
    assert est.ok, est.reason
    assert est.n_lines >= 3
    # true offset is +0.14 m (left of own lane centre, past the own left line);
    # must keep the correct sign and not under-read to the neighbour lane.
    assert est.ey > 0.10, f"under-read: ey={est.ey:.3f}"
    assert est.ey == pytest.approx(0.14, abs=0.04), f"ey={est.ey:.3f}"


def test_offcenter_legacy_rule_mislocks_to_neighbour(cam):
    """With conservative selection disabled, the legacy nearest-centre rule
    mis-locks onto the neighbour pair and reports the wrong sign — the bug D-48
    fixes (guards against regression / documents the contrast)."""
    legacy = CvLaneEstimator(
        cam, CvLaneEstimatorConfig(conservative_lane_selection=False)
    )
    est = legacy.estimate(render_lane(cam, _three_line_offcenter(ey=0.14)))
    assert est.ok, est.reason
    assert est.ey < 0.0, f"legacy should mis-lock to the wrong sign, got {est.ey:.3f}"


def test_heading_bias_inert_by_default(cam):
    # heading_bias_rad defaults to 0.0 → every Gazebo estimate is bit-identical.
    base = CvLaneEstimator(cam)
    biased_zero = CvLaneEstimator(cam, config=CvLaneEstimatorConfig(heading_bias_rad=0.0))
    img = render_lane(cam, centered_lane(yaw=0.12))
    assert base.estimate(img).epsi == pytest.approx(biased_zero.estimate(img).epsi)


def test_heading_bias_shifts_epsi_by_the_calibration(cam):
    # A straight, centred lane reads epsi ≈ 0; applying heading_bias_rad=b must
    # shift the reported epsi by exactly +b (epsi = -(heading - b)). This is the
    # D-57 Isaac renderer de-bias: it cancels a systematic heading offset.
    b = 0.084
    est0 = CvLaneEstimator(cam, config=CvLaneEstimatorConfig())
    estb = CvLaneEstimator(cam, config=CvLaneEstimatorConfig(heading_bias_rad=b))
    img = render_lane(cam, centered_lane(yaw=0.0))
    assert estb.estimate(img).epsi == pytest.approx(est0.estimate(img).epsi + b, abs=1e-6)
