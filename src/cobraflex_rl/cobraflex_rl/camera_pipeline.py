"""
camera_pipeline — the shared per-frame camera path for track 'E' (D-41/D-43).

One native camera frame per control cycle flows through exactly one place:

    raw frame ──► [runtime degradation injector] ──► degraded native frame
                                                       ├──► cage CV lane-estimator (D-43)
                                                       └──► downsample → policy observation

The degradation (scenario stressor SC-PERT-04..08, or the training-time domain
randomisation draw) is applied **once, to the native frame, before both
consumers** — the D-43 common-cause design: the policy CNN and the cage's CV
detector see the same (possibly degraded) world. Ground truth never enters
this path; it remains the sim-only reward/oracle channel.

Also hosts the pure ROS-image decoding helper (`decode_image`) so the ROS node
side stays a thin field-unpacking wrapper.

Pure numpy + cv2 (resize only) — host-testable without ROS.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

# Fixed E-design observation parameters (docs/09 §10, fixed at E2):
# 84×84 grayscale, frame stack k=4 applied by the trainer (VecFrameStack).
OBS_WIDTH = 84
OBS_HEIGHT = 84
FRAME_STACK = 4

_CHANNELS_BY_ENCODING = {
    "mono8": 1,
    "8uc1": 1,
    "bgr8": 3,
    "rgb8": 3,
    "8uc3": 3,
    "bgra8": 4,
    "rgba8": 4,
    "8uc4": 4,
}


def decode_image(
    data: bytes | np.ndarray,
    height: int,
    width: int,
    encoding: str,
    step: int = 0,
) -> np.ndarray:
    """Decode raw ROS ``sensor_msgs/Image`` fields into a BGR uint8 array.

    Mirrors the proven decoder in ``cobraflex.lane_keeper_gazebo_node`` but is
    pure (fields in, array out) so it is host-testable and reusable by the env
    bridge and the estimator node alike. Grayscale input is replicated to BGR.
    """
    enc = encoding.lower()
    channels = _CHANNELS_BY_ENCODING.get(enc)
    if channels is None:
        raise ValueError(f"Unsupported image encoding: {encoding}")
    row_stride = int(step) if step and step > 0 else int(width * channels)
    expected = int(height * row_stride)
    buf = np.frombuffer(data, dtype=np.uint8)
    if buf.size < expected:
        raise ValueError(
            f"Image buffer too small for {encoding}: {buf.size} < {expected}"
        )
    rows = buf[:expected].reshape((height, row_stride))
    if channels == 1:
        gray = rows[:, :width]
        return np.ascontiguousarray(np.repeat(gray[:, :, None], 3, axis=2))
    img = rows[:, : width * channels].reshape((height, width, channels))
    if channels == 4:
        img = img[:, :, :3] if enc.startswith(("bgra", "8uc4")) else img[:, :, [2, 1, 0]]
        return np.ascontiguousarray(img)
    if enc in ("bgr8", "8uc3"):
        return np.ascontiguousarray(img)
    return np.ascontiguousarray(img[:, :, ::-1])  # rgb8 → BGR


def to_observation(
    frame_bgr: np.ndarray,
    *,
    width: int = OBS_WIDTH,
    height: int = OBS_HEIGHT,
    grayscale: bool = True,
) -> np.ndarray:
    """Native frame → policy observation: grayscale + area-downsample to
    ``(height, width, 1)`` uint8 (or ``(height, width, 3)`` if RGB kept)."""
    if cv2 is None:  # pragma: no cover - cv2 is a hard requirement on hosts
        raise RuntimeError("cv2 is required for observation downsampling")
    img = frame_bgr
    if grayscale:
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
    if small.ndim == 2:
        small = small[:, :, None]
    return np.ascontiguousarray(small, dtype=np.uint8)


def mirror_frame(frame: np.ndarray) -> np.ndarray:
    """Mirror a camera frame horizontally, for the training-side mirror
    augmentation (sim-to-real, D-71 follow-up).

    A plain ``frame[:, ::-1]``, and deliberately so after measuring the
    alternative.

    It is not perfectly centred on the optical axis: the flip maps column ``u``
    to ``W-1-u``, so the mirrored optical centre lands at ``(W-1)/2 = 319.5``
    while ``CameraModel.cx`` is ``W/2 = 320``. Measured over the 420-frame
    Gazebo pose set, that one-pixel offset costs a **constant** 0.075 mm of
    ``ey`` — the mean, the p95 and the max are all 0.0746, i.e. it is a pure
    uniform translation with no outliers — which propagates to a bounded 0.0027
    mean / 0.0032 max steering difference through the shipped CV controller.
    That is 0.6 % of the estimator's own 13.2 mm re-placement repeatability
    (M-7 §4) and ~2 % of the +0.13 handedness bias the augmentation exists to
    remove.

    THE OBVIOUS CORRECTION IS WORSE — DO NOT RE-APPLY IT. Shifting the flipped
    frame one column right maps ``u -> W-u``, which is *exactly* antisymmetric
    about ``cx``, and on 95 % of frames it is (residual 5e-5). But the vacated
    left column has to be filled, and replicating the frame's rightmost column
    there puts a two-pixel-wide copy of whatever touched the right border at the
    extreme left edge — where the ground projection's lateral resolution is
    largest. On the same 420 frames it tipped the estimator's greedy line
    pairing on 10 of them, mean residual 0.71 mm, worst 223 mm, including one
    frame whose mirrored ``ey`` came back with the *same* sign as the original.
    Trading a uniform 0.075 mm bias for occasional sign inversions is a bad
    trade: the policy can learn around a constant, and cannot learn around a
    label that is sometimes backwards.
    """
    return np.ascontiguousarray(frame[:, ::-1])


class CameraPipeline:
    """Per-cycle camera frame processing with a single degradation point.

    ``injector`` is the per-episode degradation: any callable
    ``frame -> frame`` (e.g. a bound ``visual_degradation.degrade`` with the
    scenario's mode/level, or a ``VisualDomainRandomizer.apply`` with the
    episode's drawn spec). ``None`` means a clean frame.
    """

    def __init__(
        self,
        *,
        obs_width: int = OBS_WIDTH,
        obs_height: int = OBS_HEIGHT,
        grayscale: bool = True,
        injector: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    ) -> None:
        self.obs_width = int(obs_width)
        self.obs_height = int(obs_height)
        self.grayscale = bool(grayscale)
        self.injector = injector

    def set_injector(
        self, injector: Optional[Callable[[np.ndarray], np.ndarray]]
    ) -> None:
        """Swap the degradation for the coming episode (None = clean)."""
        self.injector = injector

    def process(self, frame_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Run one native frame through the shared path.

        Returns ``(consumer_frame, observation)`` where ``consumer_frame`` is
        the (possibly degraded) native-resolution frame for the cage's CV
        estimator and ``observation`` is the downsampled policy obs.
        """
        frame = frame_bgr if self.injector is None else self.injector(frame_bgr)
        obs = to_observation(
            frame,
            width=self.obs_width,
            height=self.obs_height,
            grayscale=self.grayscale,
        )
        return frame, obs
