"""
geometric_domain_randomization — per-episode camera-geometry sampler (M-7/D-71).

The photometric sampler in :mod:`cobraflex_rl.visual_domain_randomization` covers
*what grey the road is*. This one covers *where the camera is pointing and what
its lens does* — the second sim-to-real term, and the one that becomes binding
once the first is handled.

Why it is needed at all, when the deployment plan is to rectify
-------------------------------------------------------------
Rectification (``camera_geometry.rectification_maps_from_calibration``) removes
the measured lens: offline it restores the estimator to slope 0.998 and lane
width 249.9 +/- 1.5 mm against a 250 mm ruler. It does **not** remove everything.
The 19.08 offline pass over 3357 real frames found a *session-dependent* +8...+30
mm residual scale error surviving rectification, and named the cause: once the
optics are corrected the dominant term is the **mount pose** — a taped camera
bracket that is not in the same place twice. M-7 measured the same thing from the
other side: re-placing the car at the same tape offset moves the reading a mean
13.2 mm, worst 29.4.

That residual cannot be calibrated away, because it changes between sessions. It
can only be trained through. So this module randomises the two mount degrees of
freedom the pinhole ground model actually has — **pitch** and **height** — across
a range that brackets the measured residual, and the policy learns a lane
response that does not depend on the bracket being where it was yesterday.

The lens term, and why it is opt-in at low probability
-----------------------------------------------------
``p_lens`` draws the *full* measured barrel distortion (k1 = -0.339) instead of a
pose perturbation. This is insurance, not the operating point: the deployed chain
is supposed to rectify, and if it does, a policy trained mostly on distorted
frames would be the one out of distribution. But rectification is
``[provisional]`` on hardware — it has never run on the car — and the failure
mode if it is misconfigured is total (the trunk reads swing 0.004 on the compound
arm). A small share of episodes seeing the raw lens buys graceful degradation for
a cost the rest of the distribution barely notices.

Both terms are applied to the frame **before** the photometric one and before it
reaches either consumer, so the policy and the cage's CV estimator see the same
geometry — which is the deployed topology, where a mount error moves both.

Pure numpy + cv2, deterministic given the ``Generator``; host-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from cobraflex_rl.camera_geometry import (
    CameraModel,
    distortion_maps_to_calibration,
    ground_plane_homography,
)


@dataclass(frozen=True)
class GeometricSpec:
    """A drawn per-episode camera geometry.

    ``pitch_delta_rad`` / ``height_scale`` perturb the mount relative to the
    measured nominal; ``lens`` replaces the perturbation with the full measured
    barrel distortion. The two are mutually exclusive by construction — a frame
    is either "the canonical camera, mounted slightly wrong" or "the real lens",
    and compounding them would model a mount error the rectifier has already seen.
    """

    pitch_delta_rad: float = 0.0
    height_scale: float = 1.0
    lens: bool = False

    @property
    def is_identity(self) -> bool:
        return (
            not self.lens
            and abs(self.pitch_delta_rad) < 1e-9
            and abs(self.height_scale - 1.0) < 1e-9
        )


def _resolve_calibration(path: Optional[str]) -> Path:
    """Absolute path to the calibration JSON, or a useful error.

    A training YAML naturally writes ``experiments/calibration/M6_results.json``,
    but a ROS2 launch does not run from the repository root, so a relative path
    is resolved against the repo (three levels above this module) before being
    given up on. Absolute paths are used as written.
    """
    if not path:
        raise ValueError("calibration_path is empty")
    candidate = Path(path)
    if not candidate.is_absolute():
        repo_root = Path(__file__).resolve().parents[3]
        resolved = repo_root / candidate
        if resolved.exists():
            return resolved
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(
        f"geometric_randomization.calibration_path not found: {path!r} "
        f"(tried it as written and relative to {Path(__file__).resolve().parents[3]}). "
        "Point it at experiments/calibration/M6_results.json or set p_lens: 0."
    )


@dataclass(frozen=True)
class GeometricRandomizationConfig:
    """Sampler configuration. ``enabled=False`` (default) is a total no-op that
    consumes no RNG, so every pre-existing run stays reproducible from its seed.

    Attributes
    ----------
    p_pose:
        Probability an episode gets a mount perturbation (otherwise nominal).
    pitch_delta_rad:
        ``(low, high)`` added to the model's pitch. The horizon moves
        ``-fy*sec^2(pitch)`` ~= 353 px/rad, so the default +/- 0.026 rad
        (+/- 1.5 deg) spans a +/- 9 px horizon shift — several times the 4 px
        the 19.08 extrinsics correction was worth, which is the scale of "the
        bracket is not where it was".
    height_scale:
        ``(low, high)`` multiplying the camera height. Lateral ground resolution
        is linear in height, so this maps ~1:1 onto an ``ey`` scale error.

        Measured, not assumed: running the D-43 estimator over 140 warped Gazebo
        frames, the two terms do different jobs, and only one of them moves the
        metric scale.

        =====================  ==========  ==============
        spec                   ey ratio    lane width mm
        =====================  ==========  ==============
        unwarped reference     1.000       266.5
        pitch -1.5 deg         0.983       266.5
        pitch +1.5 deg         1.006       269.0
        height -10 %           1.105       297.4
        height +10 %           0.917       243.1
        =====================  ==========  ==============

        So ``height_scale`` +/- 10 % is what brackets the measured +8...+30 mm
        residual (3-12 % on a 250 mm lane), and ``pitch_delta_rad`` contributes
        almost nothing to it — pitch moves the *look-ahead band and the horizon
        row*, which is an appearance cue for the policy, not a scale error for
        the estimator. Both are kept because they perturb different things.

        The estimator pairs on 100 % of frames across the whole range, including
        the corners, so this term stresses the policy without blinding the cage —
        the same property the photometric ceiling was chosen for.
    p_lens:
        Probability of drawing the full measured lens instead. Default 0.0.
    calibration_path:
        ``experiments/calibration/M6_results.json``. Required only when
        ``p_lens > 0``; the intrinsics are never copied into code.
    """

    enabled: bool = False
    p_pose: float = 1.0
    pitch_delta_rad: Tuple[float, float] = (-0.026, 0.026)
    height_scale: Tuple[float, float] = (0.90, 1.10)
    p_lens: float = 0.0
    calibration_path: Optional[str] = None

    def __post_init__(self) -> None:
        for name, p in (("p_pose", self.p_pose), ("p_lens", self.p_lens)):
            if not 0.0 <= p <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.p_lens > 0.0 and not self.calibration_path:
            raise ValueError(
                "p_lens > 0 requires calibration_path (M6_results.json) — the "
                "measured intrinsics have one authority and are not inlined"
            )
        lo, hi = self.pitch_delta_rad
        if lo > hi:
            raise ValueError("pitch_delta_rad must satisfy low <= high")
        lo, hi = self.height_scale
        if not 0.0 < lo <= hi:
            raise ValueError("height_scale must satisfy 0 < low <= high")


class GeometricDomainRandomizer:
    """Draws per-episode :class:`GeometricSpec`s and warps camera frames.

    The distortion maps are ~230k point solves, so they are built once on first
    use and reused; the pose homography is four points and is rebuilt per
    episode, which is free.
    """

    def __init__(
        self,
        config: Optional[GeometricRandomizationConfig] = None,
        camera: Optional[CameraModel] = None,
    ) -> None:
        self.config = config or GeometricRandomizationConfig()
        self.camera = camera or CameraModel()
        self._lens_maps = None
        # Resolve and CHECK the calibration now, but build the maps lazily. The
        # maps are ~230k point solves and most runs never draw a lens episode;
        # the path being wrong, however, must not surface as a crash six hours
        # into a multi-day run, so it is validated at construction. Same
        # fail-at-start-up discipline as cv_lane_estimator_node.
        self._calibration: Optional[Path] = None
        if self.config.p_lens > 0.0:
            self._calibration = _resolve_calibration(self.config.calibration_path)

    def sample(self, rng: np.random.Generator) -> GeometricSpec:
        """Draw a spec. Consumes no RNG when disabled, so a config without this
        block leaves the generator exactly where it was — the same discipline
        the photometric base term follows."""
        cfg = self.config
        if not cfg.enabled:
            return GeometricSpec()
        if cfg.p_lens > 0.0 and rng.random() < cfg.p_lens:
            return GeometricSpec(lens=True)
        if rng.random() >= cfg.p_pose:
            return GeometricSpec()
        return GeometricSpec(
            pitch_delta_rad=float(rng.uniform(*cfg.pitch_delta_rad)),
            height_scale=float(rng.uniform(*cfg.height_scale)),
        )

    def perturbed_camera(self, spec: GeometricSpec) -> CameraModel:
        """The camera model a pose spec describes (the *observer*, not the
        renderer). Exposed so a test can assert what the warp is supposed to be."""
        return CameraModel(
            height_m=self.camera.height_m * spec.height_scale,
            pitch_rad=self.camera.pitch_rad + spec.pitch_delta_rad,
            hfov_rad=self.camera.hfov_rad,
            width_px=self.camera.width_px,
            height_px=self.camera.height_px,
        )

    def apply(self, img: np.ndarray, spec: GeometricSpec) -> np.ndarray:
        """Warp a canonical frame into the drawn geometry. Identity specs return
        a copy, matching :meth:`VisualDomainRandomizer.apply`'s contract."""
        import cv2

        if spec.is_identity:
            return img.copy()
        if spec.lens:
            if self._lens_maps is None:
                self._lens_maps = distortion_maps_to_calibration(
                    self._calibration or self.config.calibration_path, self.camera
                )
            return cv2.remap(
                img,
                self._lens_maps[0],
                self._lens_maps[1],
                cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
        homography = ground_plane_homography(self.camera, self.perturbed_camera(spec))
        return cv2.warpPerspective(
            img,
            homography,
            (self.camera.width_px, self.camera.height_px),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
