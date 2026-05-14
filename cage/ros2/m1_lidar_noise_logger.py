#!/usr/bin/env python3
"""
m1_lidar_noise_logger.py
------------------------
ROS2 node for the M-1 measurement (Static LiDAR noise on lateral offset).

Subscribes to `/state_obs` and logs the `lateral_offset_m` field together
with a wall-clock-equivalent timestamp into a CSV. The vehicle is
expected to be stationary at a known lateral position for the duration
of the run; the resulting CSV is consumed offline by
`tools/calibration_helpers/m1_from_csv.py` to produce the
`positions[]` array of `M1_results.json`.

Usage in a ROS2 workspace:

    ros2 run <pkg> m1_lidar_noise_logger.py \
        --ros-args \
            -p position_label:=y0 \
            -p output_dir:=/tmp/m1 \
            -p duration_s:=300.0

The node auto-shuts down after `duration_s` seconds. Three positions
are typical (`y0`, `y_pos010`, `y_neg010`); launch the node once per
position.

Message-type adaptation note. The expected message type for
`/state_obs` is the project-specific `sim_interfaces/StateObservation`
(or equivalent) with at least:

    std_msgs/Header   header
    float64           lateral_offset_m

If the message type differs in your simulator workspace, replace the
import below and adjust the field access in `state_cb()`.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

# ---------------------------------------------------------------------
# Adapt the import below to the message type used in your simulator.
# Placeholder uses a generic Float64MultiArray; replace with your real
# StateObservation message and access the field by name.
# ---------------------------------------------------------------------
try:
    from sim_interfaces.msg import StateObservation  # type: ignore[import-not-found]
    _USING_STATE_OBS = True
except ImportError:
    from std_msgs.msg import Float64MultiArray as StateObservation  # noqa: F401
    _USING_STATE_OBS = False


class M1LidarNoiseLogger(Node):
    """Log `lateral_offset_m` to CSV for a configurable duration."""

    def __init__(self) -> None:
        super().__init__("m1_lidar_noise_logger")

        self.declare_parameter("position_label", "y0")
        self.declare_parameter("output_dir", "/tmp/m1")
        self.declare_parameter("duration_s", 300.0)
        self.declare_parameter("topic", "/state_obs")

        self.position_label = self.get_parameter("position_label").value
        self.output_dir = Path(self.get_parameter("output_dir").value)
        self.duration_s = float(self.get_parameter("duration_s").value)
        self.topic = self.get_parameter("topic").value

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.output_dir / f"{self.position_label}_samples.csv"

        qos = QoSProfile(
            depth=20,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.sub = self.create_subscription(
            StateObservation, self.topic, self.state_cb, qos
        )

        self._fp = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fp)
        self._writer.writerow(["stamp_s", "lateral_offset_m"])
        self._fp.flush()

        self._start_s = time.monotonic()
        self._samples = 0
        self._shutdown_timer = self.create_timer(0.5, self._maybe_shutdown)

        self.get_logger().info(
            f"M-1 logger started: position={self.position_label}, "
            f"duration={self.duration_s}s, output={self.csv_path}, "
            f"msg_type={'sim_interfaces.StateObservation' if _USING_STATE_OBS else 'Float64MultiArray (placeholder)'}"
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def state_cb(self, msg) -> None:  # type: ignore[no-untyped-def]
        # ------------------------------------------------------------------
        # Adaptation point: extract the lateral offset from the message.
        # Replace this block with the real field access in your project.
        # ------------------------------------------------------------------
        if _USING_STATE_OBS:
            lateral_offset_m = float(msg.lateral_offset_m)
            stamp = msg.header.stamp
            stamp_s = stamp.sec + stamp.nanosec * 1e-9
        else:
            # Placeholder for Float64MultiArray: assume layout [y, theta, v, ...]
            if len(msg.data) == 0:
                self.get_logger().warn("empty Float64MultiArray; skipping sample")
                return
            lateral_offset_m = float(msg.data[0])
            stamp_s = self.get_clock().now().nanoseconds * 1e-9

        self._writer.writerow([f"{stamp_s:.9f}", f"{lateral_offset_m:.6f}"])
        self._samples += 1
        if self._samples % 200 == 0:
            self._fp.flush()

    def _maybe_shutdown(self) -> None:
        elapsed = time.monotonic() - self._start_s
        if elapsed < self.duration_s:
            return
        self.get_logger().info(
            f"M-1 logger finished: {self._samples} samples written to {self.csv_path}"
        )
        self._fp.flush()
        self._fp.close()
        rclpy.shutdown()


def main(argv: list[str] | None = None) -> int:
    rclpy.init(args=argv)
    node = M1LidarNoiseLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node._fp.close()
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
