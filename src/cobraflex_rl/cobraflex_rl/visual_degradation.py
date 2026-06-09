"""
visual_degradation — pure-numpy front-camera image degradations for track 'E'.

Track 'E' (end-to-end front-camera, decisions D-38/D-39) stresses the camera
*policy* with visual degradations (hazard H-10, verified by SR-012 over the
scenarios SC-PERT-04..06). These are the per-frame primitives applied to the
**observation** (the camera image) before it reaches the policy — they are NEVER
applied to the cage's independent ground-truth state (D-39), so the cage's safety
envelope is unaffected by the stressor.

Each primitive takes a uint8 image (grayscale ``(H, W)`` or ``(H, W, C)``) and a
``level`` in ``[0, 1]`` (0 = identity, 1 = strongest) and returns a uint8 image of
the same shape. The functions are **deterministic** (no RNG): the training-time
domain randomisation samples the mode and level; these primitives are the
deterministic kernels it draws from.

Mode strings match ``perturbations.mode`` in
``scenarios/perturbed/sc_pert_04..06.yaml``:

* ``"glare_overexposure"``      — SC-PERT-04
* ``"low_light_underexposure"`` — SC-PERT-05
* ``"motion_blur"``             — SC-PERT-06

Pure (numpy only, no ROS), host-testable on any platform. The Gazebo camera sensor
and the runtime injector that calls these primitives live on the Ubuntu+Jazzy host.
"""
from __future__ import annotations

import numpy as np

GLARE = "glare_overexposure"
LOW_LIGHT = "low_light_underexposure"
MOTION_BLUR = "motion_blur"
MODES = (GLARE, LOW_LIGHT, MOTION_BLUR)

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


def degrade(img: np.ndarray, mode: str, level: float) -> np.ndarray:
    """Dispatch to the degradation primitive for ``mode`` (one of :data:`MODES`)."""
    if mode == GLARE:
        return apply_glare(img, level)
    if mode == LOW_LIGHT:
        return apply_low_light(img, level)
    if mode == MOTION_BLUR:
        return apply_motion_blur(img, level)
    raise ValueError(f"unknown degradation mode {mode!r}; expected one of {MODES}")
