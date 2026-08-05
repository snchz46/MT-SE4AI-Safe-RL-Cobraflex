"""Host-side unit tests for the pure logic of csi_camera_node (Phase-5 deploy).

The GStreamer capture needs the Jetson; these tests cover the parts that must be
provably correct before any bring-up, because a silent error in either would
mis-scale every metric estimate the cage acts on:

* the capture → 640x360 frame preparation (the trained native geometry), and
* the CameraInfo intrinsics, which must be derived from the very CameraModel the
  cage's IPM uses, not restated independently.
"""
import math

import numpy as np
import pytest

from cobraflex_rl.camera_geometry import (
    DEFAULT_HEIGHT_PX,
    DEFAULT_HFOV_RAD,
    DEFAULT_WIDTH_PX,
    CameraModel,
)
from cobraflex_rl.camera_pipeline import OBS_HEIGHT, OBS_WIDTH, to_observation
from cobraflex_rl.csi_camera_node import (
    DEFAULT_CAPTURE_HEIGHT,
    DEFAULT_CAPTURE_WIDTH,
    camera_info_matrices,
    gstreamer_pipeline,
    prepare_frame,
)


def _capture_frame():
    """A stand-in for one CSI capture frame (1280x720 BGR)."""
    rng = np.random.default_rng(2024)
    return rng.integers(
        0, 256, (DEFAULT_CAPTURE_HEIGHT, DEFAULT_CAPTURE_WIDTH, 3), dtype=np.uint8
    )


def test_prepare_frame_outputs_the_trained_native_geometry():
    out = prepare_frame(_capture_frame())
    assert out.shape == (DEFAULT_HEIGHT_PX, DEFAULT_WIDTH_PX, 3)
    assert out.dtype == np.uint8
    assert out.flags["C_CONTIGUOUS"]


def test_prepare_frame_preserves_aspect_ratio_so_hfov_is_unchanged():
    # 1280x720 and 640x360 are both 16:9: the resize cannot crop, so the 90 deg
    # HFOV the IPM assumes survives the downsample.
    cap_aspect = DEFAULT_CAPTURE_WIDTH / DEFAULT_CAPTURE_HEIGHT
    out_aspect = DEFAULT_WIDTH_PX / DEFAULT_HEIGHT_PX
    assert cap_aspect == pytest.approx(out_aspect)


def test_prepare_frame_is_a_noop_when_already_at_target_size():
    frame = np.zeros((DEFAULT_HEIGHT_PX, DEFAULT_WIDTH_PX, 3), dtype=np.uint8)
    frame[10, 20] = (1, 2, 3)
    out = prepare_frame(frame)
    assert np.array_equal(out, frame)


def test_prepare_frame_rejects_non_bgr_input():
    with pytest.raises(ValueError):
        prepare_frame(np.zeros((720, 1280), dtype=np.uint8))


def test_prepared_frame_feeds_the_trained_observation_shape():
    # The published frame must be exactly what to_observation was trained on.
    obs = to_observation(prepare_frame(_capture_frame()), grayscale=True)
    assert obs.shape == (OBS_HEIGHT, OBS_WIDTH, 1)
    assert obs.dtype == np.uint8


def test_camera_info_matrices_come_from_the_cage_camera_model():
    model = CameraModel()
    k, p = camera_info_matrices(model)
    assert len(k) == 9 and len(p) == 12
    # fx/fy/cx/cy must be the model's, not an independent restatement.
    assert k[0] == pytest.approx(model.fx)
    assert k[4] == pytest.approx(model.fy)
    assert k[2] == pytest.approx(model.cx)
    assert k[5] == pytest.approx(model.cy)
    assert k[8] == pytest.approx(1.0)
    # P is K with a zero translation column (monocular).
    assert p[0] == pytest.approx(model.fx)
    assert p[3] == pytest.approx(0.0)
    assert p[7] == pytest.approx(0.0)


def test_camera_info_fx_matches_the_declared_hfov():
    # The single number the whole metric IPM hangs on: fx = (w/2)/tan(hfov/2).
    model = CameraModel()
    k, _ = camera_info_matrices(model)
    expected = (DEFAULT_WIDTH_PX / 2.0) / math.tan(DEFAULT_HFOV_RAD / 2.0)
    assert k[0] == pytest.approx(expected)


def test_gstreamer_pipeline_matches_the_proven_lane_keeper_pipeline():
    # Byte-identical to cobraflex.lane_keeper_node._gstreamer_pipeline for the
    # same arguments: the CNN must not see a different capture path than the one
    # this camera was proven on. `cobraflex` is an ament_python package, so it is
    # only importable once the colcon workspace is built — skip rather than fail
    # the suite on a bare checkout.
    lane_keeper = pytest.importorskip(
        "cobraflex.lane_keeper_node",
        reason="cobraflex needs a colcon build to be importable",
    )
    reference = lane_keeper._gstreamer_pipeline

    for kwargs in (
        {},
        {"sensor_id": 1, "flip_method": 2},
        {"width": 640, "height": 360, "fps": 30},
    ):
        assert gstreamer_pipeline(**kwargs) == reference(**kwargs)


def test_capture_throttle_only_inserts_videorate_before_the_cpu_convert():
    # The throttle must drop frames BEFORE videoconvert (that is the whole point
    # — the CPU conversion is what it saves) and must leave every other element,
    # including the INTER_AREA-fed appsink, exactly as proven.
    plain = gstreamer_pipeline()
    throttled = gstreamer_pipeline(throttle_fps=30)
    assert "videorate" not in plain
    assert "videorate drop-only=true" in throttled
    assert throttled.index("videorate") < throttled.index("videoconvert")
    assert "framerate=(fraction)30/1 ! videoconvert" in throttled
    # Removing the inserted segment reproduces the proven pipeline byte for byte.
    assert throttled.replace(
        "videorate drop-only=true ! video/x-raw, framerate=(fraction)30/1 ! ", ""
    ) == plain
    # 0 and negative are both "no throttle element".
    assert gstreamer_pipeline(throttle_fps=0) == plain
