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
    LOW_CONTRAST,
    LOW_LIGHT,
    MOTION_BLUR,
    MODES,
    TRAINABLE_MODES,
    apply_glare,
    apply_low_contrast,
    apply_motion_blur,
    degrade,
)


def _img(seed: int = 0, shape=(20, 20, 3)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=shape, dtype=np.uint8)


@pytest.mark.parametrize("mode", TRAINABLE_MODES)
@pytest.mark.parametrize("shape", [(16, 16), (16, 16, 3)])
def test_shape_and_dtype_preserved(mode, shape):
    img = _img(1, shape)
    out = degrade(img, mode, 0.5)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


@pytest.mark.parametrize("mode", TRAINABLE_MODES)
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


@pytest.mark.parametrize("mode", TRAINABLE_MODES)
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


# --------------------------------------------------------------------------
# low_contrast — the sim-to-real photometry mode (M-7/D-71)
# --------------------------------------------------------------------------
# Grey levels measured inside the estimator's scan band: Gazebo complex_b
# renders the road at 27 and the markings at 197; the physical lane circuit
# reads 106 and 209 over three independent sessions.
SIM_ROAD, SIM_LINE = 27, 197
REAL_ROAD, REAL_LINE = 106, 209


def _sim_like_frame() -> np.ndarray:
    """A frame with the Gazebo road/marking grey levels, nothing else."""
    img = np.full((32, 32), SIM_ROAD, dtype=np.uint8)
    img[:, 12:20] = SIM_LINE
    return img


def test_low_contrast_lifts_black_and_compresses_range():
    img = _sim_like_frame()
    out = apply_low_contrast(img, 1.0)
    assert out.min() > img.min(), "the pedestal must raise the road out of black"
    assert np.ptp(out) < np.ptp(img), "the dynamic range must compress"
    assert out.max() <= img.max() + 12, "markings must not be washed out (that is glare)"


def test_low_contrast_reaches_the_measured_physical_photometry():
    """The defaults must put the *measured* hall inside the sampling range, not
    at its edge: level 0.75 has to land on the physical track's grey levels."""
    out = apply_low_contrast(_sim_like_frame(), 0.75)
    road, line = int(out.min()), int(out.max())
    assert abs(road - REAL_ROAD) <= 15, f"road {road} vs measured {REAL_ROAD}"
    assert abs(line - REAL_LINE) <= 15, f"line {line} vs measured {REAL_LINE}"
    assert abs(line / road - REAL_LINE / REAL_ROAD) < 0.35, "contrast ratio off"


@pytest.mark.parametrize("level", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_low_contrast_never_blinds_the_cage_white_gate(level):
    """D-43 common cause: this same frame feeds the cage's CV estimator, whose
    white gate is V >= 150. No level may push the markings under it or the road
    over it — the DR must stress the policy, never silently blind the monitor."""
    out = apply_low_contrast(_sim_like_frame(), level)
    assert int(out.max()) >= 150, "markings fell under the D-43 white gate"
    assert int(out.min()) < 150, "road rose above the D-43 white gate"


def test_low_contrast_is_reachable_through_the_dispatcher():
    img = _sim_like_frame()
    np.testing.assert_array_equal(
        degrade(img, LOW_CONTRAST, 0.6), apply_low_contrast(img, 0.6)
    )


def test_frozen_h10_trio_is_unchanged():
    """MODES is what every past training run drew from; it must stay frozen so
    those runs remain reproducible."""
    assert MODES == (GLARE, LOW_LIGHT, MOTION_BLUR)
    assert LOW_CONTRAST in TRAINABLE_MODES and LOW_CONTRAST not in MODES
