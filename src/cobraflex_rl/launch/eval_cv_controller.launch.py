"""
eval_cv_controller — headless, single-run launch for the logical CV camera
lane-keeper baseline (cobraflex/lane_keeper_gazebo_node ported into the
GazeboLaneEnv eval harness). Same orchestration contract as
eval_scenario_batch.launch.py (gui off, run_id/output_root exposed, shutdown
on node exit) so it can be driven as a blocking subprocess and its result
located alongside the RL runs for a like-for-like comparison.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    cobraflex_share = get_package_share_directory("cobraflex")

    args = [
        DeclareLaunchArgument(
            "world",
            default_value=os.path.join(cobraflex_share, "worlds", "lane_following_oval.world"),
            description="World file or short map name (see gazebo_mesh resolver).",
        ),
        DeclareLaunchArgument("gui", default_value="true", description="Gazebo GUI."),
        DeclareLaunchArgument("rviz", default_value="true", description="RViz."),
        DeclareLaunchArgument("scenario", default_value="",
                              description="Scenario YAML (empty = SC-NOM-01 nominal eval)."),
        DeclareLaunchArgument("mode", default_value="enforcement",
                              description="Cage mode: enforcement | monitoring."),
        DeclareLaunchArgument("rep", default_value="0", description="Repetition index."),
        DeclareLaunchArgument("fixed_speed", default_value="0.10",
                              description="Env cruise speed m/s (controller native 0.10)."),
        DeclareLaunchArgument("max_steps", default_value="4400",
                              description="Override max_episode_steps (0 = scenario/config default)."),
        DeclareLaunchArgument("run_id", default_value="", description="Output run id."),
        DeclareLaunchArgument("output_root", default_value="",
                              description="Directory holding run subdirs."),
        DeclareLaunchArgument("train_config", default_value="",
                              description="Camera env config (empty = train_ppo_camera.yaml)."),
    ]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(cobraflex_share, "launch", "gazebo_mesh.launch.py")
        ),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "gui": LaunchConfiguration("gui"),
            "rviz": LaunchConfiguration("rviz"),
        }.items(),
    )

    eval_node = Node(
        package="cobraflex_rl",
        executable="eval_cv_controller",
        output="screen",
        arguments=[
            "--scenario", LaunchConfiguration("scenario"),
            "--mode", LaunchConfiguration("mode"),
            "--rep", LaunchConfiguration("rep"),
            "--fixed-speed", LaunchConfiguration("fixed_speed"),
            "--max-steps", LaunchConfiguration("max_steps"),
            "--run-id", LaunchConfiguration("run_id"),
            "--output-root", LaunchConfiguration("output_root"),
            "--train-config", LaunchConfiguration("train_config"),
        ],
    )

    shutdown_on_eval_exit = RegisterEventHandler(
        OnProcessExit(target_action=eval_node, on_exit=[EmitEvent(event=Shutdown())])
    )

    return LaunchDescription(args + [gazebo, eval_node, shutdown_on_eval_exit])
