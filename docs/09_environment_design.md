# Environment Design — RL Training Environment (Track 'E', end-to-end camera)

| Field | Value |
| --- | --- |
| Artifact | The RL **training environment** of the thesis's primary system: the end-to-end front-camera policy (track 'E'). Camera counterpart of the training loop; sibling of `docs/11` (training) and `docs/10` (reward). |
| Version | **0.7** (2026-07-20 — reconciles the frozen GE4 PPO 1-D environment with the posterior Gazebo PPO/SAC 1-D/2-D evidence and the separate Isaac 2-D contract; 0.6 = track-'E' retargeting; 0.5 = E2 camera freeze; 0.1–0.4 = F3 state-vector history.) |
| Phase / Gate | Track 'E' (camera) — training infrastructure reused from F3; GE3 train, GE4 eval (verdict of record). G4 closed 02.07.2026. |
| Author | Samuel Sanchez |
| Date | 2026-07-20 (v0.8) |
| Status | CONFIRMED — `GazeboLaneEnv` supports PPO/SAC and 1-D/2-D camera policies; posterior Gazebo and Isaac runs are live-validated. GE4 remains the frozen PPO 1-D verdict. |
| Normative spec | Training Specification Ch.7 §7.2 (loop) + §7.7 (camera track). **This document is supporting rationale, not the normative source**: on any numeric discrepancy, §7.2/§7.7 prevails. |
| Decisions cited | D-41 (end-to-end camera, supersedes D-01/ED-1), D-43 (cage on its own CV estimator, supersedes D-42), D-34 (cage in the training loop), D-49 (verdict action stays 1-D steering-only), D-50 (2-D action + multi-circuit, posterior), D-52 (Isaac 2-D `ent_coef`), D-56 (2-D `stall_penalty`), D-59 (Gazebo 2-D posterior), D-60 (PPO/SAC algorithm switch), D-32 (external drivers) |

> Purpose: document *what* the end-to-end camera RL training environment is and,
> above all, *why* it is designed this way — the camera observation, the action
> space (the frozen 1-D verdict action and the Gazebo/Isaac 2-D posterior extensions), the
> wrapper, reset/episode logic, actuation, visual degradation, and the cage's own
> CV state source — including the rejected alternatives and a defense-question
> bank. It complements the thesis prose (Ch.7 §7.7) with the engineering detail
> the committee may ask for.

> **Track framing.** Track 'E' (D-41/D-43) is the thesis's **primary** system: an
> end-to-end front-camera policy whose safety cage reads its own deterministic CV
> lane-estimator. This document specifies **that** environment. The F-track
> state-vector environment (a 6-D ground-truth observation, `MlpPolicy`) is the
> **frozen baseline / control arm** — the reference for "what does camera
> perception cost" — and is compressed to a short provenance note in §10; its full
> historical specification is in the v0.1–v0.4 history and Training Spec §7.2–§7.3.
> The only delta between the two environments is the **perception source**; that
> delta is exactly what the E↔F comparison measures.

---

## 1. What the environment is, in one paragraph

The training environment is `GazeboLaneEnv` in **camera mode** (`observation.type == "camera"`): a Gym env that maps either a steering-only action or a config-gated steering+throttle action to a Gazebo control cycle and returns the next front-camera frame plus a ground-truth-scored reward. Each cycle, one native Lane-Cam frame is (optionally) degraded, then split to **two parallel consumers** — the policy's CNN (downsampled to 84×84, frame-stacked) and the cage's own deterministic CV lane-estimator (D-43). The policy emits an action; the in-process safety cage (`SafetyCageNode`, D-34) filters it against C-01..C-06 on the CV-derived state; the safe action is actuated as `/cmd_vel`; the sim advances one control cycle. Ground truth survives **only** as the training reward signal and as the oracle that validates the CV estimator — never as an input to the policy or the cage at runtime. Everything the camera policy learns, it learns from pixels.

---

## 2. Observation space

```text
policy obs = front-camera frame     (Box, uint8, shape (84, 84, 1) grayscale; frame-stacked ×4 → 84×84×4)
cage obs   = CvLaneEstimate(ey, epsi, lane_width, curvature, confidence)   (D-43; from the same frame)
```

The policy observes the **image**; the cage observes the **CV lane-estimate** derived from the same image. They are disjoint pipelines fed by a **common camera** (the D-43 common-cause design, §8).

### 2.1 The source camera — the dedicated **Lane Cam** (IMX219-160 mirror)

