#!/usr/bin/env python3
"""
m2_latency_logger.py
--------------------
ROS2 node for the M-2 measurement (End-to-end control latency).

Subscribes to `/state_obs` (input) and `/safe_action` (cage output) and
logs, for every `/safe_action` message published, the time elapsed
since the most recent `/state_obs` message was received. The resulting
CSV is consumed offline by `tools/calibration_helpers/m2_from_csv.py`
to fill `latency_obs_to_safe_action_ms.{median, p05, p95, p99, max}`
in `M2_results.json`.

Usage in a ROS2 workspace:

    ros2 run <pkg> m2_latency_logger.py \
        --ros-args \
            -p output_csv:=/tmp/m2_latency.csv \
            -p duration_s:=120.0

The node auto-shuts down after `duration_s` seconds. Run the simulator
with the cage and policy nodes in nominal operation (enforcement mode)
on the straight-road map `odd1_straight_road`.

Latency definition. For every `/safe_action` message received, the
latency is computed as

    latency = stamp(safe_action) - stamp(last_state_obs_received_before)

This matches the protocol's "most recent /state_obs consumed" wording
in the approximation where the cage's per-cycle callback consumes the
state observation that was most recently received before the cage
emitted the safe action. If your cage_node attaches an explicit
"input_state_stamp" field to the safe_action message, switch the
extraction in `safe_action_cb()` to use that field directly.

Message-type adaptation notes. The expected message types are the
project-specific `sim_interfaces/StateObservation` and
`sim_interfaces/SafeAction` (or equivalent) with `std_msgs/Header`
fields. Replace the imports below to match your simulator workspace.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

# ---------------------------------------------------------------------
# Adaptation point: replace these imports with your real message types.
# The placeholders use std_msgs/Header-bearing types where available.
# ---------------------------------------------------------------------
try:
    from sim_interfaces.msg import StateObservation, SafeAction  # type: ignore[import-not-found]
    _USING_REAL_MSGS = True
except ImportError:
    # Fallback placeholders: PoseStamped has a header.stamp we can read.
    from geometry_msgs.msg import PoseStamped as StateObservation  # type: ignore[assignment]
    from geometry_msgs.msg import PoseStamped as SafeAction  # type: ignore[assignment]
    _USING_REAL_MSGS = False


def stamp_to_seconds(stamp) -> float:  # type: ignore[no-untyped-def]
    """Convert a builtin_interfaces/Time stamp to floating-point seconds."""
    return float(stamp.sec) + float(stamp.nanosec) * 1e-9


class M2LatencyLogger(Node):
    """Log per-cycle latency between /state_obs and /safe_action."""

    def __init__(self) -> None:
        super().__init__("m2_latency_logger")

        self.declare_parameter("output_csv", "/tmp/m2_latency.csv")
        self.declare_parameter("duration_s", 120.0)
        self.declare_parameter("state_topic", "/state_obs")
        self.declare_parameter("action_topic", "/safe_action")

        self.output_csv = Path(self.get_parameter("output_csv").value)
        self.duration_s = float(self.get_parameter("duration_s").value)
        self.state_topic = self.get_parameter("state_topic").value
        self.action_topic = self.get_parameter("action_topic").value

        self.output_csv.parent.mkdir(parents=True, exist_ok=True)

        qos = QoSProfile(
            depth=20,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.state_sub = self.create_subscription(
            StateObservation, self.state_topic, self.state_cb, qos
        )
        self.action_sub = self.create_subscription(
            SafeAction, self.action_topic, self.safe_action_cb, qos
        )

        self._last_state_stamp_s: Optional[float] = None

        self._fp = open(self.output_csv, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fp)
        self._writer.writerow(
            ["cycle_idx", "obs_stamp_s", "action_stamp_s", "latency_ms"]
        )
        self._fp.flush()

        self._start_s = time.monotonic()
        self._cycles = 0
        self._missing_obs = 0
        self._shutdown_timer = self.create_timer(0.5, self._maybe_shutdown)

        self.get_logger().info(
            f"M-2 logger started: duration={self.duration_s}s, "
            f"output={self.output_csv}, "
            f"msgs={'sim_interfaces' if _USING_REAL_MSGS else 'PoseStamped placeholders'}"
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def state_cb(self, msg) -> None:  # type: ignore[no-untyped-def]
        try:
            self._last_state_stamp_s = stamp_to_seconds(msg.header.stamp)
        except AttributeError:
            self.get_logger().warn(
                "/state_obs message has no `.header.stamp`; "
                "adjust the message type and field access in m2_latency_logger.py"
            )

    def safe_action_cb(self, msg) -> None:  # type: ignore[no-untyped-def]
        if self._last_state_stamp_s is None:
            self._missing_obs += 1
            return
        try:
            action_stamp_s = stamp_to_seconds(msg.header.stamp)
        except AttributeError:
            self.get_logger().warn(
                "/safe_action message has no `.header.stamp`; "
                "adjust the message type and field access in m2_latency_logger.py"
            )
            return
        latency_ms = (action_stamp_s - self._last_state_stamp_s) * 1000.0
        self._writer.writerow(
            [
                self._cycles,
                f"{self._last_state_stamp_s:.9f}",
                f"{action_stamp_s:.9f}",
                f"{latency_ms:.4f}",
            ]
        )
        self._cycles += 1
        if self._cycles % 200 == 0:
            self._fp.flush()

    def _maybe_shutdown(self) -> None:
        elapsed = time.monotonic() - self._start_s
        if elapsed < self.duration_s:
            return
        self.get_logger().info(
            f"M-2 logger finished: {self._cycles} cycles written to {self.output_csv}; "
            f"{self._missing_obs} safe_action messages dropped (no prior state_obs received)"
        )
        self._fp.flush()
        self._fp.close()
        rclpy.shutdown()


def main(argv: list[str] | None = None) -> int:
    rclpy.init(args=argv)
    node = M2LatencyLogger()
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
