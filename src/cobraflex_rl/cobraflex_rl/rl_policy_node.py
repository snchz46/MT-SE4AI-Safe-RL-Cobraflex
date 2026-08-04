"""
rl_policy_node — the trained RL camera policy as a ROS2 inference node (Phase 5).

The distributed track-'E' loop (mirrors the F2 physical demo, now camera-driven):

    camera/image_raw_lane ─► rl_policy_node ──────────────► /raw_action (Twist)
    camera/image_raw_lane ─► cv_lane_estimator_node ─────► /state_obs + /perception_invalid
    /raw_action + /state_obs + /perception_invalid ─► cage_ros_node ─► /safe_action + /cage_status
    /safe_action ─► vehicle_control_node ─► /cmd_vel ─► (real motor driver)
    /cage_status ─► cage_logger_node ─► CSV

This node is the ONE piece the sim did in-process (inside ``GazeboLaneEnv.step``);
on hardware the policy must run as its own node. It reuses the EXACT preprocessing
the policy trained on — ``camera_pipeline.decode_image`` + ``to_observation`` (84×84
grayscale) + a k=4 frame stack (the ``VecFrameStack`` equivalent, identical to
``eval_policy._FrameStacker``) — so the CNN sees bit-identical observations to
Gazebo. Inference is ``model.predict(obs, deterministic=True)``; the 2-D action
[steer, throttle] ∈ [-1, 1]² is published as a Twist with the convention
``cage_ros_node`` expects (``angular.z``=steering, ``linear.x``=throttle), so the
cage arbitrates the raw command exactly as in simulation.

Parameters
    checkpoint        (str)  SB3 .zip to load (the verdict/deploy checkpoint).
    algorithm         (str)  'ppo' (default, the deployed trunk) | 'sac' — the class
                             the checkpoint was trained with.
    image_topic       (str)  camera frames the policy saw (default camera/image_raw_lane).
    raw_action_topic  (str)  where the raw policy action is published (default /raw_action).
    frame_stack       (int)  k (default 4, the E-design value).
    grayscale         (bool) default True (the E-design observation).
    device            (str)  'cpu' (default; CNN inference at 10 Hz is ample on CPU).

**STATUS: Phase-5 deployment scaffolding — NOT yet run on the physical CobraFlex.**
The preprocessing + action-mapping logic is unit-tested host-side
(``policy/tests/test_rl_policy_node.py``); the ROS wiring is validated only by the
sim components it reuses. First hardware bring-up must follow
``docs/17_physical_deployment.md`` (camera extrinsics, safety pre-checks, e-stop).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np

from .camera_pipeline import decode_image, to_observation


def action_to_twist_fields(action) -> tuple:
    """Map a 2-D policy action [steer, throttle] ∈ [-1,1]² to the (angular_z,
    linear_x) Twist fields ``cage_ros_node`` reads. Steering-only (1-D) actions
    fall back to throttle 0 (the cage/vehicle_control then apply the cruise
    nominal, matching the frozen 1-D deployment)."""
    a = np.asarray(action, dtype=float).reshape(-1)
    steer = float(np.clip(a[0], -1.0, 1.0))
    throttle = float(np.clip(a[1], -1.0, 1.0)) if a.size >= 2 else 0.0
    return steer, throttle  # (angular.z, linear.x)


class _FrameStacker:
    """VecFrameStack equivalent (identical to eval_policy._FrameStacker): last k
    frames concatenated on the channel axis, newest last."""

    def __init__(self, k: int) -> None:
        self.k = int(k)
        self._frames: List[np.ndarray] = []

    def reset(self, frame: np.ndarray) -> np.ndarray:
        self._frames = [frame] * self.k
        return np.concatenate(self._frames, axis=-1)

    def step(self, frame: np.ndarray) -> np.ndarray:
        self._frames = (self._frames + [frame])[-self.k:]
        return np.concatenate(self._frames, axis=-1)


def main(argv: Optional[List[str]] = None) -> None:
    # ROS + SB3 imported inside main so the pure helpers above stay host-testable
    # without rclpy / stable_baselines3 installed.
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import Image
    from stable_baselines3 import PPO, SAC

    class RlPolicyNode(Node):
        def __init__(self) -> None:
            super().__init__("rl_policy_node")
            self.declare_parameter("checkpoint", "")
            # ppo: the deployed trunk is the 2-D PPO cap-0.22 550k checkpoint
            # (D-66/D-67); the SAC 2-D arms are findings, not the verdict of record.
            self.declare_parameter("algorithm", "ppo")
            self.declare_parameter("image_topic", "camera/image_raw_lane")
            self.declare_parameter("raw_action_topic", "/raw_action")
            self.declare_parameter("frame_stack", 4)
            self.declare_parameter("grayscale", True)
            self.declare_parameter("device", "cpu")

            ckpt = str(self.get_parameter("checkpoint").value)
            if not ckpt:
                raise RuntimeError("rl_policy_node: 'checkpoint' parameter is required")
            algo = str(self.get_parameter("algorithm").value).lower()
            cls = {"sac": SAC, "ppo": PPO}.get(algo)
            if cls is None:
                raise RuntimeError(f"rl_policy_node: unknown algorithm {algo!r}")
            self._grayscale = bool(self.get_parameter("grayscale").value)
            self._stacker = _FrameStacker(int(self.get_parameter("frame_stack").value))
            self._first = True

            self.get_logger().info(f"Loading {algo.upper()} checkpoint: {ckpt}")
            self._model = cls.load(ckpt, device=str(self.get_parameter("device").value))

            self._pub = self.create_publisher(
                Twist, str(self.get_parameter("raw_action_topic").value), 10
            )
            self.create_subscription(
                Image, str(self.get_parameter("image_topic").value),
                self._on_image, qos_profile_sensor_data,
            )
            self.get_logger().info("rl_policy_node ready (Phase-5 scaffolding).")

        def _on_image(self, msg: Image) -> None:
            try:
                frame_bgr = decode_image(msg.data, msg.height, msg.width,
                                         msg.encoding, msg.step)
            except ValueError as exc:  # a malformed frame must not crash the loop
                self.get_logger().warn(f"dropped frame: {exc}")
                return
            obs_frame = to_observation(frame_bgr, grayscale=self._grayscale)
            obs = (self._stacker.reset(obs_frame) if self._first
                   else self._stacker.step(obs_frame))
            self._first = False
            action, _ = self._model.predict(obs, deterministic=True)
            steer, throttle = action_to_twist_fields(action)
            twist = Twist()
            twist.angular.z = steer
            twist.linear.x = throttle
            self._pub.publish(twist)

    rclpy.init(args=argv)
    node = None
    try:
        node = RlPolicyNode()
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
