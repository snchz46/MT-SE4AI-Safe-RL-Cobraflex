# 14 — Isaac Sim Environment: RL Training Requirements

| Field | Value |
| --- | --- |
| Version | **1.1** |
| Last updated | **2026-07-20** |
| Status | LIVING — Isaac handover contract implemented; post-G4 Gazebo evidence is included only to prevent cross-simulator/action-contract conflation |
| Verdict boundary | GE4 remains the Gazebo PPO 1-D 297k verdict. Gazebo posterior and Isaac evidence do not reopen G4. |

## 0. Contract boundary across evidence families

| Evidence family | Algorithm / action | Speed authority | Role |
| --- | --- | --- | --- |
| Gazebo GE4-V2 | PPO, 1-D steering | fixed 0.20 m/s | **Frozen verdict of record** |
| Gazebo posterior | PPO/SAC, 1-D and 2-D | current 2-D configs cap at **0.25 m/s**; diagnostic eval probe at **0.22 m/s** | Algorithm/action robustness evidence; not GE4 |
| Isaac posterior | PPO, 2-D steering+throttle | **0.5 m/s** full authority | Independent simulator/retrain baseline; not GE4 |

Gazebo and Isaac checkpoints do not transfer. A matched comparison therefore requires
new training/evaluation under explicitly aligned configuration, cage calibration and
simulator conditions; sharing the observation/action API does not make the learned
policies interchangeable.

## 1. ROS2 interface

Sim time on every message; publish `/clock`; consumers run `use_sim_time:=true`.
Exact topic names and frame ids below.

| Direction | Topic | Type | Rate | Notes |
| --- | --- | --- | --- | --- |
| subscribe | `/cmd_vel` | `geometry_msgs/Twist` | ~10 Hz | §1.1 |
| publish | `/odom_truth` | `nav_msgs/Odometry` | ≥50 Hz | ground truth, §1.2 |
| publish | `/camera/image_raw_lane` | `sensor_msgs/Image` | ≥20 Hz | §1.3 |
| publish | `/camera/camera_info` | `sensor_msgs/CameraInfo` | ≥20 Hz | §1.3 (lane cam) |
| optional | `/camera/{left,right}/image_raw` | `sensor_msgs/Image` | ~20 Hz | ZED stereo, not used by RL |
| publish | `/clock` | `rosgraph_msgs/Clock` | every step | sim time |
| publish | `/joint_states` | `sensor_msgs/JointState` | ≥30 Hz | 4 wheel joints |
| publish | `/tf` (+ `/tf_static`) | `tf2_msgs/TFMessage` | ≥30 Hz | §1.4 |
| optional | `/scan`, `/imu` | `LaserScan`, `Imu` | — | not used by RL |

### 1.1 `/cmd_vel` (subscribe)

- `linear.x` = forward speed (m/s), cruise 0.20.
- `angular.z` = yaw rate (rad/s), |ω| ≤ ~0.8.
- Map to 4 wheels: `wheel_radius 0.03725`, `wheel_separation 0.154`, left =
  `front_left + rear_left`, right = `front_right + rear_right`.

> **2-D action (steering + throttle) — IMPLEMENTED for Isaac, D-50 (02.07.2026).** The Gazebo
> **GE4 verdict policy** stays steering-only (`ACT_DIM = 1`, throttle fixed at cruise;
> ED-2/D-49). Separate post-G4 Gazebo PPO/SAC runs now also exercise a config-gated 2-D
> action, currently capped at 0.25 m/s; they are posterior evidence, not a changed verdict
> contract. The Isaac in-process trainer defaults to the **2-D action**
> (`action.type: steer_throttle` in `train_isaac_2d.yaml`): the policy's throttle maps to the
> cage scale `u ∈ [0, 1]` and actuates as `linear.x = max_speed_mps · u` with
> `max_speed_mps = 0.5` (= C-04 `v_max_straight` = ODD-1.V_MAX) and a full stop below the
> 0.05 deadband — **no** `[0.35, 1]` lower clamp on this path, so the cage has speed authority
> to zero. `|linear.x|` on this contract therefore reaches **0.5 m/s** (not just cruise 0.20)
> and the cage speed rules (C-04/C-05-B/C-06) genuinely arbitrate; C-06 bounds commanded
> acceleration to 0.5 m/s² (≤ the **2.5** platform limit, §2.3). SR-009's liveness/stall
> sub-mode (M-P6, SC-PERT-03) is **well-posed** on this action space. The wheel mapping above
> is unchanged. See D-50 (design) and docs/13 (usage); an Isaac-trained 2-D policy is a new
> baseline and does not reopen the Gazebo verdicts.