The observation comes from the **dedicated front Lane Cam**, a Gazebo `camera` sensor that mirrors the real **IMX219-160** wide-angle module as consumed by the hardware lane-keeper (`lane_keeper_node.py`). This **replaces the legacy ZED reference** of earlier drafts — the ZED Mini stereo pair remains on the platform for other purposes, but the track-'E' policy and the cage read the Lane Cam, not the ZED.

| Sensor parameter | Value | Source / note |
| --- | --- | --- |
| Model mirrored | IMX219-160 (wide-angle) | HW capture 1280×720; only the **processed** stream matters. *(Capture rate was 60 fps until 26.08.2026, now **30** — `throttle_fps` sits after `nvvidconv`, so 60 cost 38 % of a core MORE than 30 and delivered a worse rate, 15.2 vs 19.0 Hz. The published stream is unchanged; docs/17 §8.10.)* |
| Resolution (rendered) | **640×360** R8G8B8 | `robot.gazebo` Lane Cam sensor |
| Horizontal FOV | **1.5707963 rad (90°)** | the **rendered** value, and the one every scored campaign was trained and evaluated under. It was ALSO believed to be the effective processed HFOV on hardware; **M-6 (17.08.2026) refuted that — the real module measures 77.89°, `fx` 395.93 px, not 320.** The assumption was circular: the simulator mirrored a configuration default, so no simulation result could ever expose it. Deployment closes the gap by **rectifying** the real frame into this canonical model rather than by changing this number (docs/17 §8.3). |
| Update rate | 20 Hz | sensor `<update_rate>` |
| Clip near / far | 0.1 m / 15 m | frustum |
| Sensor noise | Gaussian σ = 0.007 | rendered noise |
| Topic | `camera/image_raw_lane` | bridged in `gz_bridge.yaml` |
| Mount (joint `camera_link_lane`) | front of body, **pitch 0.30 rad down** (`rpy="0 0.30 0"`), height **h ≈ 0.077 m** above ground | the geometry `camera_geometry.py` / the CV estimator project against (docs/12 §5) |

The **pitch of 0.30 rad down** is load-bearing: a flat mount swept the near curves out of the FOV, and an earlier 0.25 rad value systematically biased the CV estimator's metric `ey` (corrected to 0.30 rad to match the URDF mount — docs/12 §5). Native 640×360 frames are area-downsampled (`INTER_AREA`) to the policy obs in the shared `CameraPipeline`, the single degradation point before both consumers.

### 2.2 Fixed observation parameters (E2)

`84×84` **grayscale**, frame stack **k = 4**:

- **Grayscale** — the lane cue is white-on-asphalt luminance; colour adds 3× input for no lane information and would invite reliance on the very appearance axis the H-10 domain randomisation varies (§7).
- **84×84** — the SB3 `CnnPolicy` / NatureCNN native input, at which the ~0.01 m-wide rendered lane lines stay ≥ 1 px in the near field.
- **k = 4** — a single frame is Markov-incomplete (no velocity/rate cue, and the camera obs has **no `prev_steer` channel**); the stack recovers motion/rate from the temporal difference. `VecFrameStack` stacks in the trainer; the env emits single frames. SB3 then adds `VecTransposeImage` (channels-first), so the network input is 4×84×84.

Constants in `cobraflex_rl/camera_pipeline.py`; config `train_ppo_camera.yaml`. The policy network is SB3 `CnnPolicy` (NatureCNN feature extractor). The F-track curvature-preview scalars (`kappa_near/far`, ED-7) are **not** in the camera obs — the policy must infer bend geometry from the image (the harder perception problem D-41 accepts; budget the larger training set, Shalev-Shwartz & Shashua 2016).

---

## 3. Action space

The action space has a **frozen verdict form** (1-D, the GE4-V2 evidence) and a config-gated **posterior extension** (2-D, implemented in Gazebo and Isaac).

### 3.1 Verdict action — 1-D steering-only (ED-2, D-49)

```text
action = [steering]     (Box, float32, dim 1, in [-1, 1])
speed  = fixed (fixed_speed = 0.20 m/s); the policy does NOT control throttle
```

`steering` is a normalised yaw-rate command (`angular.z = steering · yaw_gain`, §6). Fixed speed lowers the learning dimensionality; the classical CV baseline is stable at fixed speed, so there is no evidence the nominal task needs throttle. **The whole track-'E' Gazebo verdict (GE4-V2, 297k E-main) runs on this 1-D action** — decision **D-49** keeps it frozen so the F-vs-E "cost of camera" comparison stays on the same action, the cage speed rules keep their exogenous-throttle assumption, and no GE4 campaign has to be re-run. `ODD-1.ACT_DIM = 1`.

