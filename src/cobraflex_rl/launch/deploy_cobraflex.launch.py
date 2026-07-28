"""
deploy_cobraflex.launch.py — Phase-5 physical bring-up of the track-'E' RL
camera policy behind the safety cage, on the real CobraFlex 1:14.

**STATUS: deployment scaffolding — NOT yet run on hardware.** Wires the same
distributed node chain as the F2 physical demo, now camera-driven and 2-D:

    <camera driver>  ─► camera/image_raw_lane
      rl_policy_node        (image → CNN → /raw_action)           [NEW, Phase 5]
      cv_lane_estimator_node(image → /state_obs + /perception_invalid, D-43)
      cage_ros_node         (/raw_action + /state_obs → /safe_action + /cage_status)
      vehicle_control_node  (/safe_action → /cmd_vel → motor driver)
      cage_logger_node      (/cage_status → CSV evidence)

PREREQUISITES (see docs/17_physical_deployment.md):
  * A camera driver (ZED / other, installed externally per D-32) publishing frames
    on ``camera_topic`` with the SAME geometry the policy trained on.
  * Camera extrinsics matched to the trained IPM (pitch 0.30 rad, height 0.077 m)
    OR the D-57 ``perception_heading_bias_rad`` re-calibrated for the real mount.
  * A motor driver consuming /cmd_vel (Twist: linear.x m/s, angular.z yaw rate).
  * A hardware e-stop wired to /external_stop (Bool) — MANDATORY before first run.

KNOWN ITEM TO VERIFY ON HARDWARE: the 2-D throttle→speed mapping. The in-sim cage
bridge uses ``cage_bridge.target_speed_from_throttle_2d`` (max_speed·u, full stop
below the deadband); ``vehicle_control_node`` here uses ``use_safe_throttle`` to
scale ``fixed_speed_mps``. Confirm these agree (set ``fixed_speed_mps`` = the
config ``action.max_speed_mps`` and validate the deadband) before trusting speeds.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    cage_yaml_default = os.path.join(
        get_package_share_directory("cobraflex_rl"), "config", "cage.yaml"
    ) if os.path.isdir(
        os.path.join(get_package_share_directory("cobraflex_rl"), "config")
    ) else ""

    args = [
        DeclareLaunchArgument("checkpoint", description="SB3 .zip to deploy (required)."),
        DeclareLaunchArgument("algorithm", default_value="sac", description="sac|ppo."),
        DeclareLaunchArgument("cage_yaml", default_value=cage_yaml_default,
                              description="cage.yaml (empty → node default)."),
        DeclareLaunchArgument("mode", default_value="enforcement",
                              description="enforcement (deploy) | monitoring (shadow)."),
        DeclareLaunchArgument("camera_topic", default_value="camera/image_raw_lane"),
        DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel"),
        DeclareLaunchArgument("max_speed_mps", default_value="0.22",
                              description="action.max_speed_mps of the deployed contract."),
    ]
    checkpoint = LaunchConfiguration("checkpoint")
    algorithm = LaunchConfiguration("algorithm")
    cage_yaml = LaunchConfiguration("cage_yaml")
    mode = LaunchConfiguration("mode")
    camera_topic = LaunchConfiguration("camera_topic")
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")
    max_speed = LaunchConfiguration("max_speed_mps")

    rl_policy = Node(
        package="cobraflex_rl", executable="rl_policy_node", output="screen",
        parameters=[{
            "checkpoint": checkpoint, "algorithm": algorithm,
            "image_topic": camera_topic, "raw_action_topic": "/raw_action",
        }],
    )
    cv_estimator = Node(
        package="cobraflex_rl", executable="cv_lane_estimator_node", output="screen",
        parameters=[{
            "image_topic": camera_topic, "state_obs_topic": "/state_obs",
            "perception_invalid_topic": "/perception_invalid",
        }],
    )
    cage = Node(
        package="safety_cage", executable="cage_ros_node", output="screen",
        parameters=[{
            "cage_yaml": cage_yaml, "mode": mode,
            "raw_action_topic": "/raw_action", "state_obs_topic": "/state_obs",
            "safe_action_topic": "/safe_action", "cage_status_topic": "/cage_status",
            "perception_invalid_topic": "/perception_invalid",
            "external_stop_topic": "/external_stop",
        }],
    )
    vehicle_control = Node(
        package="cobraflex_rl", executable="vehicle_control_node", output="screen",
        parameters=[{
            "safe_action_topic": "/safe_action", "cmd_vel_topic": cmd_vel_topic,
            "use_safe_throttle": True, "fixed_speed_mps": max_speed,
        }],
    )
    cage_logger = Node(
        package="cobraflex_rl", executable="cage_logger_node", output="screen",
        parameters=[{"cage_status_topic": "/cage_status"}],
    )

    return LaunchDescription(args + [
        rl_policy, cv_estimator, cage, vehicle_control, cage_logger,
    ])
