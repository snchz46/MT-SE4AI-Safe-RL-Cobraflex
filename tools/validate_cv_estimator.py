#!/usr/bin/env python3
"""Validate the cage's CV lane-estimator against the sim ground-truth oracle.

D-43's stated verification plan: in simulation, ground truth (the
PolylineTracker over /odom_truth) is the *oracle* that measures the CV
estimator's error before the cage is allowed to rely on it. This tool:

1. teleports the robot to a grid of poses (centerline arc-length × lateral
   offset × heading error) on the running oval world,
2. at each pose captures a camera frame, runs `CvLaneEstimator`, and compares
   (ey, epsi) against the oracle's true values,
3. repeats a reduced grid under each visual degradation mode/level
   (applied to the frame exactly as the runtime injector would, before the
   estimator — the D-43 common-cause path),
4. writes per-sample rows (CSV) + a summary (JSON) + full repro metadata into
   an `experiments/sim/runs/<run_id>/` directory.

Run with the sim up (e.g. via tools/cam_evidence_session-style launch):
    ros2 launch cobraflex gazebo_mesh.launch.py gui:=false rviz:=false &
    python3 tools/validate_cv_estimator.py --out-root experiments/sim/runs
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "cobraflex_rl"))

import rclpy  # noqa: E402

from cobraflex_rl.camera_geometry import CameraModel  # noqa: E402
from cobraflex_rl.cv_lane_estimator import CvLaneEstimator  # noqa: E402
from cobraflex_rl.polyline_tracker import PolylineTracker  # noqa: E402
from cobraflex_rl.ros_interface import RosGazeboInterface  # noqa: E402
from cobraflex_rl.visual_degradation import degrade  # noqa: E402

CENTERLINE = REPO / "src" / "cobraflex_rl" / "config" / "oval_right_lane_centerline.yaml"
WORLD = REPO / "src" / "cobraflex" / "worlds" / "lane_following_oval.world"
CAGE_YAML = REPO / "cage" / "cage.yaml"

# Reduced-grid degradation conditions (mode, level). Levels chosen to span
# the SC-PERT envelope: mid + high for the H-10 trio, the scenario level for
# the H-11/H-12 eval stressors.
DEGRADATIONS = [
    ("glare_overexposure", 0.3),
    ("glare_overexposure", 0.6),
    ("low_light_underexposure", 0.3),
    ("low_light_underexposure", 0.6),
    ("motion_blur", 0.5),
    ("occlusion", 0.5),
    ("false_lane", 0.8),
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()


def pose_grid(tracker: PolylineTracker, n_s: int, offsets, headings):
    """(x, y, yaw, s, ey_cmd, epsi_cmd) teleport targets along the centerline."""
    total = float(tracker.cumulative_lengths[-1])
    targets = []
    for i in range(n_s):
        s = total * i / n_s
        for ey in offsets:
            for dpsi in headings:
                x, y, heading = tracker.pose_at_arclength(s, float(ey))
                targets.append((x, y, heading + dpsi, s, float(ey), float(dpsi)))
    return targets


def settle_at(iface: RosGazeboInterface, x, y, yaw, tol=0.05, attempts=10):
    iface.set_vehicle_pose(x, y, yaw)
    for _ in range(attempts):
        iface.spin_wall(0.15)
        try:
            iface.calibrate_pose_offset(x, y, yaw)
        except RuntimeError:
            continue
        iface.spin_wall(0.1)
        try:
            px, py, _ = iface.get_pose()
        except RuntimeError:
            continue
        if math.hypot(px - x, py - y) <= tol:
            return True
    return False


def fresh_frame(iface: RosGazeboInterface, timeout=3.0):
    iface.clear_camera_frame()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        iface.spin_wall(0.05)
        result = iface.get_camera_frame()
        if result is not None:
            return result[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default=str(REPO / "experiments" / "sim" / "runs"))
    parser.add_argument("--n-s", type=int, default=20, help="arc-length samples (clean grid)")
    parser.add_argument("--n-s-degraded", type=int, default=6)
    parser.add_argument("--camera-topic", default="/camera/image_raw")
    args = parser.parse_args()

    cfg = yaml.safe_load(CENTERLINE.read_text())
    points = np.asarray(cfg["centerline"]["points"], dtype=float)
    tracker = PolylineTracker(points)

    run_id = "cv_estimator_val_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    rclpy.init()
    iface = RosGazeboInterface(camera_topic=args.camera_topic)
    if not iface.wait_for_initial_data(timeout_sec=15.0):
        print("ERROR: no /odom_truth data; is the sim running?", file=sys.stderr)
        return 1

    estimator = CvLaneEstimator(CameraModel())

    offsets = (-0.06, 0.0, 0.06)
    headings = (-0.15, 0.0, 0.15)
    clean_grid = pose_grid(tracker, args.n_s, offsets, headings)
    degr_grid = pose_grid(tracker, args.n_s_degraded, (0.0,), (0.0,))

    rows = []
    conditions = [("clean", 0.0, clean_grid)] + [
        (mode, level, degr_grid) for mode, level in DEGRADATIONS
    ]
    t_start = time.monotonic()
    for mode, level, grid in conditions:
        for x, y, yaw, s, ey_cmd, dpsi_cmd in grid:
            if not settle_at(iface, x, y, yaw):
                rows.append(dict(mode=mode, level=level, s=s, settle_failed=1))
                continue
            frame = fresh_frame(iface)
            if frame is None:
                rows.append(dict(mode=mode, level=level, s=s, no_frame=1))
                continue
            # Oracle truth from the settled pose (not the commanded one).
            px, py, pyaw = iface.get_pose()
            tracker.reset_tracking()
            truth = tracker.track(px, py, pyaw)
            if mode != "clean":
                frame = degrade(frame, mode, level)
            est = estimator.estimate(frame)
            rows.append(
                dict(
                    mode=mode,
                    level=level,
                    s=round(s, 3),
                    ey_true=round(float(truth.ey), 5),
                    epsi_true=round(float(truth.epsi), 5),
                    ok=int(est.ok),
                    ey_est=round(est.ey, 5) if est.ok else "",
                    epsi_est=round(est.epsi, 5) if est.ok else "",
                    lane_width_est=round(est.lane_width, 5) if est.ok else "",
                    curvature_est=round(est.curvature, 5) if est.ok else "",
                    confidence=round(est.confidence, 4),
                    n_lines=est.n_lines,
                    reason=est.reason,
                    ey_err=round(est.ey - float(truth.ey), 5) if est.ok else "",
                    epsi_err=round(est.epsi - float(truth.epsi), 5) if est.ok else "",
                )
            )
        done = sum(1 for r in rows)
        print(f"[{time.monotonic()-t_start:7.1f}s] {mode} level={level}: {done} samples total")

    # ----- write per-sample CSV
    fieldnames = sorted({k for r in rows for k in r})
    with (out_dir / "samples.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # ----- summary per condition
    def stats(vals):
        if not vals:
            return None
        arr = np.array(vals, dtype=float)
        return dict(
            n=len(arr),
            bias=float(arr.mean()),
            mae=float(np.abs(arr).mean()),
            p95_abs=float(np.percentile(np.abs(arr), 95)),
            max_abs=float(np.abs(arr).max()),
        )

    summary = {}
    for mode, level, _ in conditions:
        cond = [r for r in rows if r.get("mode") == mode and r.get("level") == level]
        ok = [r for r in cond if r.get("ok") == 1]
        summary[f"{mode}@{level}"] = dict(
            samples=len(cond),
            detection_rate=(len(ok) / len(cond)) if cond else 0.0,
            ey_err=stats([r["ey_err"] for r in ok if r["ey_err"] != ""]),
            epsi_err=stats([r["epsi_err"] for r in ok if r["epsi_err"] != ""]),
        )

    metadata = dict(
        run_id=run_id,
        purpose="D-43 CV lane-estimator validation vs ground-truth oracle (GE2 evidence)",
        git_commit=git_commit(),
        world=str(WORLD.relative_to(REPO)),
        world_sha256=sha256_file(WORLD),
        centerline=str(CENTERLINE.relative_to(REPO)),
        centerline_sha256=sha256_file(CENTERLINE),
        cage_yaml_sha256=sha256_file(CAGE_YAML),
        camera_model=vars(CameraModel()) if hasattr(CameraModel(), "__dict__") else
            dict(height_m=CameraModel().height_m, pitch_rad=CameraModel().pitch_rad,
                 hfov_rad=CameraModel().hfov_rad, width_px=CameraModel().width_px,
                 height_px=CameraModel().height_px),
        estimator_config=vars(estimator.config),
        grid=dict(n_s=args.n_s, n_s_degraded=args.n_s_degraded,
                  offsets=list(offsets), headings=list(headings)),
        degradations=[list(d) for d in DEGRADATIONS],
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )
    (out_dir / "summary.json").write_text(
        json.dumps(dict(metadata=metadata, summary=summary), indent=2)
    )
    print(json.dumps(summary, indent=2))
    print(f"run dir: {out_dir}")

    iface.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