> **Speed-margin lesson from Gazebo (20.07.2026).** A diagnostic 0.22 m/s eval cap
> removed the zero-margin speed-conflict stop of the SAC-auto 150k checkpoint, while
> the SAC-auto 175k checkpoint still stopped on a D-43 CV heading over-read under both
> 0.25 and 0.22 m/s. The Isaac handover must therefore reserve explicit margin to the
> curvature ceiling *and* validate perception independently; reducing speed authority
> is not a substitute for fixing a confidently wrong lane estimate.

> The lesson is now executable as a **new, untrained contract**:
> `train_sac_camera_2d_tuned_entfix_margin022.yaml` preserves the historical
> entfix recipe but fixes the cap at 0.22 m/s, bounds the parent at 75k and
> keeps parent + 50k continuation inside a 150k replay buffer. It fingerprints
> the action map/horizons into new checkpoints, rejects historical 0.25 checkpoints and declares a
> D-43 preflight mandatory. This Gazebo-specific 0.22 choice does not change
> Isaac's separate 0.5 m/s full-authority handover contract.

> **SC-PERT-03 execution readiness.** The two-arm path is now implemented and
> preregistered: `lambda_stall = 4.0`, 50k one-shot continuation, stall criterion
> `M-P6 > 50.0`, 20 released + 20 stall runs per mode, with parent/derived
> checkpoint, config, VecNormalize, scenario and protocol hashes. The correction
> from `0.50` to `50.0` reconciles the criterion with M-P6's 0–100 percentage
> output. No fine-tune or Gazebo cell has run yet; “ready” means the protocol is
> reproducible, not that SR-009 has new evidence.

### 1.2 `/odom_truth` (publish)

- True simulator pose (not wheel-encoder dead-reckoning).
- `header.stamp` = sim time, ≥50 Hz.
- Frame `odom` → child `base_footprint`; fill `pose.pose` and `twist.twist`.

### 1.3 Camera `/camera/image_raw_lane` (+ `camera_info`)

- 640×360, `rgb8` (or `bgr8`/`mono8`), HFOV 1.5707963 rad (90°), square pixels.
- Frame id `camera_link_optical_lane`, sim-time stamps, ≥20 Hz.
- `camera_info`: `fx = fy ≈ 320`, `cx = 320`, `cy = 180`. (The lane cam's info
  topic is `camera/camera_info` — it took that name when the front ZED became a
  left/right stereo pair publishing `camera/{left,right}/camera_info`.)

### 1.4 `/clock`, `/joint_states`, `/tf`

- `/clock` from sim time; `/joint_states` names the 4 wheel joints.
- `robot_state_publisher` owns the robot tree (URDF + `/joint_states`); Isaac
  publishes only `odom→base_footprint`.

---

## 2. Vehicle & sensors

Robot defined in [`cobraflex_isaac.urdf`](../src/cobraflex/urdf/cobraflex_isaac.urdf).
Drivetrain + sensor parameters declared in (Gazebo-only, reference)
[`robot.gazebo`](../src/cobraflex/urdf/robot.gazebo). 4-wheel skid-steer (no
steering joint).

### 2.1 Source files

| File | Carries |
| --- | --- |
| [`cobraflex_isaac.urdf`](../src/cobraflex/urdf/cobraflex_isaac.urdf) | links, masses, inertia, collisions, mount frames (import this) |
| [`robot.gazebo`](../src/cobraflex/urdf/robot.gazebo) | DiffDrive/odom params, camera/lidar/IMU sensor blocks |
| [`camera_geometry.py`](../src/cobraflex_rl/cobraflex_rl/camera_geometry.py) | lane-cam intrinsics + extrinsics the cage assumes |
| [`lane_keeper_node.py`](../src/cobraflex/cobraflex/lane_keeper_node.py) | real IMX219-160 capture/proc params |

### 2.2 Links, mass, inertia, mounts

**Total mass: 3.5 kg — MEASURED** on the physical car (platform team, *CobraFlex
1:14 Parameters_0813*, 13.08.2026). The URDF budget was rescaled to it on
17.08.2026; it previously summed to **6.59 kg**, i.e. the simulated vehicle was
**1.88× too heavy** through F4, GE4-V2 and `campaign_2d_ppo550k`. Those campaigns
are pinned by git commit and are **not** re-runnable at HEAD.

