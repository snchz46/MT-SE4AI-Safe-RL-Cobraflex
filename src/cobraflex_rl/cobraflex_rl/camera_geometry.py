"""
camera_geometry — deterministic pinhole ground-plane projection for track 'E'.

The cage's CV lane-estimator (D-43) converts detected lane-line pixels into
metric lateral offsets, so it needs the camera's pixel↔ground mapping. The
camera is pitch-only (no roll, no yaw relative to the vehicle), which makes the
mapping closed-form and auditable:

* each image row ``v`` below the horizon corresponds to a single ground
  distance ``X(v)`` ahead of the camera, and
* within that row, the column ``u`` maps linearly to the lateral ground
  coordinate ``Y``.

Frames: vehicle/ground frame has X forward, Y left, origin at the camera's
vertical ground projection; the optical frame is the usual x-right / y-down /
z-forward. All parameters mirror the Gazebo sensor + URDF mount (the single
source of truth for the physical numbers):

* intrinsics from the ``Lane Cam`` sensor (640x360, HFOV 1.5707963 rad —
  mirroring the real IMX219-160 as configured in ``lane_keeper_node.py``),
* extrinsics from the URDF chain (camera height above ground, pitch-down).

Pure numpy/stdlib — host-testable without ROS.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

# URDF-derived defaults (my_robot_gazebo_mesh.urdf — the variant every
# train/eval launch includes via gazebo_mesh.launch.py): base_link at
# wheel_radius 0.03725, body_link at +body_height/2+chassis_height/2-0.01
# (0.05+0.03-0.01, mesh-variant body offset), camera_link_lane at -0.03
# → 0.07725 m above ground; pitch 0.30 rad (matches the camera_link_lane joint
# rpy="0 0.30 0" in my_robot_gazebo_mesh.urdf — re-run
# tools/validate_cv_estimator.py if it changes). NOTE the non-mesh URDF
# variants currently lack the -0.01 body offset (camera 1 cm higher).
DEFAULT_CAMERA_HEIGHT_M = 0.03725 + 0.05 + 0.03 - 0.01 - 0.03
DEFAULT_CAMERA_PITCH_RAD = 0.30
DEFAULT_HFOV_RAD = 1.5707963
DEFAULT_WIDTH_PX = 640
DEFAULT_HEIGHT_PX = 360


@dataclass(frozen=True)
class CameraModel:
    """Pitch-only pinhole camera over a flat ground plane."""

    height_m: float = DEFAULT_CAMERA_HEIGHT_M
    pitch_rad: float = DEFAULT_CAMERA_PITCH_RAD
    hfov_rad: float = DEFAULT_HFOV_RAD
    width_px: int = DEFAULT_WIDTH_PX
    height_px: int = DEFAULT_HEIGHT_PX

    def __post_init__(self) -> None:
        if self.height_m <= 0:
            raise ValueError("height_m must be > 0")
        if not 0.0 < self.hfov_rad < math.pi:
            raise ValueError("hfov_rad must be in (0, pi)")
        if self.width_px < 2 or self.height_px < 2:
            raise ValueError("image dimensions must be >= 2 px")

    @property
    def fx(self) -> float:
        return (self.width_px / 2.0) / math.tan(self.hfov_rad / 2.0)

    @property
    def fy(self) -> float:
        return self.fx  # square pixels (Gazebo camera default)

    @property
    def cx(self) -> float:
        return self.width_px / 2.0

    @property
    def cy(self) -> float:
        return self.height_px / 2.0

    @property
    def horizon_row(self) -> float:
        """Image row of the horizon (ground at infinity): v where the ray is
        parallel to the ground, i.e. yo = -tan(pitch)."""
        return self.cy - self.fy * math.tan(self.pitch_rad)

    def row_to_distance(self, v: float) -> float:
        """Ground distance X (m, forward) seen by image row ``v``.

        Pitch-only mounting makes X independent of the column. Rows at or
        above the horizon have no ground intersection → ValueError.
        """
        yo = (v - self.cy) / self.fy
        denom = math.sin(self.pitch_rad) + yo * math.cos(self.pitch_rad)
        if denom <= 1e-9:
            raise ValueError(f"row {v} is at/above the horizon (no ground point)")
        t = self.height_m / denom
        return t * (math.cos(self.pitch_rad) - yo * math.sin(self.pitch_rad))

    def distance_to_row(self, x_m: float) -> float:
        """Inverse of :meth:`row_to_distance` (X forward → image row)."""
        if x_m <= 0:
            raise ValueError("x_m must be > 0 (ahead of the camera)")
        sp, cp = math.sin(self.pitch_rad), math.cos(self.pitch_rad)
        # yo solves x = h(c - yo*s)/(s + yo*c)
        yo = (self.height_m * cp - x_m * sp) / (x_m * cp + self.height_m * sp)
        return self.cy + self.fy * yo

    def pixel_to_ground(self, u: float, v: float) -> Tuple[float, float]:
        """(u, v) → ground (X forward, Y left) in metres."""
        x = self.row_to_distance(v)
        yo = (v - self.cy) / self.fy
        denom = math.sin(self.pitch_rad) + yo * math.cos(self.pitch_rad)
        t = self.height_m / denom
        xo = (u - self.cx) / self.fx
        y = -t * xo
        return x, y

    def ground_to_pixel(self, x_m: float, y_m: float) -> Tuple[float, float]:
        """Ground (X forward, Y left) → image (u, v)."""
        if x_m <= 0:
            raise ValueError("x_m must be > 0 (ahead of the camera)")
        sp, cp = math.sin(self.pitch_rad), math.cos(self.pitch_rad)
        # Vector camera→point in vehicle frame: (x, y, -h); optical components:
        xo_n = -y_m                              # · x_opt axis (0,-1,0)
        yo_n = -x_m * sp + self.height_m * cp    # · y_opt axis (-s,0,-c)
        zo_n = x_m * cp + self.height_m * sp     # · z_opt axis (c,0,-s)
        u = self.cx + self.fx * xo_n / zo_n
        v = self.cy + self.fy * yo_n / zo_n
        return u, v

    def lateral_resolution(self, v: float) -> float:
        """Metres of lateral ground per pixel at image row ``v``."""
        yo = (v - self.cy) / self.fy
        denom = math.sin(self.pitch_rad) + yo * math.cos(self.pitch_rad)
        if denom <= 1e-9:
            raise ValueError(f"row {v} is at/above the horizon")
        t = self.height_m / denom
        return t / self.fx


def rectification_maps_from_calibration(
    calibration_path,
    camera: "CameraModel | None" = None,
):
    """Maps that undistort a *measured physical* camera into this module's model.

    Everything above assumes an ideal pinhole with the optical axis at the image
    centre. The physical camera is neither: M-6 measured ``fx = fy = 395.93`` (not
    the assumed 320), ``cx = 305.39`` (not 320) and plumb-bob distortion with
    ``k1 = -0.339``, which displaces a mid-row edge pixel by 129 px. Feeding those
    frames to the model above is what makes the deployed estimator under-read
    ``ey`` (M-7 §4: 0.68-0.83 x true, so C-01's 160 mm fires at a true 207-241 mm).

    Correcting the intrinsics *without* undistorting does not help — it makes it
    marginally worse (0.674 -> 0.644 on the forward model, because the focal and
    range errors partly cancel). Undistorting into the canonical model restores it
    (slope 0.998, lane width 249.9 ± 1.5 mm against a 250 mm ruler). That is M-6's
    "undistort, do not just re-parameterise", as a measurement rather than a claim.

    The canonical target is deliberately ``CameraModel()`` itself — the camera the
    simulator renders — so the rectified frame is one the rest of the stack, and
    every frozen sim result, already describes. It fits: the physical camera's true
    horizontal coverage including distortion is ~94.6°, *wider* than the canonical
    90°, so the rectified frame is 93 % filled overall and 100 % filled across the
    estimator's scan band. (The 77.89° in M-6/docs-17 is the pinhole-equivalent
    ``2·atan(320/fx)``, not the camera's angular coverage.)

    Parameters
    ----------
    calibration_path:
        ``experiments/calibration/M6_results.json`` — the single authority for
        these numbers; they are never copied into code.
    camera:
        Canonical target, default ``CameraModel()``.

    Returns ``(map1, map2)`` for ``cv2.remap``. Raises if the calibration was
    solved at a different resolution, because the intrinsics would not apply.
    """
    import json
    from pathlib import Path

    import cv2
    import numpy as np

    cam = camera or CameraModel()
    data = json.loads(Path(calibration_path).read_text())
    if int(data["width_px"]) != cam.width_px or int(data["height_px"]) != cam.height_px:
        raise ValueError(
            f"calibration solved at {data['width_px']}x{data['height_px']} but the "
            f"camera model is {cam.width_px}x{cam.height_px} — intrinsics do not apply"
        )
    k_measured = np.array(
        [[data["fx_px"], 0.0, data["cx_px"]],
         [0.0, data["fy_px"], data["cy_px"]],
         [0.0, 0.0, 1.0]],
        dtype=float,
    )
    k_canonical = np.array(
        [[cam.fx, 0.0, cam.cx], [0.0, cam.fy, cam.cy], [0.0, 0.0, 1.0]], dtype=float
    )
    distortion = np.asarray(data["distortion_plumb_bob"], dtype=float)
    return cv2.initUndistortRectifyMap(
        k_measured, distortion, None, k_canonical,
        (cam.width_px, cam.height_px), cv2.CV_32FC1,
    )
