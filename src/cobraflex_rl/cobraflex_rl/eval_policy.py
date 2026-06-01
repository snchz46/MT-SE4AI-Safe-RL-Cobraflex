"""
eval_policy — evaluate a trained PPO lane-following policy and emit the §7.5
evidence (Training Specification §7.5.1): completed laps, cage intervention
rate, emergencies, and mean tracking error, written as a reproducible run under
`experiments/sim/runs/<run_id>/`.

The policy is evaluated through `GazeboLaneEnv`, so it runs under the **same**
in-process cage as training and deployment (D-34). Spawn perturbation is
disabled so the start is deterministic and comparable with the PD baseline run.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import numpy as np
import rclpy
from rclpy.utilities import remove_ros_args
from stable_baselines3 import PPO
import yaml

from .eval_metrics import summarize_eval
from .gazebo_lane_env import GazeboLaneEnv
from .ros_interface import RosGazeboInterface
from .run_io import git_commit, sha256_file


PACKAGE_NAME = "cobraflex_rl"
SCENARIO_ID = "SC-NOM-01"


def resolve_share_directory() -> Path:
    try:
        return Path(get_package_share_directory(PACKAGE_NAME))
    except PackageNotFoundError:
        return Path(__file__).resolve().parents[1]


def resolve_runs_dir(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "experiments" / "sim" / "runs").is_dir():
            return parent / "experiments" / "sim" / "runs"
    return Path.cwd() / "experiments" / "sim" / "runs"


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate PPO lane-following policy.")
    parser.add_argument("--centerline-config", type=str, default=None)
    parser.add_argument("--train-config", type=str, default=None)
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument(
        "--max-steps", type=int, default=None,
        help="Override max_episode_steps for the eval (e.g. 4400 ≈ 10 continuous "
             "laps for the §7.5.1 lap-count comparison vs the PD). Default: the "
             "value in train_ppo.yaml.",
    )
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--output-root", type=str, default=None,
                        help="Directory holding run subdirs (default experiments/sim/runs).")
    cleaned_args = remove_ros_args(args=args)
    if cleaned_args and not cleaned_args[0].startswith("-"):
        cleaned_args = cleaned_args[1:]
    return parser.parse_args(cleaned_args)


def resolve_load_path(path: Path) -> Path:
    if path.exists():
        return path
    return path if path.suffix == ".zip" else path.with_suffix(".zip")


def _disable_spawn_perturbation(train_cfg: Dict[str, Any]) -> None:
    spawn_cfg = dict(train_cfg.get("spawn_perturbation", {}))
    spawn_cfg["enabled"] = False
    train_cfg["spawn_perturbation"] = spawn_cfg


def _record_from_info(episode: int, step: int, info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "episode": episode,
        "step": step,
        # World pose (x, y) → §7.5 trajectory overlay (RL vs PD on the oval);
        # ey/epsi/s are the Frenet/cage state at the same step.
        "x": float(info.get("x", 0.0)),
        "y": float(info.get("y", 0.0)),
        "yaw": float(info.get("yaw", 0.0)),
        "ey": float(info.get("ey", 0.0)),
        "epsi": float(info.get("epsi", 0.0)),
        "s": float(info.get("s", 0.0)),
        "speed": float(info.get("speed", 0.0)),
        "raw_steer": float(info.get("raw_steer", 0.0)),
        "safe_steer": float(info.get("safe_steer", 0.0)),
        "steer_correction": float(info.get("steer_correction", 0.0)),
        "interventions": list(info.get("cage_interventions", [])),
        "emergency": bool(info.get("cage_emergency", False)),
    }


def _write_cage_status_csv(path: Path, records: List[Dict[str, Any]]) -> None:
    fields = [
        "episode", "step", "x", "y", "yaw", "ey", "epsi", "s", "speed",
        "raw_steer", "safe_steer", "steer_correction",
        "interventions", "emergency",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for r in records:
            writer.writerow([
                r["episode"], r["step"],
                f"{r['x']:.6f}", f"{r['y']:.6f}", f"{r['yaw']:.6f}",
                f"{r['ey']:.6f}", f"{r['epsi']:.6f}", f"{r['s']:.6f}",
                f"{r['speed']:.6f}", f"{r['raw_steer']:.6f}",
                f"{r['safe_steer']:.6f}", f"{r['steer_correction']:.6f}",
                ";".join(r["interventions"]), int(r["emergency"]),
            ])


def _print_summary(summary: Dict[str, Any]) -> None:
    print("\n===== §7.5 evaluation summary (RL + cage) =====")
    print(f"  episodes / steps    : {summary['episodes']} / {summary['total_steps']}")
    print(f"  completed laps      : {summary['completed_laps']:.2f}")
    print(f"  cage emergencies    : {summary['emergency_steps']} steps")
    print(f"  cage interventions  : {summary['intervention_rate_pct']:.3f}% of steps "
          f"({summary['interventions_per_rule']})")
    print(f"  mean ey / |ey|      : {summary['mean_ey_m']:.4f} / {summary['mean_abs_ey_m']:.4f} m")
    print(f"  mean |epsi|         : {summary['mean_abs_epsi_rad']:.4f} rad")
    print(f"  duration            : {summary['duration_s']:.1f} s")
    print("===============================================\n")


def main(args: Optional[Sequence[str]] = None) -> None:
    cli_args = parse_args(args)
    rclpy.init(args=args)

    share_dir = resolve_share_directory()
    centerline_path = Path(cli_args.centerline_config or share_dir / "config" / "oval_right_lane_centerline.yaml")
    train_cfg_path = Path(cli_args.train_config or share_dir / "config" / "train_ppo.yaml")

    centerline_cfg = load_yaml(centerline_path)
    train_cfg = load_yaml(train_cfg_path)
    # Evaluation starts from the nominal spawn (no perturbation) so the run is
    # deterministic and comparable with the PD baseline (§7.5).
    _disable_spawn_perturbation(train_cfg)
    # Optional horizon override for a long continuous run (lap-count comparison).
    # Non-positive means "keep the config default" (the launch passes 0 for that).
    if cli_args.max_steps is not None and cli_args.max_steps > 0:
        train_cfg["max_episode_steps"] = int(cli_args.max_steps)

    model_path = Path(cli_args.model_path or train_cfg.get("model_path", "cobraflex_ppo_lane"))
    model_path = model_path.expanduser()
    seed = int(train_cfg.get("seed", 42))

    interface: Optional[RosGazeboInterface] = None
    env: Optional[GazeboLaneEnv] = None
    records: List[Dict[str, Any]] = []

    try:
        interface = RosGazeboInterface()
        if not interface.wait_for_initial_data(timeout_sec=10.0):
            raise RuntimeError("Timed out waiting for /odom data.")

        centerline_points = np.asarray(centerline_cfg["centerline"]["points"], dtype=float)
        lane_width = float(centerline_cfg["lane_width"])
        road_width = float(centerline_cfg.get("road_width", lane_width))

        env = GazeboLaneEnv(
            ros_interface=interface,
            centerline=centerline_points,
            lane_width=lane_width,
            road_width=road_width,
            cfg=train_cfg,
        )
        perimeter = float(env.tracker.cumulative_lengths[-1])

        model = PPO.load(str(resolve_load_path(model_path)))

        for episode in range(cli_args.episodes):
            observation, info = env.reset(seed=seed + episode)
            terminated = False
            truncated = False
            step_index = 0
            print(f"Episode {episode + 1}")

            while not (terminated or truncated):
                action, _ = model.predict(observation, deterministic=True)
                observation, reward, terminated, truncated, info = env.step(action)
                step_index += 1
                records.append(_record_from_info(episode, step_index, info))
                print(
                    f"step={step_index:04d} ey={info['ey']:.4f} "
                    f"epsi={info['epsi']:.4f} speed={info['speed']:.4f} "
                    f"reward={reward:.4f} interv={info.get('cage_interventions', [])}"
                )

        summary = summarize_eval(records, perimeter=perimeter, cycle_dt_s=env.control_dt)
        _print_summary(summary)
        _write_run(
            cli_args=cli_args,
            train_cfg=train_cfg,
            centerline_path=centerline_path,
            model_path=resolve_load_path(model_path),
            seed=seed,
            records=records,
            summary=summary,
        )
    finally:
        if env is not None:
            env.close()
        if interface is not None:
            interface.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def _write_run(
    cli_args: argparse.Namespace,
    train_cfg: Dict[str, Any],
    centerline_path: Path,
    model_path: Path,
    seed: int,
    records: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> None:
    runs_dir = resolve_runs_dir(cli_args.output_root)
    run_id = cli_args.run_id or "rl_eval_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = runs_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = str(train_cfg.get("cage", {}).get("mode", "enforcement"))
    cage_yaml = Path(train_cfg.get("cage", {}).get("yaml_path", "") or "")
    if not cage_yaml.is_file():
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "cage" / "cage.yaml"
            if candidate.is_file():
                cage_yaml = candidate
                break

    _write_cage_status_csv(out_dir / "cage_status.csv", records)

    summary_out = dict(summary)
    summary_out.update({"run_id": run_id, "scenario_id": SCENARIO_ID, "mode": mode})
    with (out_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary_out, handle, indent=2)

    metadata = {
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "mode": mode,
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "duration_s": summary["duration_s"],
        "git_commit": git_commit(out_dir),
        "cage_yaml": str(cage_yaml),
        "cage_yaml_hash": sha256_file(cage_yaml),
        "policy_checkpoint": str(model_path),
        "policy_checkpoint_hash": sha256_file(model_path),
        "scenario_yaml_hash": sha256_file(centerline_path),
        "seed": seed,
        "platform": "sim",
        "status": "completed",
    }
    with (out_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print(f"Wrote evaluation run to {out_dir}")


if __name__ == "__main__":
    main()
