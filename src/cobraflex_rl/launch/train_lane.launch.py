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
    # gui:=false disables the Gazebo client window for headless training.
    # gazebo_mesh.launch.py exposes "gui" (not "headless").
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="false",
        description="Launch Gazebo GUI (set true for debugging).",
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(cobraflex_share, "launch", "gazebo_mesh.launch.py")
        ),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "gui": LaunchConfiguration("gui"),
        }.items(),
    )

    train_node = Node(
        package="cobraflex_rl",
        executable="train_ppo",
        output="screen",
    )

    return LaunchDescription([
        world_arg,
        gui_arg,
        gazebo,
        train_node,
    ])
