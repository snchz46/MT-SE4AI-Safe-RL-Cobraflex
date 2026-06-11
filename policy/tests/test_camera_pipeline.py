"""
Unit tests for cobraflex_rl.camera_pipeline — the shared track-'E' frame path
(decode → single degradation point → cage CV frame + policy observation; D-43).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.camera_pipeline import (  # noqa: E402
    FRAME_STACK,
    OBS_HEIGHT,
    OBS_WIDTH,
    CameraPipeline,
    decode_image,
    to_observation,
)
from cobraflex_rl.visual_degradation import GLARE, degrade  # noqa: E402


def _frame(seed=0, h=48, w=64):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


# ----------------------------------------------------------------- constants
def test_e_design_constants():
    # docs/09 §10 fixed values: 84×84 grayscale, stack k=4.
    assert (OBS_WIDTH, OBS_HEIGHT, FRAME_STACK) == (84, 84, 4)


# -------------------------------------------------------------------- decode
def test_decode_rgb8_to_bgr():
    rgb = _frame(1)
    out = decode_image(rgb.tobytes(), 48, 64, "rgb8")
    np.testing.assert_array_equal(out, rgb[:, :, ::-1])


def test_decode_bgr8_passthrough():
    bgr = _frame(2)
    out = decode_image(bgr.tobytes(), 48, 64, "bgr8")
    np.testing.assert_array_equal(out, bgr)


def test_decode_mono8_replicates():
    gray = np.random.default_rng(3).integers(0, 255, size=(48, 64), dtype=np.uint8)
    out = decode_image(gray.tobytes(), 48, 64, "mono8")
    assert out.shape == (48, 64, 3)
    np.testing.assert_array_equal(out[:, :, 0], gray)
    np.testing.assert_array_equal(out[:, :, 1], gray)


def test_decode_respects_row_stride():
    bgr = _frame(4)
    padded = np.concatenate(
        [bgr.reshape(48, -1), np.zeros((48, 8), dtype=np.uint8)], axis=1
    )
    out = decode_image(padded.tobytes(), 48, 64, "bgr8", step=64 * 3 + 8)
    np.testing.assert_array_equal(out, bgr)


def test_decode_rejects_unknown_encoding():
    with pytest.raises(ValueError):
        decode_image(b"\x00" * 10, 1, 1, "yuv422")


def test_decode_rejects_short_buffer():
    with pytest.raises(ValueError):
        decode_image(b"\x00" * 10, 48, 64, "bgr8")


# --------------------------------------------------------------- observation
def test_observation_shape_dtype():
    obs = to_observation(_frame())
    assert obs.shape == (OBS_HEIGHT, OBS_WIDTH, 1)
    assert obs.dtype == np.uint8


def test_observation_rgb_kept_when_not_grayscale():
    obs = to_observation(_frame(), grayscale=False)
    assert obs.shape == (OBS_HEIGHT, OBS_WIDTH, 3)


# ------------------------------------------------------------------ pipeline
def test_clean_pipeline_passthrough():
    frame = _frame(5)
    pipe = CameraPipeline()
    consumer, obs = pipe.process(frame)
    np.testing.assert_array_equal(consumer, frame)
    assert obs.shape == (OBS_HEIGHT, OBS_WIDTH, 1)


def test_degradation_applied_before_both_consumers():
    # D-43 common cause: the injected degradation must show in the cage's
    # frame AND the policy obs, identically derived from one degraded frame.
    frame = _frame(6)
    pipe = CameraPipeline(injector=lambda f: degrade(f, GLARE, 1.0))
    consumer, obs = pipe.process(frame)
    np.testing.assert_array_equal(consumer, degrade(frame, GLARE, 1.0))
    clean_obs = CameraPipeline().process(frame)[1]
    assert obs.mean() > clean_obs.mean()  # glare brightens the obs too
    np.testing.assert_array_equal(obs, to_observation(consumer))


def test_injector_swap_per_episode():
    frame = _frame(7)
    pipe = CameraPipeline(injector=lambda f: degrade(f, GLARE, 1.0))
    pipe.set_injector(None)
    consumer, _ = pipe.process(frame)
    np.testing.assert_array_equal(consumer, frame)
