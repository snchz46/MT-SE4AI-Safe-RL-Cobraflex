# Environment Design v0.1 — RL Training Environment (CobraFlex / F3)

| Field | Value |
| --- | --- |
| Artifact | Output of day **D36** (Phase 3, Week 8) — see `docs/.phases/Fase 3/fase_3_detallada.md` §4 (local plan) |
| Version | **0.1** (design frozen before the first training run) |
| Phase / Gate | F3 (PPO training), after G2 |
| Author | Samuel Sanchez |
| Date | 2026-05-29 |
| Status | CONFIRMED — implemented in `GazeboLaneEnv` |
| Normative spec | Training Specification §7.2–§7.3 (Chapter 7). **This document is supporting rationale, not the normative source**: on any numeric discrepancy, §7.2 prevails. |
| Decisions cited | D-07 (artifact A1), D-34 (cage during training), D-32 (external drivers) |
| Spanish working copy | `docs/.phases/Fase 3/environment_design_v0.1.md` (local, gitignored) |

> Purpose: document *what* the RL training environment is and, above all, *why*
> it was designed this way, including the rejected alternatives and a bank of
> defense questions. It complements the thesis prose (Ch. 7) with the
> engineering detail the committee may ask for.

---

## 1. Origin of the decisions (D36 morning analysis)

The design starts from the analysis of the Phase 2 PD logs
(`experiments/sim/runs/ros_run_20260523T153003Z`, 9.91 laps, 0 emergencies).
From that run and §6.6.2, the **actual operating ranges** of the system on the
nominal oval are:

| Variable | Observed range (PD, F2) | Design implication |
| --- | --- | --- |
| `ey` (lateral offset) | ≈ [−0.12, +0.12] m | Key observation; the reward's main penalty |
| `epsi` (heading error) | ≈ [−0.4, +0.4] rad | Secondary observation |
| `speed` | ≈ 0.2 m/s (cruise) | Justifies **fixed speed** in training |
| Cage interventions | 0.047 % of cycles | The nominal space is "easy"; the challenge is in the perturbed scenarios (F4) |

The D36 conclusion is that the nominal problem is **lateral regulation at fixed
speed**: neither speed control nor rich perception is needed to learn the base
task. That fixes the minimal observation and action spaces.

---

## 2. Observation space

```text
obs = [ey, epsi, speed, prev_steer]            (Box, float32, dim 4)
low  = [-inf, -π, 0.0, -1.0]
high = [+inf, +π, +inf, 1.0]
```

| Component | Meaning | Why it is here |
| --- | --- | --- |
| `ey` | lateral offset to the lane centre (+ left) | Main controlled variable |
| `epsi` | heading error vs the lane tangent (+ counter-clockwise) | Anticipates lateral drift; stabilises control |
| `speed` | scalar speed (m/s) | Needed to calibrate the heading correction on curves |
| `prev_steer` | steering **applied** (post-cage) last cycle, [−1,1] | First-order memory → regularises steering without a recurrent net |

`speed` is bounded to ≥ 0 in code (`low=0.0`); §7.2.1 describes it as
`[-∞,+∞]` for simplicity. The effective operating range is narrow
(ey ∈ [−0.12,0.12], epsi ∈ [−0.4,0.4]); the infinite bounds only avoid
truncating outlier observations during exploration.

**Ground-truth state, not raw perception.** In simulation, `ey/epsi/speed` come
from the ground-truth pose (`/odom_truth`) projected by `PolylineTracker` onto
the centerline — the same state abstraction the cage and the PD consume in F2.
This keeps RL and PD comparable and isolates learning from perception noise
(which is deliberately introduced as a stressor in F4).

---

## 3. Action space

```text
action = [steering]            (Box, float32, dim 1, in [-1, 1])
speed  = fixed (fixed_speed = 0.2 m/s); the agent does NOT control throttle
```

