"""
Unit tests for cobraflex_rl.visual_domain_randomization — the track-'E' per-episode
visual-degradation sampler (training-side mitigation of H-10 / SR-012; D-41/D-42).

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


def test_low_contrast_is_trainable_but_eval_stressors_are_not():
    """The sim-to-real photometry mode may be drawn during training; occlusion and
    false-lane still may not (they would teach the policy to ignore the cues whose
    loss must trigger the SR-013/SR-014 stop)."""
    from cobraflex_rl.visual_degradation import LOW_CONTRAST, MODES

    cfg = DomainRandomizationConfig(modes=MODES + (LOW_CONTRAST,))
    assert LOW_CONTRAST in cfg.modes
    for blocked in ("occlusion", "false_lane"):
        with pytest.raises(ValueError):
            DomainRandomizationConfig(modes=(blocked,))


# ---------------------------------------------------------------------------
# operating-point (base) term — sim-to-real photometry, M-7/D-71
# ---------------------------------------------------------------------------
def _old_algorithm(cfg, rng, n):
    """The pre-19.08 sampler, transcribed. Pins the RNG stream so a config
    without a base term keeps drawing exactly what it used to draw."""
    out = []
    for _ in range(n):
        if rng.random() >= cfg.p_degrade:
            out.append((None, 0.0))
            continue
        mode = cfg.modes[int(rng.integers(0, len(cfg.modes)))]
        lo, hi = cfg.level_range
        out.append((mode, float(rng.uniform(lo, hi))))
    return out


def test_without_a_base_term_the_rng_stream_is_bit_identical():
    """The backwards-compatibility guarantee that lets every pre-19.08 training
    run stay reproducible from its seed: with no base term configured, the
    sampler must consume the generator exactly as it did before the term
    existed. Short-circuit evaluation is what buys this, so it is worth pinning."""
    cfg = DomainRandomizationConfig()
    assert cfg.base_mode is None
    randomizer = VisualDomainRandomizer(cfg)
    rng_new, rng_old = np.random.default_rng(7), np.random.default_rng(7)
    drawn = [randomizer.sample(rng_new) for _ in range(60)]
    expected = _old_algorithm(cfg, rng_old, 60)

    assert [(s.mode, s.level) for s in drawn] == expected
    assert all(s.base_mode is None and s.base_level == 0.0 for s in drawn)
    # same values AND the same number of them: both generators must be left at
    # the same position, or a later consumer of the stream would diverge.
    assert rng_new.random() == rng_old.random()


def test_base_term_is_drawn_every_episode_while_stressors_keep_their_rate():
    from cobraflex_rl.visual_degradation import LOW_CONTRAST

    cfg = DomainRandomizationConfig(base_mode=LOW_CONTRAST, p_base=1.0, p_degrade=0.5)
    r = VisualDomainRandomizer(cfg)
    rng = np.random.default_rng(11)
    specs = [r.sample(rng) for _ in range(400)]
    assert all(s.base_mode == LOW_CONTRAST for s in specs)
    assert all(0.0 <= s.base_level <= 1.0 for s in specs)
    stressed = sum(s.mode is not None for s in specs)
    assert 0.4 < stressed / len(specs) < 0.6      # p_degrade untouched by the base term
    # the operating point must sweep its whole range, not sit at one value
    levels = np.array([s.base_level for s in specs])
    assert levels.min() < 0.1 and levels.max() > 0.9


def test_a_base_only_spec_is_not_clean_and_is_applied():
    from cobraflex_rl.visual_degradation import LOW_CONTRAST, apply_low_contrast

    spec = DegradationSpec(mode=None, level=0.0, base_mode=LOW_CONTRAST, base_level=0.75)
    assert not spec.is_clean          # the env must still install an injector
    img = np.full((16, 16), 27, dtype=np.uint8)
    out = VisualDomainRandomizer().apply(img, spec)
    np.testing.assert_array_equal(out, apply_low_contrast(img, 0.75))


def test_operating_point_is_applied_before_the_stressor():
    """Order is physical: the camera sees a mid-grey floor and *then* glare
    happens to that image, not the reverse."""
    from cobraflex_rl.visual_degradation import (
        GLARE, LOW_CONTRAST, apply_glare, apply_low_contrast,
    )

    img = np.linspace(0, 255, 16 * 16, dtype=np.float64).reshape(16, 16).astype(np.uint8)
    spec = DegradationSpec(mode=GLARE, level=0.4, base_mode=LOW_CONTRAST, base_level=0.6)
    out = VisualDomainRandomizer().apply(img, spec)
    np.testing.assert_array_equal(out, apply_glare(apply_low_contrast(img, 0.6), 0.4))
    assert not np.array_equal(out, apply_low_contrast(apply_glare(img, 0.4), 0.6))


def test_base_mode_is_validated_against_the_trainable_set():
    with pytest.raises(ValueError):
        DomainRandomizationConfig(base_mode="occlusion")
    with pytest.raises(ValueError):
        DomainRandomizationConfig(base_mode="sepia")
    with pytest.raises(ValueError):
        DomainRandomizationConfig(base_mode="low_contrast", p_base=1.5)
