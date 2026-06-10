"""Unit tests for cobraflex_rl.camera_geometry (track 'E', D-40).

The pitch-only ground-plane mapping is closed-form; these tests pin the
analytic invariants the CV lane-estimator relies on.
"""
import math

import pytest

from cobraflex_rl.camera_geometry import (
    CameraModel,
    DEFAULT_CAMERA_HEIGHT_M,
    DEFAULT_CAMERA_PITCH_RAD,
)


@pytest.fixture(scope="module")
def cam():
    return CameraModel()


def test_defaults_mirror_urdf(cam):
    assert cam.height_m == pytest.approx(0.13725)
    assert cam.pitch_rad == pytest.approx(0.25)
    assert cam.width_px == 640 and cam.height_px == 480


def test_optical_axis_hits_expected_distance(cam):
    # The image centre row looks along the pitched optical axis:
    # ground distance = h / tan(pitch).
    x = cam.row_to_distance(cam.cy)
    assert x == pytest.approx(
        DEFAULT_CAMERA_HEIGHT_M / math.tan(DEFAULT_CAMERA_PITCH_RAD), rel=1e-9
    )


def test_horizon_row_above_centre(cam):
    # Pitch-down puts the horizon above the image centre row.
    assert cam.horizon_row < cam.cy
    with pytest.raises(ValueError):
        cam.row_to_distance(cam.horizon_row - 1.0)


def test_row_distance_roundtrip(cam):
    for x in (0.15, 0.3, 0.6, 1.2):
        v = cam.distance_to_row(x)
        assert cam.row_to_distance(v) == pytest.approx(x, rel=1e-9)


def test_pixel_ground_roundtrip(cam):
    for x, y in ((0.3, 0.0), (0.5, 0.12), (0.9, -0.2), (1.2, 0.26)):
        u, v = cam.ground_to_pixel(x, y)
        x2, y2 = cam.pixel_to_ground(u, v)
        assert x2 == pytest.approx(x, rel=1e-9)
        assert y2 == pytest.approx(y, rel=1e-9)


def test_centre_column_is_straight_ahead(cam):
    u, _ = cam.ground_to_pixel(0.7, 0.0)
    assert u == pytest.approx(cam.cx)


def test_left_is_lower_u(cam):
    # +Y (left) must land left of the image centre (smaller u).
    u_left, _ = cam.ground_to_pixel(0.5, 0.1)
    u_right, _ = cam.ground_to_pixel(0.5, -0.1)
    assert u_left < cam.cx < u_right


def test_row_distance_monotone(cam):
    # Lower rows (larger v) see nearer ground.
    v_near = cam.distance_to_row(0.2)
    v_far = cam.distance_to_row(1.0)
    assert v_near > v_far


def test_lateral_resolution_grows_with_distance(cam):
    v_near = cam.distance_to_row(0.2)
    v_far = cam.distance_to_row(1.0)
    assert cam.lateral_resolution(v_far) > cam.lateral_resolution(v_near)


def test_validation():
    with pytest.raises(ValueError):
        CameraModel(height_m=0.0)
    with pytest.raises(ValueError):
        CameraModel(hfov_rad=4.0)
    cam = CameraModel()
    with pytest.raises(ValueError):
        cam.ground_to_pixel(-0.1, 0.0)