`steering` is a normalised command; actuation converts it to a yaw rate
(`angular.z = steering · yaw_gain`, §6). Fixed speed reduces the learning
problem's dimensionality: the PD is already stable at constant speed (F2), so
there is no evidence the RL needs throttle for the nominal scenario. If the F4
perturbed scenarios require it, the Training Specification is revised (§7.2.2).

---

## 4. Wrapper structure

`GazeboLaneEnv(gym.Env)` (`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`)
orchestrates three pure/ROS collaborators:

- `RosGazeboInterface` — publishes `/cmd_vel`, reads `/odom_truth`, teleports
  via the `gz set_pose` service, advances the sim with `step_ros`.
- `PolylineTracker` — projects the pose to `(ey, epsi, s, curvature)` on the
  centerline (`oval_right_lane_centerline.yaml`).
- `SafetyCageNode` (in-process, D-34) — the safety cage; see §5.

**`step` loop (one control cycle, `control_dt = 0.10 s`):**

```text
policy action (steering)
   └─> raw_action = (steering, throttle_nominal)
        └─> cage.step(state, raw_action)  →  safe_action, emergency   [D-34]
             └─> safe_action_to_cmd(...)  →  /cmd_vel                 [mirror of vehicle_control_node]
                  └─> step_ros(control_dt)  →  new state
                       └─> reward(state, safe_action)                [§7.2.3]
```

The reward and `prev_steer` use the **safe** (post-cage) action, not the raw
one: from the agent's viewpoint, the cage is part of the environment dynamics
(§7.2.5).

---

## 5. Reset and episode

Per-episode `reset()`:

1. `set_vehicle_pose` — teleports the vehicle to spawn via
   `/world/lane_following_oval/set_pose`.
2. `tracker.reset_tracking()` — drops the cached segment neighbourhood (avoids
   locking onto a stale segment after the jump).
3. sends a zero action, waits for `/odom_truth`, `step_ros(0.1)`,
   `calibrate_pose_offset` — fixes the constant odom→world offset.
4. **fresh cage**: a new `SafetyCageNode` is instantiated every episode (no
   latched C-05, no rate-limiter/oscillation history carried across rollouts).

**Termination** `|ey| > road_width / 2` (the policy leaves the **road**).
**Truncation** `step_count ≥ max_episode_steps` (400 → 40 s ≈ 0.47 laps).

> Note: §7.2.4 phrases termination as `|ey| > lane_width/2`; the code terminates
> at `road_width/2` (deliberate, commented in the wrapper): with the cage
> handling **lane** departures within the road, terminating at the **road** edge
> prevents the random policy from dying in 1–2 steps at the start of training.
> Pending: reconcile the §7.2.4 wording.

**Pending (no D assigned, §7.3):** random spawn perturbation (heading
±0.15 rad, lateral ±0.05 m) for start-state diversity.

---

## 6. Actuation mapping (mirror of `vehicle_control_node`)

Because the environment publishes `/cmd_vel` directly (no `vehicle_control_node`
in the training graph), it replicates that node's mapping so the policy trains
against the **same** actuation it will face at deployment:

| Quantity | Mapping | Constant |
| --- | --- | --- |
| `linear.x` | `fixed_speed · scale`, `scale = clamp(throttle/throttle_nominal, [0.35, 1])` | `throttle_nominal=0.5`, `min_speed_scale=0.35` |
| `angular.z` | `steering · yaw_gain` | `yaw_gain=0.8` |
| Emergency | `cmd_vel = (0, 0)` (controlled stop) | — |

These constants **duplicate** the `vehicle_control_node` defaults and must be
kept in sync (declared in `train_ppo.yaml`, `cage:` block). The pure logic lives
in `cobraflex_rl/cage_bridge.py`.

---

## 7. Design decisions and rejected alternatives

