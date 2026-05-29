from __future__ import annotations

import math
import re
import subprocess
import time
from typing import Optional, Tuple

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node


class RosGazeboInterface(Node):
    def __init__(
        self,
        world_name: str = "lane_following_oval",
        model_name: str = "cobraflex_robot",
        spawn_z: float = 0.05,
        service_timeout_ms: int = 2000,
        odom_topic: str = "/odom_truth",
    ) -> None:
        super().__init__("cobraflex_rl_interface")
        self._odom_msg: Optional[Odometry] = None
        self.world_name = world_name
        self.model_name = model_name
        self.spawn_z = float(spawn_z)
        self.service_timeout_ms = int(service_timeout_ms)
        self.odom_topic = str(odom_topic)
        self._model_entity_id: Optional[int] = None
        # We subscribe to the OdometryPublisher ground-truth pose (/odom_truth),
        # NOT the DiffDrive encoder /odom. Both plugins used to publish /odom, so
        # the RL subscriber saw interleaved truth + dead-reckoning samples; after
        # a set_pose teleport the dead-reckoning half does not jump, which
        # corrupted the tracked pose on every episode reset. Ground truth
        # reflects teleports immediately, so the per-episode offset below only
        # removes a constant odom->world frame translation.
        self._odom_dx: float = 0.0
        self._odom_dy: float = 0.0
        self._odom_dyaw: float = 0.0

        self._odom_sub = self.create_subscription(
            Odometry,
            self.odom_topic,
            self._odom_callback,
            10,
        )
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

    def _odom_callback(self, msg: Odometry) -> None:
        self._odom_msg = msg

    @staticmethod
    def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        return math.atan2(siny_cosp, cosy_cosp)

    def wait_for_initial_data(self, timeout_sec: float = 10.0) -> bool:
        deadline = time.monotonic() + float(timeout_sec)
        while rclpy.ok() and self._odom_msg is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        return self._odom_msg is not None

    def send_action(self, steer: float, speed: float) -> None:
        msg = Twist()
        msg.linear.x = float(speed)
        msg.angular.z = float(steer)
        self._cmd_pub.publish(msg)

    def step_ros(self, duration: float) -> None:
        end_time = time.monotonic() + max(0.0, float(duration))
        while rclpy.ok() and time.monotonic() < end_time:
            remaining = max(0.0, end_time - time.monotonic())
            rclpy.spin_once(self, timeout_sec=min(0.05, remaining))

    def _get_raw_pose(self) -> Tuple[float, float, float]:
        if self._odom_msg is None:
            raise RuntimeError("No odometry data received yet.")
        pose = self._odom_msg.pose.pose
        orientation = pose.orientation
        yaw = self.quaternion_to_yaw(
            orientation.x, orientation.y, orientation.z, orientation.w
        )
        return float(pose.position.x), float(pose.position.y), float(yaw)

    def get_pose(self) -> Tuple[float, float, float]:
        raw_x, raw_y, raw_yaw = self._get_raw_pose()
        corrected_yaw = math.atan2(
            math.sin(raw_yaw + self._odom_dyaw),
            math.cos(raw_yaw + self._odom_dyaw),
        )
        return raw_x + self._odom_dx, raw_y + self._odom_dy, corrected_yaw

    def calibrate_pose_offset(self, true_x: float, true_y: float, true_yaw: float) -> None:
        """Compute the additive offset that maps current raw odom → known world pose.

        Call once after wait_for_initial_data + step_ros following each teleport.
        With the ground-truth /odom_truth source this offset is just the constant
        odom->world frame translation (the OdometryPublisher already reflects the
        set_pose teleport), so get_pose() returns world coordinates thereafter.
        """
        raw_x, raw_y, raw_yaw = self._get_raw_pose()
        self._odom_dx = float(true_x) - raw_x
        self._odom_dy = float(true_y) - raw_y
        self._odom_dyaw = math.atan2(
            math.sin(float(true_yaw) - raw_yaw),
            math.cos(float(true_yaw) - raw_yaw),
        )

    def get_speed(self) -> float:
        if self._odom_msg is None:
            raise RuntimeError("No odometry data received yet.")

        linear = self._odom_msg.twist.twist.linear
        return float(math.sqrt(linear.x**2 + linear.y**2 + linear.z**2))

    def reset_world(self) -> None:
        self.send_action(0.0, 0.0)

    def set_vehicle_pose(self, x: float, y: float, yaw: float) -> None:
        # Resolve entity ID once and cache it for the rest of the training run
        # to avoid a subprocess timeout on every episode reset.
        if self._model_entity_id is None:
            self._model_entity_id = self._lookup_model_entity_id()
        entity_id = self._model_entity_id or 0

        half_yaw = 0.5 * float(yaw)
        request = (
            f'name: "{self.model_name}" '
            f"id: {entity_id} "
            f"position {{ x: {float(x):.9f} y: {float(y):.9f} z: {self.spawn_z:.9f} }} "
            f"orientation {{ z: {math.sin(half_yaw):.9f} w: {math.cos(half_yaw):.9f} }}"
        )
        # Clear cached odom before attempting teleport so wait_for_initial_data
        # always blocks until fresh post-teleport data arrives, regardless of
        # whether the service call succeeds or fails.
        self._odom_msg = None
        for attempt in range(2):
            if self._call_gz_service(
                service=f"/world/{self.world_name}/set_pose",
                request_type="gz.msgs.Pose",
                response_type="gz.msgs.Boolean",
                request=request,
            ):
                return
            if attempt == 0:
                time.sleep(0.5)

    def _call_gz_service(
        self,
        service: str,
        request_type: str,
        response_type: str,
        request: str,
    ) -> bool:
        cmd = [
            "gz",
            "service",
            "-s",
            service,
            "--reqtype",
            request_type,
            "--reptype",
            response_type,
            "--timeout",
            str(self.service_timeout_ms),
            "--req",
            request,
        ]
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=(self.service_timeout_ms / 1000.0) + 1.0,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._warn_gz_service_failure(service, str(exc))
            return False

        output = f"{completed.stdout}\n{completed.stderr}"
        if completed.returncode == 0 and "data: true" in output.lower():
            return True

        self._warn_gz_service_failure(service, output.strip() or "service returned false")
        return False

    def _warn_gz_service_failure(self, service: str, reason: str) -> None:
        self.get_logger().warning(
            f"Gazebo service call failed for {service}: {reason}"
        )

    def _lookup_model_entity_id(self) -> Optional[int]:
        cmd = [
            "gz",
            "topic",
            "-e",
            "-t",
            f"/world/{self.world_name}/pose/info",
            "-n",
            "1",
        ]
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=2.0,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

        if completed.returncode != 0:
            return None

        pattern = rf'name:\s+"{re.escape(self.model_name)}"\s+id:\s+(\d+)'
        match = re.search(pattern, completed.stdout)
        if match is None:
            return None

        self._model_entity_id = int(match.group(1))
        return self._model_entity_id
