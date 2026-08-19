"""
visual_degradation — pure-numpy front-camera image degradations for track 'E'.

Track 'E' (end-to-end front-camera, decisions D-41/D-43) stresses the camera
with visual degradations (hazard H-10, verified by SR-012 over the scenarios
SC-PERT-04..06; plus the H-11/H-12 stressors of SC-PERT-07/08). Per D-43 the
degraded frame reaches **both consumers** — the policy's CNN and the cage's CV
lane-estimator — the accepted common-cause trade-off: a camera fault can blind
both at once, and the designed answer is the open-loop controlled stop
(SR-013/SR-014 → C-05 Trigger 8).

Each primitive takes a uint8 image (grayscale ``(H, W)`` or ``(H, W, C)``) and a
``level`` in ``[0, 1]`` (0 = identity, 1 = strongest) and returns a uint8 image of
the same shape. The functions are **deterministic** (no RNG): the training-time
domain randomisation samples the mode and level; these primitives are the
deterministic kernels it draws from.

Mode strings match ``perturbations.mode`` in
``scenarios/perturbed/sc_pert_04..08.yaml``:

* ``"glare_overexposure"``      — SC-PERT-04 (H-10)
* ``"low_light_underexposure"`` — SC-PERT-05 (H-10)
* ``"motion_blur"``             — SC-PERT-06 (H-10)
* ``"low_contrast"``            — sim-to-real photometry (M-7/D-71); training-only
* ``"occlusion"``               — SC-PERT-07 (H-11; perception loss)
* ``"false_lane"``              — SC-PERT-08 (H-12; misleading marking)

``MODES`` is the frozen H-10 trio the SR-012 training-side domain randomisation
drew from; ``TRAINABLE_MODES`` adds ``low_contrast``, which no scenario exercises
because it is not a hazard — it is the *physical track's own photometry*, added
after M-7 measured it. Occlusion and false-lane are **eval stressors** — training on them would teach the policy to ignore
exactly the cues whose loss must trigger the SR-013/SR-014 stop — and are
exposed separately via ``EVAL_ONLY_MODES`` / ``ALL_MODES``.

Pure (numpy only, no ROS), host-testable on any platform. The Gazebo camera sensor
and the runtime injector that calls these primitives live on the Ubuntu+Jazzy host.
"""
from __future__ import annotations

import numpy as np

GLARE = "glare_overexposure"
LOW_LIGHT = "low_light_underexposure"
MOTION_BLUR = "motion_blur"
LOW_CONTRAST = "low_contrast"
OCCLUSION = "occlusion"
FALSE_LANE = "false_lane"
# The frozen H-10 trio. Left EXACTLY as it was so every past training run's DR
# draw stays reproducible (the 550k trunk included) — new modes go in
# TRAINABLE_MODES, never in here.
MODES = (GLARE, LOW_LIGHT, MOTION_BLUR)
# What training-time DR may draw from. LOW_CONTRAST is the sim-to-real addition
# (M-7/D-71); occlusion and false-lane stay out for the reason in the module
# docstring — training on them teaches the policy to ignore the very cues whose
# loss must trigger the SR-013/SR-014 stop.
TRAINABLE_MODES = MODES + (LOW_CONTRAST,)
EVAL_ONLY_MODES = (OCCLUSION, FALSE_LANE)
ALL_MODES = TRAINABLE_MODES + EVAL_ONLY_MODES

_MAX = 255.0


def _check(img: np.ndarray, level: float) -> None:
    if not isinstance(img, np.ndarray):
        raise TypeError("img must be a numpy ndarray")
    if img.dtype != np.uint8:
        raise ValueError(f"img must be uint8, got {img.dtype}")
    if img.ndim not in (2, 3):
        raise ValueError(f"img must be (H,W) or (H,W,C), got shape {img.shape}")
    if not 0.0 <= float(level) <= 1.0:
        raise ValueError(f"level must be in [0, 1], got {level}")


def apply_glare(img: np.ndarray, level: float, *,
                max_gain: float = 2.0, max_bias: float = 160.0) -> np.ndarray:
    """Over-exposure / glare: multiplicative gain plus an additive wash toward white.

    ``level=0`` is the identity; ``level=1`` applies ``gain=max_gain`` and
    ``bias=max_bias`` (strong wash-out). Models sun glare / specular highlights
    saturating the sensor.
    """
    _check(img, level)
    gain = 1.0 + level * (max_gain - 1.0)
    bias = level * max_bias
    out = img.astype(np.float32) * gain + bias
    return np.clip(out, 0.0, _MAX).astype(np.uint8)


