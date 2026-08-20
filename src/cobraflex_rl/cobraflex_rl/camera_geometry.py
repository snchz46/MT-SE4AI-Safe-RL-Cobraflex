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

# MEASURED extrinsics (M-6, 17.08.2026): pitch and height fitted jointly over 17
# tape marks on the real car, residual rms 0.485 px —
# experiments/calibration/M6_pitch_results.json.
#
# The direction of authority reversed here on 19.08.2026. These used to be
# *derived from the URDF* (0.30 rad, 0.07725 m), which was a hand-picked mount
# nobody had measured; the sim and this model agreed with each other and with
# nothing else — the same circular agreement M-6 found for HFOV. Now the
# measurement is the authority and the URDF chain is solved to land on it:
# camera_joint_lane z = 0.07794 - (0.03725 + 0.075) = -0.03431 in all five
# variants of src/cobraflex/urdf/. Re-run tools/validate_cv_estimator.py after
# any change to either side, and keep them in step — a captured Gazebo frame
# puts the horizon at row 81 for this pitch and at 180 for a zero one, which is
# how the 10.08 regression (a44ed5f0 dropped rpy="0 0.30 0" in an .stl commit)
# was eventually caught.
#
# The 550k trunk trained at 0.30 / 0.07725, i.e. 0.65 deg and 0.7 mm from these —
# far inside the 0.15 rad spawn heading perturbation it already trains under, so
# adopting the measured pair does not invalidate a continuation of it.
#
# Not modelled, and small: the mount sits 1.5 mm off the vehicle centreline
# (y = -0.0015 in the URDF). The projection below assumes a pitch-only mount, so
# that appears as a constant 1.5 mm ey bias — an order of magnitude under the
# estimator's own 13.2 mm re-placement repeatability (M-7 §4).
DEFAULT_CAMERA_HEIGHT_M = 0.07794
DEFAULT_CAMERA_PITCH_RAD = 0.31132
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


def distortion_maps_to_calibration(
    calibration_path,
    camera: "CameraModel | None" = None,
):
    """The inverse of :func:`rectification_maps_from_calibration`: render a
    *canonical* (simulated) frame as the **measured physical lens** would see it.

    Rectification exists to remove the real optics at deployment. This exists to
    put them back in simulation, so a policy can be trained against them instead
    of merely corrected afterwards — the same argument ``low_contrast`` makes for
    photometry (M-7/D-71). It matters because the geometric term is *not* small
    once the photometric one stops being the binding constraint: measured on the
    420-frame Gazebo pose set, pushing the canonical render through this map costs
    the 550k trunk a third of its lane response (steering swing 0.363 -> 0.232),
    and on the compound photometric+geometric arm — the deployed condition — the
    fine-tuned policy reads swing 0.030 raw against 0.081 rectified.

    (The 19.08 observation that rectification "changes almost nothing" was made on
    the trunk's *physical* frames, 0.097 -> 0.090, where the photometric collapse
    had already taken the response to zero and nothing could move it. It does not
    generalise to a policy that still responds.)

    Construction, per destination pixel ``(u_d, v_d)`` of the physical camera:
    undistort it through the measured intrinsics to recover the true ray, then
    project that ray with the canonical intrinsics to get the source pixel. That
    is ``cv2.undistortPoints(..., P=K_canonical)`` over the full pixel grid.

    **Limitation, and it is inherent.** The physical camera's angular coverage
    (~94.6 deg) is *wider* than the canonical 90 deg, so the outer columns of the
    distorted frame ask for scene content the simulator never rendered. Those
    pixels have no source and come back as border. A rectify-then-distort round
    trip is therefore lossy at the edges in a way the real pipeline is not, and
    the arm is pessimistic by that much. It is still the right training signal:
    the estimator's scan band sits well inside the covered region.

    Parameters mirror :func:`rectification_maps_from_calibration`; the same
    ``M6_results.json`` is the single authority for the intrinsics.

    Returns ``(map1, map2)`` for ``cv2.remap``.
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
    grid = np.stack(
        np.meshgrid(
            np.arange(cam.width_px, dtype=np.float32),
            np.arange(cam.height_px, dtype=np.float32),
        ),
        axis=-1,
    ).reshape(-1, 1, 2)
    src = cv2.undistortPoints(grid, k_measured, distortion, P=k_canonical)
    src = src.reshape(cam.height_px, cam.width_px, 2)
    return (
        np.ascontiguousarray(src[..., 0], dtype=np.float32),
        np.ascontiguousarray(src[..., 1], dtype=np.float32),
    )


def ground_plane_homography(src: "CameraModel", dst: "CameraModel"):
    """Image-to-image homography between two pinhole cameras viewing the ground.

    Both cameras see the same flat road, so for points *on that plane* the
    mapping between their images is exactly a homography — no approximation, no
    depth needed. This is what makes a mount-pose perturbation cheap to simulate:
    re-render is unnecessary, a warp of the existing frame is exact for the
    markings, which are painted on the plane.

    It is **only** exact on the plane. Anything with height — the horizon, walls,
    objects — is displaced wrongly. For this scene that is acceptable and, in the
    estimator's scan band, irrelevant: the band is ground by construction. Do not
    reuse this to warp a frame whose *content above the horizon* matters.

    Correspondences are taken at four ground points spanning the near/far scan
    rows and +/- 0.35 m laterally (the lane half-width plus margin), projected
    through each model with :meth:`CameraModel.ground_to_pixel`.

    Returns the 3x3 matrix ``H`` such that ``cv2.warpPerspective(img_src, H,
    (dst.width_px, dst.height_px))`` renders what ``dst`` would have seen.
    """
    import cv2
    import numpy as np

    near_row = src.cy + 0.90 * (src.height_px - src.cy)
    far_row = src.cy + 0.30 * (src.height_px - src.cy)
    x_near = src.row_to_distance(near_row)
    x_far = src.row_to_distance(far_row)
    ground = [
        (x_near, -0.35), (x_near, 0.35),
        (x_far, -0.35), (x_far, 0.35),
    ]
    src_pts = np.array([src.ground_to_pixel(x, y) for x, y in ground], dtype=np.float32)
    dst_pts = np.array([dst.ground_to_pixel(x, y) for x, y in ground], dtype=np.float32)
    return cv2.getPerspectiveTransform(src_pts, dst_pts)