**Distribution — from the itemised bill of materials (17.08.2026).** The platform
team weighed the three printed body shells and named the three bought-in
components. That is enough to place the mass per link instead of scaling it
uniformly, and it shows the **entire 3.09 kg overshoot lived in one link**: the
`chassis_mass` placeholder. `body_link`, `lidar_link` and the wheels were already
right, which is why the first (uniform) rescale was replaced.

| Link | Now | Composition | Confidence |
| --- | --- | --- | --- |
| `body_link` | **0.8928** | PLA shells **0.2778** (measured: 91.3 g bottom, carries the lane cam / 118.5 g centre, carries the ZED + powerbank + cables / 68.0 g top cover, carries the lidar) + powerbank **0.550** + ZED Mini **0.060** + lane cam ≈0.005 | measured + datasheet |
| `lidar_link` | **0.190** | RPLIDAR A2M4, manufacturer — **unchanged from the original URDF, which had it right** | manufacturer |
| wheel ×4 | **0.1** | **NOT MEASURED.** Left at the original value; the single largest remaining assumption | assumption |
| `base_link` | **2.0172** | remainder: frame + 4 motors + driver board + motor battery + **Jetson Orin Nano DevKit 0.175** + wiring + fasteners | derived total; **Jetson placement confirmed** by the platform team (17.08.2026) — it rides on the chassis, not in the printed body |
| **total** | **3.5000** | | measured |

Two datasheet corrections against the figures quoted with the parts, both verified
in the PDFs the team already holds:

- **Powerbank = 550 g, not 500 g.** XTPower XT-27000DC datasheet, *"Weigth 550g"*.
- **Jetson Orin Nano DevKit = 175 g.** NVIDIA SP-11324-001 v1.3 p33, *"The Developer
  Kit Weighs 0.175 kg"*. It was previously unaccounted for anywhere in the budget.

The ZED Mini's 60 g is folded into `body_link` because
[`zed_macro.urdf.xacro`](../src/cobraflex/urdf/zed_macro.urdf.xacro) declares **no
`<inertial>` element at all** — the ZED is currently a massless link in every URDF.
Fixing that properly means editing a vendor description; folding it into the shell it
is bolted to is equivalent for the dynamics and keeps the vendor file clean.

**What is still unweighed: 2.25 kg, 64 % of the car.** Everything below the body — frame,
motors, wheels, driver board, motor battery — is a single derived remainder. The two
highest-value follow-up measurements are **one wheel** and **the bare rolling chassis**;
together they would close the budget completely.

> **Open conflict with the platform repo — reconcile before either is cited.** The platform
> repo (`Waveshare-Cobra-Flex-ROS2-Autonomous-Car`, `assets/Mathematical Model/parameters.md`
> §2.1, and its URDFs) reaches the same 3.5 kg total but splits it **2.20 / 0.71** for
> chassis / body, against the **2.0172 / 0.8928** above. Its 0.71 kg body is **arithmetically
> impossible** on the itemisation: the weighed PLA (277.8 g) plus the powerbank (550 g by
> datasheet, 500 g as quoted) plus the ZED (62 g) already comes to **890 g — 180 g more than
> the whole link**. The 2.20 / 0.71 split has no stated provenance and predates the weighing,
> so this document keeps the itemised one; the platform repo should adopt it rather than the
> reverse. Second conflict, same section: `parameters.md` places the **Jetson in the body**
> ("upper deck, Jetson, LiPo, wiring"), whereas the platform team confirmed on 17.08.2026 that
> it rides on the **chassis**. Both discrepancies are the platform team's to settle; flagging
> them here so the two repos do not silently diverge. Note the platform document **agrees** on
> the two points that matter most: the ZED is ~62 g and carries no separate inertial, and the
> lidar is 0.19 kg.

**Inertias: still NOT measured.** The tensor the platform team supplied
(`Ixx/Iyy/Izz = 0.008542 / 0.023160 / 0.028702`) is *this repo's own value read
back out of Isaac* — it reproduces `(1/12)·m·(…)` for the URDF chassis box at the
**old 5.0 kg** to nine decimals, so it is circular and was additionally
inconsistent with the 3.5 kg they measured alongside it. The URDF now carries the
same box/cylinder primitives evaluated at the rescaled masses. A real tensor needs
a bifilar-pendulum (or CAD) measurement; treat the current values as modelling
assumptions, not evidence.

