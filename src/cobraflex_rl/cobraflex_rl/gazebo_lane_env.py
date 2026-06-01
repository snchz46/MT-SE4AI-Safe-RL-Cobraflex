from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from .cage_bridge import (
    SafetyCageNode,
    build_cage_state,
    resolve_cage_yaml,
    safe_action_to_cmd,
)
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
        road_width: Optional[float] = None,
    ) -> None:
        super().__init__()
        self.ros_interface = ros_interface
        self.tracker = PolylineTracker(centerline)
        self.lane_width = float(lane_width)
        # Termination at road boundary (not lane boundary) so random-policy
        # episodes don't terminate in 1–2 steps; the cage handles lane
        # violations within the road. Falls back to lane_width if unset.
        self.road_width = float(road_width) if road_width is not None else float(lane_width)
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

        # Safety cage in the training loop (D-34, TS-01). The cage is invoked
        # in-process via the same SafetyCageNode/cage.yaml that cage_ros_node
        # wraps in deployment; the actuation constants below mirror
        # vehicle_control_node so the env emits the same /cmd_vel mapping the
        # policy will face at deployment. cage_enabled=False keeps the legacy
        # no-cage loop for pipeline debugging (Training Spec §7.2.5).
        cage_cfg = dict(self.cfg.get("cage", {}))
        self.cage_enabled = bool(cage_cfg.get("enabled", True))
        self.cage_mode = str(cage_cfg.get("mode", "enforcement"))
        self.cage_yaml_path = str(cage_cfg.get("yaml_path", "") or "")
        self.lookahead_segments = int(cage_cfg.get("lookahead_segments", 5))
        self.throttle_nominal = float(cage_cfg.get("throttle_nominal", 0.5))
        self.yaw_gain = float(cage_cfg.get("yaw_gain", 0.8))
        self.min_speed_scale = float(cage_cfg.get("min_speed_scale", 0.35))
        self.cage: Optional[SafetyCageNode] = None

        # Random spawn perturbation per episode (Training Spec §7.3) for
        # start-state diversity. Disabled (exact centerline spawn) for
        # deterministic evaluation. Reproducible via self.np_random, seeded by
        # reset(seed=...).
        spawn_cfg = dict(self.cfg.get("spawn_perturbation", {}))
        self.spawn_perturb_enabled = bool(spawn_cfg.get("enabled", True))
        self.spawn_heading_range = float(spawn_cfg.get("heading_rad", 0.15))
        self.spawn_lateral_range = float(spawn_cfg.get("lateral_m", 0.05))

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        super().reset(seed=seed)
        self.step_count = 0
        # prev_steer tracks the steering actually applied (post-cage) last cycle.
        self.prev_steer = 0.0

        # Fresh cage per episode: no latched C-05 emergency, clean rate-limiter
        # and oscillation history. Each RL episode is an independent rollout, so
        # the cage starts from a known state (D-34, TS-01).
        if self.cage_enabled:
            self.cage = SafetyCageNode(
                resolve_cage_yaml(self.cage_yaml_path), mode=self.cage_mode
            )

        start_point = self.tracker.points[0]
        start_heading = float(self.tracker.segment_headings[0])
        spawn_x, spawn_y, spawn_heading = self._perturbed_spawn(
            float(start_point[0]), float(start_point[1]), start_heading
        )

        self.ros_interface.reset_world()
        self.ros_interface.set_vehicle_pose(spawn_x, spawn_y, spawn_heading)
        self.tracker.reset_tracking()
        self.ros_interface.send_action(0.0, 0.0)

        if not self.ros_interface.wait_for_initial_data(timeout_sec=10.0):
            raise RuntimeError("Timed out waiting for initial /odom data.")

        # Ground-truth odom is reported in the fixed `odom` frame whose origin is
        # the run's initial spawn, so each episode recalibrates the constant
        # odom->world offset against the known spawn pose. A set_pose teleport
        # propagates to /odom_truth a few sim steps *after* the service returns,
        # so calibrating immediately can latch the previous-crash pose and yield
        # an impossible multi-metre ey on step 1. Settle first (see helper).
        if not self._calibrate_spawn_settled(spawn_x, spawn_y, spawn_heading):
            self.ros_interface.get_logger().warning(
                "Spawn pose did not settle after teleport; first-step ey may be unreliable."
            )
        track_state = self._compute_track_state()
        speed = self.ros_interface.get_speed()
        self.last_track_state = track_state

        observation = self._make_observation(track_state, speed, self.prev_steer)
        info = self._make_info(track_state, speed)
        return observation, info

    def _calibrate_spawn_settled(
        self,
        spawn_x: float,
        spawn_y: float,
        spawn_heading: float,
        tol: float = 0.08,
        max_attempts: int = 8,
        settle_dt: float = 0.06,
    ) -> bool:
        """Calibrate the odom->world offset against a *settled* post-teleport pose.

        ``calibrate_pose_offset`` forces ``get_pose() == spawn`` at the instant it
        runs, so a stale (pre-teleport) calibration only reveals itself once the
        real teleport lands and the raw odom jumps. We exploit that: the car is
        stationary (zero command) this cycle, so after a *valid* calibration it
        must stay at ``spawn`` across a short settle step. If a stale offset was
        latched, the teleport propagates during that step and ``get_pose`` drifts
        far from ``spawn`` — we detect it and recalibrate against the now-correct
        raw pose. Converges in 1–2 attempts; returns False if it never settles
        (e.g. the teleport silently failed).

        Settling uses *wall-clock* spins, not the sim-time step_ros: the teleport
        needs real server time to propagate, and a sim-time wait can be fooled
        into returning instantly by the odom backlog accumulated during the
        set_pose subprocess (which is exactly what latched stale calibrations).
        """
        for _ in range(max_attempts):
            self.ros_interface.spin_wall(settle_dt)  # let the teleport propagate
            self.ros_interface.calibrate_pose_offset(spawn_x, spawn_y, spawn_heading)
            self.ros_interface.spin_wall(settle_dt)  # verify the car stays put
            x, y, _ = self.ros_interface.get_pose()
            if math.hypot(x - spawn_x, y - spawn_y) <= tol:
                return True
        return False

    def _perturbed_spawn(self, x: float, y: float, heading: float):
        """Apply a random spawn perturbation (Training Spec §7.3) for start-state
        diversity: a lateral offset perpendicular to the track tangent plus a
        heading jitter. Returns the unperturbed pose when disabled (e.g. during
        deterministic evaluation). Uses self.np_random (seeded via reset(seed))
        so the perturbation is reproducible."""
        if not self.spawn_perturb_enabled:
            return x, y, heading
        dlat = float(
            self.np_random.uniform(-self.spawn_lateral_range, self.spawn_lateral_range)
        )
        dpsi = float(
            self.np_random.uniform(-self.spawn_heading_range, self.spawn_heading_range)
        )
        # +dlat is to the left of the tangent, matching the +left ey convention.
        return (
            x - dlat * math.sin(heading),
            y + dlat * math.cos(heading),
            heading + dpsi,
        )

    def step(self, action):
        policy_steer = float(np.clip(np.asarray(action).reshape(-1)[0], -1.0, 1.0))
        prev_steer = self.prev_steer

        applied_steer, cmd_linear, cmd_angular, cage_info = self._apply_cage(
            policy_steer
        )

        # send_action(steer, speed) publishes Twist(angular.z=steer, linear.x=speed).
        self.ros_interface.send_action(cmd_angular, cmd_linear)
        self.ros_interface.step_ros(self.control_dt)

        track_state = self._compute_track_state()
        speed = self.ros_interface.get_speed()
        self.last_track_state = track_state
        self.step_count += 1

        # End the episode the instant the cage latches a C-05 emergency stop:
        # the rollout has already failed (the policy drove into a state the cage
        # could only answer with an emergency), so the remaining frozen steps
        # carry no learning signal — they just burn wall-clock. Both conditions
        # set `terminated` (value target bootstraps from 0); they differ only in
        # the reward, see below. (Requested extension to D-34 / TS-01.)
        off_road = abs(track_state.ey) > (self.road_width * 0.5)
        cage_emergency = bool(cage_info.get("cage_emergency", False))
        terminated = off_road or cage_emergency
        truncated = self.step_count >= self.max_episode_steps
        # Reward is computed on the *applied* (post-cage) steering and resulting
        # state — D-34 / Training Spec §7.2.5: the policy sees the cage as part
        # of the environment dynamics, not as an explicit penalty. Consistent
        # with that, a C-05 emergency termination carries NO termination penalty
        # (the cage's action is not punished — the episode simply ends, so the
        # policy only forgoes future reward); only a genuine off-road failure,
        # which predates the cage in the loop, incurs the penalty.
        reward = compute_reward(
            track_state=track_state,
            speed=speed,
            steer=applied_steer,
            prev_steer=prev_steer,
            done=off_road,
            cfg=self.cfg,
        )

        self.prev_steer = applied_steer
        observation = self._make_observation(track_state, speed, self.prev_steer)
        info = self._make_info(track_state, speed)
        info.update(cage_info)
        if terminated:
            info["termination_reason"] = "cage_emergency" if cage_emergency else "off_road"
        elif truncated:
            info["termination_reason"] = "truncated"
        return observation, reward, terminated, truncated, info

    def _apply_cage(self, policy_steer: float):
        """Route the raw policy steering through the safety cage in-process.

        Returns ``(applied_steer, cmd_linear_x, cmd_angular_z, info)`` where
        ``applied_steer`` is the normalised steering actually actuated (post-cage),
        used for the reward and the ``prev_steer`` observation. When the cage is
        disabled the raw action passes through with the legacy direct actuation
        (debug fallback, Training Spec §7.2.5).
        """
        if not self.cage_enabled or self.cage is None or self.last_track_state is None:
            # Legacy no-cage loop: angular.z = steer, linear.x = fixed_speed.
            return (
                policy_steer,
                self.fixed_speed,
                policy_steer,
                {
                    "cage_enabled": False,
                    "cage_emergency": False,
                    "cage_interventions": [],
                    "raw_steer": policy_steer,
                    "safe_steer": policy_steer,
                    "steer_correction": 0.0,
                },
            )

        # The policy controls steering only; throttle is the fixed cruise nominal
        # so C-04/C-05/C-06 act on a realistic throttle stream (§7.2.2).
        raw_action = (policy_steer, self.throttle_nominal)
        timestamp = self.step_count * self.control_dt
        state = build_cage_state(
            lateral_offset=self.last_track_state.ey,
            heading_error=self.last_track_state.epsi,
            speed=self.ros_interface.get_speed(),
            road_width=self.road_width,
            curvature_ahead=self.tracker.curvature_ahead(
                self.last_track_state.segment_index, self.lookahead_segments
            ),
            timestamp=timestamp,
        )
        result = self.cage.step(
            state, raw_action, {"current_time": timestamp, "external_stop": False}
        )
        safe_steer, safe_throttle = result["safe_action"]
        emergency = bool(result["emergency"])
        cmd_linear, cmd_angular = safe_action_to_cmd(
            safe_steer,
            safe_throttle,
            emergency,
            fixed_speed=self.fixed_speed,
            throttle_nominal=self.throttle_nominal,
            min_speed_scale=self.min_speed_scale,
            yaw_gain=self.yaw_gain,
        )
        info = {
            "cage_enabled": True,
            "cage_emergency": emergency,
            "cage_interventions": [iv["rule"] for iv in result["interventions"]],
            "raw_steer": policy_steer,
            "safe_steer": float(safe_steer),
            "steer_correction": float(safe_steer) - policy_steer,
        }
        return float(safe_steer), cmd_linear, cmd_angular, info

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
