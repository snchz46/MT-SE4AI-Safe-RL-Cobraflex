"""
Pure-Python kinematic smoke test on the oval centerline.

Closes the §4.2 gap of `docs/.phases/Fase 2/phase2_implementation_notes.md`
(combined-rule test across the chain) by running BaselinePD → cage chain
on a kinematic bicycle that integrates over the oval centerline.

Run:
    python experiments/sim/oval_pd_cage_smoke.py [--laps N] [--out DIR]

Output (under experiments/sim/runs/<run_id>/):
    cage_status.csv     per-cycle decision log
    metadata.json       run identification
    trajectory.csv      x, y, yaw, s, ey, epsi per cycle (for plotting)
    summary.json        completion-rate, intervention counts, max excursion

F2 status:
    This script is a pure-Python chain sanity check, not the Gate-2 closure
    demo. The ROS2/Gazebo pipeline now uses EKF-filtered odometry, right-lane
    tracking, safe-throttle scaling, and skid-steer Gazebo dynamics that this
    simplified bicycle model does not reproduce. Gate-2 evidence is therefore
    taken from ROS2/Gazebo runs under experiments/sim/runs/ros_run_*/.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "src" / "cobraflex_rl" / "cobraflex_rl"))

from cage.cage_node import SafetyCageNode  # noqa: E402
from cage.logger import CageLogger  # noqa: E402
from cage.rules import State  # noqa: E402
from policy.baseline_pd import BaselinePD  # noqa: E402
from polyline_tracker import PolylineTracker  # noqa: E402


CYCLE_DT = 0.05            # 20 Hz, matches cage cycle_period_ms
WHEELBASE_M = 0.18         # cobraflex 1:14 approx
STEERING_MAX_RAD = 0.35    # normalised [-1, 1] -> ±0.35 rad steering


def _wrap_pi(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def _curvature_ahead(
    tracker: PolylineTracker,
    segment_index: int,
    lookahead: int = 5,
) -> float:
    headings = tracker.segment_headings
    cum = tracker.cumulative_lengths
    n = len(headings)
    if n < 2:
        return 0.0
    i_end = min(n - 1, segment_index + lookahead)
    arc = float(cum[i_end] - cum[segment_index])
    if arc <= 1e-6:
        return 0.0
    return _wrap_pi(float(headings[i_end]) - float(headings[segment_index])) / arc


def _build_state(
    tracker: PolylineTracker,
    x: float,
    y: float,
    yaw: float,
    speed: float,
    road_half: float,
    timestamp: float,
) -> tuple[State, int]:
    track = tracker.track(x, y, yaw)
    kappa = _curvature_ahead(tracker, track.segment_index)
    state = State(
        lateral_offset=track.ey,
        heading_error=track.epsi,
        speed=speed,
        curvature_ahead=kappa,
        distance_left=max(0.0, road_half - track.ey),
        distance_right=max(0.0, road_half + track.ey),
        state_valid=True,
        timestamp=timestamp,
    )
    return state, track.segment_index


def _integrate_bicycle(
    x: float,
    y: float,
    yaw: float,
    steering_norm: float,
    speed_mps: float,
    dt: float,
) -> tuple[float, float, float]:
    delta = max(-1.0, min(1.0, steering_norm)) * STEERING_MAX_RAD
    yaw_dot = speed_mps * math.tan(delta) / WHEELBASE_M
    yaw_new = _wrap_pi(yaw + yaw_dot * dt)
    yaw_mid = _wrap_pi(yaw + 0.5 * yaw_dot * dt)
    x_new = x + speed_mps * math.cos(yaw_mid) * dt
    y_new = y + speed_mps * math.sin(yaw_mid) * dt
    return x_new, y_new, yaw_new


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--centerline",
        type=Path,
        default=_REPO_ROOT / "src" / "cobraflex_rl" / "config" / "oval_centerline.yaml",
    )
    parser.add_argument(
        "--cage-yaml",
        type=Path,
        default=_REPO_ROOT / "cage" / "cage.yaml",
    )
    parser.add_argument(
        "--baseline-yaml",
        type=Path,
        default=_REPO_ROOT / "policy" / "baseline_pd.yaml",
    )
    parser.add_argument("--laps", type=int, default=3)
    parser.add_argument("--mode", choices=["enforcement", "monitoring"], default="enforcement")
    parser.add_argument("--speed", type=float, default=0.2)
    parser.add_argument("--initial-offset", type=float, default=0.05)
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT / "experiments" / "sim" / "runs",
    )
    parser.add_argument("--run-id", type=str, default="")
    args = parser.parse_args()

    with args.centerline.open("r", encoding="utf-8") as handle:
        centerline_cfg = yaml.safe_load(handle)
    pts = np.asarray(centerline_cfg["centerline"]["points"], dtype=float)
    road_width = float(centerline_cfg.get("road_width", 0.5))
    perimeter = float(centerline_cfg["centerline"]["perimeter_m"])

    tracker = PolylineTracker(pts)
    cage = SafetyCageNode(args.cage_yaml, mode=args.mode)
    pd = BaselinePD.from_yaml(args.baseline_yaml)

    run_id = args.run_id or "smoke_oval_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    out_dir = args.out / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    x = float(pts[0, 0])
    y = float(pts[0, 1]) + args.initial_offset
    yaw = float(tracker.segment_headings[0])

    speed = float(args.speed)
    sim_t = 0.0
    laps_target_s = args.laps * perimeter
    max_steps = int(args.laps * perimeter / max(speed, 1e-6) / CYCLE_DT * 1.5) + 50

    intervention_counter: dict[str, int] = {}
    emergency_steps = 0
    max_ey = 0.0

    trajectory_path = out_dir / "trajectory.csv"
    traj_file = trajectory_path.open("w", newline="", encoding="utf-8")
    traj_writer = csv.writer(traj_file)
    traj_writer.writerow([
        "step", "sim_t", "x", "y", "yaw", "s", "ey", "epsi",
        "raw_steer", "safe_steer", "rules_fired",
    ])

    completed = False
    last_s = 0.0
    s_total = 0.0

    with CageLogger(out_dir, run_id=run_id, metadata={
        "smoke_script": "experiments/sim/oval_pd_cage_smoke.py",
        "centerline": str(args.centerline),
        "cage_yaml": str(args.cage_yaml),
        "baseline_yaml": str(args.baseline_yaml),
        "mode": args.mode,
        "speed_mps": speed,
        "laps_target": args.laps,
        "initial_offset_m": args.initial_offset,
    }) as cage_log:

        for step in range(max_steps):
            state, seg = _build_state(tracker, x, y, yaw, speed, road_width / 2.0, sim_t)
            ds = state.lateral_offset
            max_ey = max(max_ey, abs(ds))

            raw_action = pd.step(state, current_t=sim_t)
            ctx = {"current_time": sim_t}
            result = cage.step(state, raw_action, ctx=ctx)
            cage_log.add_cycle(result)

            safe_steer, _ = result["safe_action"]
            track_s = tracker.cumulative_lengths[seg]
            if track_s + 1e-3 < last_s:
                s_total += perimeter
            last_s = track_s

            for iv in result["interventions"]:
                intervention_counter[iv["rule"]] = intervention_counter.get(iv["rule"], 0) + 1
            if result["emergency"]:
                emergency_steps += 1

            traj_writer.writerow([
                step,
                f"{sim_t:.4f}",
                f"{x:.4f}",
                f"{y:.4f}",
                f"{yaw:.4f}",
                f"{(s_total + track_s):.4f}",
                f"{state.lateral_offset:.4f}",
                f"{state.heading_error:.4f}",
                f"{raw_action[0]:.4f}",
                f"{safe_steer:.4f}",
                ";".join(iv["rule"] for iv in result["interventions"]),
            ])

            x, y, yaw = _integrate_bicycle(x, y, yaw, safe_steer, speed, CYCLE_DT)
            sim_t += CYCLE_DT

            if (s_total + track_s) >= laps_target_s:
                completed = True
                break

    traj_file.close()

    summary = {
        "run_id": run_id,
        "completed_laps": (s_total + last_s) / perimeter,
        "target_laps": args.laps,
        "completed": completed,
        "max_abs_ey_m": max_ey,
        "emergency_steps": emergency_steps,
        "interventions_per_rule": intervention_counter,
        "total_steps": step + 1,
        "cycle_dt_s": CYCLE_DT,
        "mode": args.mode,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if completed and emergency_steps == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
