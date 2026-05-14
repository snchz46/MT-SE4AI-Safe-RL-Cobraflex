from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import numpy as np
import rclpy
from rclpy.utilities import remove_ros_args
from stable_baselines3 import PPO
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
    parser = argparse.ArgumentParser(description="Evaluate PPO lane-following policy.")
    parser.add_argument("--centerline-config", type=str, default=None)
    parser.add_argument("--train-config", type=str, default=None)
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--episodes", type=int, default=1)
    cleaned_args = remove_ros_args(args=args)
    if cleaned_args and not cleaned_args[0].startswith("-"):
        cleaned_args = cleaned_args[1:]
    return parser.parse_args(cleaned_args)


def resolve_load_path(path: Path) -> Path:
    if path.exists():
        return path

    zipped_path = path if path.suffix == ".zip" else path.with_suffix(".zip")
    return zipped_path


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

        model = PPO.load(str(resolve_load_path(model_path)))

        for episode in range(cli_args.episodes):
            observation, info = env.reset()
            terminated = False
            truncated = False
            step_index = 0

            print(f"Episode {episode + 1}")
            print(
                f"step={step_index:04d} ey={info['ey']:.4f} "
                f"epsi={info['epsi']:.4f} speed={info['speed']:.4f}"
            )

            while not (terminated or truncated):
                action, _ = model.predict(observation, deterministic=True)
                observation, reward, terminated, truncated, info = env.step(action)
                step_index += 1
                print(
                    f"step={step_index:04d} ey={info['ey']:.4f} "
                    f"epsi={info['epsi']:.4f} speed={info['speed']:.4f} "
                    f"reward={reward:.4f}"
                )
    finally:
        if env is not None:
            env.close()
        if interface is not None:
            interface.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
