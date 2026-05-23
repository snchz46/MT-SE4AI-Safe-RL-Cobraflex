import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    cobraflex_share = get_package_share_directory("cobraflex")

    world_arg = DeclareLaunchArgument(
        "world",
        default_value=os.path.join(cobraflex_share, "worlds", "lane_following_oval.world"),
        description="Path to the Gazebo .world file for RL training.",
    )
    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="true",
        description="Run Gazebo without GUI (faster training).",
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(cobraflex_share, "launch", "gazebo_mesh.launch.py")
        ),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "headless": LaunchConfiguration("headless"),
        }.items(),
    )

    train_node = Node(
        package="cobraflex_rl",
        executable="train_ppo",
        output="screen",
    )

    return LaunchDescription([
        world_arg,
        headless_arg,
        gazebo,
        train_node,
    ])
