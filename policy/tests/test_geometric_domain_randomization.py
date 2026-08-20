"""
Unit tests for cobraflex_rl.geometric_domain_randomization — the per-episode
camera-geometry sampler (sim-to-real, M-7/D-71).

Covers the sampler's contract (determinism, gating, RNG discipline, fail-fast on
a bad calibration path) and the two warps it applies: the ground-plane
homography for a mount-pose error, and the measured lens.

Pure numpy + cv2; ``cobraflex_rl/__init__`` is lazy so this imports without ROS.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
_PKG_PARENT = _REPO / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

cv2 = pytest.importorskip("cv2")

from cobraflex_rl.camera_geometry import (  # noqa: E402
    CameraModel,
    distortion_maps_to_calibration,
    ground_plane_homography,
)
from cobraflex_rl.geometric_domain_randomization import (  # noqa: E402
    GeometricDomainRandomizer,
    GeometricRandomizationConfig,
    GeometricSpec,
)

_CALIB = _REPO / "experiments" / "calibration" / "M6_results.json"


def _frame(seed: int = 0, shape=(360, 640, 3)):
    return np.random.default_rng(seed).integers(0, 256, size=shape, dtype=np.uint8)


# --- sampler contract -------------------------------------------------------


def test_disabled_is_identity_and_consumes_no_rng():
    """A config without this block must leave the generator exactly where it
    was, so every pre-existing run stays reproducible from its seed."""
    r = GeometricDomainRandomizer()
    rng = np.random.default_rng(3)
    before = rng.bit_generator.state
    specs = [r.sample(rng) for _ in range(100)]
    assert all(s.is_identity for s in specs)
    assert rng.bit_generator.state == before


def test_sampling_is_deterministic_per_seed():
    r = GeometricDomainRandomizer(GeometricRandomizationConfig(enabled=True))
    a = [r.sample(np.random.default_rng(11)) for _ in range(5)]
    b = [r.sample(np.random.default_rng(11)) for _ in range(5)]
    assert a == b


def test_pose_draws_stay_inside_the_configured_ranges():
    cfg = GeometricRandomizationConfig(
        enabled=True, pitch_delta_rad=(-0.026, 0.026), height_scale=(0.90, 1.10)
    )
    r = GeometricDomainRandomizer(cfg)
    rng = np.random.default_rng(0)
    specs = [r.sample(rng) for _ in range(2000)]
    assert all(-0.026 <= s.pitch_delta_rad <= 0.026 for s in specs)
    assert all(0.90 <= s.height_scale <= 1.10 for s in specs)


def test_p_pose_zero_never_perturbs():
    r = GeometricDomainRandomizer(
        GeometricRandomizationConfig(enabled=True, p_pose=0.0)
    )
    rng = np.random.default_rng(0)
    assert all(r.sample(rng).is_identity for _ in range(200))


def test_lens_share_matches_p_lens():
    r = GeometricDomainRandomizer(
        GeometricRandomizationConfig(
            enabled=True, p_lens=0.10, calibration_path=str(_CALIB)
        )
    )
    rng = np.random.default_rng(2024)
    share = np.mean([r.sample(rng).lens for _ in range(4000)])
    assert 0.08 < share < 0.12


def test_lens_and_pose_are_mutually_exclusive():
    """A frame is either 'the canonical camera mounted slightly wrong' or 'the
    real lens'; compounding them would model a mount error the rectifier has
    already removed."""
    r = GeometricDomainRandomizer(
        GeometricRandomizationConfig(
            enabled=True, p_lens=0.5, calibration_path=str(_CALIB)
        )
    )
    rng = np.random.default_rng(5)
    for _ in range(500):
        s = r.sample(rng)
        if s.lens:
            assert s.pitch_delta_rad == 0.0 and s.height_scale == 1.0


# --- configuration guards ---------------------------------------------------


def test_p_lens_without_calibration_is_rejected():
    with pytest.raises(ValueError, match="calibration_path"):
        GeometricRandomizationConfig(enabled=True, p_lens=0.1)


def test_bad_calibration_path_fails_at_construction_not_mid_run():
    """The maps are built lazily, but the path is checked eagerly: a typo must
    not surface six hours into a multi-day run."""
    with pytest.raises(FileNotFoundError, match="calibration_path"):
        GeometricDomainRandomizer(
            GeometricRandomizationConfig(
                enabled=True, p_lens=0.1, calibration_path="nope/M6_results.json"
            )
        )


def test_relative_calibration_path_resolves_against_the_repo():
    """A training YAML writes a repo-relative path; a ROS2 launch does not run
    from the repo root."""
    r = GeometricDomainRandomizer(
        GeometricRandomizationConfig(
            enabled=True,
            p_lens=0.1,
            calibration_path="experiments/calibration/M6_results.json",
        )
    )
    assert r._calibration == _CALIB.resolve()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"p_pose": 1.5},
        {"p_lens": -0.1, "calibration_path": "x"},
        {"pitch_delta_rad": (0.1, -0.1)},
        {"height_scale": (1.2, 0.8)},
        {"height_scale": (0.0, 1.0)},
    ],
)
def test_invalid_ranges_are_rejected(kwargs):
    with pytest.raises(ValueError):
        GeometricRandomizationConfig(enabled=True, **kwargs)


# --- warps ------------------------------------------------------------------


def test_identity_spec_returns_an_unchanged_copy():
    r = GeometricDomainRandomizer(GeometricRandomizationConfig(enabled=True))
    img = _frame()
    out = r.apply(img, GeometricSpec())
    assert np.array_equal(out, img)
    assert out is not img


def test_perturbed_camera_reflects_the_spec():
    base = CameraModel()
    r = GeometricDomainRandomizer(GeometricRandomizationConfig(enabled=True), base)
    cam = r.perturbed_camera(GeometricSpec(pitch_delta_rad=0.02, height_scale=1.05))
    assert cam.pitch_rad == pytest.approx(base.pitch_rad + 0.02)
    assert cam.height_m == pytest.approx(base.height_m * 1.05)
    # Intrinsics are the sensor's, not the mount's — they must not move.
    assert cam.hfov_rad == base.hfov_rad
    assert (cam.width_px, cam.height_px) == (base.width_px, base.height_px)


def test_pose_warp_changes_the_frame_and_is_deterministic():
    r = GeometricDomainRandomizer(GeometricRandomizationConfig(enabled=True))
    img = _frame(1)
    spec = GeometricSpec(pitch_delta_rad=0.02, height_scale=1.08)
    a, b = r.apply(img, spec), r.apply(img, spec)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, img)
    assert a.shape == img.shape and a.dtype == img.dtype


def test_lens_warp_runs_and_preserves_shape():
    r = GeometricDomainRandomizer(
        GeometricRandomizationConfig(
            enabled=True, p_lens=1.0, calibration_path=str(_CALIB)
        )
    )
    img = _frame(2)
    out = r.apply(img, GeometricSpec(lens=True))
    assert out.shape == img.shape and out.dtype == img.dtype
    assert not np.array_equal(out, img)


# --- the geometry the warps rest on -----------------------------------------


def test_homography_between_a_camera_and_itself_is_the_identity():
    cam = CameraModel()
    h = ground_plane_homography(cam, cam)
    assert np.allclose(h / h[2, 2], np.eye(3), atol=1e-6)


def test_homography_agrees_with_the_projection_model_on_the_ground():
    """The warp claims to be exact on the road plane. Check it against
    CameraModel's own ground_to_pixel at points the fit did not use."""
    src = CameraModel()
    dst = CameraModel(height_m=src.height_m * 1.07, pitch_rad=src.pitch_rad + 0.02)
    h = ground_plane_homography(src, dst)
    for x_m, y_m in ((0.30, 0.10), (0.55, -0.22), (0.80, 0.05)):
        u_s, v_s = src.ground_to_pixel(x_m, y_m)
        expected = np.array(dst.ground_to_pixel(x_m, y_m))
        p = h @ np.array([u_s, v_s, 1.0])
        assert np.allclose(p[:2] / p[2], expected, atol=1e-3)


def test_distortion_and_rectification_are_inverses_in_the_scan_band():
    """distortion_maps_to_calibration is the stated inverse of
    rectification_maps_from_calibration. Checked away from the borders, where
    the round trip is lossy by construction (the real lens covers ~94.6 deg
    against the canonical 90, so the outer columns have no source)."""
    from cobraflex_rl.camera_geometry import rectification_maps_from_calibration

    cam = CameraModel()
    fwd = distortion_maps_to_calibration(_CALIB, cam)
    rev = rectification_maps_from_calibration(_CALIB, cam)
    img = _frame(7, (cam.height_px, cam.width_px, 3))
    # A smooth image: the round trip resamples twice, so per-pixel equality on
    # white noise would test the interpolator, not the geometry.
    img = cv2.GaussianBlur(img, (0, 0), 6.0)
    out = cv2.remap(img, *fwd, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    out = cv2.remap(out, *rev, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    h, w = cam.height_px, cam.width_px
    band = (slice(int(0.55 * h), int(0.95 * h)), slice(int(0.30 * w), int(0.70 * w)))
    assert np.mean(np.abs(out[band].astype(float) - img[band].astype(float))) < 6.0
