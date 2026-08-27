"""
frame_capture_node — write the lane camera frames around a perception failure,
and only those.

THE MEASUREMENT THIS EXISTS TO MAKE. `docs/17` §8.9: *"The measurement that
would settle it is recording /camera/image_raw_lane in the bag and looking at
what the estimator saw; do that next session."* Two track sessions have now
ended on `/perception_invalid` events nobody can explain — the 26.08
`noloopclosure` lap covered 18.05 m and was ended by a single 400 ms pulse with
the car 27 mm from the lane centre — and in both the frames were absent.

WHY NOT `ros2 bag record /camera/image_raw_lane`. Because that is what crashed
the car. Raw 640x360 bgr8 at 20 Hz is 13.8 MB/s to eMMC; run alongside the
deploy chain on 18.08.2026 it took the Jetson down mid-run and cost the
`circuit_survey` run its bag index and the tail of its CSV. See
`tools/record_lane_dataset.py`'s header for the same arithmetic, and
`experiments/physical/runs/circuit_survey/REPAIR_NOTE.md` for the damage.

So: hold ``pre_seconds`` of frames in RAM, write nothing while the chain is
healthy, and dump the window around each trigger. On the 26.08 lap that is one
event — about 100 frames, ~20 MB — against 1.4 GB for the naive bag. Encoding
happens on a writer thread, so a dump cannot stall the executor and starve the
20 Hz subscription it feeds from.

CPU is the scarce resource on this platform (§8.6: load 5.49 on 6 cores with
Layer 3 not even running), so the steady-state cost here is deliberately one
deque append per frame and no decode.

Triggers: `/perception_invalid` rising edge, `/emergency` rising edge, and a
manual `std_msgs/Empty` on `/frame_capture_trigger` for "that looked wrong,
keep it" — the operator's equivalent of a marker in the log.
"""

from __future__ import annotations

import csv
import queue
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from .camera_pipeline import decode_image
from .frame_capture import (
    TRIGGER_EMERGENCY,
    TRIGGER_MANUAL,
    TRIGGER_PERCEPTION_INVALID,
    FrameCapture,
    frame_filename,
)

EVENTS_CSV_COLUMNS = ["event", "reason", "trigger_time", "frame_stamp", "filename"]


class _FrameWriter:
    """Encode-and-write worker. One thread, unbounded queue, drained on stop.

    Unbounded on purpose: the bound that matters is ``FrameCapture``'s frame
    budget, which is applied before anything is enqueued. A bounded queue here
    would drop exactly the frames a burst was opened to capture.
    """

    def __init__(self, out_dir: Path, extension: str, logger) -> None:
        self._dir = out_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ext = extension
        self._log = logger
        self._queue = queue.Queue()
        self._events_path = self._dir.parent / "capture_events.csv"
        self._events_file = self._events_path.open("w", newline="", buffering=1)
        self._events = csv.DictWriter(self._events_file, fieldnames=EVENTS_CSV_COLUMNS)
        self._events.writeheader()
        self._written = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, event_index: int, reason: str, trigger_time: float,
               stamp: float, msg) -> None:
        self._queue.put((event_index, reason, trigger_time, stamp, msg))

    def _run(self) -> None:
        import cv2

        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                return
            event_index, reason, trigger_time, stamp, msg = item
            try:
                frame = decode_image(
                    msg.data, int(msg.height), int(msg.width),
                    msg.encoding, int(msg.step),
                )
                name = frame_filename(event_index, stamp, self._ext)
                cv2.imwrite(str(self._dir / name), frame)
                self._events.writerow({
                    "event": event_index, "reason": reason,
                    "trigger_time": f"{trigger_time:.6f}",
                    "frame_stamp": f"{stamp:.6f}", "filename": name,
                })
                self._written += 1
            except Exception as exc:                     # noqa: BLE001
                # A failed frame must never take the node with it: this runs
                # alongside a driving car and its whole value is diagnostic.
                self._log.warning(f"frame_capture: could not write frame: {exc}")
            finally:
                self._queue.task_done()

    @property
    def written(self) -> int:
        return self._written

    def stop(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=30.0)
        self._events_file.close()