**Centre of gravity: frame ambiguous, NOT applied — but the itemisation now
identifies the likely frame.** The supplied CoG is `(x, y, z) = (0.006, −0.004,
0.030) m` in body axes (x fwd, y left, z up). Read in `base_link` it is
**unreachable by this link layout**, and the bill of materials makes that
conclusive: the powerbank (550 g, the single heaviest item) sits in the *centre*
shell and the lidar (190 g) on the *top* cover, so **740 g — 21 % of the car — is
demonstrably in the upper two layers**. With the itemised budget the composite sits
at **0.0566 m** above `base_link` (0.0938 m above ground), nearly **2× the claimed
0.030 m**.

The most likely reading is that the CoG was reported from the **chassis box centre**,
which sits 0.030 m above `base_link` — that would put it at 0.060 m in `base_link`,
**3.4 mm from the itemised model's 0.0566 m**. That is close enough to be a
confirmation rather than a coincidence, but it is a hypothesis: confirm the reference
frame with the platform team before moving any inertial origin. (Read from the ground
it is worse still — 0.030 m would be *below* the wheel axle at 0.03725 m.)

Links and frames can be found in [`cobraflex_isaac.urdf`](../src/cobraflex/urdf/cobraflex_isaac.urdf).

### 2.3 Drivetrain

| Parameter | Value | Provenance |
| --- | --- | --- |
| wheel_radius | 0.03725 m | **measured** — matches the URDF exactly |
| wheel_separation | 0.154 m | sim value; **measured track is 0.153 m** (0.65 % high, see note) |
| wheelbase (measured) | **0.154 m** | **measured**. The URDF places the wheels at `wheel_off_x = ±0.060` → **0.120 m**, 22 % short. See note. |
| left wheels | front_left + rear_left | |
| right wheels | front_right + rear_right | |
| max linear accel | **±2.5 m/s²** | platform spec — **corrected 17.08.2026 from 0.53 / −10**, see note |
| max angular accel | **3.2 rad/s²** | platform spec (new) |
| max wheel torque | **20 N·m** | platform spec (new) |
| cruise speed | 0.20 m/s | |
| max linear velocity | 0.53 m/s | firmware clamp, ~0.99 tracking measured to 0.53 |
| max angular velocity | 6.0 rad/s | firmware clamp — **not achievable**, see note |
| **plant yaw gain (real)** | **0.4954 × commanded** | **measured** (§2.3a) |

> **Note — the 0.53 m/s² "measured acceleration" was a unit error, now refuted.** `robot.gazebo`
> carried `max_linear_acceleration 0.53` / `min_linear_acceleration −10`, and this spec, docs/09,
> docs/13, `cage_bridge.py` and D-50 all cited 0.53 m/s² as *the platform's measured max linear
> acceleration*. The platform repo's own parameter document diagnoses it: **0.53 is this chassis's
> maximum velocity in m/s, copied into an acceleration field**, and −10 was an arbitrary 20×
> braking limit. The platform figures are **±2.5 m/s²** linear and **3.2 rad/s²** angular. All four
> citations were corrected; **every conclusion survives with a larger margin** — C-06 bounds
> commanded acceleration to 0.5 m/s² on the Isaac contract and 0.22 m/s² at the 0.22 m/s trunk cap,
> so the bound went from "6 % of headroom" to "5× of headroom". Caveat on the replacement: the
> 2.5 m/s² has **no stated measurement provenance** either, and the 0813 bench sheet independently
> reports "≈0.5–0.53 m/s²" — i.e. the same copied number. Treat 0.53 as refuted and 2.5 as the
> platform spec; **M-3 (deceleration) is informed, not closed.**

> **Note — the URDF wheelbase is 0.120 m, the real one is 0.154 m (22 % short).** Three different
> values are in circulation: the URDF's `wheel_off_x = ±0.060` → **0.120 m**; the platform repo's
> Mathematical Model → **0.1356 m** "(calculated)"; the physical measurement → **0.154 m**. Gazebo's
> DiffDrive is unaffected — it is kinematic and consumes only `wheel_separation` — which is why this
> never surfaced. **Isaac is affected, and in the direction that matters:** PhysX resolves real
> contacts, and a 22 %-short wheelbase geometrically *under-models the very scrub* that produces the
> measured 0.4954 yaw deficit. Fixing it is therefore part of the Isaac yaw calibration (docs/13),
> not a cosmetic change. Left as-is pending that work, because moving the wheels also perturbs the
> contact geometry of the frozen Gazebo plant.

