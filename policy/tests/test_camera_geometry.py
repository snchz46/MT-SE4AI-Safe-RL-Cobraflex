"""Unit tests for cobraflex_rl.camera_geometry (track 'E', D-43).

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
    # camera_link_lane mount (IMX219-160 mirror): 5 cm below the body-front
    # reference, 640x360 @ 90 deg hfov per lane_keeper_node.py proc stream.
    assert cam.height_m == pytest.approx(0.07725)
    assert cam.pitch_rad == pytest.approx(0.30)
    assert cam.hfov_rad == pytest.approx(1.5707963)
    assert cam.width_px == 640 and cam.height_px == 360


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


# ---------------------------------------------------------------------------
# rectification of the measured physical camera into the canonical model
# (M-6/M-7, D-71)
# ---------------------------------------------------------------------------
_M6 = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "experiments" / "calibration" / "M6_results.json"
)


@pytest.fixture(scope="module")
def maps():
    from cobraflex_rl.camera_geometry import rectification_maps_from_calibration

    return rectification_maps_from_calibration(_M6)


def test_rectification_maps_cover_the_canonical_frame(maps, cam):
    map_x, map_y = maps
    assert map_x.shape == (cam.height_px, cam.width_px)
    assert map_y.shape == (cam.height_px, cam.width_px)


def test_rectification_actually_undistorts(maps, cam):
    """A pure intrinsics swap would leave the map affine in u. Barrel distortion
    is what makes it curve, and it is the whole reason C-01 fires late."""
    import numpy as np

    map_x, _ = maps
    row = map_x[int(cam.cy)]
    # second difference along a row is ~0 for any affine map, non-zero here
    assert np.abs(np.diff(row, n=2)).max() > 1e-3


def test_rectified_pixel_traces_back_to_the_measured_camera(maps, cam):
    """The load-bearing invariant: the ray a canonical pixel represents must be
    fetched from wherever the *measured* camera actually put it. Checked against
    an independent forward projection through the M-6 intrinsics + distortion."""
    import json

    import cv2
    import numpy as np

    m6 = json.loads(_M6.read_text())
    k_measured = np.array(
        [[m6["fx_px"], 0.0, m6["cx_px"]],
         [0.0, m6["fy_px"], m6["cy_px"]],
         [0.0, 0.0, 1.0]], dtype=float,
    )
    dist = np.asarray(m6["distortion_plumb_bob"], dtype=float)
    map_x, map_y = maps

    for u, v in ((320, 200), (120, 300), (520, 250), (320, 120)):
        # the ray this canonical pixel stands for
        ray = np.array(
            [[(u - cam.cx) / cam.fx, (v - cam.cy) / cam.fy, 1.0]], dtype=float
        )
        expected, _ = cv2.projectPoints(
            ray, np.zeros(3), np.zeros(3), k_measured, dist
        )
        eu, ev = expected.ravel()
        assert map_x[v, u] == pytest.approx(eu, abs=0.5)
        assert map_y[v, u] == pytest.approx(ev, abs=0.5)


def test_rectification_rejects_a_resolution_mismatch():
    from cobraflex_rl.camera_geometry import rectification_maps_from_calibration

    with pytest.raises(ValueError, match="intrinsics do not apply"):
        rectification_maps_from_calibration(
            _M6, CameraModel(width_px=1280, height_px=720)
        )
