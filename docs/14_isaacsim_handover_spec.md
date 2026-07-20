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
> acceleration to 0.5 m/s² (≤ the 0.53 platform limit, §2.3). SR-009's liveness/stall
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

Total mass to be measured from real car.

Inertias to be measured from real car.

Links and frames can be found in [`cobraflex_isaac.urdf`](../src/cobraflex/urdf/cobraflex_isaac.urdf)

### 2.3 Drivetrain

| Parameter | Value |
| --- | --- |
| wheel_radius | 0.03725 m |
| wheel_separation | 0.154 m |
| left wheels | front_left + rear_left |
| right wheels | front_right + rear_right |
| max linear accel | 0.53 m/s² |
| min linear accel | −10 m/s² |
| cruise speed | 0.20 m/s |

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
