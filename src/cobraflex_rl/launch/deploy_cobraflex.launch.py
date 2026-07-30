"""
deploy_cobraflex.launch.py — Phase-5 physical bring-up of the track-'E' RL
camera policy behind the safety cage, on the real CobraFlex 1:14.

**STATUS: deployment scaffolding — NOT yet run on hardware.** Wires the same
distributed node chain as the F2 physical demo, now camera-driven and 2-D:

      csi_camera_node       (Jetson CSI → camera/image_raw_lane) [NEW, Phase 5]
      rl_policy_node        (image → CNN → /raw_action)           [NEW, Phase 5]
      cv_lane_estimator_node(image → /state_obs + /perception_invalid, D-43)
      cage_ros_node         (/raw_action + /state_obs → /safe_action + /cage_status)
      vehicle_control_node  (/safe_action → /cmd_vel)
      cobraflex_ros_driver  (/cmd_vel → JSON {"T":13,"X":vx,"Z":wz} over serial)
      cage_logger_node      (/cage_status → CSV evidence)

This is a **Layer-3 controller launch**, matching the platform's own layering:

    Layer 1  cobraflex_bringup.launch.xml   description (robot_state_publisher +
             joint_state_publisher + rviz) + cobraflex_ros_driver (ROS→JSON serial)
    Layer 2  cobraflex_sensors.launch.xml   SLLIDAR A2M8 + ZED Mini  [not needed here]
    Layer 3  a controller: cobraflex_lane_keeper.launch.py (classical CV),
             cobraflex_automatic.launch.xml (lidar avoidance), or THIS launch (RL)

Like `cobraflex_lane_keeper.launch.py`, it attaches to a Layer-1 bring-up that is
already running, so the RL policy actuates through exactly the same ROS→JSON
serial interface as every other CobraFlex controller. ``bringup:=true`` includes
Layer 1 for a one-shot standalone start; do NOT use it if the bring-up is already
up (Linux does not lock /dev/ttyACM*, so a second driver silently interleaves
writes on the same port).

The lane camera is the **Jetson CSI cam** — the same camera the Gazebo ``Lane Cam``
sensor was built to mirror (640x360, 90 deg HFOV, 20 Hz). It is published here by
``csi_camera_node``, which reuses ``lane_keeper_node``'s proven GStreamer pipeline
and its 640x360 INTER_AREA downsample. It has to be a separate node because the
classical controller opens the device *inside* ``lane_keeper_node``, which also
publishes ``/cmd_vel`` and would fight this chain for actuation — so never run the
two at once (they also contend for the CSI device itself). ``camera:=false``
attaches to an externally-published topic instead.

The ZED Mini (Layer 2) is NOT in this loop — it is only a human monitoring view.
To watch exactly what the policy sees, put rviz on ``camera_topic``.

PREREQUISITES (see docs/17_physical_deployment.md):
  * Layer-1 bring-up running (or ``bringup:=true``).
  * ``lane_keeper_node`` NOT running (same CSI device, competing /cmd_vel).
  * Camera extrinsics matched to the trained IPM (pitch 0.30 rad, height 0.077 m)
    OR the D-57 ``perception_heading_bias_rad`` re-calibrated for the real mount.
  * A hardware e-stop wired to /external_stop (Bool) — MANDATORY before first run.

KNOWN ITEMS TO VERIFY ON HARDWARE:
  1. The 2-D throttle→speed mapping. The in-sim cage bridge uses
     ``cage_bridge.target_speed_from_throttle_2d`` (max_speed·u, full stop below
     the deadband); ``vehicle_control_node`` here uses ``use_safe_throttle`` to
     scale ``fixed_speed_mps``. Confirm these agree (set ``fixed_speed_mps`` =
     the config ``action.max_speed_mps`` and validate the deadband).
  2. The ``steering_to_yaw_rate_gain`` (0.8). It was calibrated against the
     Gazebo DiffDrive plugin's reading of /cmd_vel.angular.z; the firmware's
     ``Z`` in ``{"T":13,...}`` is a nominally equivalent yaw rate on an Ackermann
     chassis, but the two have never been compared on the real car. Re-calibrate
     before trusting the cage's C-02/C-03 margins on hardware.
  3. The driver has NO /cmd_vel watchdog: ``_resend_last_cmd`` re-sends the last
     command every 50 ms as a firmware keep-alive. ``vehicle_control_node``
     covers the cage dying (``safe_action_timeout_s`` → zero Twist), but if
     *vehicle_control_node itself* dies the car keeps driving on the last
     command. The hardware e-stop is the only mitigation — hence MANDATORY.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import AnyLaunchDescriptionSource
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
        DeclareLaunchArgument("camera", default_value="true",
                              description="launch csi_camera_node (the Jetson CSI lane "
                                          "camera). false = camera_topic is published "
                                          "externally."),
        DeclareLaunchArgument("sensor_id", default_value="0",
                              description="CSI sensor index."),
        DeclareLaunchArgument("flip_method", default_value="0",
                              description="nvvidconv flip-method for the CSI capture."),
        DeclareLaunchArgument("bringup", default_value="false",
                              description="also launch cobraflex_bringup.launch.xml "
                                          "(description + ROS→JSON serial driver). Leave "
                                          "false when the platform bring-up is already "
                                          "running — two drivers on one serial port is "
                                          "silent corruption, not an error."),
        DeclareLaunchArgument("serial_port", default_value="/dev/ttyACM1",
                              description="chassis serial device (used only with bringup:=true)."),
        DeclareLaunchArgument("baudrate", default_value="115200"),
        DeclareLaunchArgument("use_rviz", default_value="false",
                              description="rviz in the included bring-up (default off for "
                                          "a deploy run; the platform default is true)."),
    ]
    checkpoint = LaunchConfiguration("checkpoint")
    algorithm = LaunchConfiguration("algorithm")
    cage_yaml = LaunchConfiguration("cage_yaml")
    mode = LaunchConfiguration("mode")
    camera_topic = LaunchConfiguration("camera_topic")
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")
    max_speed = LaunchConfiguration("max_speed_mps")

    # The image source both consumers subscribe to. Frame geometry is NOT
    # parameterised here on purpose: csi_camera_node defaults out_width/out_height
    # from camera_geometry, so the trained 640x360 / 90 deg contract cannot be
    # overridden from a launch file by accident.
    csi_camera = Node(
        package="cobraflex_rl", executable="csi_camera_node", output="screen",
        condition=IfCondition(LaunchConfiguration("camera")),
        parameters=[{
            "image_topic": camera_topic,
            "sensor_id": LaunchConfiguration("sensor_id"),
            "flip_method": LaunchConfiguration("flip_method"),
        }],
    )
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
    # Layer 1 of the platform's own bring-up (robot_state_publisher +
    # joint_state_publisher + rviz, then the ROS→JSON serial driver), included
    # verbatim so the RL policy actuates through exactly the same interface as
    # the PD/CV controllers. OFF by default: the platform convention is that a
    # controller launch attaches to a bring-up that is already running (cf.
    # cobraflex_lane_keeper.launch.py). Enabling it while cobraflex_bringup is
    # already up would start a SECOND cobraflex_ros_driver on the same serial
    # device — Linux does not lock /dev/ttyACM*, so both would interleave JSON
    # writes and keep-alives undetected.
    platform_bringup = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(os.path.join(
            get_package_share_directory("cobraflex"), "launch",
            "cobraflex_bringup.launch.xml",
        )),
        launch_arguments={
            "serial_port": LaunchConfiguration("serial_port"),
            "baudrate": LaunchConfiguration("baudrate"),
            "use_rviz": LaunchConfiguration("use_rviz"),
        }.items(),
        condition=IfCondition(LaunchConfiguration("bringup")),
    )

    return LaunchDescription(args + [
        platform_bringup, csi_camera, rl_policy, cv_estimator, cage,
        vehicle_control, cage_logger,
    ])