| # | Decision | Rejected alternative | Why |
| --- | --- | --- | --- |
| ED-1 | Abstract 4-dim obs (ey, epsi, speed, prev_steer) | Image / LiDAR point cloud as obs | The sim uses ground-truth perception (F2); abstract obs keeps RL↔PD comparable and isolates from sensor noise (an F4 stressor) |
| ED-2 | Action = steering only, fixed speed | 2D action (steering + throttle) | PD stable at fixed speed; lower dimensionality speeds up learning (§7.2.2) |
| ED-3 | Cage **in-process** during training | Cage over topics `/raw_action`→`/safe_action` | Determinism (fixed seed), no asynchrony, identical cage behaviour; see **D-34** |
| ED-4 | Termination at `road_width/2` | Termination at `lane_width/2` (§7.2.4 text) | The random policy would die in 1–2 steps; the cage handles the lane within the road |
| ED-5 | Pose from `/odom_truth` (ground truth) | Encoder `/odom` (DiffDrive dead-reckoning) | The encoder does not reflect the reset teleport → corrupted the pose every episode |
| ED-6 | Fresh cage per episode | Single cage for the whole run | Each RL episode is an independent rollout; avoids carrying a latched C-05 |

---

## 8. Traceability

- **Spec:** Training Specification §7.2 (obs/action), §7.3 (environment).
- **Decision:** D-34 (cage in enforcement during training, in-process).
- **Safety:** SR-009 (policy evaluated under the same constraints as deployment)
  → satisfied because the cage in training is the same class and config as in
  deployment.
- **Reward:** see the sibling document `docs/10_reward_function.md`.
- **Code:** `gazebo_lane_env.py`, `ros_interface.py`, `polyline_tracker.py`,
  `cage_bridge.py`; config `train_ppo.yaml`.

---

## 9. Anticipated defense questions

**Q1. Why fixed speed if a real car modulates its speed?**
Because F3's goal is to learn *lateral regulation* in the nominal ODD, where the
PD already demonstrated stability at 0.2 m/s. Adding throttle would double the
action dimension with no evidence of benefit. It is a revisable decision for F4
(perturbed scenarios), documented in §7.2.2.

**Q2. Why only 4 observations? Isn't that too few?**
They are the variables sufficient for the task: lateral error, heading error,
speed (for the curve correction) and the previous steering (smoothing). It is
the same abstract state the cage and the PD use, which makes the RL↔PD
comparison clean. More dimensions (curvature, history) were judged unnecessary
for the nominal case.

**Q3. Isn't training on ground-truth state cheating w.r.t. sim-to-real?**
In F3 ground truth is used, exactly like the F2 PD, to isolate the control
problem from the perception problem. The perception gap (noise, OOD, latency) is
introduced as a controlled stressor in F4, where its impact is measured.
Separating the two error sources is an explicit methodological decision, not an
omission.

**Q4. Why is the cage active during training?**
So the policy learns under the same envelope that governs it at deployment
(SR-009): what it learns is what gets deployed, with no distribution shift at
the cage boundaries. See D-34. The cage is invoked in-process with the same
class and `cage.yaml` as the deployment node.

**Q5. Why terminate at the road edge and not the lane edge?**
A pragmatic training decision: an initial random policy would leave the lane in
1–2 steps and never accumulate useful experience. The cage corrects lane
violations *within* the road; terminating at the road edge marks the "cage could
not prevent it" case. (Wording discrepancy with §7.2.4 pending reconciliation.)

**Q6. The environment runs at 10 Hz (`control_dt=0.1`) but the cage is specified
at 20 Hz (`cycle_period_ms=50`). Is that a problem?**
It is a known open point. C-06's *per-cycle* limits (`delta_max_*_per_cycle`)
are interpreted per environment step. They are marked
`[provisional, M-5 + F3 prototype]` and will be recalibrated against the policy's
real action distribution after the first prototype. If cadence matters,
`control_dt` will be aligned with the cage cycle or the deltas rescaled.

---

## Version log

- **v0.1 (2026-05-29):** first freeze, consistent with the TS-01 cage wiring
  (D-34) and Training Specification §7.2–§7.3.
