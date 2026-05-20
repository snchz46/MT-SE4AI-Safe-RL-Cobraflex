"""
lane_perception_node — ground-truth Perception for the F2 pipeline.

Consumes:
    /odom    nav_msgs/Odometry

Publishes:
    /state_obs   std_msgs/Float64MultiArray with fixed ordering:
        [lateral_offset_m,
         heading_error_rad,
         speed_mps,
         curvature_ahead_inv_m,
         distance_left_m,
         distance_right_m,
         state_valid (1.0/0.0)]

Centerline source: YAML at the path given by parameter `centerline_yaml`.
Curvature look-ahead: the heading delta between the current segment and
the segment `lookahead_segments` ahead, divided by their arc length.

The node is the F2 "sim-only" Perception (cf. fase_2_detallada.md §9.1).
Sensor-noise and OOD handling come later; in F2 the only conditions
that force `state_valid=False` are:
    - never received /odom yet
    - pose contains NaN/Inf
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import numpy as np
import rclpy
import yaml
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from std_msgs.msg import Float64MultiArray

from .polyline_tracker import PolylineTracker


def _yaw_from_quat(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def _wrap_pi(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


class LanePerceptionNode(Node):
    def __init__(self) -> None:
        super().__init__("lane_perception")

        self.declare_parameter("centerline_yaml", "")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("lookahead_segments", 5)
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("state_obs_topic", "/state_obs")

        centerline_path = self._resolve_centerline_path()
        with Path(centerline_path).open("r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle)

        centerline_points = np.asarray(cfg["centerline"]["points"], dtype=float)
        self._lane_width = float(cfg["lane_width"])
        self._road_width = float(cfg.get("road_width", self._lane_width))
        self._tracker = PolylineTracker(centerline_points)
        self._lookahead = int(
            self.get_parameter("lookahead_segments").get_parameter_value().integer_value
            or 5
        )

        sensor_qos = QoSPresetProfiles.SENSOR_DATA.value
        self._odom_msg: Optional[Odometry] = None
        self._got_odom_once = False

        self.create_subscription(
            Odometry,
            self.get_parameter("odom_topic").value,
            self._on_odom,
            sensor_qos,
        )
        self._pub = self.create_publisher(
            Float64MultiArray,
            self.get_parameter("state_obs_topic").value,
            sensor_qos,
        )

        period = 1.0 / float(self.get_parameter("publish_rate_hz").value or 20.0)
        self._timer = self.create_timer(period, self._tick)

        self.get_logger().info(
            f"Centerline loaded: {len(centerline_points)} points, "
            f"perimeter={self._tracker.cumulative_lengths[-1]:.3f} m, "
            f"lane_width={self._lane_width} m, road_width={self._road_width} m."
        )

    def _resolve_centerline_path(self) -> str:
        param = self.get_parameter("centerline_yaml").get_parameter_value().string_value
        if param:
            return param

        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "config" / "oval_centerline.yaml"
            if candidate.is_file():
                return str(candidate)
        raise RuntimeError(
            "centerline_yaml parameter is empty and config/oval_centerline.yaml "
            "could not be located by walking up from the node source file."
        )

    def _on_odom(self, msg: Odometry) -> None:
        self._odom_msg = msg
        self._got_odom_once = True

    def _tick(self) -> None:
        msg = Float64MultiArray()
        if not self._got_odom_once or self._odom_msg is None:
            msg.data = [0.0, 0.0, 0.0, 0.0, self._road_width / 2, self._road_width / 2, 0.0]
            self._pub.publish(msg)
            return

        pose = self._odom_msg.pose.pose
        x = float(pose.position.x)
        y = float(pose.position.y)
        yaw = _yaw_from_quat(
            float(pose.orientation.x),
            float(pose.orientation.y),
            float(pose.orientation.z),
            float(pose.orientation.w),
        )

        lin = self._odom_msg.twist.twist.linear
        speed = math.sqrt(float(lin.x) ** 2 + float(lin.y) ** 2)

        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(yaw) and math.isfinite(speed)):
            msg.data = [0.0, 0.0, 0.0, 0.0, self._road_width / 2, self._road_width / 2, 0.0]
            self._pub.publish(msg)
            return

        track_state = self._tracker.track(x, y, yaw)
        kappa_ahead = self._curvature_ahead(track_state.segment_index)

        ey = float(track_state.ey)
        epsi = float(track_state.epsi)
        d_left = max(0.0, (self._road_width / 2) - ey)
        d_right = max(0.0, (self._road_width / 2) + ey)

        msg.data = [ey, epsi, speed, kappa_ahead, d_left, d_right, 1.0]
        self._pub.publish(msg)

    def _curvature_ahead(self, segment_index: int) -> float:
        headings = self._tracker.segment_headings
        cum = self._tracker.cumulative_lengths
        n = len(headings)
        if n < 2:
            return 0.0
        i_end = min(n - 1, segment_index + self._lookahead)
        arc = float(cum[i_end] - cum[segment_index])
        if arc <= 1e-6:
            return 0.0
        dpsi = _wrap_pi(float(headings[i_end]) - float(headings[segment_index]))
        return dpsi / arc


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LanePerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
