from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from .polyline_tracker import PolylineTracker, TrackState
from .rewards import compute_reward
from .ros_interface import RosGazeboInterface


class GazeboLaneEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        ros_interface: RosGazeboInterface,
        centerline: np.ndarray,
        lane_width: float,
        cfg: Mapping[str, Any],
    ) -> None:
        super().__init__()
        self.ros_interface = ros_interface
        self.tracker = PolylineTracker(centerline)
        self.lane_width = float(lane_width)
        self.cfg = dict(cfg)
        self.fixed_speed = float(self.cfg.get("fixed_speed", 0.2))
        self.control_dt = float(self.cfg.get("control_dt", 0.1))
        self.max_episode_steps = int(self.cfg.get("max_episode_steps", 400))
        self.prev_steer = 0.0
        self.step_count = 0
        self.last_track_state: Optional[TrackState] = None

        self.action_space = spaces.Box(
            low=np.array([-1.0], dtype=np.float32),
            high=np.array([1.0], dtype=np.float32),
            dtype=np.float32,
        )
        self.observation_space = spaces.Box(
            low=np.array([-np.inf, -math.pi, 0.0, -1.0], dtype=np.float32),
            high=np.array([np.inf, math.pi, np.inf, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        super().reset(seed=seed)
        self.step_count = 0
        self.prev_steer = 0.0

        start_point = self.tracker.points[0]
        start_heading = float(self.tracker.segment_headings[0])

        self.ros_interface.reset_world()
        self.ros_interface.set_vehicle_pose(
            float(start_point[0]),
            float(start_point[1]),
            start_heading,
        )
        self.ros_interface.send_action(0.0, 0.0)

        if not self.ros_interface.wait_for_initial_data(timeout_sec=10.0):
            raise RuntimeError("Timed out waiting for initial /odom data.")

        self.ros_interface.step_ros(0.1)
        track_state = self._compute_track_state()
        speed = self.ros_interface.get_speed()
        self.last_track_state = track_state

        observation = self._make_observation(track_state, speed, self.prev_steer)
        info = self._make_info(track_state, speed)
        return observation, info

    def step(self, action):
        steer = float(np.clip(np.asarray(action).reshape(-1)[0], -1.0, 1.0))
        prev_steer = self.prev_steer

        self.ros_interface.send_action(steer, self.fixed_speed)
        self.ros_interface.step_ros(self.control_dt)

        track_state = self._compute_track_state()
        speed = self.ros_interface.get_speed()
        self.last_track_state = track_state
        self.step_count += 1

        terminated = abs(track_state.ey) > (self.lane_width * 0.5)
        truncated = self.step_count >= self.max_episode_steps
        reward = compute_reward(
            track_state=track_state,
            speed=speed,
            steer=steer,
            prev_steer=prev_steer,
            done=terminated,
            cfg=self.cfg,
        )

        self.prev_steer = steer
        observation = self._make_observation(track_state, speed, self.prev_steer)
        info = self._make_info(track_state, speed)
        return observation, reward, terminated, truncated, info

    def close(self) -> None:
        try:
            self.ros_interface.send_action(0.0, 0.0)
            self.ros_interface.step_ros(0.05)
        except RuntimeError:
            pass

    def _compute_track_state(self) -> TrackState:
        x, y, yaw = self.ros_interface.get_pose()
        return self.tracker.track(x, y, yaw)

    @staticmethod
    def _make_observation(
        track_state: TrackState,
        speed: float,
        previous_steer: float,
    ) -> np.ndarray:
        return np.array(
            [
                track_state.ey,
                track_state.epsi,
                speed,
                previous_steer,
            ],
            dtype=np.float32,
        )

    @staticmethod
    def _make_info(track_state: TrackState, speed: float) -> Dict[str, float]:
        return {
            "ey": float(track_state.ey),
            "epsi": float(track_state.epsi),
            "s": float(track_state.s),
            "speed": float(speed),
        }