> **Note — `wheel_separation` 0.154 is the wheelbase, not the track.** The measured
> track is 0.153 m and the wheelbase is 0.154 m; the plugin/`isaac_scene` constant
> was set from the wrong one. It is **deliberately left at 0.154**: the error is
> 0.65 %, three orders of magnitude below the yaw error in §2.3a, and changing it
> would perturb the plant that produced every frozen verdict for no physical gain.
> Recorded here so the provenance is not lost.

> **Note — the 6.0 rad/s ceiling is not reachable.** Ideal diff-drive gives
> `2·v_max/T = 2·0.53/0.153 = 6.93 rad/s`; with the measured 0.4954 scrub factor the
> real ceiling is ≈ **3.4 rad/s**. 6.0 is the serial driver's clamp constant
> (docs/17 §2 item 3), not a measurement. The calibration campaign only reached
> 0.396 rad/s achieved.

### 2.3a Yaw-rate transfer — the measured sim-to-real gap

In-place rotation, 10 s per point, physical car (same source):

| Commanded | Expected | Measured | Achieved | Gain |
| --- | --- | --- | --- | --- |
| 0.20 rad/s | 114.6° | 55.6° | 0.097 rad/s | 0.485 |
| 0.40 rad/s | 229.2° | 114.5° | 0.200 rad/s | 0.500 |
| 0.53 rad/s | 303.7° | 150.4° | 0.263 rad/s | 0.495 |
| 0.80 rad/s | 458.4° | 226.9° | 0.396 rad/s | 0.495 |

Least squares through the origin: **k = 0.4954**, no offset. Straight-line motion
over the same 10 s tracks at ~0.99 (1.998/2.000, 3.964/4.000, 5.207/5.300), so the
deficit is **purely rotational** — the four fixed wheels scrub. Implied effective
track `T/k = 0.309 m`, ≈ 2.02× the physical 0.153 m.

> **The single-gain model is superseded WHILE MOVING (M-7 §5, 18.08.2026; docs/17 §6d).**
> The table above is an **in-place** bench rotation. Measured on the lane circuit *while
> driving forward at 0.20 m/s*, the achieved/commanded ratio is **not constant**: it falls
> **0.482 → 0.436 → 0.341** as the command grows 0.2 → 0.4 → 0.8 rad/s. The plant is
> **compressive**, so no constant `k` fits it — a gain calibrated at moderate demand
> under-delivers exactly where C-01/C-02 correct. 0.4954 brackets the moving figures and
> remains the right deployment default (`steering_to_yaw_rate_gain = 1.615`), so nothing
> below changes; but read every `0.4954`-derived number here as **an optimistic bound at high
> demand**, not as an exact transfer. Two further caveats: scrub is **surface-dependent** (the
> same in-place test on the lane-circuit floor gives 0.150, far below the bench 0.4954), and
> **where the compression ends — soft compression or hard saturation — is unmeasured**, so the
> `R_min` the platform can actually achieve is unknown. The bench discriminator is written
> (`tools/measure_yaw_authority.py`) and was not run before Phase 5 closed; it is future-work
> item T2 of Ch. 12.

This brackets the two simulators from opposite sides, and it is the single most
consequential number this handover carries:

| Plant | Yaw delivered / commanded |
| --- | --- |
| Gazebo DiffDrive (all frozen verdicts) | ≈ 1.00 — **2× optimistic** |
| **Real CobraFlex 1:14** | **0.4954** |
| Isaac skid-steer @ `friction 0.05` (D-54) | ≈ 0.18 — **2.75× pessimistic** |

Consequences:

- **Isaac now has a calibration target.** D-54 raised `cage.yaw_gain` to 2.4 to
  paper over a plant that was too slippery. The physically correct fix is to tune
  `WHEEL_FRICTION`/`GROUND_FRICTION` until the `--turn` test returns **≈0.495**, then
  put `yaw_gain` back to the Gazebo 0.8. Until that is done, Isaac's yaw is wrong in
  a *known direction and magnitude*, which is strictly better than before.
- **Hardware deployment** compensates at the command side:
  `steering_to_yaw_rate_gain = 0.8 / 0.4954 = 1.615`
  ([`deploy_cobraflex.launch.py`](../src/cobraflex_rl/launch/deploy_cobraflex.launch.py)).
