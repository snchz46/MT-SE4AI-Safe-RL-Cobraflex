"""Launch metadata: tags, phase, starred, descriptions, args, presets.

Loaded from `tools/launch_gui_meta.yaml` if pyyaml is available and the
file exists. Otherwise falls back to the in-code `DEFAULT_LAUNCH_META`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict


DEFAULT_LAUNCH_META: Dict[str, dict] = {
    "safety_cage/lane_following": {
        "starred": True, "phase": "F2", "tags": ["F2", "Sim"],
        "description": "F2 end-to-end demo: Gazebo + perception + PD + cage + logger",
        "args": [
            {"key": "use_sim_time", "default": "true", "kind": "bool",
             "help": "Use /clock from simulator"},
            {"key": "world", "default": "lane_following_oval", "kind": "enum",
             "options": ["lane_following_oval", "lane_following_eight", "empty_world"],
             "help": "World file (sdf name)"},
            {"key": "log_csv", "default": "true", "kind": "bool",
             "help": "Write cage_log.csv for the run"},
            {"key": "rviz", "default": "true", "kind": "bool"},
        ],
        "presets": [
            {"name": "demo", "args": {"use_sim_time": "true", "world": "lane_following_oval", "log_csv": "true", "rviz": "true"}},
            {"name": "friday talk", "args": {"use_sim_time": "true", "world": "lane_following_eight", "log_csv": "false", "rviz": "true"}},
            {"name": "headless eval", "args": {"use_sim_time": "true", "world": "lane_following_oval", "log_csv": "true", "rviz": "false"}},
        ],
    },
    "cobraflex_rl/train_lane": {
        "starred": True, "phase": "F3", "tags": ["F3", "Sim"],
        "description": "PPO training, headless Gazebo (D-34, TS-01 open)",
        "args": [
            {"key": "use_sim_time", "default": "true", "kind": "bool"},
            {"key": "gui", "default": "false", "kind": "bool",
             "help": "Launch Gazebo GUI (false = headless)"},
            {"key": "world", "default": "lane_following_oval", "kind": "enum",
             "options": ["lane_following_oval", "lane_following_eight"]},
            {"key": "n_envs", "default": "8", "kind": "number",
             "help": "Parallel envs"},
            {"key": "total_steps", "default": "1000000", "kind": "number",
             "help": "Train budget (timesteps)"},
        ],
        "presets": [
            {"name": "quick smoke", "args": {"gui": "false", "n_envs": "2", "total_steps": "20000"}},
            {"name": "full run",    "args": {"gui": "false", "n_envs": "8", "total_steps": "1000000"}},
            {"name": "debug visual", "args": {"gui": "true", "n_envs": "1", "total_steps": "5000"}},
        ],
    },
    "cobraflex/gazebo": {
        "tags": ["Sim"],
        "description": "Gazebo simulation with obstacles.world (basic URDF)",
        "args": [
            {"key": "use_sim_time", "default": "true", "kind": "bool"},
            {"key": "rviz", "default": "true", "kind": "bool"},
            {"key": "world", "default": "obstacles.world", "kind": "string"},
        ],
    },
    "cobraflex/gazebo_mesh": {
        "tags": ["Sim"],
        "description": "Gazebo with lane_following_oval.world + mesh URDF",
        "args": [
            {"key": "use_sim_time", "default": "true", "kind": "bool"},
            {"key": "gui", "default": "true", "kind": "bool"},
            {"key": "rviz", "default": "false", "kind": "bool"},
            {"key": "start_paused", "default": "false", "kind": "bool"},
            {"key": "world", "default": "lane_following_oval", "kind": "enum",
             "options": ["lane_following_oval", "lane_following_eight"]},
        ],
    },
    "cobraflex/lane_keeper_gazebo": {
        "tags": ["Sim"],
        "description": "Lane keeper standalone (no cage) in Gazebo",
        "args": [
            {"key": "use_sim_time", "default": "true", "kind": "bool"},
            {"key": "use_rviz", "default": "true", "kind": "bool"},
            {"key": "launch_sim", "default": "true", "kind": "bool"},
            {"key": "show_debug_windows", "default": "false", "kind": "bool"},
        ],
    },
    "cobraflex/mapping": {
        "tags": ["Sim"],
        "description": "SLAM mapping in simulation with RViz",
        "args": [
            {"key": "use_sim_time", "default": "true", "kind": "bool"},
            {"key": "rviz", "default": "true", "kind": "bool"},
        ],
    },
    "cobraflex/navigation": {
        "tags": ["Sim"],
        "description": "Nav2 + RViz in simulation",
        "args": [
            {"key": "use_sim_time", "default": "true", "kind": "bool"},
            {"key": "rviz", "default": "true", "kind": "bool"},
        ],
    },
    "cobraflex/description": {
        "tags": ["Utils"],
        "description": "Robot description (URDF) + joint_state_publisher_gui + RViz",
    },
    "cobraflex/rsp": {
        "tags": ["Utils"],
        "description": "robot_state_publisher only",
    },
    "cobraflex/cobraflex_bringup": {
        "tags": ["Hardware"],
        "description": "Physical robot: description + serial driver",
    },
    "cobraflex/cobraflex_driver": {
        "tags": ["Hardware"],
        "description": "Serial driver for the CobraFlex JSON protocol (/dev/ttyACM1)",
    },
    "cobraflex/cobraflex_description": {
        "tags": ["Hardware"],
        "description": "Hardware URDF + RSP + JSP + optional RViz",
    },
    "cobraflex/cobraflex_sensors": {
        "tags": ["Hardware"],
        "description": "SLLIDAR A2M8 + ZED Mini camera drivers",
    },
    "cobraflex/cobraflex_automatic": {
        "tags": ["Hardware"],
        "description": "Sensors + lidar-based obstacle avoidance",
    },
    "cobraflex/cobraflex_lane_keeper": {
        "tags": ["Hardware"],
        "description": "Lane keeper on the physical robot",
    },
    "cobraflex/cobraflex_mapping": {
        "tags": ["Hardware"],
        "description": "SLAM mapping on the physical robot",
    },
}


_META_YAML = Path(__file__).resolve().parent.parent / "launch_gui_meta.yaml"


def _load_from_yaml() -> Dict[str, dict] | None:
    if not _META_YAML.exists():
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        with _META_YAML.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        launches = data.get("launches", {})
        if not isinstance(launches, dict):
            return None
        return launches
    except Exception as e:
        print(f"[launch_gui] Failed to load {_META_YAML}: {e}", file=sys.stderr)
        return None


def load_meta() -> Dict[str, dict]:
    """Load metadata, preferring the external YAML when present."""
    return _load_from_yaml() or DEFAULT_LAUNCH_META


LAUNCH_META = load_meta()
