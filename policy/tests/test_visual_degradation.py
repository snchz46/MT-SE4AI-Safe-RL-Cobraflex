"""
Unit tests for cobraflex_rl.visual_degradation — the track-'E' front-camera
visual-degradation primitives (D-41/D-42; H-10, SR-012, SC-PERT-04..06).

Pure numpy, host-testable: the module degrades the *observation* only, never the
cage's independent ground-truth state. ``cobraflex_rl/__init__`` is lazy (no rclpy),
so the submodule imports without the ROS toolchain (same pattern as test_rewards.py).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.visual_degradation import (  # noqa: E402
    GLARE,
    LOW_LIGHT,
    MOTION_BLUR,
    MODES,
    apply_glare,
    apply_motion_blur,
    degrade,
)


def _img(seed: int = 0, shape=(20, 20, 3)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=shape, dtype=np.uint8)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("shape", [(16, 16), (16, 16, 3)])
def test_shape_and_dtype_preserved(mode, shape):
    img = _img(1, shape)
    out = degrade(img, mode, 0.5)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


@pytest.mark.parametrize("mode", MODES)
def test_level_zero_is_identity(mode):
    img = _img(2)
    np.testing.assert_array_equal(degrade(img, mode, 0.0), img)


def test_glare_brightens():
    img = _img(3)
    assert degrade(img, GLARE, 1.0).mean() > img.mean()


def test_low_light_darkens():
    img = _img(4)
    assert degrade(img, LOW_LIGHT, 1.0).mean() < img.mean()


def test_motion_blur_smooths_a_vertical_edge():
    # A vertical edge (left half black, right half white): horizontal motion blur
    # must soften the column step, lowering the max adjacent-column difference.
    img = np.zeros((10, 20), dtype=np.uint8)
    img[:, 10:] = 255
    blurred = degrade(img, MOTION_BLUR, 1.0)
    sharp = int(np.abs(np.diff(img.astype(int), axis=1)).max())
    soft = int(np.abs(np.diff(blurred.astype(int), axis=1)).max())
    assert soft < sharp


@pytest.mark.parametrize("mode", MODES)
def test_determinism(mode):
    img = _img(5)
    np.testing.assert_array_equal(degrade(img, mode, 0.7), degrade(img, mode, 0.7))


@pytest.mark.parametrize("level", [0.25, 0.5, 1.0])
def test_glare_monotonic_in_level(level):
    # Brighter for larger level (until saturation): mean is non-decreasing in level.
    img = _img(6)
    assert degrade(img, GLARE, level).mean() >= img.mean()


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        degrade(_img(), "sepia", 0.5)


def test_invalid_level_raises():
    with pytest.raises(ValueError):
        apply_glare(_img(), 1.5)


def test_non_uint8_raises():
    with pytest.raises(ValueError):
        apply_motion_blur(np.zeros((4, 4), dtype=np.float32), 0.5)
