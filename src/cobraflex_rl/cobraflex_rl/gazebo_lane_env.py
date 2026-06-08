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
        self.max_episode_steps = int(self.cfg.get("max_episode_steps", 500))
        self.prev_steer = 0.0
        # Raw (pre-cage) policy steering of the previous cycle. The smoothness
        # reward term penalises the *raw* delta, not the post-cage applied delta,
        # so the policy pays for its own bang-bang instead of letting C-06 absorb
        # it for free (§7.2.5, §7.5.2; reward v1.2). Kept separate from
        # prev_steer, which is the applied steering exposed in the observation.
        self.prev_policy_steer = 0.0
        self.step_count = 0
        self.last_track_state: Optional[TrackState] = None
        self._last_pose = (0.0, 0.0, 0.0)  # world (x, y, yaw), refreshed each cycle
        # Total centerline arc length, for the closed-loop progress wrap (§7.2.3).
        self._track_length = float(self.tracker.cumulative_lengths[-1])
        self.prev_s = 0.0

        # Signed-curvature preview added to the observation so the policy can
        # anticipate the upcoming curve instead of only reacting to ey/epsi (the
        # cage already consumes curvature internally; the policy did not). Two
        # look-ahead horizons (near + far, in centerline segments).
        obs_cfg = dict(self.cfg.get("observation", {}))
        self.curv_lookahead_near = int(obs_cfg.get("curvature_lookahead_near", 3))
        self.curv_lookahead_far = int(obs_cfg.get("curvature_lookahead_far", 8))

        self.action_space = spaces.Box(
            low=np.array([-1.0], dtype=np.float32),
            high=np.array([1.0], dtype=np.float32),
            dtype=np.float32,
        )
        # [ey, epsi, speed, prev_steer, kappa_near, kappa_far]
        self.observation_space = spaces.Box(
            low=np.array([-np.inf, -math.pi, 0.0, -1.0, -np.inf, -np.inf], dtype=np.float32),
            high=np.array([np.inf, math.pi, np.inf, 1.0, np.inf, np.inf], dtype=np.float32),
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
        # prev_steer tracks the steering actually applied (post-cage) last cycle
        # (for the observation); prev_policy_steer tracks the raw policy command
        # last cycle (for the smoothness reward term, §7.2.5).
        self.prev_steer = 0.0
        self.prev_policy_steer = 0.0

        # Fresh cage per episode: no latched C-05 emergency, clean rate-limiter
        # and oscillation history. Each RL episode is an independent rollout, so
        # the cage starts from a known state (D-34, TS-01).
        if self.cage_enabled:
            self.cage = SafetyCageNode(
                resolve_cage_yaml(self.cage_yaml_path), mode=self.cage_mode
            )

        # Scenario initial conditions (F4 executor): an SC-* run can start at a
        # given centerline arc-length (`start_s_m`, e.g. 1.5 = curve entry), with
        # a deterministic heading error (`heading_error_rad`, e.g. SC-EDGE-01's
        # 15 deg) and/or lateral offset (`lateral_offset_m`). Absent (training /
        # nominal eval), the spawn is the first centerline point as before.
        opts = options or {}
        start_s = opts.get("start_s_m")
        if start_s is not None:
            base_x, base_y, base_heading = self.tracker.pose_at_arclength(
                float(start_s), float(opts.get("lateral_offset_m", 0.0) or 0.0)
            )
            base_heading += float(opts.get("heading_error_rad", 0.0) or 0.0)
        else:
            start_point = self.tracker.points[0]
            base_x, base_y = float(start_point[0]), float(start_point[1])
            base_heading = float(self.tracker.segment_headings[0])
        spawn_x, spawn_y, spawn_heading = self._perturbed_spawn(
            base_x, base_y, base_heading
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
        self.prev_s = float(track_state.s)

        kappa_near, kappa_far = self._curvature_preview(track_state.segment_index)
        observation = self._make_observation(
            track_state, speed, self.prev_steer, kappa_near, kappa_far
        )
        info = self._make_info(track_state, speed)
        return observation, info

    def _curvature_preview(self, segment_index: int):
        """Signed curvature (rad/m, + = left) at a near and a far look-ahead, for
        the observation. Mirrors the cage's curvature source so policy and cage
        see a consistent road preview."""
        near = self.tracker.curvature_ahead(segment_index, self.curv_lookahead_near)
        far = self.tracker.curvature_ahead(segment_index, self.curv_lookahead_far)
        return float(near), float(far)

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
        prev_policy_steer = self.prev_policy_steer

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

        # Normalised progress along the centerline this cycle (§7.2.3): the
        # arc-length advance ds, unwrapped across the closed-loop s reset and
        # scaled by the nominal per-step advance so ~1.0 == one cruise step.
        ds = track_state.s - self.prev_s
        if ds < -0.5 * self._track_length:
            ds += self._track_length
        self.prev_s = float(track_state.s)
        ds_nominal = max(self.fixed_speed * self.control_dt, 1e-6)
        progress = float(np.clip(ds / ds_nominal, -2.0, 2.0))

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
        # Reward is computed on the resulting state (ey/epsi/progress) and, for
        # the smoothness term only, on the *raw* policy steering delta — D-34 /
        # Training Spec §7.2.5. The policy sees the cage as part of the
        # environment dynamics, not as an explicit penalty, so cage interventions
        # are never punished; but the smoothness term is the deliberate exception
        # (reward v1.2): measuring the post-cage delta is toothless because C-06
        # absorbs raw bang-bang for free (§7.5.2), so the policy pays for its own
        # raw jerk instead. Consistent with the no-punish-the-cage rule, a C-05
        # emergency termination carries NO termination penalty (the episode simply
        # ends, the policy only forgoes future reward); only a genuine off-road
        # failure, which predates the cage in the loop, incurs the penalty.
        reward = compute_reward(
            track_state=track_state,
            progress=progress,
            steer=policy_steer,
            prev_steer=prev_policy_steer,
            done=off_road,
            cfg=self.cfg,
        )

        self.prev_steer = applied_steer
        self.prev_policy_steer = policy_steer
        kappa_near, kappa_far = self._curvature_preview(track_state.segment_index)
        observation = self._make_observation(
            track_state, speed, self.prev_steer, kappa_near, kappa_far
        )
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
        # Cache the world pose so _make_info can expose it (x, y for the §7.5
        # trajectory plots; the cage/Frenet state is in ey/epsi/s).
        self._last_pose = (float(x), float(y), float(yaw))
        return self.tracker.track(x, y, yaw)

    @staticmethod
    def _make_observation(
        track_state: TrackState,
        speed: float,
        previous_steer: float,
        kappa_near: float,
        kappa_far: float,
    ) -> np.ndarray:
        return np.array(
            [
                track_state.ey,
                track_state.epsi,
                speed,
                previous_steer,
                kappa_near,
                kappa_far,
            ],
            dtype=np.float32,
        )

    def _make_info(self, track_state: TrackState, speed: float) -> Dict[str, float]:
        x, y, yaw = self._last_pose
        return {
            "ey": float(track_state.ey),
            "epsi": float(track_state.epsi),
            "s": float(track_state.s),
            "speed": float(speed),
            # World pose (for the §7.5 trajectory overlay RL vs PD on the oval).
            "x": float(x),
            "y": float(y),
            "yaw": float(yaw),
        }
