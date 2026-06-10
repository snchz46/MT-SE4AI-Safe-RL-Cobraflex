from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import numpy as np
import rclpy
from rclpy.utilities import remove_ros_args
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecFrameStack
import yaml

from .callbacks import (
    ActionSampleCallback,
    LearningCurveCallback,
    ProgressBarCallback,
)
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


def _resolve_repo_subdir(*parts: str) -> Path:
    """Walk up to the repo root (marked by .git/ or experiments/) and return the
    given subdirectory, creating it if needed. Falls back to a cwd-relative path."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists() or (parent / "experiments").is_dir():
            target = parent.joinpath(*parts)
            target.mkdir(parents=True, exist_ok=True)
            return target
    target = Path.cwd().joinpath(*parts)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _resolve_cage_yaml(train_cfg: Dict[str, Any]) -> Path:
    explicit = train_cfg.get("cage", {}).get("yaml_path", "") or ""
    if explicit and Path(explicit).is_file():
        return Path(explicit)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "cage" / "cage.yaml"
        if candidate.is_file():
            return candidate
    return Path("cage/cage.yaml")


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PPO lane-following policy.")
    parser.add_argument("--centerline-config", type=str, default=None)
    parser.add_argument("--train-config", type=str, default=None)
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    cleaned_args = remove_ros_args(args=args)
    if cleaned_args and not cleaned_args[0].startswith("-"):
        cleaned_args = cleaned_args[1:]
    return parser.parse_args(cleaned_args)


def resolve_save_path(path: Path) -> Path:
    return path if path.suffix == ".zip" else path.with_suffix(".zip")


def _write_training_metadata(
    run_dir: Path,
    run_id: str,
    seed: int,
    train_cfg: Dict[str, Any],
    centerline_path: Path,
    cage_yaml: Path,
    model_path: Path,
    total_timesteps: int,
    status: str,
) -> None:
    metadata = {
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "mode": str(train_cfg.get("cage", {}).get("mode", "enforcement")),
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(run_dir),
        "cage_yaml": str(cage_yaml),
        "cage_yaml_hash": sha256_file(cage_yaml),
        "scenario_yaml_hash": sha256_file(centerline_path),
        "policy_checkpoint": str(resolve_save_path(model_path)),
        "policy_checkpoint_hash": sha256_file(resolve_save_path(model_path)),
        "seed": seed,
        "platform": "sim",
        "total_timesteps": total_timesteps,
        "hyperparameters": {
            "learning_rate": float(train_cfg.get("learning_rate", 3.0e-4)),
            "gamma": float(train_cfg.get("gamma", 0.99)),
            "n_steps": int(train_cfg.get("n_steps", 1024)),
            "batch_size": int(train_cfg.get("batch_size", 64)),
        },
        # Track 'E' provenance (inert for the state-vector track): policy
        # class, observation type, frame stack and the H-10 DR envelope.
        "policy": str(train_cfg.get("policy", "MlpPolicy")),
        "observation": dict(train_cfg.get("observation", {})),
        "domain_randomization": dict(train_cfg.get("domain_randomization", {})),
        "status": status,
    }
    with (run_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)


def _append_checkpoint_registry(
    seed: int, total_timesteps: int, cage_yaml: Path, run_id: str
) -> None:
    registry = _resolve_repo_subdir("policy", "checkpoints") / "checkpoint_registry.csv"
    write_header = not registry.exists()
    with registry.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow([
                "checkpoint_id", "seed", "training_steps", "scenario_evaluated",
                "timestamp", "git_commit", "cage_yaml_hash", "notes",
            ])
        writer.writerow([
            "cobraflex_ppo_lane",
            seed,
            total_timesteps,
            "",  # scenario_evaluated — filled in by eval_policy later
            datetime.now(timezone.utc).isoformat(),
            git_commit(registry.parent),
            sha256_file(cage_yaml) or "",
            f"run_id={run_id}",
        ])


def main(args: Optional[Sequence[str]] = None) -> None:
    cli_args = parse_args(args)
    rclpy.init(args=args)

    share_dir = resolve_share_directory()
    centerline_path = Path(cli_args.centerline_config or share_dir / "config" / "oval_right_lane_centerline.yaml")
    train_cfg_path = Path(cli_args.train_config or share_dir / "config" / "train_ppo.yaml")

    centerline_cfg = load_yaml(centerline_path)
    train_cfg = load_yaml(train_cfg_path)

    model_path = Path(cli_args.model_path or train_cfg.get("model_path", "cobraflex_ppo_lane"))
    model_path = model_path.expanduser()
    model_path.parent.mkdir(parents=True, exist_ok=True)

    seed = int(train_cfg.get("seed", 42))
    total_timesteps = int(train_cfg.get("total_timesteps", 50000))
    run_id = cli_args.run_id or "ppo_train_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = _resolve_repo_subdir("experiments", "sim", "training", run_id)
    checkpoints_dir = _resolve_repo_subdir("policy", "checkpoints")
    cage_yaml = _resolve_cage_yaml(train_cfg)

    interface: Optional[RosGazeboInterface] = None
    env: Optional[GazeboLaneEnv] = None
    status = "failed"

    obs_cfg = dict(train_cfg.get("observation", {}))
    camera_obs = str(obs_cfg.get("type", "state")) == "camera"

    try:
        interface = RosGazeboInterface(
            camera_topic=(
                str(obs_cfg.get("camera", {}).get("topic", "/camera/image_raw"))
                if camera_obs
                else ""
            )
        )
        if not interface.wait_for_initial_data(timeout_sec=10.0):
            raise RuntimeError("Timed out waiting for /odom data.")

        # Unthrottle the sim clock for headless training so episodes don't play
        # out in real time. Reversible, session-only: it touches neither the
        # (hash-tracked) .world nor max_step_size, so physics fidelity and run
        # reproducibility are unchanged. Set sim_real_time_factor: 1 to restore
        # real-time pacing. control_dt cadence stays correct via sim-time step_ros.
        rtf = float(train_cfg.get("sim_real_time_factor", 0.0))
        if rtf != 1.0:
            if interface.set_real_time_factor(rtf):
                interface.get_logger().info(
                    f"Set simulation real_time_factor to {rtf} (0 = as fast as possible)."
                )
            else:
                interface.get_logger().warning(
                    "Could not set real_time_factor via /set_physics; "
                    "training will run at the world's default pace."
                )

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

        check_env(env, warn=True, skip_render_check=True)

        # Track 'E' (docs/09 §10): camera obs trains a CnnPolicy over a frame
        # stack (k=4 fixed at E2; VecFrameStack recovers the velocity/rate
        # cues a single frame loses). SB3 adds VecTransposeImage on top
        # automatically. The state-vector track keeps the raw env + MlpPolicy.
        policy_name = str(train_cfg.get("policy", "MlpPolicy"))
        if camera_obs:
            frame_stack = int(obs_cfg.get("camera", {}).get("frame_stack", 4))
            # Monitor must wrap the raw env (SB3 only auto-wraps non-vec
            # envs); without it ep_rew_mean/ep_len_mean stay NaN in the
            # learning curve.
            train_env = VecFrameStack(
                DummyVecEnv([lambda: Monitor(env)]), n_stack=frame_stack
            )
        else:
            train_env = env

        model = PPO(
            policy=policy_name,
            env=train_env,
            learning_rate=float(train_cfg.get("learning_rate", 3.0e-4)),
            gamma=float(train_cfg.get("gamma", 0.99)),
            n_steps=int(train_cfg.get("n_steps", 1024)),
            batch_size=int(train_cfg.get("batch_size", 64)),
            device=str(train_cfg.get("device", "cpu")),
            # §7.2.7: seeds python/numpy/torch + action space, and propagates to
            # env.reset(seed=...) so the spawn perturbation is reproducible too.
            seed=seed,
            verbose=1,
        )

        # §7.2.8: persist the learning curve + periodic checkpoints so the run
        # produces its §7.4 evidence automatically.
        checkpoint_freq = int(train_cfg.get("checkpoint_freq", train_cfg.get("n_steps", 1024)))
        callback = CallbackList([
            ProgressBarCallback(total_timesteps=total_timesteps),
            LearningCurveCallback(csv_path=run_dir / "learning_curve.csv"),
            ActionSampleCallback(
                csv_path=run_dir / "action_samples.csv",
                sample_every=int(train_cfg.get("action_sample_every", 10)),
            ),
            CheckpointCallback(
                save_freq=checkpoint_freq,
                save_path=str(checkpoints_dir),
                name_prefix="cobraflex_ppo_lane",
            ),
        ])

        model.learn(total_timesteps=total_timesteps, callback=callback)
        model.save(str(model_path))
        status = "completed"
        print(f"Saved PPO model to {resolve_save_path(model_path)}")
        print(f"Learning curve + metadata under {run_dir}")
    finally:
        if env is not None:
            env.close()
        if interface is not None:
            interface.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        # Always record the run (even on failure) for reproducibility.
        _write_training_metadata(
            run_dir=run_dir,
            run_id=run_id,
            seed=seed,
            train_cfg=train_cfg,
            centerline_path=centerline_path,
            cage_yaml=cage_yaml,
            model_path=model_path,
            total_timesteps=total_timesteps,
            status=status,
        )
        if status == "completed":
            _append_checkpoint_registry(seed, total_timesteps, cage_yaml, run_id)


if __name__ == "__main__":
    main()
