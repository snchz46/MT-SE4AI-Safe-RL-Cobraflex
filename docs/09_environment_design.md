# Environment Design v0.1 — RL Training Environment (CobraFlex / F3)

| Field | Value |
| --- | --- |
| Artifact | Output of day **D36** (Phase 3, Week 8) — see `docs/.phases/Fase 3/fase_3_detallada.md` §4 (local plan) |
| Version | **0.2** (2026-06-01 — post-first-run reconciliation with §7.2/§7.3; v0.1 was the pre-first-run freeze) |
| Phase / Gate | F3 (PPO training), after G2 |
| Author | Samuel Sanchez |
| Date | 2026-06-01 (v0.2) · 2026-05-29 (v0.1) |
| Status | CONFIRMED — implemented in `GazeboLaneEnv` |
| Normative spec | Training Specification §7.2–§7.3 (Chapter 7). **This document is supporting rationale, not the normative source**: on any numeric discrepancy, §7.2 prevails. |
| Decisions cited | D-07 (artifact A1), D-34 (cage during training), D-32 (external drivers) |
| Spanish working copy | `docs/.phases/Fase 3/environment_design_v0.1.md` (local, gitignored) |

> Purpose: document *what* the RL training environment is and, above all, *why*
> it was designed this way, including the rejected alternatives and a bank of
> defense questions. It complements the thesis prose (Ch. 7) with the
> engineering detail the committee may ask for.