### 3.2 Posterior action — 2-D steering + throttle (D-50)

The 2-D action was **deferred, then implemented as posterior work** (D-49 → D-50), because SR-009's stall/liveness sub-mode (M-P6) and its negative test SC-PERT-03 are ill-posed for a steering-only policy: with no speed authority the policy cannot converge to inaction. Giving the policy throttle makes them well-posed and is closer to real driving. It is **config-gated and inert by default** — the default `action.type` is `steer` (the 1-D ED-2 contract), so every frozen F/E run and verdict stays bit-identical.

```text
action = [steer, throttle]   (Box, float32, dim 2, in [-1, 1]²)     # action.type: steer_throttle
throttle → cage scale  u = (throttle + 1) / 2 ∈ [0, 1]              # cage_bridge.policy_throttle_to_cage
speed    = max_speed_mps · u   (full stop below throttle_deadband = 0.05; no lower clamp)
```

- **The speed authority is a backend/config contract, not a universal 2-D constant.** The frozen 1-D verdict uses `fixed_speed = 0.20`. The **evidence-bearing Gazebo 2-D** configs use `max_speed_mps = 0.25`, equal to the curve ceiling; a diagnostic eval at **0.22 m/s** tested explicit margin. A separate **untrained** Gazebo contract now preregisters 0.22 for fresh training, but contributes no result yet. The **Isaac 2-D** config separately uses `max_speed_mps = 0.5` (= C-04 `v_max_straight` = `ODD-1.V_MAX`) and can exceed the curve ceiling and C-05's high-energy warning band. All 2-D contracts make a true stop commandable and SR-009's stall arm well-posed, but exercise different parts of the speed envelope.
- **No cage change.** The cage rules already operate on a `(steering, throttle)` tuple on the `u ∈ [0,1]` scale — C-04 attenuates throttle, C-06 rate-limits it at `0.10`/cycle — so `cage.yaml` 0.6.1 is consumed as-is (thresholds stay `[provisional]`, now actually exercised). At 10 Hz, C-06 bounds commanded acceleration to `max_speed_mps · 0.10 / control_dt`: 0.25 m/s² under the current Gazebo cap and 0.5 m/s² under Isaac's full-authority contract, both inside the **2.5 m/s²** platform limit (docs/14 §2.3). *(Corrected 17.08.2026: this read "0.53 m/s²" — that figure was the chassis's maximum **velocity** in m/s copied into an acceleration field, diagnosed in the platform repo's own parameter document. The conclusion is unchanged and the margin is 5× larger than believed.)*
- **Reward adds a longitudinal smoothness + liveness pair** (in `rewards.py`; D-50/D-56 — `docs/10` documents the 1-D reward, these 2-D terms are posterior): `throttle_delta` (weight 0.10, on the **raw** policy throttle delta — the mirror of the v1.2 `steer_delta` rationale) and `stall_penalty` (0.5 below `stall_progress_min = 0.25`, D-56) to make the degenerate "park" optimum unprofitable. Both default to weights that leave legacy returns bit-identical when 1-D.

**Config surfaces, one environment contract.** The action mapping is algorithm-agnostic and backend-gated:

- `train_isaac_2d.yaml` — the **Isaac in-process PPO** full-authority config (D-50; `tools/isaac_train.py` default), on the **multi-circuit** CV-safe trio `complex_b,complex_d,complex_e` (§5.3), with `ent_coef 0.01` (D-52, after run-1 exploration collapse) and `max_speed_mps = 0.5`.
- `train_ppo_camera_2d.yaml` — the **Gazebo PPO** 2-D counterpart, with the canonical Gazebo cage/CV path and current `max_speed_mps = 0.25`.
- `train_sac_camera_2d.yaml`, `train_sac_camera_2d_tuned.yaml`, and `train_sac_camera_2d_tuned_entfix.yaml` — the **Gazebo SAC** 2-D variants (D-60), using the same env/cage/reward and action cap; the tuned fixed-entropy variant produced the first full-horizon 2-D enforcement evidence.
- `train_sac_camera_2d_tuned_entfix_margin022.yaml` — the **Gazebo SAC preregistration**, not an evidence config: fresh bounded 75k checkpoint only, cap 0.22, minimum 0.03 m/s margin to C-04, 150k replay buffer covering parent + 50k stall continuation, embedded contract fingerprint and mandatory checkpoint-bound D-43 preflight.

**A policy trained under either is a new posterior baseline** — new action space, new circuits (and, for Isaac, new simulator) — **never** a re-run of the frozen 297k E-main, and it **does not reopen G4** (D-49 stands for the track-'E' verdict).

