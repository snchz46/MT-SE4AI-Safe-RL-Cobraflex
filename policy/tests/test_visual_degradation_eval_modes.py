"""
Unit tests for the eval-only degradation modes of cobraflex_rl.visual_degradation:
occlusion (SC-PERT-07, H-11) and false_lane (SC-PERT-08, H-12), added for the
track-'E' camera pipeline under D-43 (the degraded frame reaches both the policy
CNN and the cage's CV lane-estimator).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.visual_degradation import (  # noqa: E402
    ALL_MODES,
    EVAL_ONLY_MODES,
    FALSE_LANE,
    MODES,
    OCCLUSION,
    apply_false_lane,
    apply_occlusion,
    degrade,
)


def _img(seed: int = 0, shape=(40, 60, 3)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 90, size=shape, dtype=np.uint8)


def test_mode_partition():
    # The DR training envelope (MODES) must stay the H-10 trio; the eval-only
    # stressors live beside it, and degrade() dispatches all of them.
    assert OCCLUSION not in MODES and FALSE_LANE not in MODES
    assert set(EVAL_ONLY_MODES) == {OCCLUSION, FALSE_LANE}
    assert set(ALL_MODES) == set(MODES) | set(EVAL_ONLY_MODES)


@pytest.mark.parametrize("mode", EVAL_ONLY_MODES)
def test_level_zero_is_identity(mode):
    img = _img()
    np.testing.assert_array_equal(degrade(img, mode, 0.0), img)


@pytest.mark.parametrize("mode", EVAL_ONLY_MODES)
def test_determinism(mode):
    img = _img(3)
    np.testing.assert_array_equal(degrade(img, mode, 0.6), degrade(img, mode, 0.6))


def test_occlusion_covers_bottom_rows():
    img = _img(1)
    out = apply_occlusion(img, 0.5, fill_value=25, max_height_frac=0.75)
    h = img.shape[0]
    covered = int(round(h * 0.5 * 0.75))
    assert (out[h - covered:, :, :] == 25).all()
    np.testing.assert_array_equal(out[: h - covered], img[: h - covered])


def test_occlusion_grows_with_level():
    img = _img(1)
    n_changed = [
        int((apply_occlusion(img, lv) != img).any(axis=2).sum())
        for lv in (0.2, 0.5, 1.0)
    ]
    assert n_changed[0] < n_changed[1] < n_changed[2]


def test_false_lane_paints_bright_lower_half_only():
    img = _img(2)
    out = apply_false_lane(img, 1.0, brightness=235)
    h = img.shape[0]
    changed = (out != img).any(axis=2)
    assert not changed[: h // 2].any()  # upper half untouched
    assert changed[h // 2:].any()
    assert out[changed].min() >= 200  # painted pixels are bright (lane-like)


def test_false_lane_opacity_scales_with_level():
    img = _img(2)
    faint = apply_false_lane(img, 0.3)
    strong = apply_false_lane(img, 1.0)
    changed = (strong != img).any(axis=2)
    assert strong[changed].mean() > faint[changed].mean()


def test_false_lane_grayscale_supported():
    img = _img(4, shape=(40, 60))
    out = apply_false_lane(img, 0.8)
    assert out.shape == img.shape
    assert (out != img).any()


def test_occlusion_grayscale_supported():
    img = _img(4, shape=(40, 60))
    out = apply_occlusion(img, 0.6)
    assert (out[-5:] == 25).all()
