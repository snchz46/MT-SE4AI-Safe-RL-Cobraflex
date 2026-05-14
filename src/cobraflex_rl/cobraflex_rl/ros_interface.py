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
        world_name: str = "road_carpet_world",
        model_name: str = "cobraflex_robot",
        spawn_z: float = 0.2,
        service_timeout_ms: int = 1000,
    ) -> None:
        super().__init__("cobraflex_rl_interface")
        self._odom_msg: Optional[Odometry] = None
        self.world_name = world_name
        self.model_name = model_name
        self.spawn_z = float(spawn_z)
        self.service_timeout_ms = int(service_timeout_ms)
        self._warned_gz_service_failure = False
        self._model_entity_id: Optional[int] = None

        self._odom_sub = self.create_subscription(
            Odometry,
            "/odom",
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

    def get_pose(self) -> Tuple[float, float, float]:
        if self._odom_msg is None:
            raise RuntimeError("No odometry data received yet.")

        pose = self._odom_msg.pose.pose
        orientation = pose.orientation
        yaw = self.quaternion_to_yaw(
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w,
        )
        return float(pose.position.x), float(pose.position.y), float(yaw)

    def get_speed(self) -> float:
        if self._odom_msg is None:
            raise RuntimeError("No odometry data received yet.")

        linear = self._odom_msg.twist.twist.linear
        return float(math.sqrt(linear.x**2 + linear.y**2 + linear.z**2))

    def reset_world(self) -> None:
        self.send_action(0.0, 0.0)

    def set_vehicle_pose(self, x: float, y: float, yaw: float) -> None:
        entity_id = self._model_entity_id or self._lookup_model_entity_id()
        half_yaw = 0.5 * float(yaw)
        request = (
            f'name: "{self.model_name}" '
            f"id: {entity_id or 0} "
            f"position {{ x: {float(x):.9f} y: {float(y):.9f} z: {self.spawn_z:.9f} }} "
            f"orientation {{ z: {math.sin(half_yaw):.9f} w: {math.cos(half_yaw):.9f} }}"
        )
        if self._call_gz_service(
            service=f"/world/{self.world_name}/set_pose",
            request_type="gz.msgs.Pose",
            response_type="gz.msgs.Boolean",
            request=request,
        ):
            self._odom_msg = None
            return

        self._model_entity_id = None
        entity_id = self._lookup_model_entity_id()
        if entity_id is None:
            return

        request = (
            f'name: "{self.model_name}" '
            f"id: {entity_id} "
            f"position {{ x: {float(x):.9f} y: {float(y):.9f} z: {self.spawn_z:.9f} }} "
            f"orientation {{ z: {math.sin(half_yaw):.9f} w: {math.cos(half_yaw):.9f} }}"
        )
        if self._call_gz_service(
            service=f"/world/{self.world_name}/set_pose",
            request_type="gz.msgs.Pose",
            response_type="gz.msgs.Boolean",
            request=request,
        ):
            self._odom_msg = None

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
        if self._warned_gz_service_failure:
            return
        self._warned_gz_service_failure = True
        self.get_logger().warning(
            f"Gazebo service call failed for {service}; continuing with current simulation state. "
            f"Reason: {reason}"
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
