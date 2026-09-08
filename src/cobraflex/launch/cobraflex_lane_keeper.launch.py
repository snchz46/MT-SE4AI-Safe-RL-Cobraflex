"""Launch the CobraFlex lane keeper node with optional RViz."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Build the lane keeper launch description."""
    use_rviz = LaunchConfiguration("use_rviz")
    rviz_config = LaunchConfiguration("rviz_config")
    show_debug_windows = LaunchConfiguration("show_debug_windows")
    show_control_window = LaunchConfiguration("show_control_window")

    # Vision tuning, exposed as launch arguments so a tuning sweep does not need
    # a rebuild: ros2 launch ... threshold_val:=40 tophat_k:=51
    invert = LaunchConfiguration("invert")
    threshold_val = LaunchConfiguration("threshold_val")
    tophat_k = LaunchConfiguration("tophat_k")
    max_white_pct = LaunchConfiguration("max_white_pct")
    peak_min = LaunchConfiguration("peak_min")

    ae_lock = LaunchConfiguration("ae_lock")
    exposure_max_ns = LaunchConfiguration("exposure_max_ns")

    lane_keeper_node = Node(
        package="cobraflex",
        executable="lane_keeper_node",
        name="lane_keeper",
        output="screen",
        emulate_tty=True,
        parameters=[
            {"lane_side": 1},
            {"linear_speed": 0.12},
            {"angular_gain": 1.30},
            {
                "show_debug_windows": ParameterValue(
                    show_debug_windows,
                    value_type=bool,
                )
            },
            {
                "show_control_window": ParameterValue(
                    show_control_window,
                    value_type=bool,
                )
            },
            {"publish_raw_image": True},
            {"publish_overlay_image": True},
            {"publish_mask_image": True},
            {"publish_histogram_image": True},
            {"publish_camera_info": True},
            {"publish_markers": True},
            {"camera_frame_id": "camera_link_optical_lane"},
            {"marker_frame_id": "base_footprint"},
            {"flip_method": 0},
            # ===== Camera exposure =====
            {"ae_lock": ParameterValue(ae_lock, value_type=bool)},
            {
                "exposure_max_ns": ParameterValue(
                    exposure_max_ns,
                    value_type=int,
                )
            },
            # ===== Line detection =====
            # invert=False keeps pixels ABOVE the threshold: bright lines on dark
            # road. Set it to true only for dark tape on a light floor.
            {"invert": ParameterValue(invert, value_type=bool)},
            {"threshold_val": ParameterValue(threshold_val, value_type=int)},
            {"tophat_k": ParameterValue(tophat_k, value_type=int)},
            {"max_white_pct": ParameterValue(max_white_pct, value_type=int)},
            {"peak_min": ParameterValue(peak_min, value_type=int)},
            # ===== ROI =====
            {"roi_start_pct": 17},
            {"trap_top_y_pct": 20},
            {"trap_top_w_pct": 100},
            {"trap_bottom_w_pct": 100},
        ],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2_lane_keeper",
        output="screen",
        condition=IfCondition(use_rviz),
        arguments=[
            "-d",
            PathJoinSubstitution(
                [FindPackageShare("cobraflex"), "rviz", rviz_config]
            ),
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Launch RViz with a lane-keeper focused layout.",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value="lane_keeper.rviz",
                description="RViz config file inside the cobraflex/rviz folder.",
            ),
            DeclareLaunchArgument(
                "show_debug_windows",
                default_value="false",
                description="Show OpenCV debug windows alongside RViz.",
            ),
            DeclareLaunchArgument(
                "show_control_window",
                default_value="false",
                description=(
                    "Show the OpenCV tuning panel with trackbars. While enabled the "
                    "trackbars override the vision parameters every cycle, so "
                    "ros2 param set has no effect on them."
                ),
            ),
            DeclareLaunchArgument(
                "invert",
                default_value="false",
                description=(
                    "false: bright lines on dark road. true: dark lines on a light "
                    "floor."
                ),
            ),
            DeclareLaunchArgument(
                "threshold_val",
                default_value="30",
                description=(
                    "Binary threshold. Roughly 25-45 with the top-hat enabled, "
                    "roughly 150-200 with tophat_k=0."
                ),
            ),
            DeclareLaunchArgument(
                "tophat_k",
                default_value="41",
                description=(
                    "Top-hat kernel width in px, about 2-3x the lane line width. "
                    "0 disables it and thresholds the raw grey image."
                ),
            ),
            DeclareLaunchArgument(
                "max_white_pct",
                default_value="55",
                description=(
                    "White ratio inside the trapezoid above which a band is treated "
                    "as saturated and dropped."
                ),
            ),
            DeclareLaunchArgument(
                "peak_min",
                default_value="5",
                description="Minimum column-histogram height for a line candidate.",
            ),
            DeclareLaunchArgument(
                "ae_lock",
                default_value="true",
                description=(
                    "Pin exposure, gain and white balance. false falls back to the "
                    "ISP auto mode, which blows out bright asphalt."
                ),
            ),
            DeclareLaunchArgument(
                "exposure_max_ns",
                default_value="15000000",
                description=(
                    "Upper bound of the exposure range in ns. Lower it if the road "
                    "still looks washed out."
                ),
            ),
            lane_keeper_node,
            rviz_node,
        ]
    )