- **The cage's corrective authority halves in physical units.** At `steer = 1.0`:
  0.800 rad/s in Gazebo → 0.396 rad/s real; minimum turn radius at 0.22 m/s goes
  0.275 m → 0.555 m; C-06's `delta_max_steering_per_cycle = 0.15` bounds yaw
  acceleration at 2.40 rad/s² in sim → 1.19 rad/s² real (20 Hz). The tightest
  `complex_b` curve (driven `R_min ≈ 0.998 m`) needs 0.220 rad/s at 0.22 m/s, i.e.
  **27.6 % of full steer in sim but 55.6 % on hardware** — still feasible, with the
  headroom cut from 3.6× to 1.8×. This quantifies the **T2** transfer risk.
- **Caveat: scrub is surface-dependent.** 0.4954 was measured on the platform team's
  bench surface. Re-run the in-place test on the lane circuit before trusting it.

### 2.4 Sensor suite

Only the Lane Cam is on the RL path; the rest are optional.

| Sensor | Frame | Topic(s) | Resolution / FOV / range | Rate | Noise | RL |
| --- | --- | --- | --- | --- | --- | --- |
| Lane Cam (IMX219-160) | `camera_link_optical_lane` | `/camera/image_raw_lane`, `/camera/camera_info` | 640×360, HFOV 1.5707963 rad (90°), `rgb8`, clip 0.1–15 m | 20 Hz | gaussian σ 0.007 | yes |
| ZED Mini left | `zedm_left_camera_frame_optical` | `/camera/left/image_raw`, `/camera/left/camera_info` | 640×480, HFOV 1.3962634 rad (80°), `rgb8`, clip 0.1–15 m | 20 Hz | gaussian σ 0.007 | no |
| ZED Mini right | `zedm_right_camera_frame_optical` | `/camera/right/image_raw`, `/camera/right/camera_info` | 640×480, HFOV 1.3962634 rad (80°), `rgb8`, clip 0.1–15 m | 20 Hz | gaussian σ 0.007 | no |
| RPLiDAR A2M4 | `lidar_link` | `/scan` | 360°, 4000 samples, range 0.015–8.0 m | 10 Hz | gaussian σ 0.01 m | no |
| IMU | `imu_link` | `/imu` | 6-DoF | 200 Hz | — | no |

Real Lane Cam: Jetson CSI, capture 1280×720 @ 60 fps, processed 640×360, HFOV 90°.
Sim simulates the processed 640×360 @ 20 Hz stream only.

---

## 3. In-process RL interface contract

The Isaac trainer reuses `GazeboLaneEnv` through the duck-typed
`IsaacSimInterface`; it does not recreate reward, cage or episode logic in an
Isaac-specific environment. The backend must provide the same operations the env
expects:

| Operation | Isaac responsibility |
| --- | --- |
| `set_vehicle_pose` | Teleport to the requested reset pose and zero articulation velocities |
| `send_action` | Convert the safe `(steering, throttle)` command to four-wheel differential-drive actuation using the §2.3 geometry |
| `step_ros` | Advance deterministic physics substeps for one `control_dt` and update pose/twist state |
| `get_pose` / velocity access | Return simulator truth used only for reward, termination and metrics |
| `get_camera_frame` | Return the Lane-Cam render product at 640×360 for the shared camera/CV pipeline |

The action contract comes from the archived training YAML and must be copied into
`metadata.json`. For Isaac 2-D this is `action.type: steer_throttle`,
`max_speed_mps: 0.5` and `throttle_deadband: 0.05`; absence of an `action:` block
means the legacy 1-D steering contract. The cage consumes the same normalised throttle
scale `u ∈ [0,1]`, and the reward extension is limited to `throttle_delta` plus
`stall_penalty` (docs/10). The current Isaac trainer is PPO; the Gazebo SAC evidence
does **not** establish an Isaac SAC baseline.

Each Isaac run must archive the git commit, checkpoint hash, cage YAML hash, train-config
path/hash, seed, action block, circuit paths/hashes and simulator/platform label. A
successful host smoke or nominal eval validates this interface only; it is not GE4 and
must not be combined with Gazebo campaign cells in one verdict roll-up.

---

## 4. Version log

- **v1.0 (2026-07-02):** initial ROS2, vehicle, sensor and Isaac 2-D handover contract.
- **v1.1 (2026-07-20):** separates frozen Gazebo GE4 PPO 1-D, posterior Gazebo
  PPO/SAC 1-D/2-D and posterior Isaac PPO 2-D; records the current 0.25 m/s Gazebo
  cap, the 0.22 m/s diagnostic margin probe, checkpoint non-transferability and the
  in-process backend/provenance contract. No Isaac parameter or G4 verdict changed.