def main(args=None) -> None:
    # rclpy imported here, not at module scope, so the pure buffer in
    # `frame_capture.py` stays testable on a host with no ROS (the
    # csi_camera_node / rl_policy_node idiom).
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSPresetProfiles, qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from std_msgs.msg import Bool, Empty

    class FrameCaptureNode(Node):
        def __init__(self) -> None:
            super().__init__("frame_capture")
            self.declare_parameter("image_topic", "camera/image_raw_lane")
            self.declare_parameter("perception_invalid_topic", "/perception_invalid")
            self.declare_parameter("emergency_topic", "/emergency")
            self.declare_parameter("manual_trigger_topic", "/frame_capture_trigger")
            self.declare_parameter("output_dir", "")
            self.declare_parameter("run_id", "")
            self.declare_parameter("pre_seconds", 3.0)
            self.declare_parameter("post_seconds", 2.0)
            self.declare_parameter("max_events", 8)
            self.declare_parameter("max_frames", 4000)
            self.declare_parameter("image_format", "png")

            output_dir = (
                self.get_parameter("output_dir").get_parameter_value().string_value
                or "experiments/physical/runs"
            )
            run_id = (
                self.get_parameter("run_id").get_parameter_value().string_value
                or "ros_run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            )
            out = Path(output_dir).expanduser().resolve() / run_id / "frames"

            self._capture = FrameCapture(
                pre_seconds=float(self.get_parameter("pre_seconds").value),
                post_seconds=float(self.get_parameter("post_seconds").value),
                max_events=int(self.get_parameter("max_events").value),
                max_frames=int(self.get_parameter("max_frames").value),
            )
            self._writer = _FrameWriter(
                out,
                str(self.get_parameter("image_format").value),
                self.get_logger(),
            )
            self._invalid = False
            self._emergency = False

            self.create_subscription(
                Image, self.get_parameter("image_topic").value,
                self._on_image, qos_profile_sensor_data,
            )
            reliable = QoSPresetProfiles.SYSTEM_DEFAULT.value
            self.create_subscription(
                Bool, self.get_parameter("perception_invalid_topic").value,
                self._on_invalid, reliable,
            )
            self.create_subscription(
                Bool, self.get_parameter("emergency_topic").value,
                self._on_emergency, reliable,
            )
            self.create_subscription(
                Empty, self.get_parameter("manual_trigger_topic").value,
                lambda _msg: self._fire(TRIGGER_MANUAL), reliable,
            )
            self.get_logger().info(
                "frame_capture armed: %.1f s pre / %.1f s post, at most %d events "
                "/ %d frames, writing to %s"
                % (self._capture.pre_seconds, self._capture.post_seconds,
                   self._capture.max_events, self._capture.max_frames, out)
            )

        # --------------------------------------------------------- callbacks
        def _stamp(self, msg) -> float:
            return float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9

        def _on_image(self, msg: Image) -> None:
            stamp = self._stamp(msg)
            for frame_stamp, payload in self._capture.add_frame(stamp, msg):
                event = self._capture.events[-1]
                self._writer.submit(
                    event.index, event.reason, event.trigger_time,
                    frame_stamp, payload,
                )

        def _on_invalid(self, msg: Bool) -> None:
            rising = bool(msg.data) and not self._invalid
            self._invalid = bool(msg.data)
            if rising:
                self._fire(TRIGGER_PERCEPTION_INVALID)

        def _on_emergency(self, msg: Bool) -> None:
            rising = bool(msg.data) and not self._emergency
            self._emergency = bool(msg.data)
            if rising:
                self._fire(TRIGGER_EMERGENCY)

        def _fire(self, reason: str) -> None:
            now = self.get_clock().now().nanoseconds * 1e-9
            was_recording = self._capture.recording(now)
            pre = self._capture.trigger(now, reason)
            if was_recording:
                self.get_logger().info(
                    f"frame_capture: '{reason}' extends event "
                    f"{self._capture.events[-1].index}."
                )
                return
            if not self._capture.events or self._capture.events[-1].trigger_time != now:
                # trigger() refused to open one: the budget is spent.
                self.get_logger().warning(
                    "frame_capture budget exhausted (%d events, %d frames) — "
                    "'%s' NOT captured."
                    % (len(self._capture.events),
                       self._capture.frames_written, reason)
                )
                return
            event = self._capture.events[-1]
            for frame_stamp, payload in pre:
                self._writer.submit(
                    event.index, reason, event.trigger_time, frame_stamp, payload
                )
            self.get_logger().warning(
                "frame_capture event %d ('%s'): %d buffered frames queued."
                % (event.index, reason, len(pre))
            )

        def destroy_node(self) -> bool:
            self._writer.stop()
            self.get_logger().info(
                "frame_capture closed: %d events, %d frames written."
                % (len(self._capture.events), self._writer.written)
            )
            return super().destroy_node()

    rclpy.init(args=args)
    node = FrameCaptureNode()
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