### 3.3 Posterior evidence status (17–20.07.2026)

The following observations validate the environment contracts; they are not GE4 verdict cells:

| Family | Evidence |
| --- | --- |
| Gazebo PPO 2-D | Historical full-authority run (`max_speed_mps = 0.5`): peak `ep_rew_mean = 654.4` at 510k; monitoring completed competently. No full-horizon PPO 2-D enforcement run is claimed; this result is not attributed to the current 0.25 m/s configs. |
| Gazebo SAC 1-D | Auto-entropy reached 720 at 89k. Fixing `ent_coef = 0.005` removed the abrupt entropy collapse; all three seeds completed clean enforcement evals, while paired nominal enforcement+monitoring exists for 2/2 evaluated pairs (seed 42 monitoring is pending). Increasing replay capacity from 100k to 200k held rewards through 180k; this bounded single-seed intervention strongly supports replay eviction, rather than reward drift, as the explanation for the observed slow decay. |
| Gazebo SAC 2-D | Tuned auto-entropy reached 527 at 154k but enforcement stopped on either a zero-margin speed conflict or D-43 CV over-read. Fixed entropy reached 558.7 at 78k and produced full-horizon enforcement for seeds 2024 and 42. |
| Speed-margin probe | Evaluating the auto 150k checkpoint at 0.22 instead of 0.25 m/s removed its speed-conflict stop; the auto 175k checkpoint still stopped on the D-43 heading over-read under both caps. Margin helps longitudinal arbitration but cannot repair perception. |
| D-43 preflight | Entfix-2024/75k and entfix-42/50k pass the centred-oracle gate individually; auto-175k at 0.25 and its 0.22 probe block. The aggregate reference is `BLOCKED`; a future run must produce its own PASS bound to checkpoint **and** config hashes. |
| SAC SC-PERT subset | Two 100-cell seed subsets: enforcement 100/100 PASS combined versus monitoring 68/100; SC-PERT-11 monitoring was 0/10 for each seed. The subset roll-ups are intentionally globally `INCOMPLETE`, not verdict campaigns. |

Within the matched **1-D PPO↔SAC comparison**, SAC changes the optimiser/data
regime, not the observation, action, reward, cage, scenario, or metric
contracts. The 2-D rows validate separate posterior contracts; they are not a
controlled PPO↔SAC algorithm comparison because the historical PPO 2-D arm used
the 0.5 m/s cap while current SAC 2-D uses 0.25 m/s plus later tuning/random
spawns. Every PPO-based thesis verdict remains intact.

---

## 4. Wrapper structure (camera mode)

`GazeboLaneEnv(gym.Env)` (`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`) orchestrates:

- `RosGazeboInterface` — publishes `/cmd_vel`, reads `/odom_truth` (sim oracle) and the Lane-Cam frame (`camera/image_raw_lane`), teleports via the `gz set_pose` service, advances the sim with `step_ros`.
- `CameraPipeline` (`camera_pipeline.py`) — applies the per-episode degradation injector once to the native frame, then returns `(consumer_frame, observation)`: the native-resolution (possibly degraded) frame for the cage's CV estimator and the 84×84 policy observation. Hosts the proven `decode_image()` shared by the ROS node and the env.
- `CvLaneEstimator` + `CagePerceptionSupervisor` (`cv_lane_estimator.py`, `cage_perception.py`) — the cage's deterministic state source (D-43, §8), with the SR-013 health / SR-014 plausibility checks.
- `SafetyCageNode` (in-process, D-34) — the safety cage; C-01..C-06 on the CV-derived state.

**`step` loop (one control cycle, `control_dt = 0.10 s` → 10 Hz):**

```text
policy action (steering [, throttle])
   └─> raw_action = (steering, throttle)          # 1-D: throttle = throttle_nominal; 2-D: from the policy
        └─> cage.step(cv_state, raw_action) → safe_action, emergency      [D-34, cage on CV state D-43]
             └─> safe_action_to_cmd(...) → /cmd_vel                        [mirror of vehicle_control_node]
                  └─> step_ros(control_dt) → next frame + ground-truth pose
                       └─> reward(ground_truth_state, raw policy delta)    [docs/10; sim-only]
```

Most reward terms use the **safe** (post-cage) action — from the agent's viewpoint the cage is part of the environment dynamics — **except** the smoothness terms (`steer_delta`, and 2-D `throttle_delta`), which use the **raw** policy delta (ED-10): C-06 masks raw bang-bang into a near-identical post-cage signal, so a post-cage smoothness penalty never bites.

---

## 5. Reset and episode

