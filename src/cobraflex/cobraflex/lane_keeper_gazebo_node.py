#!/usr/bin/env python3
"""Camera lane keeper for Gazebo.

Logical (non-learned) lane-keeping controller, the fair baseline for the RL
camera agent. It uses the shared :class:`cobraflex_rl.cv_lane_controller.CVLaneController`
— the deterministic CV lane estimator (D-43, the same the safety cage reads)
plus a PD + curvature-feedforward law — so this deployment node and the scored
evaluation (``cobraflex_rl.eval_cv_controller``) drive identically.

It supersedes the previous histogram pure-P controller, whose uncalibrated
"lane centre = image centre" set-point could not hold the lane above ~0.1 m/s.
The CV+PD law tracks the nominal oval to RMSE ~10 mm at 0.2 m/s (req < 50 mm).
"""

import time

import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
    qos_profile_sensor_data,
)

from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image

from cobraflex_rl.cv_lane_controller import CVLaneController


def _ros_image_to_bgr(msg: Image) -> np.ndarray:
    """Convert a ROS Image message to a BGR OpenCV frame."""
    encoding = msg.encoding.lower()
    channels_by_encoding = {
        "mono8": 1,
        "8uc1": 1,
        "bgr8": 3,
        "rgb8": 3,
        "8uc3": 3,
        "bgra8": 4,
        "rgba8": 4,
        "8uc4": 4,
    }

    channels = channels_by_encoding.get(encoding)
    if channels is None:
        raise ValueError(f"Unsupported image encoding: {msg.encoding}")

    row_stride = int(msg.step) if msg.step > 0 else int(msg.width * channels)
    expected_size = int(msg.height * row_stride)
    data = np.frombuffer(msg.data, dtype=np.uint8)

    if data.size < expected_size:
        raise ValueError(
            f"Image buffer too small for {msg.encoding}: {data.size} < {expected_size}"
        )

    rows = data[:expected_size].reshape((msg.height, row_stride))

    if channels == 1:
        gray = np.ascontiguousarray(rows[:, : msg.width])
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    image = rows[:, : msg.width * channels].reshape((msg.height, msg.width, channels))
    image = np.ascontiguousarray(image)

    if channels == 3:
        if encoding in ("bgr8", "8uc3"):
            return image
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    if encoding in ("bgra8", "8uc4"):
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)


class LaneKeeperGazeboNode(Node):
    """Camera lane keeper: calibrated CV lane estimate + PD/feedforward steering."""

    def __init__(self):
        super().__init__("lane_keeper_gazebo_node")

        self.declare_parameter("image_topic", "camera/image_raw_lane")
        self.declare_parameter("linear_speed", 0.20)
        self.declare_parameter("kp_ey", 6.0)
        self.declare_parameter("kd_epsi", 1.6)
        self.declare_parameter("kff_curv", 1.0)
        self.declare_parameter("max_angular_z", 0.9)
        # Stop (vs coast straight) when the estimator finds no usable lane.
        self.declare_parameter("stop_on_no_lane", True)
        self.declare_parameter("publish_debug_image", False)
        self.declare_parameter("show_debug_windows", False)
        self.declare_parameter("watchdog_timeout_sec", 1.5)

        debug_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        self.controller = CVLaneController(
            speed=float(self.get_parameter("linear_speed").value),
            kp_ey=float(self.get_parameter("kp_ey").value),
            kd_epsi=float(self.get_parameter("kd_epsi").value),
            kff_curv=float(self.get_parameter("kff_curv").value),
            max_angular_z=float(self.get_parameter("max_angular_z").value),
        )

        image_topic = str(self.get_parameter("image_topic").value)
        self.image_sub = self.create_subscription(
            Image, image_topic, self._image_callback, qos_profile_sensor_data
        )
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.debug_pub = self.create_publisher(Image, "/lane/image_overlay", debug_qos)

        self.last_frame_time = 0.0
        self.last_warn_time = 0.0
        self.timer = self.create_timer(0.2, self._watchdog_callback)

        self.get_logger().info(
            f"lane_keeper_gazebo_node (CV+PD) listening on '{image_topic}'"
        )

    def _build_image_msg(self, image, stamp, frame_id):
        """Wrap a numpy image as a sensor_msgs/Image."""
        if not image.flags["C_CONTIGUOUS"]:
            image = np.ascontiguousarray(image)
        msg = Image()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.height = int(image.shape[0])
        msg.width = int(image.shape[1])
        msg.encoding = "bgr8"
        msg.is_bigendian = False
        msg.step = int(image.strides[0])
        msg.data = image.tobytes()
        return msg

    def _publish_zero(self):
        """Publish a zero Twist (stop)."""
        self.cmd_pub.publish(Twist())

    def _watchdog_callback(self):
        """Stop the robot when no camera frame arrived within the watchdog window."""
        timeout = float(self.get_parameter("watchdog_timeout_sec").value)
        if timeout <= 0.0 or self.last_frame_time <= 0.0:
            return
        now = time.time()
        if now - self.last_frame_time > timeout:
            self._publish_zero()
            if now - self.last_warn_time >= 1.0:
                self.get_logger().warning("No camera frames received, publishing zero cmd_vel")
                self.last_warn_time = now

    def _image_callback(self, msg: Image):
        """Per-frame control tick: CV estimate → PD/feedforward steering → /cmd_vel."""
        try:
            frame_bgr = _ros_image_to_bgr(msg)
        except ValueError as exc:
            self.get_logger().warning(f"Could not decode camera image: {exc}")
            return

        self.last_frame_time = time.time()
        angular, detected = self.controller.compute(frame_bgr)

        cmd = Twist()
        if detected:
            cmd.linear.x = float(self.get_parameter("linear_speed").value)
            cmd.angular.z = float(angular)
        elif not bool(self.get_parameter("stop_on_no_lane").value):
            cmd.linear.x = float(self.get_parameter("linear_speed").value)
        self.cmd_pub.publish(cmd)

        if bool(self.get_parameter("publish_debug_image").value) or bool(
            self.get_parameter("show_debug_windows").value
        ):
            debug_image = self._render_debug(frame_bgr, cmd)
            if bool(self.get_parameter("publish_debug_image").value):
                self.debug_pub.publish(
                    self._build_image_msg(debug_image, msg.header.stamp, msg.header.frame_id)
                )
            if bool(self.get_parameter("show_debug_windows").value):
                cv2.imshow("Lane Keeper Gazebo (CV+PD)", debug_image)
                cv2.waitKey(1)

    def _render_debug(self, frame_bgr, cmd):
        """White-mask overlay + the CV estimate / command, for the watch window."""
        debug = frame_bgr.copy()
        try:
            mask = self.controller.estimator.white_mask(frame_bgr)
            mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            debug = cv2.addWeighted(debug, 0.6, mask_bgr, 0.4, 0.0)
        except Exception:  # pragma: no cover - overlay is best-effort
            pass
        d = self.controller.dbg
        if d.get("ok"):
            txt = (f"ey={d['ey']:+.3f} epsi={d['epsi']:+.3f} k={d['kappa']:+.2f} "
                   f"cmd=({cmd.linear.x:.2f},{cmd.angular.z:+.2f})")
        else:
            txt = f"NO LANE ({d.get('reason', '')})  cmd=({cmd.linear.x:.2f},{cmd.angular.z:+.2f})"
        cv2.putText(debug, txt, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 255, 255), 2)
        return debug


def main(args=None):
    rclpy.init(args=args)
    node = LaneKeeperGazeboNode()
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
