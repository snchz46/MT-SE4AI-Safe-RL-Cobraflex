from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import numpy as np
import rclpy
from rclpy.utilities import remove_ros_args
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
import yaml

from .gazebo_lane_env import GazeboLaneEnv
from .ros_interface import RosGazeboInterface


PACKAGE_NAME = "cobraflex_rl"


def resolve_share_directory() -> Path:
    try:
        return Path(get_package_share_directory(PACKAGE_NAME))
    except PackageNotFoundError:
        return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PPO lane-following policy.")
    parser.add_argument("--centerline-config", type=str, default=None)
    parser.add_argument("--train-config", type=str, default=None)
    parser.add_argument("--model-path", type=str, default=None)
    cleaned_args = remove_ros_args(args=args)
    if cleaned_args and not cleaned_args[0].startswith("-"):
        cleaned_args = cleaned_args[1:]
    return parser.parse_args(cleaned_args)


def resolve_save_path(path: Path) -> Path:
    return path if path.suffix == ".zip" else path.with_suffix(".zip")


def main(args: Optional[Sequence[str]] = None) -> None:
    cli_args = parse_args(args)
    rclpy.init(args=args)

    share_dir = resolve_share_directory()
    centerline_path = Path(cli_args.centerline_config or share_dir / "config" / "centerline.yaml")
    train_cfg_path = Path(cli_args.train_config or share_dir / "config" / "train_ppo.yaml")

    centerline_cfg = load_yaml(centerline_path)
    train_cfg = load_yaml(train_cfg_path)

    model_path = Path(cli_args.model_path or train_cfg.get("model_path", "cobraflex_ppo_lane"))
    model_path = model_path.expanduser()
    model_path.parent.mkdir(parents=True, exist_ok=True)

    interface: Optional[RosGazeboInterface] = None
    env: Optional[GazeboLaneEnv] = None

    try:
        interface = RosGazeboInterface()
        if not interface.wait_for_initial_data(timeout_sec=10.0):
            raise RuntimeError("Timed out waiting for /odom data.")

        centerline_points = np.asarray(centerline_cfg["centerline"]["points"], dtype=float)
        lane_width = float(centerline_cfg["lane_width"])

        env = GazeboLaneEnv(
            ros_interface=interface,
            centerline=centerline_points,
            lane_width=lane_width,
            cfg=train_cfg,
        )

        check_env(env, warn=True, skip_render_check=True)

        model = PPO(
            policy="MlpPolicy",
            env=env,
            learning_rate=float(train_cfg.get("learning_rate", 3.0e-4)),
            gamma=float(train_cfg.get("gamma", 0.99)),
            n_steps=int(train_cfg.get("n_steps", 1024)),
            batch_size=int(train_cfg.get("batch_size", 64)),
            device=str(train_cfg.get("device", "cpu")),
            verbose=1,
        )

        model.learn(total_timesteps=int(train_cfg.get("total_timesteps", 50000)))
        model.save(str(model_path))
        print(f"Saved PPO model to {resolve_save_path(model_path)}")
    finally:
        if env is not None:
            env.close()
        if interface is not None:
            interface.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
