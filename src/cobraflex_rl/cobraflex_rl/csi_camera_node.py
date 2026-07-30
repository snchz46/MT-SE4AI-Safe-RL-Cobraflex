"""
csi_camera_node — the Jetson CSI lane camera as a ROS2 image source (Phase 5).

The one piece the physical track-'E' chain was missing. In Gazebo the lane frames
came from the ``Lane Cam`` sensor in ``cobraflex/urdf/robot.gazebo``; on hardware
the same camera exists but nothing published it: the CSI device is opened *inside*
``cobraflex.lane_keeper_node`` (the classical CV controller), which also drives
``/cmd_vel`` and therefore cannot serve as a mere image source without fighting
the RL chain for actuation. This node is that source and nothing else.

    csi_camera_node ─► camera/image_raw_lane ─┬─► rl_policy_node      ─► /raw_action
                                              └─► cv_lane_estimator_node ─► /state_obs
                    ─► camera/camera_info

THE OBSERVATION CONTRACT (every number has one source of truth, all three agree):

    | quantity      | value        | authority                                    |
    | native frame  | 640x360      | Lane Cam <image>; camera_geometry.DEFAULT_*  |
    | HFOV          | 90 deg       | Lane Cam <horizontal_fov>; CameraModel       |
    | rate          | 20 Hz        | Lane Cam <update_rate>; lane_keeper timer_hz |
    | capture       | 1280x720@60  | lane_keeper capture_* (INTER_AREA -> 640x360)|
    | optical frame | camera_link_optical_lane | Lane Cam <optical_frame_id>       |

The sim sensor was built to mirror the hardware pipeline (see the comment above
``Lane Cam``: "proc frames 640x360, effective hfov 90 deg, timer 20 Hz; capture is
1280x720@60 but only the processed stream matters"), so reproducing the hardware
path *is* reproducing the training distribution. The 640x360 output size is a hard
contract, not a preference: ``cv_lane_estimator`` defaults to ``CameraModel()`` and
indexes its scan bands by ``camera.height_px``, so a different frame size silently
mis-projects every ``ey``/``epsi`` the cage acts on. The defaults here are imported
from ``camera_geometry`` for exactly that reason — they cannot drift apart.

Encoding is ``bgr8`` where the sim sensor emitted ``R8G8B8``; that is not a
difference, because ``camera_pipeline.decode_image`` normalises both to the same
BGR array before ``to_observation``.

FAIL-SAFE CHAIN (why a dead camera is safe): no frames -> ``rl_policy_node``
publishes no ``/raw_action`` -> ``/raw_action`` is ``cage_ros_node``'s cycle
trigger, so no ``/safe_action`` -> ``vehicle_control_node``'s
``safe_action_timeout_s`` (0.5 s) publishes a zero Twist -> the driver's 50 ms
keep-alive re-sends zeros. The car stops without the e-stop being needed.

**[VERIFY] The 90 deg effective HFOV is the load-bearing unverified number of the
whole sim-to-real transfer.** It originates as a *parameter default* in
``lane_keeper_node`` (``camera_hfov_deg`` 90.0) for an IMX219-**160** wide-angle
lens, and the Gazebo sensor mirrored it. ``CameraModel.fx`` is derived from it, so
it scales the IPM's metric output directly: if the true effective HFOV at 640x360
differs, every ``ey`` in metres is scaled wrong and C-01's 0.12 m threshold no
longer means 0.12 m. The published ``CameraInfo`` is deliberately the *ideal
pinhole the cage assumes* (no distortion terms), not a measured calibration —
publishing measured intrinsics would contradict the IPM. Calibrate the lens and
reconcile both before trusting any metric cage threshold on hardware.

**STATUS: Phase-5 deployment scaffolding — NOT yet run on the physical CobraFlex.**
The pure frame/intrinsics logic is unit-tested host-side
(``policy/tests/test_csi_camera_node.py``); the GStreamer capture needs the Jetson.

Parameters
    sensor_id      (int)  CSI sensor index (default 0).
    capture_width  (int)  1280 — native capture, then area-resized to out_width.
    capture_height (int)  720.
    capture_fps    (int)  60.
    flip_method    (int)  nvvidconv flip-method (default 0).
    out_width      (int)  640 — the trained native frame. Changing it breaks D-43.
    out_height     (int)  360.
    rate_hz        (float) 20.0 — the Lane Cam update rate.
    image_topic    (str)  camera/image_raw_lane.
    camera_info_topic (str) camera/camera_info.
    frame_id       (str)  camera_link_optical_lane.
    hfov_rad       (float) 1.5707963 — feeds the published CameraInfo.
    gst_pipeline   (str)  override the whole GStreamer string (bench testing on a
                          non-Jetson host, e.g. a videotestsrc or filesrc); empty
                          = build the proven nvarguscamerasrc pipeline.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from .camera_geometry import (
    DEFAULT_HEIGHT_PX,
    DEFAULT_HFOV_RAD,
    DEFAULT_WIDTH_PX,
    CameraModel,
)

try:
    import cv2
except ImportError:  # pragma: no cover - cv2 is present on both hosts
    cv2 = None

# The Lane Cam <update_rate>, and lane_keeper_node's timer_hz.
DEFAULT_RATE_HZ = 20.0
# lane_keeper_node's capture_* defaults: the CSI stream it was proven on.
DEFAULT_CAPTURE_WIDTH = 1280
DEFAULT_CAPTURE_HEIGHT = 720
DEFAULT_CAPTURE_FPS = 60
# Lane Cam <optical_frame_id> — the frame camera_geometry's extrinsics refer to.
DEFAULT_FRAME_ID = "camera_link_optical_lane"


def gstreamer_pipeline(
    sensor_id: int = 0,
    width: int = DEFAULT_CAPTURE_WIDTH,
    height: int = DEFAULT_CAPTURE_HEIGHT,
    fps: int = DEFAULT_CAPTURE_FPS,
    flip_method: int = 0,
) -> str:
    """The Jetson CSI pipeline, kept identical to the one ``lane_keeper_node``
    proved on this hardware (nvarguscamerasrc -> NV12 -> BGRx -> BGR, latest
    frame only). Deviating here would change what the CNN sees for no reason."""
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){width}, height=(int){height}, "
        f"format=(string)NV12, framerate=(fraction){fps}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){width}, height=(int){height}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! "
        f"appsink drop=true max-buffers=1 sync=false"
    )


def prepare_frame(
    frame_bgr: np.ndarray,
    width: int = DEFAULT_WIDTH_PX,
    height: int = DEFAULT_HEIGHT_PX,
) -> np.ndarray:
    """Capture frame → the trained native frame: area-downsample to
    ``(height, width, 3)`` uint8, contiguous.

    ``cv2.INTER_AREA`` is not a free choice — it is what
    ``lane_keeper_node._process_frame`` used to produce the 640x360 stream the
    Gazebo sensor was built to mirror, and what ``to_observation`` uses again for
    the 84x84 step. Both capture and target are 16:9, so this rescales without
    cropping and the 90 deg HFOV is preserved.
    """
    if cv2 is None:  # pragma: no cover
        raise RuntimeError("cv2 is required to resize camera frames")
    if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        raise ValueError(f"expected an HxWx3 BGR frame, got shape {frame_bgr.shape}")
    if frame_bgr.shape[0] == height and frame_bgr.shape[1] == width:
        out = frame_bgr
    else:
        out = cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_AREA)
    return np.ascontiguousarray(out, dtype=np.uint8)


def camera_info_matrices(model: CameraModel) -> Tuple[List[float], List[float]]:
    """``(K, P)`` for a ``sensor_msgs/CameraInfo``, derived from the very
    ``CameraModel`` the cage's IPM uses — so the advertised intrinsics can never
    disagree with the projection ``cv_lane_estimator`` actually applies. Ideal
    pinhole, no distortion (see the [VERIFY] note in the module docstring)."""
    fx, fy, cx, cy = model.fx, model.fy, model.cx, model.cy
    k = [fx, 0.0, cx,
         0.0, fy, cy,
         0.0, 0.0, 1.0]
    p = [fx, 0.0, cx, 0.0,
         0.0, fy, cy, 0.0,
         0.0, 0.0, 1.0, 0.0]
    return k, p


def main(argv: Optional[List[str]] = None) -> None:
    # ROS imported inside main so the pure helpers above stay host-testable
    # without rclpy installed (the rl_policy_node idiom).
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import CameraInfo, Image

    class CsiCameraNode(Node):
        def __init__(self) -> None:
            super().__init__("csi_camera_node")
            self.declare_parameter("sensor_id", 0)
            self.declare_parameter("capture_width", DEFAULT_CAPTURE_WIDTH)
            self.declare_parameter("capture_height", DEFAULT_CAPTURE_HEIGHT)
            self.declare_parameter("capture_fps", DEFAULT_CAPTURE_FPS)
            self.declare_parameter("flip_method", 0)
            self.declare_parameter("out_width", DEFAULT_WIDTH_PX)
            self.declare_parameter("out_height", DEFAULT_HEIGHT_PX)
            self.declare_parameter("rate_hz", DEFAULT_RATE_HZ)
            self.declare_parameter("image_topic", "camera/image_raw_lane")
            self.declare_parameter("camera_info_topic", "camera/camera_info")
            self.declare_parameter("frame_id", DEFAULT_FRAME_ID)
            self.declare_parameter("hfov_rad", DEFAULT_HFOV_RAD)
            self.declare_parameter("gst_pipeline", "")

            self._out_w = int(self.get_parameter("out_width").value)
            self._out_h = int(self.get_parameter("out_height").value)
            self._frame_id = str(self.get_parameter("frame_id").value)
            # A frame size other than the trained one mis-projects every cage
            # estimate (cv_lane_estimator indexes scan bands by height_px), so
            # say so loudly rather than driving on a silently wrong IPM.
            if (self._out_w, self._out_h) != (DEFAULT_WIDTH_PX, DEFAULT_HEIGHT_PX):
                self.get_logger().error(
                    f"out_width/out_height = {self._out_w}x{self._out_h} but the "
                    f"trained/D-43 contract is {DEFAULT_WIDTH_PX}x{DEFAULT_HEIGHT_PX}; "
                    "the cage's IPM and the CNN's input distribution are both wrong "
                    "at this size."
                )

            self._model = CameraModel(
                hfov_rad=float(self.get_parameter("hfov_rad").value),
                width_px=self._out_w,
                height_px=self._out_h,
            )
            self._k, self._p = camera_info_matrices(self._model)

            pipeline = str(self.get_parameter("gst_pipeline").value) or gstreamer_pipeline(
                sensor_id=int(self.get_parameter("sensor_id").value),
                width=int(self.get_parameter("capture_width").value),
                height=int(self.get_parameter("capture_height").value),
                fps=int(self.get_parameter("capture_fps").value),
                flip_method=int(self.get_parameter("flip_method").value),
            )
            self.get_logger().info(f"CSI pipeline: {pipeline}")
            if cv2 is None:
                raise RuntimeError("csi_camera_node: cv2 is required")
            self._cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if not self._cap.isOpened():
                raise RuntimeError(
                    "csi_camera_node: could not open the CSI camera. Check that "
                    "nothing else holds it (lane_keeper_node opens the same "
                    "device) and that the sensor_id is right."
                )

            self._image_pub = self.create_publisher(
                Image, str(self.get_parameter("image_topic").value),
                qos_profile_sensor_data,
            )
            self._info_pub = self.create_publisher(
                CameraInfo, str(self.get_parameter("camera_info_topic").value),
                qos_profile_sensor_data,
            )
            self._drops = 0
            rate = float(self.get_parameter("rate_hz").value)
            self.create_timer(1.0 / rate, self._on_tick)
            self.get_logger().info(
                f"csi_camera_node ready: {self._out_w}x{self._out_h} @ {rate} Hz, "
                f"HFOV {self._model.hfov_rad:.7f} rad, frame_id {self._frame_id} "
                "(Phase-5 scaffolding)."
            )

        def _on_tick(self) -> None:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                # Publishing nothing is the safe outcome: it propagates to the
                # vehicle_control timeout and stops the car (see module docstring).
                self._drops += 1
                if self._drops % 20 == 1:
                    self.get_logger().warn(
                        f"CSI read failed ({self._drops} so far) — no frame published"
                    )
                return
            self._drops = 0
            try:
                out = prepare_frame(frame, self._out_w, self._out_h)
            except ValueError as exc:  # a malformed frame must not kill the node
                self.get_logger().warn(f"dropped frame: {exc}")
                return

            stamp = self.get_clock().now().to_msg()
            img = Image()
            img.header.stamp = stamp
            img.header.frame_id = self._frame_id
            img.height = int(out.shape[0])
            img.width = int(out.shape[1])
            img.encoding = "bgr8"
            img.is_bigendian = False
            img.step = int(out.strides[0])
            img.data = out.tobytes()
            self._image_pub.publish(img)

            info = CameraInfo()
            info.header.stamp = stamp
            info.header.frame_id = self._frame_id
            info.height = int(out.shape[0])
            info.width = int(out.shape[1])
            info.distortion_model = "plumb_bob"
            info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
            info.k = self._k
            info.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
            info.p = self._p
            self._info_pub.publish(info)

        def destroy_node(self) -> bool:
            try:
                if self._cap is not None:
                    self._cap.release()
            except Exception:  # noqa: BLE001 - release must never mask shutdown
                pass
            return super().destroy_node()

    rclpy.init(args=argv)
    node = None
    try:
        node = CsiCameraNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
