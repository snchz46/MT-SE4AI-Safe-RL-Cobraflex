#!/usr/bin/env python3
"""
calibrate_camera_hfov — measure the lane camera's effective HFOV on the car.

Closes the highest-priority ``[VERIFY]`` of docs/17 §2: the **90 deg effective
HFOV**. That number is a *parameter default* in ``lane_keeper_node``
(``camera_hfov_deg`` 90.0) for an IMX219-160 lens, which the Gazebo ``Lane Cam``
sensor then mirrored — so sim and hardware are wrong in the *same* way if it is
wrong, and no simulation result can expose it. ``CameraModel.fx =
(w/2)/tan(hfov/2)`` = 320 px at 640x360, and the IPM's metric output scales with
it: a wrong HFOV means every ``ey`` in metres is mis-scaled and **C-01's 0.12 m
threshold no longer means 0.12 m**.

WHAT IT MEASURES, AND WHY IT NEEDS NO PRINTED TARGET
----------------------------------------------------
A pinhole camera images a fronto-parallel line at distance ``D`` with a constant
scale::

    u_i = cx + fx * (y_i - y0) / (D + delta)

where ``y_i`` is a lateral tape reading, ``y0`` the (unknown) tape reading on the
optical axis, and ``delta`` the (unknown) offset between the reference face you
measured ``D`` from and the lens entrance pupil. Fit one line per distance::

    slope  s_j = fx / (D_j + delta)      [px per metre]

``cx`` and ``y0`` collapse into that line's intercept and are never needed. Then
one more regression separates the two remaining unknowns::

    1 / s_j = D_j / fx + delta / fx

so a plot of ``1/s_j`` against ``D_j`` has slope ``1/fx`` and intercept
``delta/fx``. **Two or more distances give fx without knowing where the optical
axis is and without trusting the zero of your tape measure.** A steel tape held
across the field of view is a sufficient target.

The residuals of each per-distance line are the lens distortion the cage's
pinhole IPM ignores — reported in px and converted to the lateral metric error
they cause, because that is the number C-01 cares about.

SUBCOMMANDS
-----------
``preview``  grab frames from ``camera/image_raw_lane`` and write a raw PNG plus
             a ruler-annotated PNG (needs ROS 2 + the running csi_camera_node).
``capture``  same, but tagged with the measured distance for one observation set.
``detect``   find the tape's tick marks in a horizontal band of a captured PNG
             and print their sub-pixel columns (this is the precise half of the
             job; you supply the cm labels, which is the half a human is good at).
``solve``    fit the model above over the observation sets and report the
             effective HFOV, its disagreement with the assumed 90 deg, and what
             that does to C-01's 0.12 m threshold.

Capture talks to ROS; detect and solve are pure numpy/cv2 and run anywhere.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

# The pinhole the cage assumes — camera_geometry.CameraModel defaults. Kept as
# literals so this tool runs on the Jetson without the repo installed.
ASSUMED_HFOV_RAD = 1.5707963
ASSUMED_WIDTH_PX = 640
ASSUMED_HEIGHT_PX = 360
# camera_geometry.DEFAULT_CAMERA_PITCH_RAD — the URDF camera_link_lane mount.
DEFAULT_PITCH_RAD = 0.30
# The metric thresholds in cage/cage.yaml that a focal-length error corrupts.
# NOTE docs/17 §2 calls 0.12 m "C-01's threshold"; it is not. C-01 (and the
# C-03 mirror) use d_max_m = 0.16, traced to ODD-1.ROAD_WIDTH/2 - delta;
# 0.12 m is C-05's d_warning_m, part of the compound emergency trigger.
METRIC_THRESHOLDS_M = {
    "C-01 d_max_m": 0.16,
    "C-03 d_max_m": 0.16,
    "C-05 d_warning_m": 0.12,
    "state_validity lateral_offset_m": 0.30,
}
C01_THRESHOLD_M = METRIC_THRESHOLDS_M["C-01 d_max_m"]
DEFAULT_TOPIC = "camera/image_raw_lane"


def assumed_fx(width_px: int = ASSUMED_WIDTH_PX, hfov_rad: float = ASSUMED_HFOV_RAD) -> float:
    return (width_px / 2.0) / math.tan(hfov_rad / 2.0)


def hfov_from_fx(fx: float, width_px: int) -> float:
    return 2.0 * math.atan((width_px / 2.0) / fx)


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


# --------------------------------------------------------------------------
# capture / preview  (ROS 2 side)
# --------------------------------------------------------------------------

def _decode_image_msg(msg) -> np.ndarray:
    """sensor_msgs/Image -> BGR uint8 array. Mirrors camera_pipeline.decode_image."""
    enc = msg.encoding.lower()
    buf = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    if enc in ("bgr8", "rgb8"):
        chan = 3
    elif enc in ("mono8",):
        chan = 1
    else:
        raise ValueError(f"unsupported encoding {msg.encoding!r}")
    expected = msg.height * msg.step
    if buf.size != expected:
        raise ValueError(f"buffer {buf.size} != height*step {expected}")
    img = buf.reshape(msg.height, msg.step)[:, : msg.width * chan]
    img = img.reshape(msg.height, msg.width, chan)
    if enc == "rgb8":
        img = img[:, :, ::-1]
    elif enc == "mono8":
        img = np.repeat(img, 3, axis=2)
    return np.ascontiguousarray(img)


def _grab_frames(topic: str, n_frames: int, timeout_s: float) -> Tuple[List[np.ndarray], Dict]:
    """Collect n_frames from the image topic. Returns (frames, stats)."""
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from sensor_msgs.msg import Image

    frames: List[np.ndarray] = []
    stamps: List[float] = []
    encodings: set = set()
    shapes: set = set()

    rclpy.init(args=None)
    node = Node("calibrate_camera_hfov_capture")
    # The publisher is best-effort friendly; match loosely so we never miss it.
    qos = QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
    )

    def _cb(msg):
        if len(frames) >= n_frames:
            return
        try:
            frames.append(_decode_image_msg(msg))
        except ValueError as exc:
            node.get_logger().warn(f"dropped frame: {exc}")
            return
        stamps.append(msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9)
        encodings.add(msg.encoding)
        shapes.add((msg.height, msg.width))

    node.create_subscription(Image, topic, _cb, qos)

    t0 = time.time()
    while len(frames) < n_frames and (time.time() - t0) < timeout_s:
        rclpy.spin_once(node, timeout_sec=0.1)
    wall = time.time() - t0

    node.destroy_node()
    rclpy.shutdown()

    stats = {
        "topic": topic,
        "frames_requested": n_frames,
        "frames_received": len(frames),
        "wall_s": round(wall, 3),
        "encodings": sorted(encodings),
        "shapes": sorted(f"{h}x{w}" for h, w in shapes),
    }
    if len(stamps) >= 2:
        gaps = np.diff(np.array(stamps))
        gaps = gaps[gaps > 0]
        if gaps.size:
            stats["rate_hz_from_stamps"] = round(float(1.0 / gaps.mean()), 2)
            stats["max_stamp_gap_s"] = round(float(gaps.max()), 4)
    return frames, stats


def _stack(frames: Sequence[np.ndarray]) -> np.ndarray:
    """Per-pixel median across frames — kills sensor noise without blurring edges."""
    if not frames:
        raise RuntimeError("no frames captured")
    if len(frames) == 1:
        return frames[0].copy()
    return np.median(np.stack(frames, axis=0), axis=0).astype(np.uint8)


def _annotate(img: np.ndarray, band: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """Overlay a labelled column ruler + centre crosshair, so columns are readable."""
    out = img.copy()
    h, w = out.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    for u in range(0, w, 20):
        major = (u % 100 == 0)
        length = 14 if major else 6
        colour = (0, 255, 255) if major else (0, 180, 180)
        cv2.line(out, (u, 0), (u, length), colour, 1)
        cv2.line(out, (u, h - length), (u, h - 1), colour, 1)
        if major:
            cv2.putText(out, str(u), (max(u - 12, 1), length + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, colour, 1, cv2.LINE_AA)
    for v in range(0, h, 20):
        major = (v % 100 == 0)
        length = 14 if major else 6
        colour = (0, 255, 255) if major else (0, 180, 180)
        cv2.line(out, (0, v), (length, v), colour, 1)
        if major:
            cv2.putText(out, str(v), (length + 3, min(v + 4, h - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, colour, 1, cv2.LINE_AA)

    # Optical centre the pinhole model assumes (cx, cy) = (w/2, h/2).
    cv2.line(out, (int(cx), 0), (int(cx), h - 1), (0, 0, 255), 1)
    cv2.line(out, (0, int(cy)), (w - 1, int(cy)), (0, 0, 255), 1)

    if band is not None:
        v0, v1 = band
        cv2.rectangle(out, (0, v0), (w - 1, v1), (0, 255, 0), 1)
    return out


def cmd_capture(args: argparse.Namespace) -> int:
    if cv2 is None:
        print("ERROR: cv2 not available", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    frames, stats = _grab_frames(args.topic, args.frames, args.timeout)
    if not frames:
        print(f"ERROR: no frames on {args.topic} in {args.timeout}s — "
              "is csi_camera_node running, and is ROS_DOMAIN_ID right?", file=sys.stderr)
        return 1

    stacked = _stack(frames)
    band = tuple(args.band) if args.band else None
    label = args.label or "preview"
    raw_path = os.path.join(args.out, f"{label}_raw.png")
    ann_path = os.path.join(args.out, f"{label}_annotated.png")
    cv2.imwrite(raw_path, stacked)
    cv2.imwrite(ann_path, _annotate(stacked, band))

    meta = {
        "label": label,
        "distance_m": args.distance_m,
        "distance_reference": args.distance_reference,
        "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": _git_commit(),
        "raw_png": os.path.basename(raw_path),
        "annotated_png": os.path.basename(ann_path),
        "note": args.note,
        **stats,
    }
    meta_path = os.path.join(args.out, f"{label}_meta.json")
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, indent=2)

    h, w = stacked.shape[:2]
    print(f"captured {len(frames)}/{args.frames} frames  {w}x{h}  "
          f"enc={stats['encodings']}  rate~{stats.get('rate_hz_from_stamps', '?')} Hz")
    if (w, h) != (ASSUMED_WIDTH_PX, ASSUMED_HEIGHT_PX):
        print(f"WARNING: frame is {w}x{h}, not the 640x360 hard contract — "
              "cv_lane_estimator indexes its scan bands by camera.height_px, so "
              "this size silently mis-projects every ey/epsi.", file=sys.stderr)
    print(f"  raw       {raw_path}")
    print(f"  annotated {ann_path}")
    print(f"  meta      {meta_path}")
    return 0


# --------------------------------------------------------------------------
# detect  (pure cv2)
# --------------------------------------------------------------------------

def _subpixel_peak(profile: np.ndarray, i: int) -> float:
    """Parabolic interpolation around integer peak i."""
    if i <= 0 or i >= profile.size - 1:
        return float(i)
    a, b, c = float(profile[i - 1]), float(profile[i]), float(profile[i + 1])
    denom = a - 2.0 * b + c
    if abs(denom) < 1e-9:
        return float(i)
    return float(i) + 0.5 * (a - c) / denom


def detect_marks(
    img: np.ndarray,
    band: Tuple[int, int],
    mode: str = "edge",
    min_sep_px: int = 6,
    threshold: float = 3.0,
    max_marks: int = 60,
    vertical: bool = False,
) -> List[Dict]:
    """Locate tick marks in a band. Returns [{u_px, strength}] sorted by position.

    ``vertical=False`` scans a *row* band and returns columns — the lateral tape,
    for fx. ``vertical=True`` scans a *column* band and returns rows — the tape
    laid forward on the ground plane, for the pitch fit. The two are the same
    algorithm on a transposed image, so the key is reported as ``u_px`` either
    way and simply means "position along the scan".

    ``edge``  — peaks of |d/du| of the band-averaged intensity: any high-contrast
                feature across the tape (its printed tick marks, a pen, a taped
                paper marker).
    ``dark``  — centroids of runs darker than mean - threshold*std: for dark
                markers on a light background, more robust than edges when the
                marker is a few px wide.
    """
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float64)
    if vertical:
        grey = grey.T
    v0, v1 = int(band[0]), int(band[1])
    v0, v1 = max(0, min(v0, v1)), min(grey.shape[0], max(v0, v1) + 1)
    if v1 - v0 < 1:
        raise ValueError("empty band")
    prof = grey[v0:v1, :].mean(axis=0)
    prof = cv2.GaussianBlur(prof.reshape(1, -1), (5, 1), 0).ravel()

    if mode == "dark":
        mu, sd = prof.mean(), prof.std() or 1.0
        mask = prof < (mu - threshold * sd)
        marks = []
        i = 0
        while i < mask.size:
            if mask[i]:
                j = i
                while j < mask.size and mask[j]:
                    j += 1
                seg = prof[i:j]
                weight = (seg.max() - seg)
                if weight.sum() > 0:
                    u = i + float((np.arange(seg.size) * weight).sum() / weight.sum())
                else:
                    u = (i + j - 1) / 2.0
                marks.append({"u_px": round(u, 2), "strength": round(float(mu - seg.min()), 2)})
                i = j
            else:
                i += 1
    else:
        grad = np.abs(np.gradient(prof))
        mu, sd = grad.mean(), grad.std() or 1.0
        cut = mu + threshold * sd
        cand = [i for i in range(1, grad.size - 1)
                if grad[i] >= cut and grad[i] >= grad[i - 1] and grad[i] >= grad[i + 1]]
        cand.sort(key=lambda i: -grad[i])
        chosen: List[int] = []
        for i in cand:
            if all(abs(i - c) >= min_sep_px for c in chosen):
                chosen.append(i)
            if len(chosen) >= max_marks:
                break
        marks = [{"u_px": round(_subpixel_peak(grad, i), 2),
                  "strength": round(float(grad[i]), 2)} for i in sorted(chosen)]

    return sorted(marks, key=lambda m: m["u_px"])[:max_marks]


def cmd_detect(args: argparse.Namespace) -> int:
    if cv2 is None:
        print("ERROR: cv2 not available", file=sys.stderr)
        return 2
    img = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if img is None:
        print(f"ERROR: cannot read {args.image}", file=sys.stderr)
        return 1
    h, w = img.shape[:2]
    across = w if args.vertical else h   # the axis the band is cut from
    centre = h / 2.0 if args.vertical else w / 2.0
    band = tuple(args.band) if args.band else (across // 2 - 6, across // 2 + 6)
    marks = detect_marks(img, band, mode=args.mode, min_sep_px=args.min_sep,
                         threshold=args.threshold, max_marks=args.max_marks,
                         vertical=args.vertical)
    axis, centre_name = ("v (row)", "cy") if args.vertical else ("u (col)", "cx")
    band_axis = "u" if args.vertical else "v"
    print(f"# {os.path.basename(args.image)}  {w}x{h}  band {band_axis}={band[0]}..{band[1]}  "
          f"mode={args.mode}  axis={axis}  {len(marks)} marks")
    print(f"# {'idx':>3}  {'pos_px':>8}  {'pos-' + centre_name:>8}  {'strength':>8}")
    for k, m in enumerate(marks):
        print(f"  {k:>3}  {m['u_px']:>8.2f}  {m['u_px'] - centre:>8.2f}  {m['strength']:>8.2f}")

    if args.overlay:
        vis = _annotate(img, None if args.vertical else band)
        for m in marks:
            p = int(round(m["u_px"]))
            if args.vertical:
                cv2.line(vis, (band[0], p), (band[1], p), (255, 0, 255), 1)
            else:
                cv2.line(vis, (p, band[0]), (p, band[1]), (255, 0, 255), 1)
        if args.vertical:
            cv2.rectangle(vis, (band[0], 0), (band[1], h - 1), (0, 255, 0), 1)
        cv2.imwrite(args.overlay, vis)
        print(f"# overlay -> {args.overlay}")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"image": args.image, "band": list(band), "mode": args.mode,
                       "vertical": args.vertical, "width_px": w, "height_px": h,
                       "marks": marks}, fh, indent=2)
        print(f"# json    -> {args.json}")
    return 0


# --------------------------------------------------------------------------
# solve-pitch  —  docs/17 §2 [VERIFY] #2 (camera extrinsics)
# --------------------------------------------------------------------------

def _row_for_distance(x_m: np.ndarray, fy: float, cy: float, h_m: float,
                      theta: float) -> np.ndarray:
    """Image row of a ground point at forward distance x, for a pitch-only camera.

    Optical axis (cos t, 0, -sin t) and image-down (-sin t, 0, -cos t) in the
    vehicle frame put a ground point (x, 0, -h) at::

        z_o = x cos t + h sin t      y_o = h cos t - x sin t
        v   = cy + fy * y_o / z_o

    which is ``camera_geometry``'s ground projection written row-wise.
    """
    z_o = x_m * math.cos(theta) + h_m * math.sin(theta)
    y_o = h_m * math.cos(theta) - x_m * math.sin(theta)
    return cy + fy * (y_o / z_o)


def solve_pitch(marks: List[Dict], fy: float, cy: float, h_m: float,
                free_height: bool = False) -> Dict:
    """Fit the mount pitch from (tape reading, image row) pairs on the ground plane.

    Each mark is ``{"s_m": tape reading, "v_px": row}``; the tape's zero sits at an
    unknown distance from the camera, so the true forward distance is ``x = s + c``
    with ``c`` **fitted**, not measured. That is the same trick the fx step uses for
    the entrance pupil, and it means the only physical quantity you have to measure
    for this step is the camera height above the plane the tape lies on. A mark may
    instead carry ``x_m`` directly, in which case ``c`` is pinned to zero.

    The focal length comes from the fx step; one line of ground points cannot
    identify pitch, height and focal length at once. ``free_height`` additionally
    frees h as a consistency check against the tape reading — a large disagreement
    means the plane was not flat, the marks were mis-labelled, or fy is wrong.
    """
    if any("x_m" in m for m in marks):
        s = np.array([float(m["x_m"]) for m in marks], dtype=float)
        c_grid = np.array([0.0])
    else:
        s = np.array([float(m["s_m"]) for m in marks], dtype=float)
        c_grid = np.linspace(-0.40, 0.60, 1001)
    v = np.array([float(m["v_px"]) for m in marks], dtype=float)
    if s.size < 2:
        raise ValueError("need >= 2 marks")
    if s.size < 3 and c_grid.size > 1:
        raise ValueError("fitting the tape offset needs >= 3 marks")

    def sse_grid(thetas: np.ndarray, cs: np.ndarray, hh: float) -> np.ndarray:
        """Vectorised sum-of-squares over the (theta, c) grid."""
        x = s[None, None, :] + cs[None, :, None]          # (1, C, N)
        ct = np.cos(thetas)[:, None, None]
        st = np.sin(thetas)[:, None, None]
        z_o = x * ct + hh * st
        y_o = hh * ct - x * st
        with np.errstate(divide="ignore", invalid="ignore"):
            model = cy + fy * (y_o / z_o)
        bad = (z_o <= 1e-6) | ~np.isfinite(model) | (x <= 1e-6)
        model = np.where(bad, 1e9, model)
        return np.sum((model - v[None, None, :]) ** 2, axis=2)

    def best_for_height(hh: float) -> Tuple[float, float, float]:
        thetas = np.linspace(-0.6, 1.2, 901)
        cs = c_grid
        for _ in range(4):                                 # coarse -> fine
            sse = sse_grid(thetas, cs, hh)
            i, j = np.unravel_index(int(np.argmin(sse)), sse.shape)
            t_best, c_best, val = float(thetas[i]), float(cs[j]), float(sse[i, j])
            dt = (thetas[1] - thetas[0]) * 2 if thetas.size > 1 else 0.0
            dc = (cs[1] - cs[0]) * 2 if cs.size > 1 else 0.0
            thetas = np.linspace(t_best - dt, t_best + dt, 201) if dt else np.array([t_best])
            cs = np.linspace(c_best - dc, c_best + dc, 201) if dc else np.array([c_best])
        return val, t_best, c_best

    heights = np.array([h_m]) if not free_height else h_m * np.linspace(0.6, 1.6, 401)
    best = (float("inf"), DEFAULT_PITCH_RAD, 0.0, h_m)
    for hh in heights:
        val, t_best, c_best = best_for_height(float(hh))
        if val < best[0]:
            best = (val, t_best, c_best, float(hh))
    _, theta, c_off, hh = best

    x_true = s + c_off
    res = _row_for_distance(x_true, fy, cy, hh, theta) - v
    rms_px = float(np.sqrt(np.mean(res ** 2)))

    # Turn the pitch error into the number the cage cares about: how far off the
    # IPM's forward distance is at the near band it actually reads.
    x_probe = np.array([0.15, 0.25, 0.40, 0.60])
    v_meas = _row_for_distance(x_probe, fy, cy, hh, theta)
    v_asm = _row_for_distance(x_probe, fy, cy, hh, DEFAULT_PITCH_RAD)
    return {
        "pitch_measured_rad": round(theta, 5),
        "pitch_measured_deg": round(math.degrees(theta), 3),
        "pitch_assumed_rad": DEFAULT_PITCH_RAD,
        "pitch_assumed_deg": round(math.degrees(DEFAULT_PITCH_RAD), 3),
        "pitch_error_deg": round(math.degrees(theta - DEFAULT_PITCH_RAD), 3),
        "camera_height_m": round(hh, 5),
        "camera_height_free": bool(free_height),
        "camera_height_measured_m": round(h_m, 5),
        "tape_offset_m": round(c_off, 4),
        "tape_offset_fitted": bool(c_grid.size > 1),
        "distance_span_m": [round(float(x_true.min()), 3), round(float(x_true.max()), 3)],
        "fy_px": round(fy, 2),
        "cy_px": round(cy, 2),
        "n_marks": int(s.size),
        "residual_rms_px": round(rms_px, 3),
        "residual_max_px": round(float(np.max(np.abs(res))), 3),
        "row_shift_vs_assumed_px": {
            f"x={xx:.2f}m": round(float(a - b), 2)
            for xx, a, b in zip(x_probe, v_meas, v_asm)
        },
        "note": (
            "Pitch is a mount property, so a bench measurement transfers to the "
            "track; the height does not (measure it again above the floor with "
            "the car on its wheels)."),
    }


def cmd_solve_pitch(args: argparse.Namespace) -> int:
    with open(args.obs) as fh:
        doc = json.load(fh)
    fy = args.fx if args.fx is not None else float(doc.get("fx_px", assumed_fx()))
    cy = float(doc.get("cy_px", doc.get("height_px", ASSUMED_HEIGHT_PX) / 2.0))
    h_m = args.height_m if args.height_m is not None else float(doc["camera_height_m"])
    res = solve_pitch(doc["marks"], fy, cy, h_m, free_height=args.free_height)
    res["source_observations"] = os.path.abspath(args.obs)
    res["git_commit"] = _git_commit()
    res["solved_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    print("=" * 72)
    print("LANE CAMERA PITCH / EXTRINSICS — docs/17 §2 [VERIFY] #2")
    print("=" * 72)
    print(f"fy used           : {res['fy_px']:.2f} px   (from the fx step)")
    print(f"camera height     : {res['camera_height_m'] * 1000:.1f} mm"
          + ("  [fitted]" if args.free_height else "  [measured]"))
    if args.free_height:
        print(f"  vs tape measure : {res['camera_height_measured_m'] * 1000:.1f} mm")
    print(f"tape zero offset  : {res['tape_offset_m'] * 1000:+.1f} mm ahead of the camera"
          + ("  [fitted]" if res["tape_offset_fitted"] else "  [given]"))
    print(f"distance span     : {res['distance_span_m'][0]:.3f} .. "
          f"{res['distance_span_m'][1]:.3f} m")
    print(f"pitch measured    : {res['pitch_measured_rad']:.4f} rad "
          f"({res['pitch_measured_deg']:.2f} deg)")
    print(f"pitch assumed     : {res['pitch_assumed_rad']:.4f} rad "
          f"({res['pitch_assumed_deg']:.2f} deg)   "
          f"error {res['pitch_error_deg']:+.2f} deg")
    print(f"fit residual      : rms {res['residual_rms_px']:.2f} px, "
          f"max {res['residual_max_px']:.2f} px over {res['n_marks']} marks")
    print("row shift vs the pitch camera_geometry assumes:")
    for k, val in res["row_shift_vs_assumed_px"].items():
        print(f"    {k:>12} : {val:+.1f} px")
    print("=" * 72)
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(res, fh, indent=2)
        print(f"\nwrote {args.out}")
    return 0


# --------------------------------------------------------------------------
# solve
# --------------------------------------------------------------------------

def _fit_line(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, np.ndarray]:
    """Least-squares y = m*x + b. Returns (m, b, residuals)."""
    A = np.vstack([x, np.ones_like(x)]).T
    (m, b), *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(m), float(b), y - (m * x + b)


def solve_hfov(obs_sets: List[Dict], width_px: int, ground_plane: bool = True,
               pitch_rad: float = DEFAULT_PITCH_RAD, height_m: float = 0.0) -> Dict:
    """Fit fx (and the entrance-pupil offset) from the per-distance scale slopes.

    Each observation set: {"distance_m": D, "marks": [{"u_px": u, "y_m": y}, ...]}

    ``ground_plane`` (the default) accounts for the target lying **flat on the
    surface the car stands on**, with ``D`` measured as a horizontal forward
    distance. The lateral scale is set by the optical depth, not by ``D``::

        z_o = D cos(pitch) + H sin(pitch)

    so ``1/s = (cos(pitch)/fx) D + (H sin(pitch) + p cos(pitch))/fx`` and
    **fx = cos(pitch)/slope**. Ignoring the cosine biases fx by 1/cos(pitch) —
    +4.7 % at the assumed 0.30 rad, which alone would exceed the 2 % "confirmed"
    band of this protocol's decision rule. Pass ``ground_plane=False`` only if the
    target was held perpendicular to the *optical axis* rather than flat.

    The pitch enters only through its cosine, so it barely matters: a 3 deg pitch
    error moves fx by 0.3 %. Take it from Part B and, if you like, iterate once.
    """
    per_distance = []
    for s in obs_sets:
        marks = s["marks"]
        if len(marks) < 2:
            raise ValueError(f"distance {s['distance_m']} m has <2 marks")
        y = np.array([float(m["y_m"]) for m in marks])
        u = np.array([float(m["u_px"]) for m in marks])
        slope, intercept, resid = _fit_line(y, u)  # u = s*y + b, s in px/m
        rms = float(np.sqrt(np.mean(resid ** 2)))
        per_distance.append({
            "distance_m": float(s["distance_m"]),
            "n_marks": len(marks),
            "slope_px_per_m": round(slope, 3),
            "intercept_px": round(intercept, 2),
            "residual_rms_px": round(rms, 3),
            "residual_max_px": round(float(np.max(np.abs(resid))), 3),
            # A pinhole makes this line straight; what is left is lens distortion,
            # expressed as the lateral metric error it injects at this distance.
            "residual_max_m": round(float(np.max(np.abs(resid))) / abs(slope), 5),
            "label": s.get("label", ""),
        })

    D = np.array([d["distance_m"] for d in per_distance])
    S = np.array([d["slope_px_per_m"] for d in per_distance])
    if np.any(S == 0):
        raise ValueError("degenerate slope (0 px/m)")
    inv_s = 1.0 / S

    result: Dict = {"per_distance": per_distance}
    if len(per_distance) >= 2:
        # 1/s = D/fx + delta/fx  ->  slope 1/fx, intercept delta/fx
        m, b, resid = _fit_line(D, inv_s)
        if m <= 0:
            raise ValueError(
                "non-physical fit (1/slope decreasing with distance) — check that "
                "distances and tape readings are not swapped or mis-signed")
        cos_p = math.cos(pitch_rad) if ground_plane else 1.0
        fx = cos_p / m
        delta = (b * fx - height_m * math.sin(pitch_rad)) / cos_p if ground_plane else b * fx
        result.update({
            "method": ("multi-distance, target flat on the ground plane"
                       if ground_plane else
                       "multi-distance, target perpendicular to the optical axis"),
            "fx_px": fx,
            "entrance_pupil_offset_m": delta,
            "pitch_used_rad": pitch_rad if ground_plane else None,
            "invslope_fit_residual_rms": float(np.sqrt(np.mean(resid ** 2))),
            "n_distances": len(per_distance),
        })
    else:
        d0 = per_distance[0]
        cos_p = math.cos(pitch_rad) if ground_plane else 1.0
        z_o = d0["distance_m"] * cos_p + height_m * math.sin(pitch_rad)
        fx = d0["slope_px_per_m"] * z_o
        result.update({
            "method": "single-distance (entrance-pupil offset assumed 0)",
            "fx_px": fx,
            "entrance_pupil_offset_m": 0.0,
            "pitch_used_rad": pitch_rad if ground_plane else None,
            "n_distances": 1,
            "caveat": (
                "A SINGLE DISTANCE DOES NOT IDENTIFY fx. Verified by Monte Carlo: "
                "with one image the fit is degenerate — a wrong fx is absorbed by "
                "the height/pitch/pose and still fits to zero residual. Varying D "
                "is what breaks the degeneracy. This number is a rough indication "
                "only; capture at least two well-separated distances."),
        })

    fx_meas = result["fx_px"]
    hfov_meas = hfov_from_fx(fx_meas, width_px)
    fx_asm = assumed_fx(width_px)
    scale = fx_asm / fx_meas  # ey_true = ey_reported * fx_assumed / fx_measured

    result.update({
        "width_px": width_px,
        "fx_px": round(fx_meas, 2),
        "entrance_pupil_offset_m": round(result["entrance_pupil_offset_m"], 4),
        "hfov_measured_rad": round(hfov_meas, 6),
        "hfov_measured_deg": round(math.degrees(hfov_meas), 3),
        "hfov_assumed_deg": round(math.degrees(ASSUMED_HFOV_RAD), 3),
        "fx_assumed_px": round(fx_asm, 2),
        "hfov_error_deg": round(math.degrees(hfov_meas - ASSUMED_HFOV_RAD), 3),
        "metric_scale_error": round(scale, 4),
        "metric_scale_error_pct": round((scale - 1.0) * 100.0, 2),
        # The number the cage actually cares about: what 0.12 m has been meaning.
        "c01_effective_threshold_m": round(C01_THRESHOLD_M * scale, 4),
    })
    return result


def _report(res: Dict) -> str:
    L = []
    L.append("=" * 72)
    L.append("LANE CAMERA HFOV CALIBRATION — docs/17 §2 [VERIFY] #1")
    L.append("=" * 72)
    L.append(f"method            : {res['method']}")
    L.append(f"observation sets  : {res['n_distances']} distance(s)")
    L.append("")
    L.append(f"{'D [m]':>8}  {'marks':>5}  {'slope [px/m]':>13}  {'resid rms [px]':>14}  "
             f"{'resid max [px]':>14}  {'-> [mm]':>8}")
    for d in res["per_distance"]:
        L.append(f"{d['distance_m']:>8.3f}  {d['n_marks']:>5}  {d['slope_px_per_m']:>13.2f}  "
                 f"{d['residual_rms_px']:>14.3f}  {d['residual_max_px']:>14.3f}  "
                 f"{d['residual_max_m'] * 1000:>8.1f}")
    L.append("")
    L.append(f"fx measured       : {res['fx_px']:.2f} px      (assumed {res['fx_assumed_px']:.2f} px)")
    L.append(f"entrance-pupil off: {res['entrance_pupil_offset_m'] * 1000:+.1f} mm "
             "(from the face you measured D against)")
    L.append(f"HFOV measured     : {res['hfov_measured_deg']:.2f} deg  "
             f"(assumed {res['hfov_assumed_deg']:.2f} deg, "
             f"error {res['hfov_error_deg']:+.2f} deg)")
    L.append("")
    L.append("CONSEQUENCE FOR THE CAGE")
    L.append(f"  every metric ey the IPM reports is off by a factor "
             f"{res['metric_scale_error']:.4f} ({res['metric_scale_error_pct']:+.2f} %)")
    for k, v in METRIC_THRESHOLDS_M.items():
        L.append(f"  {k:>32} : {v:.3f} m  ->  {v * res['metric_scale_error']:.4f} m")
    if "caveat" in res:
        L.append("")
        L.append(f"CAVEAT: {res['caveat']}")
    L.append("=" * 72)
    return "\n".join(L)


def cmd_solve(args: argparse.Namespace) -> int:
    with open(args.obs) as fh:
        doc = json.load(fh)
    obs_sets = doc["observation_sets"] if isinstance(doc, dict) else doc
    width_px = int(doc.get("width_px", ASSUMED_WIDTH_PX)) if isinstance(doc, dict) else ASSUMED_WIDTH_PX
    pitch = args.pitch_rad if args.pitch_rad is not None else float(
        doc.get("pitch_rad", DEFAULT_PITCH_RAD)) if isinstance(doc, dict) else DEFAULT_PITCH_RAD
    height = args.height_m if args.height_m is not None else float(
        doc.get("camera_height_m", 0.0)) if isinstance(doc, dict) else 0.0
    res = solve_hfov(obs_sets, width_px, ground_plane=not args.perpendicular,
                     pitch_rad=pitch, height_m=height)
    res["source_observations"] = os.path.abspath(args.obs)
    res["git_commit"] = _git_commit()
    res["solved_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(_report(res))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(res, fh, indent=2)
        print(f"\nwrote {args.out}")
    return 0


# --------------------------------------------------------------------------
# checkerboard route — the standard method, and the one that needs no measured
# distance at all. Many views of a known planar grid over-determine fx, fy, cx,
# cy AND the distortion coefficients, so none of the failure modes that sank the
# tape route (blade bow, target yaw, single-image degeneracy) apply.
# --------------------------------------------------------------------------

def cmd_board(args: argparse.Namespace) -> int:
    """Render a checkerboard PNG to display full-screen on a flat monitor."""
    if cv2 is None:
        print("ERROR: cv2 not available", file=sys.stderr)
        return 2
    cols, rows = args.cols, args.rows            # inner corners
    sq = args.square_px
    w, h = (cols + 1) * sq, (rows + 1) * sq
    board = np.zeros((h, w), np.uint8)
    for i in range(rows + 1):
        for j in range(cols + 1):
            if (i + j) % 2 == 0:
                board[i * sq:(i + 1) * sq, j * sq:(j + 1) * sq] = 255
    canvas = np.full((h + 2 * args.margin_px, w + 2 * args.margin_px), 255, np.uint8)
    canvas[args.margin_px:args.margin_px + h, args.margin_px:args.margin_px + w] = board
    cv2.imwrite(args.out, canvas)
    print(f"wrote {args.out}  ({canvas.shape[1]}x{canvas.shape[0]} px)")
    print(f"  inner corners : {cols} x {rows}   (this is what --cols/--rows mean)")
    print(f"  square        : {sq} screen px")
    print("Display it FULL SCREEN with no scaling, then measure the side of one")
    print("square with the tape — best accuracy is measuring across N squares and")
    print("dividing. Pass that as --square-m to board-solve.")
    return 0


def cmd_board_capture(args: argparse.Namespace) -> int:
    """Collect checkerboard views from the live topic, keeping only spread poses."""
    if cv2 is None:
        print("ERROR: cv2 not available", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    pattern = (args.cols, args.rows)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from sensor_msgs.msg import Image

    latest: List[np.ndarray] = []

    def _cb(msg):
        try:
            del latest[:]
            latest.append(_decode_image_msg(msg))
        except ValueError:
            pass

    # One node held open for the whole session — re-initialising rclpy per frame
    # both thrashes the Jetson and trips repeated-init errors.
    rclpy.init(args=None)
    node = Node("calibrate_camera_hfov_board")
    node.create_subscription(
        Image, args.topic, _cb,
        QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                   history=HistoryPolicy.KEEP_LAST, depth=2))

    kept: List[np.ndarray] = []
    centres: List[Tuple[float, float]] = []
    t_end = time.time() + args.seconds
    n_seen = 0
    print(f"watching {args.topic} for {args.seconds:.0f}s — move and TILT the board")
    while time.time() < t_end and len(kept) < args.views:
        rclpy.spin_once(node, timeout_sec=0.2)
        if not latest:
            continue
        img = latest.pop()
        n_seen += 1
        grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(grey, pattern, flags)
        if not found:
            continue
        pts = corners.reshape(-1, 2)
        c = pts.mean(axis=0)
        # Keep a view only if it is meaningfully different from the ones we have —
        # 20 near-identical views constrain nothing. Position alone is too crude a
        # signature: a board rotated in place is a genuinely new constraint while
        # its centre barely moves, and tilt is exactly what this calibration is
        # short of. So the signature also carries the board's apparent extent,
        # which encodes how far it is and how steeply it is inclined.
        bb = pts.max(axis=0) - pts.min(axis=0)
        sig = np.array([c[0], c[1], bb[0], bb[1]], dtype=float)
        if any(float(np.linalg.norm(sig - p)) < args.min_move_px for p in centres):
            continue
        cv2.cornerSubPix(grey, corners, (5, 5), (-1, -1),
                         (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01))
        kept.append(corners)
        centres.append(sig)
        path = os.path.join(args.out, f"view_{len(kept):02d}.png")
        cv2.imwrite(path, img)
        vis = img.copy()
        cv2.drawChessboardCorners(vis, pattern, corners, True)
        cv2.imwrite(os.path.join(args.out, f"view_{len(kept):02d}_corners.png"), vis)
        print(f"  kept view {len(kept):2d}/{args.views}  centre ({c[0]:6.1f},{c[1]:6.1f})"
              f"  extent {bb[0]:5.0f}x{bb[1]:4.0f} px", flush=True)

    node.destroy_node()
    rclpy.shutdown()
    print(f"\n{len(kept)} usable views from {n_seen} frames -> {args.out}")
    if len(kept) < 8:
        print("WARNING: fewer than 8 well-spread views — move the board to more "
              "positions AND tilt it; tilt is what separates focal length from "
              "distance.", file=sys.stderr)
    return 0 if kept else 1


def cmd_board_solve(args: argparse.Namespace) -> int:
    if cv2 is None:
        print("ERROR: cv2 not available", file=sys.stderr)
        return 2
    import glob
    paths = sorted(p for p in glob.glob(os.path.join(args.views, "view_*.png"))
                   if not p.endswith("_corners.png"))
    if not paths:
        print(f"ERROR: no view_*.png in {args.views}", file=sys.stderr)
        return 1
    pattern = (args.cols, args.rows)
    objp = np.zeros((args.cols * args.rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:args.cols, 0:args.rows].T.reshape(-1, 2) * args.square_m

    obj_pts, img_pts, used = [], [], []
    size = None
    for p in paths:
        img = cv2.imread(p)
        grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        size = grey.shape[::-1]
        found, corners = cv2.findChessboardCorners(
            grey, pattern, cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
        if not found:
            continue
        cv2.cornerSubPix(grey, corners, (5, 5), (-1, -1),
                         (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01))
        obj_pts.append(objp)
        img_pts.append(corners)
        used.append(os.path.basename(p))
    if len(obj_pts) < 4:
        print(f"ERROR: only {len(obj_pts)} views with a detected board", file=sys.stderr)
        return 1

    w, h = size
    # Free-aspect solve first, purely as a CONDITIONING PROBE. The lane pipeline
    # resizes 1280x720 -> 640x360 with an isotropic INTER_AREA, so the pixels are
    # square and fy must equal fx; camera_geometry.CameraModel asserts exactly
    # that. A free-aspect fit that disagrees is therefore not telling us about the
    # lens, it is telling us the views do not constrain the solution.
    free = cv2.calibrateCamera(obj_pts, img_pts, size, None, None)
    aspect = float(free[1][1, 1] / free[1][0, 0])

    if args.free_aspect:
        rms, K, dist, rvecs, tvecs = free
    else:
        K0 = np.array([[600.0, 0, w / 2.0], [0, 600.0, h / 2.0], [0, 0, 1.0]])
        rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
            obj_pts, img_pts, size, K0, None, flags=cv2.CALIB_FIX_ASPECT_RATIO)
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]

    # Coverage diagnostics — the thing that actually decides whether the answer
    # means anything. Corners must reach the edges, and the views must be tilted.
    all_c = np.concatenate([c.reshape(-1, 2) for c in img_pts], axis=0)
    cover = {
        "u_span_frac": round(float((all_c[:, 0].max() - all_c[:, 0].min()) / w), 3),
        "v_span_frac": round(float((all_c[:, 1].max() - all_c[:, 1].min()) / h), 3),
    }
    # occupancy over a 4x4 grid of the image
    gx = np.clip((all_c[:, 0] / w * 4).astype(int), 0, 3)
    gy = np.clip((all_c[:, 1] / h * 4).astype(int), 0, 3)
    cover["grid_cells_hit"] = int(len(set(zip(gx.tolist(), gy.tolist()))))
    # tilt spread: angle between each board normal and the optical axis
    tilts = []
    for rv in rvecs:
        R, _ = cv2.Rodrigues(rv)
        tilts.append(math.degrees(math.acos(min(1.0, abs(float(R[2, 2]))))))
    cover["tilt_deg_min"] = round(float(np.min(tilts)), 1)
    cover["tilt_deg_max"] = round(float(np.max(tilts)), 1)
    cover["tilt_deg_spread"] = round(float(np.max(tilts) - np.min(tilts)), 1)

    problems = []
    if abs(aspect - 1.0) > 0.05:
        problems.append(
            f"free-aspect fy/fx = {aspect:.2f}, but this pipeline has square pixels. "
            "The views do not constrain the solution — add spread and tilt.")
    if rms > 0.5:
        problems.append(f"rms reprojection {rms:.3f} px > 0.5 px.")
    if cover["grid_cells_hit"] < 10:
        problems.append(
            f"corners reach only {cover['grid_cells_hit']}/16 image regions — the "
            "distortion coefficients are extrapolated where the board never went.")
    if cover["tilt_deg_spread"] < 25:
        problems.append(
            f"tilt spread only {cover['tilt_deg_spread']:.0f} deg — tilt is what "
            "separates focal length from distance.")
    if len(obj_pts) < 10:
        problems.append(f"only {len(obj_pts)} views.")
    hfov = hfov_from_fx(fx, w)
    fx_asm = assumed_fx(w)
    scale = fx_asm / fx

    # Per-view reprojection error, so one bad view cannot hide in the mean.
    per_view = []
    for i in range(len(obj_pts)):
        proj, _ = cv2.projectPoints(obj_pts[i], rvecs[i], tvecs[i], K, dist)
        e = float(np.sqrt(np.mean(np.sum((proj.reshape(-1, 2) - img_pts[i].reshape(-1, 2)) ** 2, axis=1))))
        per_view.append({"view": used[i], "reproj_px": round(e, 3)})

    # How far the measured lens is from the zero-distortion pinhole the IPM
    # assumes — expressed where it matters, as pixel displacement in the image.
    corners_uv = np.array([[[0.0, 0.0]], [[w - 1.0, 0.0]], [[0.0, h - 1.0]],
                           [[w - 1.0, h - 1.0]], [[w / 2, h - 1.0]]], np.float32)
    undist = cv2.undistortPoints(corners_uv, K, dist, P=K).reshape(-1, 2)
    disp = [round(float(math.hypot(u - c[0][0], v - c[0][1])), 2)
            for (u, v), c in zip(undist, corners_uv)]

    res = {
        "method": "checkerboard, cv2.calibrateCamera",
        "n_views_used": len(obj_pts), "n_views_found": len(paths),
        "views": per_view,
        "aspect_free_fy_over_fx": round(aspect, 4),
        "aspect_fixed": not args.free_aspect,
        "coverage": cover,
        "conditioning_problems": problems,
        "trustworthy": not problems,
        "square_m": args.square_m,
        "pattern_inner_corners": [args.cols, args.rows],
        "width_px": w, "height_px": h,
        "rms_reprojection_px": round(float(rms), 4),
        "fx_px": round(float(fx), 2), "fy_px": round(float(fy), 2),
        "cx_px": round(float(cx), 2), "cy_px": round(float(cy), 2),
        "cx_assumed_px": w / 2.0, "cy_assumed_px": h / 2.0,
        "distortion_plumb_bob": [round(float(x), 5) for x in dist.ravel()],
        "hfov_measured_deg": round(math.degrees(hfov), 3),
        "hfov_assumed_deg": round(math.degrees(ASSUMED_HFOV_RAD), 3),
        "hfov_error_deg": round(math.degrees(hfov - ASSUMED_HFOV_RAD), 3),
        "fx_assumed_px": round(fx_asm, 2),
        "metric_scale_error": round(scale, 4),
        "metric_scale_error_pct": round((scale - 1.0) * 100.0, 2),
        "c01_effective_threshold_m": round(C01_THRESHOLD_M * scale, 4),
        "effective_thresholds_m": {k: round(v * scale, 4)
                                   for k, v in METRIC_THRESHOLDS_M.items()},
        "distortion_displacement_px": {
            "top_left": disp[0], "top_right": disp[1], "bottom_left": disp[2],
            "bottom_right": disp[3], "bottom_centre": disp[4]},
        "git_commit": _git_commit(),
        "solved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    print("=" * 72)
    print("LANE CAMERA INTRINSICS — checkerboard — docs/17 §2 [VERIFY] #1")
    print("=" * 72)
    print(f"views used        : {res['n_views_used']} of {res['n_views_found']}")
    print(f"rms reprojection  : {res['rms_reprojection_px']:.3f} px  "
          f"(> ~0.5 px means the views or the square size are suspect)")
    print(f"fx / fy           : {fx:.2f} / {fy:.2f} px   (pinhole assumes {fx_asm:.2f})")
    print(f"cx / cy           : {cx:.2f} / {cy:.2f} px   (assumes {w/2:.1f} / {h/2:.1f})")
    print(f"HFOV measured     : {res['hfov_measured_deg']:.2f} deg  "
          f"(assumed {res['hfov_assumed_deg']:.2f}, error {res['hfov_error_deg']:+.2f})")
    print(f"distortion        : {res['distortion_plumb_bob']}")
    print("")
    print("CONSEQUENCE FOR THE CAGE")
    print(f"  metric ey scale error {res['metric_scale_error']:.4f} "
          f"({res['metric_scale_error_pct']:+.2f} %)")
    print("  what each metric cage threshold really means on this camera:")
    for k, v in METRIC_THRESHOLDS_M.items():
        print(f"      {k:>32} : {v:.3f} m  ->  {v * scale:.4f} m")
    print("  pixel displacement between the real lens and the IPM's ideal pinhole:")
    for k, v in res["distortion_displacement_px"].items():
        print(f"      {k:>14} : {v:6.2f} px")
    print("")
    print("CONDITIONING")
    print(f"  free-aspect fy/fx : {aspect:.3f}   (must be ~1.00 — square pixels)")
    print(f"  corner coverage   : {cover['grid_cells_hit']}/16 image regions, "
          f"u span {cover['u_span_frac']:.2f}, v span {cover['v_span_frac']:.2f}")
    print(f"  board tilt        : {cover['tilt_deg_min']:.0f}..{cover['tilt_deg_max']:.0f} deg "
          f"(spread {cover['tilt_deg_spread']:.0f})")
    if problems:
        print("")
        print("  *** NOT TRUSTWORTHY — do not quote these numbers ***")
        for p in problems:
            print(f"    - {p}")
    else:
        print("  all conditioning checks passed")
    print("=" * 72)
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(res, fh, indent=2)
        print(f"\nwrote {args.out}")
    return 0 if not problems else 3


# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n")[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, help_ in (("preview", "grab a frame to check framing"),
                        ("capture", "grab an observation set at a measured distance")):
        c = sub.add_parser(name, help=help_)
        c.add_argument("--out", default="experiments/calibration/M6_camera_hfov")
        c.add_argument("--topic", default=DEFAULT_TOPIC)
        c.add_argument("--frames", type=int, default=15,
                       help="frames to median-stack (default 15)")
        c.add_argument("--timeout", type=float, default=20.0)
        c.add_argument("--label", default=None, help="e.g. d030 for D=0.30 m")
        c.add_argument("--distance-m", type=float, default=None,
                       help="measured distance to the tape (required for capture)")
        c.add_argument("--distance-reference", default="lens front face",
                       help="the face D was measured from — must be identical across sets")
        c.add_argument("--band", type=int, nargs=2, metavar=("V0", "V1"), default=None)
        c.add_argument("--note", default="")
        c.set_defaults(func=cmd_capture)

    c = sub.add_parser("detect", help="find tick marks in a band of a captured PNG")
    c.add_argument("image")
    c.add_argument("--band", type=int, nargs=2, metavar=("A0", "A1"), default=None,
                   help="band to scan (default: 12 px around the image centre)")
    c.add_argument("--vertical", action="store_true",
                   help="scan a COLUMN band and return rows — the forward tape, "
                        "for solve-pitch (default: row band -> columns, for solve)")
    c.add_argument("--mode", choices=["edge", "dark"], default="edge")
    c.add_argument("--min-sep", type=int, default=6, help="min px between marks")
    c.add_argument("--threshold", type=float, default=3.0, help="sigma above background")
    c.add_argument("--max-marks", type=int, default=60)
    c.add_argument("--overlay", default=None, help="write an annotated PNG here")
    c.add_argument("--json", default=None, help="write detections here")
    c.set_defaults(func=cmd_detect)

    c = sub.add_parser("solve", help="fit fx / HFOV from the observation sets")
    c.add_argument("obs", help="observations JSON (see docs — M6 protocol)")
    c.add_argument("--perpendicular", action="store_true",
                   help="target was held perpendicular to the OPTICAL AXIS; default "
                        "assumes it lay flat on the ground plane (fx = cos(pitch)/slope)")
    c.add_argument("--pitch-rad", type=float, default=None,
                   help=f"mount pitch for the ground-plane correction (default {DEFAULT_PITCH_RAD})")
    c.add_argument("--height-m", type=float, default=None,
                   help="camera height above the target's plane (refines the pupil offset only)")
    c.add_argument("--out", default=None, help="write the result JSON here")
    c.set_defaults(func=cmd_solve)

    c = sub.add_parser("solve-pitch", help="fit the mount pitch from the forward tape")
    c.add_argument("obs", help="observations JSON with camera_height_m + marks[{x_m,v_px}]")
    c.add_argument("--fx", type=float, default=None,
                   help="focal length in px from the solve step (square pixels -> fy=fx)")
    c.add_argument("--height-m", type=float, default=None,
                   help="camera height above the plane the tape lies on")
    c.add_argument("--free-height", action="store_true",
                   help="also fit the height, as a check against the tape reading")
    c.add_argument("--out", default=None, help="write the result JSON here")
    c.set_defaults(func=cmd_solve_pitch)

    c = sub.add_parser("board", help="render a checkerboard PNG for a monitor")
    c.add_argument("--out", default="checkerboard.png")
    c.add_argument("--cols", type=int, default=9, help="INNER corners across")
    c.add_argument("--rows", type=int, default=6, help="INNER corners down")
    c.add_argument("--square-px", type=int, default=110)
    c.add_argument("--margin-px", type=int, default=60)
    c.set_defaults(func=cmd_board)

    c = sub.add_parser("board-capture", help="collect checkerboard views from the topic")
    c.add_argument("--out", default="experiments/calibration/M6_camera_hfov/board_views")
    c.add_argument("--topic", default=DEFAULT_TOPIC)
    c.add_argument("--cols", type=int, default=9)
    c.add_argument("--rows", type=int, default=6)
    c.add_argument("--views", type=int, default=20)
    c.add_argument("--seconds", type=float, default=180.0)
    c.add_argument("--min-move-px", type=float, default=30.0,
                   help="reject a view this close to a kept one in (centre, extent) space")
    c.set_defaults(func=cmd_board_capture)

    c = sub.add_parser("board-solve", help="run cv2.calibrateCamera over the views")
    c.add_argument("views", help="directory of view_*.png")
    c.add_argument("--cols", type=int, default=9)
    c.add_argument("--rows", type=int, default=6)
    c.add_argument("--square-m", type=float, required=True,
                   help="physical side of one square, in metres")
    c.add_argument("--free-aspect", action="store_true",
                   help="let fy differ from fx. Default fixes fy=fx, which this "
                        "pipeline guarantees (isotropic 1280x720->640x360 resize); "
                        "the free-aspect solve is still run as a conditioning probe")
    c.add_argument("--out", default=None)
    c.set_defaults(func=cmd_board_solve)

    args = p.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "capture" and args.distance_m is None:
        p.error("capture requires --distance-m (preview does not)")
    if args.cmd == "capture" and not args.label:
        args.label = f"d{int(round(args.distance_m * 100)):03d}"
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
