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
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    cobraflex_share = get_package_share_directory("cobraflex")
    cobraflex_rl_share = get_package_share_directory("cobraflex_rl")

    default_world = os.path.join(
        cobraflex_share, "worlds", "lane_following_oval.world"
    )
    # Right-lane centerline: matches the spawn at y = -0.1225 (centred in
    # the right lane of the two-lane oval). Pass centerline_yaml:= to
    # override, e.g. to track the road centerline (oval_centerline.yaml).
    default_centerline = os.path.join(
        cobraflex_rl_share, "config", "oval_right_lane_centerline.yaml"
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
        description="Straight cruise speed before safe throttle scaling.",
    )

    # Start Gazebo paused so the sim clock is frozen at t≈0 while all
    # ROS2 nodes (EKF, lane_perception, cage) initialise. The unpause
    # action fires after 4 real-world seconds, by which time the EKF has
    # a clock signal and the pipeline is wired. This prevents the sim
    # from racing ahead (>1000× RTF headless) before the EKF publishes
    # its first odom, which caused the car to drift from spawn and report
    # ey=0.13 m, epsi=0.42 rad at pipeline start → C-05 immediate latch.
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(cobraflex_share, "launch", "gazebo_mesh.launch.py")
        ),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "rviz": "false",
            "use_sim_time": "true",
            "start_paused": "true",
        }.items(),
    )

    unpause = TimerAction(
        period=4.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "gz", "service",
                    "-s", "/world/lane_following_oval/control",
                    "--reqtype", "gz.msgs.WorldControl",
                    "--reptype", "gz.msgs.Boolean",
                    "--timeout", "5000",
                    "--req", "pause: false",
                ],
                output="screen",
            )
        ],
    )

    perception = Node(
        package="cobraflex_rl",
        executable="lane_perception_node",
        name="lane_perception",
        output="screen",
        parameters=[{
            "centerline_yaml": LaunchConfiguration("centerline_yaml"),
            # Use the EKF-fused estimate instead of raw Gazebo encoder odom.
            # Raw skid-steer odom oscillates ~20 cm between consecutive 50 ms
            # ticks at the curve (~0.07 m/s), producing alternating ey ≈ -0.14
            # and +0.06, which drives C-05 Trigger 7. The EKF fuses IMU +
            # velocities and is substantially smoother.
            "odom_topic": "/odometry/filtered",
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
            "use_safe_throttle": True,
            "throttle_nominal": 0.5,
            "min_speed_scale": 0.35,
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
            "cage_mode": LaunchConfiguration("cage_mode"),
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
        unpause,
        perception,
        pd,
        cage,
        vehicle,
        logger,
    ])
