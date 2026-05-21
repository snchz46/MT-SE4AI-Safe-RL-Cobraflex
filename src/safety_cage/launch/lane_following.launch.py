"""
lane_following.launch.py — F2 end-to-end demo launch.

Pipeline:
    Gazebo (lane_following_oval.world + cobraflex robot)
      |  /odom
      v
    lane_perception_node  --(state_obs)-->  pd_baseline_node
                                              |
                                              v  /raw_action (Twist)
                                          cage_ros_node
                                              |
                                              +-- /safe_action (Twist) ---> vehicle_control_node -> /cmd_vel
                                              +-- /cage_status (CageStatus) -> cage_logger_node -> CSV
                                              +-- /emergency (Bool)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    cobraflex_share = get_package_share_directory("cobraflex")
    cobraflex_rl_share = get_package_share_directory("cobraflex_rl")

    default_world = os.path.join(
        cobraflex_share, "worlds", "lane_following_oval.world"
    )
    default_centerline = os.path.join(
        cobraflex_rl_share, "config", "oval_centerline.yaml"
    )

    world_arg = DeclareLaunchArgument(
        "world",
        default_value=default_world,
        description="Gazebo .world to load (default: oval lane-following).",
    )
    centerline_arg = DeclareLaunchArgument(
        "centerline_yaml",
        default_value=default_centerline,
        description="Centerline YAML consumed by lane_perception and the cage.",
    )
    cage_yaml_arg = DeclareLaunchArgument(
        "cage_yaml",
        default_value="",
        description="Path to cage.yaml. Empty triggers the walk-up search.",
    )
    cage_mode_arg = DeclareLaunchArgument(
        "cage_mode",
        default_value="enforcement",
        description="enforcement | monitoring",
    )
    output_dir_arg = DeclareLaunchArgument(
        "output_dir",
        default_value="experiments/sim/runs",
        description="Directory under which the cage logger writes CSV runs.",
    )
    run_id_arg = DeclareLaunchArgument(
        "run_id",
        default_value="",
        description="Override the auto-generated run id.",
    )
    fixed_speed_arg = DeclareLaunchArgument(
        "fixed_speed_mps",
        default_value="0.2",
        description="Constant /cmd_vel.linear.x for the F2 1D-steering demo.",
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(cobraflex_share, "launch", "gazebo_mesh.launch.py")
        ),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "rviz": "false",
            "use_sim_time": "true",
        }.items(),
    )

    perception = Node(
        package="cobraflex_rl",
        executable="lane_perception_node",
        name="lane_perception",
        output="screen",
        parameters=[{
            "centerline_yaml": LaunchConfiguration("centerline_yaml"),
            "use_sim_time": True,
        }],
    )

    pd = Node(
        package="cobraflex_rl",
        executable="pd_baseline_node",
        name="pd_baseline",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    cage = Node(
        package="safety_cage",
        executable="cage_ros_node",
        name="safety_cage",
        output="screen",
        parameters=[{
            "cage_yaml": LaunchConfiguration("cage_yaml"),
            "mode": LaunchConfiguration("cage_mode"),
            "use_sim_time": True,
        }],
    )

    vehicle = Node(
        package="cobraflex_rl",
        executable="vehicle_control_node",
        name="vehicle_control",
        output="screen",
        parameters=[{
            "fixed_speed_mps": LaunchConfiguration("fixed_speed_mps"),
            "use_sim_time": True,
        }],
    )

    logger = Node(
        package="cobraflex_rl",
        executable="cage_logger_node",
        name="cage_logger",
        output="screen",
        parameters=[{
            "output_dir": LaunchConfiguration("output_dir"),
            "run_id": LaunchConfiguration("run_id"),
            "use_sim_time": True,
        }],
    )

    return LaunchDescription([
        world_arg,
        centerline_arg,
        cage_yaml_arg,
        cage_mode_arg,
        output_dir_arg,
        run_id_arg,
        fixed_speed_arg,
        gazebo,
        perception,
        pd,
        cage,
        vehicle,
        logger,
    ])
