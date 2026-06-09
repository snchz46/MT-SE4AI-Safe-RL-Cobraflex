"""
Unit tests for cobraflex_rl.visual_domain_randomization — the track-'E' per-episode
visual-degradation sampler (training-side mitigation of H-10 / SR-012; D-38/D-39).

Pure logic over a numpy Generator, host-testable. ``cobraflex_rl/__init__`` is lazy
(no rclpy), so the submodule imports without the ROS toolchain.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.visual_degradation import MODES  # noqa: E402
from cobraflex_rl.visual_domain_randomization import (  # noqa: E402
    DegradationSpec,
    DomainRandomizationConfig,
    VisualDomainRandomizer,
)


def _img(seed: int = 0):
    return np.random.default_rng(seed).integers(0, 256, size=(16, 16, 3), dtype=np.uint8)


def test_sampling_is_deterministic_per_seed():
    r = VisualDomainRandomizer()
    a = [r.sample(np.random.default_rng(7)) for _ in range(1)]
    b = [r.sample(np.random.default_rng(7)) for _ in range(1)]
    assert a == b


def test_p_degrade_zero_is_always_clean():
    r = VisualDomainRandomizer(DomainRandomizationConfig(p_degrade=0.0))
    rng = np.random.default_rng(0)
    assert all(r.sample(rng).is_clean for _ in range(50))


def test_p_degrade_one_is_never_clean():
    r = VisualDomainRandomizer(DomainRandomizationConfig(p_degrade=1.0))
    rng = np.random.default_rng(0)
    assert all(not r.sample(rng).is_clean for _ in range(50))


def test_sampled_mode_and_level_within_config():
    cfg = DomainRandomizationConfig(p_degrade=1.0, modes=(MODES[0], MODES[2]), level_range=(0.3, 0.8))
    r = VisualDomainRandomizer(cfg)
    rng = np.random.default_rng(1)
    for _ in range(200):
        spec = r.sample(rng)
        assert spec.mode in cfg.modes
        assert 0.3 <= spec.level <= 0.8


def test_p_degrade_half_is_roughly_balanced():
    r = VisualDomainRandomizer(DomainRandomizationConfig(p_degrade=0.5))
    rng = np.random.default_rng(2)
    n = 2000
    degraded = sum(not r.sample(rng).is_clean for _ in range(n))
    assert 0.4 * n < degraded < 0.6 * n


def test_apply_clean_returns_unchanged_copy():
    r = VisualDomainRandomizer()
    img = _img(3)
    out = r.apply(img, DegradationSpec(mode=None, level=0.0))
    assert out is not img
    np.testing.assert_array_equal(out, img)


def test_apply_degraded_preserves_shape_and_dtype():
    r = VisualDomainRandomizer()
    img = _img(4)
    out = r.apply(img, DegradationSpec(mode=MODES[0], level=0.7))
    assert out.shape == img.shape and out.dtype == np.uint8


@pytest.mark.parametrize("kwargs", [
    {"p_degrade": 1.5},
    {"modes": ()},
    {"modes": ("sepia",)},
    {"level_range": (0.8, 0.2)},
    {"level_range": (-0.1, 0.5)},
])
def test_config_validation(kwargs):
    with pytest.raises(ValueError):
        DomainRandomizationConfig(**kwargs)
