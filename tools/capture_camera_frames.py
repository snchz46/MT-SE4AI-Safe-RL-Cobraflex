#!/usr/bin/env python3
"""Capture N frames from the bridged Gazebo camera topic and save them as PNGs.

Evidence tool for track 'E' (D-41/D-43): verifies the front camera publishes and
that the lane lines are visible in the rendered frame. Optionally teleports the
robot to a set of poses (via the gz set_pose service, like the RL env does) so
the saved frames cover straights and curve entries.

Usage (after sourcing ROS2 + install/setup.bash, with the sim running):
    python3 tools/capture_camera_frames.py --out <dir> --frames 5
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


def image_to_array(msg: Image) -> np.ndarray:
    channels = {"mono8": 1, "rgb8": 3, "bgr8": 3, "rgba8": 4, "bgra8": 4}.get(
        msg.encoding.lower()
    )
    if channels is None:
        raise ValueError(f"unsupported encoding {msg.encoding}")
    data = np.frombuffer(msg.data, dtype=np.uint8)
    row = int(msg.step) if msg.step else msg.width * channels
    img = data[: msg.height * row].reshape(msg.height, row)[:, : msg.width * channels]
    img = img.reshape(msg.height, msg.width, channels)
    if channels == 1:
        return np.repeat(img, 3, axis=2)
    if msg.encoding.lower().startswith("rgb"):
        img = img[:, :, [2, 1, 0]] if channels >= 3 else img  # to BGR for cv2
    return img[:, :, :3]


class FrameGrabber(Node):
    def __init__(self, topic: str):
        super().__init__("camera_frame_grabber")
        self.frames: list[tuple[float, np.ndarray]] = []
        self.last: np.ndarray | None = None
        self.count = 0
        self.create_subscription(
            Image, topic, self._cb, qos_profile_sensor_data
        )

    def _cb(self, msg: Image) -> None:
        try:
            self.last = image_to_array(msg)
            self.count += 1
        except ValueError as exc:
            self.get_logger().warning(str(exc))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="/camera/image_raw")
    parser.add_argument("--out", required=True)
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    import cv2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rclpy.init()
    node = FrameGrabber(args.topic)
    deadline = time.monotonic() + args.timeout
    saved = 0
    next_save = time.monotonic()
    while rclpy.ok() and saved < args.frames and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.last is not None and time.monotonic() >= next_save:
            path = out / f"frame_{saved:02d}.png"
            cv2.imwrite(str(path), node.last)
            stats = node.last
            print(
                f"saved {path} shape={stats.shape} "
                f"min={stats.min()} max={stats.max()} mean={stats.mean():.1f}"
            )
            saved += 1
            next_save = time.monotonic() + args.interval
    node.destroy_node()
    rclpy.shutdown()
    if saved == 0:
        print("ERROR: no frames received", file=sys.stderr)
        return 1
    print(f"received {node.count} messages total, saved {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