def apply_low_light(img: np.ndarray, level: float, *,
                    min_gain: float = 0.15, contrast_drop: float = 0.5) -> np.ndarray:
    """Under-exposure / low light: brightness gain down + contrast compression
    toward the per-image mean.

    ``level=0`` is the identity; ``level=1`` darkens to ``min_gain`` of the original
    brightness and compresses contrast by ``contrast_drop``. Models dusk / deep
    shadow reducing lane contrast.
    """
    _check(img, level)
    gain = 1.0 - level * (1.0 - min_gain)
    contrast = 1.0 - level * contrast_drop
    f = img.astype(np.float32)
    mean = float(f.mean())
    out = ((f - mean) * contrast + mean) * gain
    return np.clip(out, 0.0, _MAX).astype(np.uint8)


def apply_low_contrast(img: np.ndarray, level: float, *,
                       max_black_lift: float = 110.0, min_gain: float = 0.5) -> np.ndarray:
    """Lifted black level + compressed dynamic range — the *physical track's*
    photometry, and the sim-to-real gap the 550k trunk fell into (M-7/D-71).

    Neither existing primitive can produce it. ``apply_glare`` needs gain >= 1
    and saturates the markings; ``apply_low_light`` compresses toward the mean
    and then *darkens*. The real hall does the opposite of both: it leaves the
    markings where they are and raises the road out of black.

    Measured inside the estimator's scan band, over three independent physical
    sessions (1521-frame circuit survey + two hand sweeps) against 420 Gazebo
    complex_b frames:

    ======================  ======  =========  =====
    ..                      line    road       ratio
    ======================  ======  =========  =====
    Gazebo complex_b        197     **27**     7.3x
    physical lane circuit   209-217 **106-108**  2.0x
    ======================  ======  =========  =====

    The markings already agree to 6 %; the whole error is the road, which
    ``generate_complex_track.ASPHALT = (0, 0, 0)`` renders as near-black while a
    real hall floor sits at mid grey. Squeezing a sim frame into that band is
    enough on its own to destroy the trunk policy — its lane response collapses
    from a 0.363 steering swing to 0.004 and it stops commanding right turns
    entirely, reproducing the observed physical failure. Pasting the entire
    workshop above the horizon, by contrast, changes nothing (0.352 vs 0.363),
    so this is *the* appearance term worth randomising.

    ``level=0`` is the identity. ``level=1`` gives ``min_gain`` with a
    ``max_black_lift`` pedestal. The defaults are chosen so the **measured**
    physical condition lands at ``level≈0.75`` (road 27 -> 99, line 197 -> 206,
    ratio 2.07 against the measured 106/209/2.0) — i.e. inside, not at the edge
    of, the standard ``level_range=(0.2, 1.0)`` draw, leaving the run headroom
    on both sides for a different hall or a different floor.

    Fixing the world's asphalt colour instead would hit the same centre but
    would regenerate every track texture and world, perturbing frozen sim
    evidence for a single point estimate; randomising the *frame* covers the
    range and leaves every world bit-identical.

    Deliberately gain-and-pedestal only: the cage's D-43 estimator consumes this
    same frame (the common-cause design in ``camera_pipeline``), and its white
    gate is ``V >= 150``. Across the whole level range the markings stay above
    it and the road stays below, so the DR cannot silently blind the safety
    monitor during training — asserted in ``test_visual_degradation.py``.
    """
    _check(img, level)
    gain = 1.0 - level * (1.0 - min_gain)
    lift = level * max_black_lift
    out = img.astype(np.float32) * gain + lift
    return np.clip(out, 0.0, _MAX).astype(np.uint8)


def apply_motion_blur(img: np.ndarray, level: float, *,
                      max_kernel: int = 15, axis: int = 1) -> np.ndarray:
    """Directional motion blur: a box average over a window that grows with ``level``.

    ``level=0`` is the identity (window 1); ``level=1`` uses ``max_kernel``. ``axis=1``
    blurs along columns (horizontal motion, the dominant case for a forward camera on
    a turning vehicle). Models motion blur / rolling-shutter smear at speed.
    """
    _check(img, level)
    k = 1 + int(round(level * (max_kernel - 1)))
    if k <= 1:
        return img.copy()
    return _box_blur_1d(img, k, axis)


