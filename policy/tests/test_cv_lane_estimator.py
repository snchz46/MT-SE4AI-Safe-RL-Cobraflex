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
