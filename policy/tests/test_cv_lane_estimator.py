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
