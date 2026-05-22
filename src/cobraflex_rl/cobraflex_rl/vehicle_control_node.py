"""
vehicle_control_node — relay /safe_action to /cmd_vel.

For the F2 demo (1D-steering decision), the longitudinal speed is fixed
at `fixed_speed` rather than mapped from the cage's safe throttle. C-04
is therefore dormant in this lazo (speed stays under v_max_straight),
but the cage still computes and logs its decisions. Emergency mode is
honoured via /emergency: when latched True, /cmd_vel.linear.x is forced
to zero so the controlled stop of C-05 is actuated.

The steering on /cmd_vel.angular.z always comes from /safe_action.angular.z.
"""

from __future__ import annotations

from typing import Optional

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from std_msgs.msg import Bool


class VehicleControlNode(Node):
    def __init__(self) -> None:
        super().__init__("vehicle_control")

        self.declare_parameter("fixed_speed_mps", 0.2)
        self.declare_parameter("steering_to_yaw_rate_gain", 0.8)
        self.declare_parameter("safe_action_topic", "/safe_action")
        self.declare_parameter("emergency_topic", "/emergency")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")

        self._fixed_speed = float(
            self.get_parameter("fixed_speed_mps").get_parameter_value().double_value
            or 0.2
        )
        # The DiffDrive plugin interprets /cmd_vel.angular.z as a yaw rate
        # in rad/s. The cage / PD operate on a normalised steering in
        # [-1, 1]; this gain maps one to the other. Default 0.8 gives a
        # min turn radius of v/omega = 0.2/0.8 = 0.25 m at v=0.2 m/s,
        # leaving comfortable headroom over the oval's R=0.8 m curves;
        # the previous 0.4 left only ~0.5 m and caused the PD to
        # saturate against C-05 on the curve.
        self._yaw_gain = float(
            self.get_parameter("steering_to_yaw_rate_gain")
            .get_parameter_value()
            .double_value
            or 0.8
        )
        self._emergency = False
        self._last_safe: Optional[Twist] = None

        sensor_qos = QoSPresetProfiles.SENSOR_DATA.value
        reliable_qos = QoSPresetProfiles.SYSTEM_DEFAULT.value

        self.create_subscription(
            Twist,
            self.get_parameter("safe_action_topic").value,
            self._on_safe,
            sensor_qos,
        )
        self.create_subscription(
            Bool,
            self.get_parameter("emergency_topic").value,
            self._on_emergency,
            reliable_qos,
        )
        self._pub = self.create_publisher(
            Twist,
            self.get_parameter("cmd_vel_topic").value,
            reliable_qos,
        )

        self.get_logger().info(
            f"Relaying {self.get_parameter('safe_action_topic').value} -> "
            f"{self.get_parameter('cmd_vel_topic').value} "
            f"(fixed_speed={self._fixed_speed} m/s, emergency-aware)."
        )

    def _on_emergency(self, msg: Bool) -> None:
        self._emergency = bool(msg.data)

    def _on_safe(self, msg: Twist) -> None:
        self._last_safe = msg
        cmd = Twist()
        if self._emergency:
            # Controlled stop: zero both axes so the robot does not pivot
            # in place while linear.x is being braked. The cage may still
            # publish a frozen non-zero safe_action.angular.z (cf.
            # cage.yaml c05_emergency.freeze_steering), but actuating it
            # against linear.x=0 produces pure yaw, not a stop.
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
        else:
            cmd.angular.z = float(msg.angular.z) * self._yaw_gain
            cmd.linear.x = self._fixed_speed
        self._pub.publish(cmd)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VehicleControlNode()
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