def _box_blur_1d(img: np.ndarray, k: int, axis: int) -> np.ndarray:
    """Moving average of window ``k`` along ``axis`` (edge-padded), pure numpy via a
    cumulative-sum sliding window."""
    f = img.astype(np.float32)
    left = k // 2
    right = k - 1 - left
    pad = [(0, 0)] * f.ndim
    pad[axis] = (left, right)
    fp = np.pad(f, pad, mode="edge")
    csum = np.cumsum(fp, axis=axis)
    zero_shape = list(csum.shape)
    zero_shape[axis] = 1
    csum = np.concatenate([np.zeros(zero_shape, dtype=csum.dtype), csum], axis=axis)
    n = f.shape[axis]
    hi = [slice(None)] * f.ndim
    lo = [slice(None)] * f.ndim
    hi[axis] = slice(k, k + n)
    lo[axis] = slice(0, n)
    out = (csum[tuple(hi)] - csum[tuple(lo)]) / float(k)
    return np.clip(out, 0.0, _MAX).astype(np.uint8)


def apply_occlusion(img: np.ndarray, level: float, *,
                    fill_value: int = 25, max_height_frac: float = 0.75) -> np.ndarray:
    """Occlusion / perception loss (SC-PERT-07, H-11): an opaque dark patch
    grows from the bottom of the frame — where the near-field lane features
    live — covering ``level * max_height_frac`` of the image height across the
    full width. Models debris on the lens, a tarp, or a deep cast shadow
    swallowing the markings. ``level=0`` is the identity.
    """
    _check(img, level)
    out = img.copy()
    rows = int(round(img.shape[0] * level * max_height_frac))
    if rows > 0:
        out[img.shape[0] - rows:, ...] = fill_value
    return out


def apply_false_lane(img: np.ndarray, level: float, *,
                     brightness: int = 235, width_frac: float = 0.02,
                     base_col_frac: float = 0.55, top_col_frac: float = 0.95) -> np.ndarray:
    """False lane marking (SC-PERT-08, H-12): paint a bright line that starts
    near the bottom centre (right of the true centre) and slants toward the
    image edge — a plausible-but-wrong feature (fork, old paint, tar seam) a
    lane detector can lock onto. ``level`` blends the line's opacity from
    invisible (0) to fully painted (1). Geometry is fixed and deterministic so
    a given level is exactly reproducible.
    """
    _check(img, level)
    if level <= 0.0:
        return img.copy()
    h, w = img.shape[0], img.shape[1]
    out = img.astype(np.float32)
    half = max(1, int(round(w * width_frac / 2.0)))
    # Line runs from (row h-1, col base) up to (row h//2, col top): only the
    # lower half of the frame, where ground features are metrically plausible.
    rows = np.arange(h // 2, h)
    frac = (rows - h // 2) / max(1, (h - 1) - h // 2)  # 0 at mid, 1 at bottom
    cols = (top_col_frac + (base_col_frac - top_col_frac) * frac) * (w - 1)
    for r, c in zip(rows, cols):
        lo = max(0, int(round(c)) - half)
        hi = min(w, int(round(c)) + half + 1)
        if lo < hi:
            out[r, lo:hi, ...] = (
                (1.0 - level) * out[r, lo:hi, ...] + level * float(brightness)
            )
    return np.clip(out, 0.0, _MAX).astype(np.uint8)


def degrade(img: np.ndarray, mode: str, level: float) -> np.ndarray:
    """Dispatch to the degradation primitive for ``mode`` (one of :data:`ALL_MODES`)."""
    if mode == GLARE:
        return apply_glare(img, level)
    if mode == LOW_LIGHT:
        return apply_low_light(img, level)
    if mode == MOTION_BLUR:
        return apply_motion_blur(img, level)
    if mode == LOW_CONTRAST:
        return apply_low_contrast(img, level)
    if mode == OCCLUSION:
        return apply_occlusion(img, level)
    if mode == FALSE_LANE:
        return apply_false_lane(img, level)
    raise ValueError(f"unknown degradation mode {mode!r}; expected one of {ALL_MODES}")