> **Track framing (2026-06-22).** This document specifies the **state-vector**
> training environment (F3), now the **baseline / control arm**. The thesis's
> **primary** system is the **end-to-end camera** track (track 'E', D-41/D-43):
> its environment — image observation, camera pipeline, visual domain
> randomisation, and the cage's own CV estimator — is specified in **§10** here
> and, normatively, in `docs/11_camera_rl_training.md` and Chapter 7. The only
> delta between the two environments is the **perception source**; that delta is
> exactly what measures the cost of camera perception (E↔F).

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
obs = [ey, epsi, speed, prev_steer, kappa_near, kappa_far]   (Box, float32, dim 6)
low  = [-inf, -π, 0.0, -1.0, -inf, -inf]
high = [+inf, +π, +inf, 1.0, +inf, +inf]
```

| Component | Meaning | Why it is here |
| --- | --- | --- |
| `ey` | lateral offset to the lane centre (+ left) | Main controlled variable |
| `epsi` | heading error vs the lane tangent (+ counter-clockwise) | Anticipates lateral drift; stabilises control |
| `speed` | scalar speed (m/s) | Needed to calibrate the heading correction on curves |
| `prev_steer` | steering **applied** (post-cage) last cycle, [−1,1] | First-order memory → regularises steering without a recurrent net |
| `kappa_near` | signed centerline curvature, near look-ahead (3 segments) | Curve preview — lets the policy *anticipate* the bend (ED-7) |
| `kappa_far` | signed centerline curvature, far look-ahead (8 segments) | Longer-horizon preview for bend entry/exit (ED-7) |

`speed` is bounded to ≥ 0 in code (`low=0.0`); §7.2.1 describes it as
`[-∞,+∞]` for simplicity. The effective operating range is narrow
(ey ∈ [−0.12,0.12], epsi ∈ [−0.4,0.4], |kappa| ≤ 1.25 rad/m for R=0.8 m);
the infinite bounds only avoid truncating outlier observations during
exploration. The two curvature components were added in the F3 first-run
revision (ED-7) after the original 4-dim, purely-reactive observation
blocked learning on the bend.

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

The `prev_steer` observation and most reward terms use the **safe** (post-cage)
action, not the raw one: from the agent's viewpoint, the cage is part of the
environment dynamics (§7.2.5). **Exception (reward v1.2): the smoothness term
`w_ds·|Δsteer|` uses the raw policy delta** (ED-10), because C-06 masks raw
bang-bang into a near-identical post-cage signal and a post-cage smoothness
penalty never bites.

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
**Truncation** `step_count ≥ max_episode_steps` (500 → 50 s ≈ 1.14 laps).

> Note: §7.2.4 phrases termination as `|ey| > lane_width/2`; the code terminates
> at `road_width/2` (deliberate, commented in the wrapper): with the cage
> handling **lane** departures within the road, terminating at the **road** edge
> prevents the random policy from dying in 1–2 steps at the start of training.
> Pending: reconcile the §7.2.4 wording.

**Random spawn perturbation (§7.3, implemented).** Each episode perturbs the
spawn heading by ±0.15 rad and the lateral position by ±0.05 m
(`spawn_perturbation` block in `train_ppo.yaml`, ranges `[provisional, M-P5]`)
for start-state diversity; `eval_policy` disables it for a deterministic,
comparable start.

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
| ED-1 | Abstract 6-dim obs (ey, epsi, speed, prev_steer, kappa_near, kappa_far) | Image / LiDAR point cloud as obs | The sim uses ground-truth perception (F2); abstract obs keeps RL↔PD comparable and isolates from sensor noise (an F4 stressor). Curvature added in F3 — see ED-7 |
| ED-2 | Action = steering only, fixed speed | 2D action (steering + throttle) | PD stable at fixed speed; lower dimensionality speeds up learning (§7.2.2) |
| ED-3 | Cage **in-process** during training | Cage over topics `/raw_action`→`/safe_action` | Determinism (fixed seed), no asynchrony, identical cage behaviour; see **D-34** |
| ED-4 | Termination at `road_width/2`; plus C-05 emergency (ED-8) | Termination at `lane_width/2` (§7.2.4 text) | The random policy would die in 1–2 steps; the cage handles the lane within the road |
| ED-5 | Pose from `/odom_truth` (ground truth) | Encoder `/odom` (DiffDrive dead-reckoning) | The encoder does not reflect the reset teleport → corrupted the pose every episode |
| ED-6 | Fresh cage per episode | Single cage for the whole run | Each RL episode is an independent rollout; avoids carrying a latched C-05 |
| ED-7 | Signed-curvature preview in obs (`kappa_near`, `kappa_far`) | Reactive 4-dim obs (ey, epsi, speed, prev_steer) | F3 first run: without preview the policy could not anticipate the R=0.8 m bend, drifted, the cage took over and emergency-stopped → `explained_variance ≈ 0`, flat learning. The cage already used `curvature_ahead`; exposing it to the policy unblocked learning (laps completed) |
| ED-8 | Episode ends on a C-05 emergency, **penalty-free** | Run the frozen post-emergency car to the horizon; or end with the `w_term` penalty | A latched C-05 freezes the car → remaining steps carry no signal and burn wall-clock. Ending early avoids that; making it penalty-free keeps the cage's action as dynamics, not punishment (D-34). Only off-road incurs `w_term` |
| ED-9 | Forward reward = normalised **progress** (Δs along centerline) | `w_fwd · speed` (instantaneous, cage-fixed ≈ const) | F3 first run: constant speed made the forward term non-discriminating → the return barely depended on the policy (`explained_variance ≈ 0`). Progress rewards surviving + advancing and keeps each on-track step net-positive, closing the penalty-free-emergency perverse incentive. See `docs/10_reward_function.md` |
| ED-10 | Smoothness term `w_ds·\|Δsteer\|` on the **raw** policy delta, `w_ds` 0.10→0.20 (reward v1.2) | Δsteer on the post-cage applied delta (v1.0/v1.1) | F3 reward-v1.0 eval: C-06 absorbs raw bang-bang for free, so a post-cage smoothness penalty is toothless (policy drove C-06 to its limit ~89% of steps unpenalised; §7.5.2). Measuring the raw delta makes the policy pay for its own jerk. Deliberate, scoped exception to the reward-on-safe-action rule (this term only). **Confirmed** by the seed-2024/200k definitive run: native smooth raw steering (sign-flips 1.1%, mean \|Δraw\|≈0.030 < C-06's 0.15) and **0% cage** (zero interventions) in nominal (§7.5.2); weights still `[provisional, M-P4]` pending Ch.8. See `docs/10_reward_function.md` |

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
<!--
## 9. Anticipated defense questions

**Q1. Why fixed speed if a real car modulates its speed?**
Because F3's goal is to learn *lateral regulation* in the nominal ODD, where the
PD already demonstrated stability at 0.2 m/s. Adding throttle would double the
action dimension with no evidence of benefit. It is a revisable decision for F4
(perturbed scenarios), documented in §7.2.2.

**Q2. Why 6 observations — and why was curvature added?**
The first four (lateral error, heading error, speed, previous steering) are the
abstract control state the cage and the PD also use, which keeps the RL↔PD
comparison clean. Curvature (`kappa_near`, `kappa_far`) was **added in the F3
first run** (ED-7): the original 4-dim observation was purely reactive, so the
policy could not anticipate the R=0.8 m bend — it drifted until the cage took
over and emergency-stopped, leaving `explained_variance ≈ 0` and no learning.
The cage already consumed `curvature_ahead` internally; exposing the same signed
preview to the policy unblocked learning (the agent began completing laps). It
remains an *abstract* preview (two scalars from the known centerline), not raw
perception, so the F2 ground-truth assumption (Q3) is unchanged.

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
--->
## 10. Track E — end-to-end camera observation variant (D-41 / D-43)

> Parallel track 'E' (branch `e2e-camera`). This section specifies how the F3
> environment above changes for the **end-to-end front-camera** policy. Everything
> not listed here is **unchanged** — that minimal delta is the point of D-43 (which refines
> D-42's cage independence into a deterministic vision lane-estimator for generalisation).

**What changes: the observation only.** ED-1 rejected an image observation *for F3*
(to keep RL↔PD comparable and isolate perception). **D-41 supersedes that choice for
track 'E'**: the observation becomes the front-camera image; the policy *learns*
perception.

```text
obs    = front-camera frame      (Box, uint8, shape (84, 84, 1) grayscale — FIXED at E2, inside the v0.3 envelope)
action = [steering]              (UNCHANGED: Box float32 dim 1; fixed speed 0.2 m/s)
```

- **Fixed observation parameters (E2).** 84×84 **grayscale**, frame stack **k=4**
  (`VecFrameStack` in the trainer; the env emits single frames). Grayscale because the
  lane cue is white-on-asphalt luminance — colour adds 3× input for no lane information
  and would invite reliance on the very appearance axis the H-10 domain randomisation
  varies; 84×84 is the SB3 `CnnPolicy`/NatureCNN native input, at which the ~0.01 m-wide
  rendered lane lines remain ≥1 px in the near field; k=4 (envelope upper end) because
  steering-rate cues must come entirely from the stack — the camera obs has no
  `prev_steer` channel. Constants in `cobraflex_rl/camera_pipeline.py`; config
  `train_ppo_camera.yaml`.
- **Source camera:** the existing `ZEDm Cam` Gazebo sensor (640×480 RGB @ 20 Hz, HFOV
  1.3962634, topic `camera/image_raw`, bridged in `gz_bridge.yaml`), **pitched down
  0.25 rad** (E2: flat-mounted, the R=0.80 m curve swept out of the FOV — evidence in
  `experiments/sim/e_cam_visibility/`). Native frames are area-downsampled to the obs
  in the shared `CameraPipeline` (one degradation point before both consumers, D-43).
- **Policy network:** SB3 `CnnPolicy` (NatureCNN feature extractor) replaces the MLP
  over the 6-dim vector. The curvature-preview scalars (`kappa_near/far`, ED-7) are
  **not** in the obs — the policy must infer bend geometry from the image (the harder
  perception problem D-41 accepts; budget the larger training set, Shalev-Shwartz &
  Shashua 2016).

**Training-world diversity (decided: oval first).** The first camera-policy prototype trains
on the **current oval** (`lane_following_oval`) — now with **visible lane lines** rendered for
the camera — to validate that a CNN can drive from the camera at all. World diversity
(varied geometries / appearances, for the "any road with visible lines" generalisation goal)
is added **after** that first result; the appearance axis is already covered by the
visual-degradation domain randomisation below.

**What does NOT change.**

- **Action / actuation** (§3, §6): steering-only, fixed speed, same `cmd_vel` mapping.
- **Reward** (`docs/10`): computed on ground-truth state + progress, hence
  **observation-agnostic** → carries over unchanged (smoothness term still on the raw
  policy steering delta).
- **Cage:** `SafetyCageNode` still evaluates C-01..C-06 **unchanged**, but its `state` now
  comes from a **dedicated deterministic CV lane-estimator** (D-43, supersedes D-42) — not
  from `PolylineTracker(/odom_truth)` and not from the policy's CNN. The cage thus generalises
  to any road with visible lines, like the policy, and stays independent of the *learned*
  policy and auditable. **Trade-off:** a camera fault now blinds policy and cage alike
  (common-cause) → residual safety is the open-loop controlled stop (SR-013 / SR-014). Ground
  truth survives **in sim only**, as the reward signal and an **oracle** to validate the CV
  estimator's error.
- **Reset / episode / termination** (§5).

**Visual-degradation stressors (SC-PERT-04..06 → SR-012 → H-10).** Applied to the **camera
frame** before it reaches *both* consumers — the policy's CNN **and** the cage's CV detector
(common-cause, D-43) — glare/over-exposure, low-light/under-exposure, motion blur,
contrast/shadow. The pure transforms live in `cobraflex_rl/visual_degradation.py` (numpy,
host-testable); the Gazebo camera plug-in and the runtime injector are the Ubuntu part. Domain
randomisation over the same envelope (`cobraflex_rl/visual_domain_randomization.py`,
host-testable) is the training-side mitigation of H-10.

**Perception loss & misdetection (SC-PERT-07/08 → SR-013/SR-014 → H-11/H-12).** The cage's
**CV-estimator health check** raises the C-05 controlled-stop trigger (Trigger 8, `docs/04`)
on either a lost lane (occlusion / absent features / stale-or-dropped frame, H-11) or a
suspect estimate failing the plausibility / temporal-consistency check (false lane, H-12). The
stop is open-loop (needs no perception). The health / plausibility logic is host-testable
(`cobraflex_rl/perception_health.py`); the camera subscription and the CV detector are the
Ubuntu part.

**Cage state source.** The cage runs a **deterministic classical-CV lane estimator** on the
camera (D-43), separate from the policy's CNN. In simulation, ground truth is used to (a)
compute the reward and (b) **validate** the CV estimator's error (an oracle). The same CV
estimator transfers to E-physical with no ground truth required.

**Implementation status (E2, 2026-06-10).** The "deferred to Ubuntu" list is built and
live: the camera sensor publishes headless and the lane lines are evidence-verified
(`experiments/sim/e_cam_visibility/`); `gazebo_lane_env` has the camera observation mode
(`observation.type: camera` — image obs via the shared `CameraPipeline`, cage state via
`CagePerceptionSupervisor`); the runtime degradation injectors run per episode from
`reset(options)` (scenario stressors) or from the in-env H-10 domain randomisation
(`domain_randomization` config block, per-episode draw via the seeded `np_random`); the
deterministic CV lane-estimator + SR-013/SR-014 supervision feed C-05 Trigger 8 (cage
YAML 0.6.0). Estimator-vs-oracle accuracy per D-43's plan:
`experiments/sim/runs/cv_estimator_val_*`. Remaining for later E-phases: the CNN
training runs themselves and the eval campaign.

**Traceability.** Spec: this §10 + Training Spec (E-design, pending). Decisions: D-41
(supersedes ED-1/D-01 for track 'E'), **D-43** (cage on a deterministic CV estimator,
supersedes D-42); D-34 (cage in enforcement during training) carries over. Safety: SR-012,
SR-013, SR-014 (H-10/H-11/H-12). Code (host): `visual_degradation.py`,
`visual_domain_randomization.py`, `perception_health.py`, `lane_plausibility.py`,
`camera_geometry.py`, `cv_lane_estimator.py`, `cage_perception.py`, `camera_pipeline.py`;
(sim loop): camera mode in `gazebo_lane_env.py` + image subscription in
`ros_interface.py`; (tools): `validate_cv_estimator.py`, `capture_camera_frames.py`.

---

## Version log

- **v0.1 (2026-05-29):** first freeze, consistent with the TS-01 cage wiring
  (D-34) and Training Specification §7.2–§7.3.
- **v0.2 (2026-06-01):** post-first-run reconciliation with §7.2/§7.3 — truncation
  horizon `max_episode_steps = 500` (50 s ≈ 1.14 laps; was 400 / 40 s / 0.47 laps)
  and the random spawn perturbation marked **implemented** (§7.3,
  `train_ppo.yaml`). Design rationale unchanged; numeric values realigned to the
  Training Specification.
- **v0.3 (2026-06-09):** added §10 (Track E — end-to-end camera observation variant,
  D-41/D-42): the observation becomes the front-camera image (CNN policy), while the
  action, reward, cage and episode logic are unchanged. F-track design (v0.2) untouched.
- **v0.4 (2026-06-09):** §10 revised for **D-43** (supersedes D-42): the cage's state now
  comes from a dedicated deterministic CV lane-estimator (not ground truth), for
  generalisation to any road with visible lines; common-cause trade-off + the new H-12/SR-014
  (cage misdetection) recorded; training-world diversity decided as **oval-first**; ground
  truth retained in sim only as reward + CV-estimator oracle.
- **v0.5 (2026-06-10, E2):** §10 reconciled to the implementation. Provisional obs
  choices **fixed inside the v0.3 envelope**: 84×84 **grayscale**, frame stack **k=4**
  (rationale in §10; no new D-NN — the envelope was the decided design, this freezes the
  point). Source camera documented (ZEDm 640×480@20 Hz, pitch 0.25 rad, E2 evidence);
  the "deferred to Ubuntu" list replaced by the implementation-status block (camera obs
  mode + in-env H-10 domain randomisation + CV estimator/supervisor → C-05 Trigger 8,
  cage YAML 0.6.0; oracle validation runs under `experiments/sim/runs/cv_estimator_val_*`).
  F-track design (§1–§9) untouched.
