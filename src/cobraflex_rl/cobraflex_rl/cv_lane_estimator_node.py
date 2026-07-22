"""
cv_lane_estimator_node — ROS2 wrapper for the cage's CV lane-estimator (D-43).

Deployment analogue of the in-process path used by `gazebo_lane_env`: replaces
`lane_perception_node` (odom + authored centerline) as the source of the
cage's `/state_obs` on track 'E', so the cage generalises to any road with
visible lane lines.

Subscribes:
    camera/image_raw_lane  sensor_msgs/Image  (the same frames the policy sees)
    /odom              nav_msgs/Odometry      (speed only — plausibility + cage state)

Publishes (at ``publish_rate_hz``):
    /state_obs           std_msgs/Float64MultiArray
                         [ey, epsi, speed, kappa_ahead, d_left, d_right, 1.0]
                         — same fixed ordering as lane_perception_node. The
                         publish is SUPPRESSED while the supervisor has no
                         acceptable estimate (F2 precedent: the cage's
                         missing-state path handles the gap; publishing
                         state_valid=0 would latch C-05 Trigger 4).
    /perception_invalid  std_msgs/Bool — the C-05 Trigger 8 input
                         (cage_ros_node latches it into ctx like
                         /external_stop). Published every tick.

The estimator, health monitor and plausibility check are the host-tested pure
modules (`cv_lane_estimator`, `perception_health`, `lane_plausibility`)
composed by `cage_perception.CagePerceptionSupervisor` — identical logic to
training/eval, only the transport differs.

Clock domain — run with ``use_sim_time:=true`` in simulation. The gz bridge
stamps camera frames with sim time; the supervisor's staleness check compares
those stamps against this node's clock, so a wall-clock node sees every frame
as ancient and latches perception_invalid permanently.
"""
from __future__ import annotations

import math
from typing import Optional

import rclpy
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float64MultiArray

from .cage_perception import CagePerceptionSupervisor
from .camera_pipeline import decode_image
from .cv_lane_estimator import CvLaneEstimator, CvLaneEstimatorConfig


class CvLaneEstimatorNode(Node):
    """Camera → /state_obs + /perception_invalid via the perception supervisor."""

    def __init__(self) -> None:
        super().__init__("cv_lane_estimator_node")
        self.declare_parameter("image_topic", "camera/image_raw_lane")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("state_obs_topic", "/state_obs")
        self.declare_parameter("perception_invalid_topic", "/perception_invalid")
        self.declare_parameter("publish_rate_hz", 10.0)
        self.declare_parameter("road_width_m", 0.52)
        self.declare_parameter("heading_fit_mode", "near_secant")
        self.declare_parameter("heading_gain", 1.0)

        estimator = CvLaneEstimator(config=CvLaneEstimatorConfig(
            heading_fit_mode=str(self.get_parameter("heading_fit_mode").value),
            heading_gain=float(self.get_parameter("heading_gain").value),
        ))
        self._supervisor = CagePerceptionSupervisor(estimator=estimator)
        self._image_msg: Optional[Image] = None
        self._speed = 0.0
        self._road_width = float(self.get_parameter("road_width_m").value)

        self.create_subscription(
            Image,
            str(self.get_parameter("image_topic").value),
            self._on_image,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Odometry,
            str(self.get_parameter("odom_topic").value),
            self._on_odom,
            QoSPresetProfiles.SENSOR_DATA.value,
        )
        self._state_pub = self.create_publisher(
            Float64MultiArray, str(self.get_parameter("state_obs_topic").value), 10
        )
        self._invalid_pub = self.create_publisher(
            Bool, str(self.get_parameter("perception_invalid_topic").value), 10
        )
        rate = float(self.get_parameter("publish_rate_hz").value or 10.0)
        self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(
            "cv_lane_estimator_node up (D-43 cage perception source; "
            f"heading_fit_mode={estimator.config.heading_fit_mode}, "
            f"heading_gain={estimator.config.heading_gain:.3f})"
        )

    def _on_image(self, msg: Image) -> None:
        self._image_msg = msg

    def _on_odom(self, msg: Odometry) -> None:
        """Track planar speed only (the estimator never sees the odom pose)."""
        lin = msg.twist.twist.linear
        speed = math.sqrt(float(lin.x) ** 2 + float(lin.y) ** 2)
        if math.isfinite(speed):
            self._speed = speed

    def _tick(self) -> None:
        """One supervisor cycle: decode the latest frame, publish invalid flag + state."""
        now = self.get_clock().now().nanoseconds * 1e-9
        frame = None
        stamp = 0.0
        msg = self._image_msg
        if msg is not None:
            try:
                frame = decode_image(
                    msg.data, int(msg.height), int(msg.width),
                    msg.encoding, int(msg.step),
                )
                stamp = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9
            except ValueError as exc:
                self.get_logger().warning(f"camera decode failed: {exc}")

        result = self._supervisor.update(
            frame, frame_timestamp_s=stamp, now_s=now, speed_mps=self._speed
        )

        invalid = Bool()
        invalid.data = bool(result.perception_invalid)
        self._invalid_pub.publish(invalid)

        if not result.state_available:
            return  # suppressed publish → cage missing-state path (F2 precedent)
        est = result.estimate
        half = self._road_width / 2.0
        out = Float64MultiArray()
        out.data = [
            float(est.ey),
            float(est.epsi),
            float(self._speed),
            float(est.curvature),
            max(0.0, half - est.ey),
            max(0.0, half + est.ey),
            1.0,
        ]
        self._state_pub.publish(out)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CvLaneEstimatorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
