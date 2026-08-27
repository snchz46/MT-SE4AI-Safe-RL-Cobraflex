"""
cage_reset_proxy_node — automate, under guards, the five `/cage_reset`
publications the operator made by hand on 26.08.2026.

READ `cage_reset_proxy.py`'s module docstring first. The short version: this is
NOT a change to C-05 and nothing here runs inside the cage. `docs/17` §8.5 says
the fix for "C-05 has no operational story on hardware" needs a decision, not a
patch; **D-74 is that decision**, and it picks the *operator reset path*
candidate, implemented outside the artefact under test.

DISABLED BY DEFAULT (``enabled:=false``), and a run with it enabled is a
diagnostic run, never a scored one: with it running, part of the vehicle's
stopping behaviour is this node's rather than the cage's. Every decision — the
resets issued AND the last reason each was withheld — is written to
``<run>/reset_events.csv`` next to the cage CSV, and `/cage_reset` should be in
the session's rosbag so the two can be cross-checked.

Inputs are the same three the operator eyeballed before each manual reset:
`/perception_invalid`, the cage's active rules, and the speed. The guards live
in `ResetPolicy`; this file only wires them to topics.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from .cage_reset_proxy import ResetPolicy

RESET_CSV_COLUMNS = ["timestamp", "action", "reason", "resets_issued"]


def main(args=None) -> None:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSPresetProfiles
    from std_msgs.msg import Bool, Empty, Float64MultiArray

    from cobraflex_safety_msgs.msg import CageStatus

    class CageResetProxyNode(Node):
        def __init__(self) -> None:
            super().__init__("cage_reset_proxy")
            self.declare_parameter("enabled", False)
            self.declare_parameter("cage_status_topic", "/cage_status")
            self.declare_parameter("perception_invalid_topic", "/perception_invalid")
            self.declare_parameter("emergency_topic", "/emergency")
            self.declare_parameter("reset_topic", "/cage_reset")
            self.declare_parameter("state_obs_topic", "/state_obs")
            self.declare_parameter("output_dir", "")
            self.declare_parameter("run_id", "")
            self.declare_parameter("min_healthy_seconds", 1.0)
            self.declare_parameter("min_interval_seconds", 3.0)
            self.declare_parameter("max_resets", 6)
            self.declare_parameter("max_speed_mps", 0.02)

            self._enabled = bool(self.get_parameter("enabled").value)
            self._policy = ResetPolicy(
                min_healthy_seconds=float(
                    self.get_parameter("min_healthy_seconds").value),
                min_interval_seconds=float(
                    self.get_parameter("min_interval_seconds").value),
                max_resets=int(self.get_parameter("max_resets").value),
                max_speed_mps=float(self.get_parameter("max_speed_mps").value),
            )

            output_dir = (
                self.get_parameter("output_dir").get_parameter_value().string_value
                or "experiments/physical/runs"
            )
            run_id = (
                self.get_parameter("run_id").get_parameter_value().string_value
                or "ros_run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            )
            run_path = Path(output_dir).expanduser().resolve() / run_id
            run_path.mkdir(parents=True, exist_ok=True)
            self._csv_file = (run_path / "reset_events.csv").open(
                "w", newline="", buffering=1
            )
            self._csv = csv.DictWriter(self._csv_file, fieldnames=RESET_CSV_COLUMNS)
            self._csv.writeheader()

            self._emergency = False
            self._perception_invalid = False
            self._speed = 0.0
            self._last_withheld = ""

            reliable = QoSPresetProfiles.SYSTEM_DEFAULT.value
            sensor = QoSPresetProfiles.SENSOR_DATA.value
            self._reset_pub = self.create_publisher(
                Empty, self.get_parameter("reset_topic").value, reliable
            )
            self.create_subscription(
                Bool, self.get_parameter("perception_invalid_topic").value,
                self._on_invalid, reliable,
            )
            self.create_subscription(
                Bool, self.get_parameter("emergency_topic").value,
                self._on_emergency, reliable,
            )
            self.create_subscription(
                CageStatus, self.get_parameter("cage_status_topic").value,
                self._on_status, reliable,
            )
            self.create_subscription(
                Float64MultiArray,
                self.get_parameter("state_obs_topic").value,
                self._on_state_obs, sensor,
            )

            if self._enabled:
                self.get_logger().warning(
                    "cage_reset_proxy ENABLED: up to %d resets, %.1f s healthy "
                    "hold, %.1f s apart. THIS RUN IS DIAGNOSTIC, NOT SCORED — "
                    "part of the stopping behaviour is this node's, not the "
                    "cage's." % (self._policy.max_resets,
                                 self._policy.min_healthy_seconds,
                                 self._policy.min_interval_seconds)
                )
            else:
                self.get_logger().info(
                    "cage_reset_proxy running in OBSERVE-ONLY mode "
                    "(enabled:=false): decisions are logged, nothing is "
                    "published. Reset by hand with "
                    "`ros2 topic pub --once /cage_reset std_msgs/msg/Empty {}`."
                )

        # --------------------------------------------------------- callbacks
        def _on_invalid(self, msg: Bool) -> None:
            self._perception_invalid = bool(msg.data)

        def _on_emergency(self, msg: Bool) -> None:
            self._emergency = bool(msg.data)

        def _on_state_obs(self, msg) -> None:
            if len(msg.data) >= 3:
                self._speed = float(msg.data[2])

        def _on_status(self, msg: CageStatus) -> None:
            """One cage cycle observed → one policy decision."""
            now = self.get_clock().now().nanoseconds * 1e-9
            decision = self._policy.update(
                now,
                emergency=bool(msg.emergency_mode) or self._emergency,
                perception_invalid=self._perception_invalid,
                active_rules=list(msg.rules_triggered),
                speed_mps=self._speed,
            )
            if not decision.issue:
                # Log a withheld reason only when it CHANGES, or a latched car
                # writes 10 identical rows a second for the rest of the run.
                if bool(msg.emergency_mode) and decision.reason != self._last_withheld:
                    self._last_withheld = decision.reason
                    self._csv.writerow({
                        "timestamp": f"{now:.6f}", "action": "withheld",
                        "reason": decision.reason,
                        "resets_issued": self._policy.resets_issued,
                    })
                    self.get_logger().info(
                        f"cage_reset_proxy withholding: {decision.reason}"
                    )
                return

            self._last_withheld = ""
            self._csv.writerow({
                "timestamp": f"{now:.6f}",
                "action": "reset" if self._enabled else "would_reset",
                "reason": decision.reason,
                "resets_issued": self._policy.resets_issued,
            })
            if self._enabled:
                self._reset_pub.publish(Empty())
                self.get_logger().warning(
                    f"cage_reset_proxy PUBLISHED /cage_reset: {decision.reason}"
                )
            else:
                self.get_logger().warning(
                    f"cage_reset_proxy WOULD reset ({decision.reason}) — "
                    "observe-only, publish it by hand if you want the car to go."
                )

        def destroy_node(self) -> bool:
            self._csv_file.close()
            self.get_logger().info(
                "cage_reset_proxy closed after %d resets."
                % self._policy.resets_issued
            )
            return super().destroy_node()

    rclpy.init(args=args)
    node = CageResetProxyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