### 5.1 Per-episode `reset()`

1. `set_vehicle_pose` — teleports the vehicle to spawn via the `gz set_pose` service (hardened: timeout 3500 ms, 4 retries — the camera reset path is slower than the state env's).
2. `tracker.reset_tracking()` — drops the cached segment neighbourhood (avoids locking onto a stale segment after the jump).
3. sends a zero action, waits for `/odom_truth`, `step_ros(0.1)`, `calibrate_pose_offset`.
4. **fresh cage** — a new `SafetyCageNode` per episode (no latched C-05, no rate-limiter/oscillation history carried across rollouts).
5. **CV supervisor priming (camera-specific)** — the perception supervisor is run on the settled spawn view until it accepts one frame, so the cage's first cycle starts from an accepted state. Without priming, one bad first frame put the cage on its no-state-ever path → instant emergency → 1-step episodes (a live E2 bug).

### 5.2 Termination and truncation

**Termination = off-road.** On the convex F-track oval this is the perpendicular `|ey| > road_width/2`. On the **self-approaching `complex_b`** the perpendicular test folds back where the road passes near itself, so the camera env judges off-road by the **global** distance from the vehicle to the **road-centre** centerline vs `road_width/2` (docs/11 §3.5; `PolylineTracker.distance_to`, a stateless full sweep). The reward centerline stays the **right lane** (offset) — reward target and containment edge play different roles. Both are opt-in / gated, so the oval is byte-for-byte unchanged. **Truncation** at `step_count ≥ max_episode_steps`.

### 5.3 Spawn perturbation and multi-circuit sampling

**Random spawn perturbation** (`spawn_perturbation`, ranges `[provisional, M-P5]`) perturbs the spawn heading/lateral for start-state diversity; `eval_policy` disables it for a deterministic, comparable start.

**Multi-circuit per-episode sampling (2-D posterior, D-50).** For the Isaac full-authority track the env is built with `circuits=[complex_b, complex_d, complex_e]` — a CV-safe trio (each designed against the docs/12 §4.7 monocular curvature boundary; `complex_e` re-cut clockwise for steering-handedness balance, D-51). One circuit is sampled per episode via the seeded `np_random` (`options["circuit_index"]` pins it for deterministic eval; `info` carries `circuit_index`/`circuit_name`). The scene lays the circuits out 15 m apart (the Lane-Cam far-clip distance) so a neighbour never enters the frustum. Run metadata records per-circuit YAML paths + hashes. Single-circuit runs (the frozen verdict) are unaffected.

---

## 6. Actuation mapping (mirror of `vehicle_control_node`)

The env publishes `/cmd_vel` directly, replicating `vehicle_control_node`'s mapping so the policy trains against the **same** actuation it faces at deployment. The pure logic lives in `cobraflex_rl/cage_bridge.py`.

| Quantity | 1-D verdict mapping | 2-D posterior mapping (D-50) |
| --- | --- | --- |
| `linear.x` | `fixed_speed · clamp(throttle/throttle_nominal, [0.35, 1])`, throttle held at `throttle_nominal` | `max_speed_mps · u`, `u = (throttle+1)/2`; **full stop below `throttle_deadband = 0.05`, no lower clamp** |
| `angular.z` | `steering · yaw_gain` (`yaw_gain = 0.8`) | same |
| Emergency | `cmd_vel = (0, 0)` (controlled stop) | same |

The 1-D map floors speed at `0.35·cruise`; the 2-D map gives the cage's attenuation authority **all the way to zero** (so C-04/C-05 can actually stop the car). Constants duplicate the `vehicle_control_node` defaults and must be kept in sync (declared in the train config `cage:` block).

---

## 7. Visual degradation and domain randomisation (H-10 / SR-012)

The one **additive** element of camera training, applied to the **camera frame before both consumers** (D-43 common-cause), so a camera fault can blind policy and cage at once and the designed answer is the cage's controlled stop.

**Training-time domain randomisation.** At each `reset()`, `VisualDomainRandomizer.sample()` draws a per-episode `(mode, level)` with `p_degrade = 0.5`, `level_range = [0.2, 0.8]`, from the **H-10 trio** (`visual_degradation.MODES`, deterministic numpy kernels): `glare_overexposure`, `low_light_underexposure`, `motion_blur`. The draw is **per-episode** (a degradation persists across an episode the way a real condition would) and **disabled at evaluation** (a harsh spawn draw would blind perception before the run starts).

**Why only these three at training.** `occlusion` (SC-PERT-07, H-11) and `false_lane` (SC-PERT-08, H-12) are **eval-only** (`EVAL_ONLY_MODES`): training the policy to "see through" them would teach it to ignore exactly the cues whose loss must trigger the SR-013/SR-014 controlled stop — the cage's job, not the policy's.

Pure transforms in `cobraflex_rl/visual_degradation.py` and `visual_domain_randomization.py` (numpy, host-testable); the Gazebo camera plug-in and runtime injector are the Ubuntu part. The eval stressor scenarios (SC-PERT-04..13, world variants) are specified in `docs/05` and `docs/08` §5.5.

---

## 8. Cage state from a deterministic CV estimator (D-43)

The cage no longer reads ground truth or the policy's CNN. It reads its **own deterministic classical-CV lane estimator** on the camera frame (`CvLaneEstimator`, `docs/12` §4), separate from the policy — so the cage generalises to any road with visible lines (like the policy) yet stays independent of the *learned* policy and fully auditable. Per cycle the supervisor:

- samples the freshest frame (so the cage is not one control cycle behind — a live E2 bug that tripped C-05's staleness trigger),
- runs the SR-013 health + SR-014 plausibility / temporal-consistency checks,
- on a trustworthy estimate builds a cage `State` stamped with the frame's **age** (so C-05's staleness trigger measures real latency in episode time); otherwise passes `state=None` + `perception_invalid=True`, so the cage takes its missing-state path and, once persistence elapses, fires **C-05 Trigger 8** (the open-loop controlled stop — needs no perception).

**Trade-off (accepted, D-43).** A camera fault now blinds policy and cage alike (common-cause); the residual safety is the controlled stop (SR-013 / SR-014). A confidently *wrong* CV estimate is the new hazard **H-12** (the GE4-V2 under-read, docs/12 §4.4 / docs/08 §12.2), backstopped by SR-014 where the estimate is self-inconsistent. **Ground truth survives in simulation only**, as (a) the reward signal and (b) the oracle that validates the CV estimator's error (`experiments/sim/runs/cv_estimator_val_*`); neither policy nor cage consumes it at runtime.

---

## 9. Design decisions and rejected alternatives

| # | Decision | Rejected alternative | Why |
| --- | --- | --- | --- |
| ED-2 | Verdict action = **steering only, fixed speed** (`ACT_DIM = 1`) | 2-D action for the verdict | Lower dimensionality, faster learning; keeps the F↔E comparison and the cage's exogenous-throttle assumption on one action. Kept frozen for the whole Gazebo E verdict by **D-49**; 2-D is posterior work (ED-13) |
| ED-3 | Cage **in-process** during training | Cage over ROS topics | Determinism (fixed seed), no asynchrony, identical cage behaviour; **D-34** |
| ED-4 | Termination at the **road edge** (off-road), plus C-05 emergency (ED-8) | Termination at the lane edge | A random policy would die in 1–2 steps; the cage handles lane departures *within* the road. On `complex_b` the off-road test is the global road-centre distance (§5.2) |
| ED-5 | Ground-truth pose from `/odom_truth` as the sim oracle | Encoder `/odom` (dead-reckoning) | The encoder does not reflect the reset teleport → corrupted pose every episode. (Ground truth is oracle-only on track 'E' — never a policy/cage input, D-43) |
| ED-6 | Fresh cage per episode | Single cage for the whole run | Each rollout is independent; avoids carrying a latched C-05 |
| ED-8 | Episode ends on a C-05 emergency, **penalty-free** | Run the frozen post-emergency car to the horizon; or end with `w_term` | A latched C-05 freezes the car → remaining steps carry no signal; ending early avoids that, penalty-free keeps the cage as dynamics not punishment (D-34). Only off-road incurs `w_term` |
| ED-9 | Forward reward = normalised **progress** (Δs along centerline) | `w_fwd · speed` (const at fixed speed) | Constant speed made a speed term non-discriminating (`explained_variance ≈ 0`); progress rewards surviving + advancing. See `docs/10` |
| ED-10 | Smoothness term on the **raw** policy delta (`steer_delta`; 2-D adds `throttle_delta`) | Δ on the post-cage applied delta | C-06 absorbs raw bang-bang for free, so a post-cage smoothness penalty is toothless; measuring the raw delta makes the policy pay for its own jerk. See `docs/10` |
| **ED-11** | **Observation = front-camera image** (Lane Cam, 84×84×4), CNN policy | Abstract state vector (ED-1, F-track) | **D-41 supersedes ED-1/D-01 for track 'E'**: the policy *learns* perception from pixels — the thesis's primary system and its generality claim. Source = the dedicated **Lane Cam (IMX219-160 mirror)**, not the legacy ZED (§2.1) |
| **ED-12** | **Cage state from a dedicated deterministic CV estimator** | Cage on ground truth (D-42) or on the policy's CNN | **D-43**: "any road, sees lines → drives" needs the cage to key on visible lines too, without an authored centerline, while staying independent of the *learned* policy and auditable. Accepts the common-cause trade-off (§8) |
| **ED-13** | **2-D action (steering + throttle) as posterior work**, config-gated + inert by default | Expand to 2-D for the verdict; or never | **D-49 → D-50/D-59**: makes SR-009's stall test well-posed and lets the cage speed rules arbitrate for real, but doing it in the verdict would invalidate the frozen baseline and force a full retrain + GE4 re-run. It is therefore a **new posterior baseline**: Gazebo currently caps PPO/SAC 2-D at 0.25 m/s; Isaac PPO uses its separate 0.5 m/s contract. Neither is a re-run of the 297k E-main |

*(ED-1 "abstract obs" and ED-7 "curvature preview in obs" were F-track decisions, superseded on track 'E' by the camera observation — the policy infers bend geometry from the image. They remain in the v0.1–v0.4 history for provenance.)*

---

## 10. Baseline (F-track) note — provenance and the E↔F comparison

The **F-track** state-vector environment is the frozen **baseline / control arm**, not the deployable artefact. It is identical to the camera environment above **except the perception source**: the policy observes a 6-D ground-truth vector `[ey, epsi, speed, prev_steer, kappa_near, kappa_far]` (`MlpPolicy`), and the cage reads ground-truth-derived state (`PolylineTracker` on `/odom_truth`) rather than the CV estimator. It runs on the oval, needs a prior map + privileged pose (hence "known-track baseline"), and its F4 results are frozen. It exists so the E↔F difference isolates **the cost of camera perception**; its full specification lives in this document's v0.1–v0.4 history and Training Spec §7.2–§7.3. Nothing in it is reopened by track 'E' or by the 2-D posterior.

---

## 11. Traceability

- **Spec:** Training Specification §7.2 (loop) + §7.7 (camera track); `docs/11` (camera training, normative); `docs/10` (reward); `docs/12` (the CV baseline + estimator); `docs/08` (ODD — camera interfaces §4.6, stressor profiles §5.5).
- **Decisions:** D-41 (camera, supersedes ED-1/D-01), D-43 (cage on CV estimator, supersedes D-42), D-34 (cage in the loop), D-49 (verdict 1-D), D-50/D-59 (Isaac/Gazebo 2-D posterior), D-52/D-56 (Isaac 2-D training levers), D-60 (PPO/SAC switch), D-32 (external drivers).
- **Safety:** SR-009 (policy evaluated under the same cage as deployment — satisfied because the training cage is the deployment class/config); SR-012/SR-013/SR-014 (H-10/H-11/H-12, camera hazards).
- **Code (host-testable):** `camera_pipeline.py`, `camera_geometry.py`, `visual_degradation.py`, `visual_domain_randomization.py`, `cv_lane_estimator.py`, `perception_health.py`, `lane_plausibility.py`, `cage_perception.py`, `cage_bridge.py`, `polyline_tracker.py`. **(sim loop):** camera mode in `gazebo_lane_env.py` + image subscription in `ros_interface.py`; algorithm selection in `train_ppo.py` and `eval_policy.py`. **(posterior configs):** `train_ppo_camera_2d.yaml`, `train_sac_camera*.yaml`, `train_sac_camera_2d*.yaml`, and `train_isaac_2d.yaml`.

---
<!--
## 12. Anticipated defense questions

**Q1. The policy trains from ground-truth-scored reward — isn't a "camera" agent that reads ground truth cheating?**
No. The reward is a *training-time* signal that exists only in simulation; it is never an input to the policy. At evaluation there is no reward and no ground truth in the loop — the policy drives from the Lane-Cam image alone and the cage from its CV estimate. Ground truth's only runtime role is the metrics oracle that scores the verdict.

**Q2. Why a CNN over a frame stack rather than a recurrent policy?**
A 4-frame stack supplies the short temporal window (motion/rate cues) at a fraction of the cost and instability of a recurrent net, and keeps the architecture comparable to the well-understood Atari-CNN baseline. The camera obs has no `prev_steer` channel, so the stack is where the steering-rate cue must come from.

**Q3. The cage reads a CV estimator that the same frame can fool — isn't that a single point of failure?**
It is a deliberate, documented common cause (D-43): on a real road the cage cannot have privileged ground truth, so it must perceive from the same sensor. The mitigation is a redundant *response*, not a redundant input — when perception is untrustworthy the cage does not trust a possibly-wrong estimate, it executes the open-loop controlled stop (SR-013/SR-014 → C-05 Trigger 8). The eval-only occlusion/false-lane stressors verify that response.

**Q4. Why keep the verdict on a 1-D action if the 2-D action is "closer to real driving"?**
Because expanding to 2-D in the verdict would invalidate the frozen F-track baseline and the controlled F↔E comparison (both on the 1-D action), force a full E-main retrain, require re-calibrating the cage speed rules, and re-run every GE4 campaign — disproportionate to closing one CL-B SR that resolves cleanly as N/A for a steering-only action (D-49). The 2-D action is instead implemented as posterior work in Gazebo and Isaac, where it makes SR-009's stall test well-posed and exposes speed arbitration under explicitly different caps. Those runs are new baselines and do not reopen G4; SC-PERT-03 still needs its dedicated two-arm 2-D execution before any new SR-009 verdict claim.

**Q5. The source camera changed from the ZED to the Lane Cam — does that invalidate earlier camera evidence?**
No. The Lane Cam (IMX219-160 mirror, 640×360, 90° HFOV, pitch 0.30 rad) is the camera the whole track-'E' verdict (GE4-V2, 297k E-main) trained and evaluated on; the ZED reference in earlier drafts was a documentation carry-over from the platform's stereo suite, not what the policy read. The 0.30 rad pitch and the IMX219 geometry are the values `camera_geometry.py` and the CV estimator are calibrated to (docs/12 §5).

--->

## Version log

- **v0.1 (2026-05-29):** first freeze — F3 state-vector environment, TS-01 cage wiring (D-34), Training Spec §7.2–§7.3.
- **v0.2 (2026-06-01):** post-first-run reconciliation — truncation horizon `max_episode_steps = 500`; spawn perturbation marked implemented.
- **v0.3 (2026-06-09):** added §10 (Track E — camera observation variant, D-41/D-42): image observation, CNN policy; action/reward/cage/episode unchanged.
- **v0.4 (2026-06-09):** §10 revised for **D-43** (supersedes D-42): cage state from a dedicated deterministic CV estimator; common-cause trade-off + H-12/SR-014; oval-first training; ground truth as sim-only reward + oracle.
- **v0.5 (2026-06-10, E2):** §10 reconciled to the implementation — 84×84 grayscale, k=4 fixed; camera obs mode + in-env H-10 DR + CV estimator/supervisor → C-05 Trigger 8 (cage YAML 0.6.0).
- **v0.6 (2026-07-07):** **retargeted to track 'E' as the sole subject.** The camera environment is now the body of the document (§1–§9); the F-track state-vector env is compressed to a baseline note (§10). The **source camera is corrected from the legacy ZED to the dedicated Lane Cam (IMX219-160 mirror, 640×360, 90° HFOV, pitch 0.30 rad, topic `camera/image_raw_lane`)** with the full sensor table (§2.1). The **2-D action (steering + throttle) posterior design (D-50)** is added to §3.2 / §6 (throttle → cage scale `u` → `speed = max_speed·u`, `max_speed = V_MAX`, so the cage speed rules arbitrate for real and SR-009's stall test is well-posed), inert by default (D-49 keeps the verdict 1-D), with the Isaac (`train_isaac_2d.yaml`) and Gazebo (`train_ppo_camera_2d.yaml`) config surfaces, `ent_coef 0.01` (D-52) and `stall_penalty` (D-56), and multi-circuit per-episode sampling (§5.3, D-50/D-51). ED table reworked to a track-'E' basis (new ED-11/12/13). No reward/cage/scenario constant changed.
- **v0.7 (2026-07-20):** separated the three active contracts: frozen GE4 PPO 1-D at 0.20 m/s, posterior Gazebo PPO/SAC 1-D/2-D with the current 0.25 m/s 2-D cap (plus the 0.22 diagnostic probe), and posterior Isaac PPO 2-D at 0.5 m/s. Added the 17–20.07 evidence summary (SAC entropy fix, replay-buffer probe, full-horizon 2-D enforcement, and two-seed SC-PERT subset), D-59/D-60 traceability, and the explicit warning that these runs do not reopen G4 or close SC-PERT-03.
- **v0.8 (2026-07-20):** added the untrained qualification contract as a fourth, explicitly non-evidence surface: bounded 75k SAC-entfix parent at 0.22 m/s, 150k replay covering parent + 50k SC-PERT continuation, embedded checkpoint fingerprint and mandatory hash-bound D-43 preflight. Historical 0.25 evidence remains unchanged.
