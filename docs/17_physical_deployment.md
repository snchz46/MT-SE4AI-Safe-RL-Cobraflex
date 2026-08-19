# 17 · Physical deployment (Phase 5) — bring-up plan for the real CobraFlex

**Status: RUN ON THE CAR — bench only (2026-08-05 and 2026-08-17, `mode:=monitoring`,
wheels off the ground, no track). The car has still NOT been driven.** Both §2
`[VERIFY]` items are now measured (M-6, 17.08.2026) and the HFOV one came back
**wrong — 77.89°, not 90°**; its propagated `ey` under-read was CONFIRMED on
18.08.2026 by hands-off tape measurement (M-7 §4/D-71: 0.68–0.83 × true − 10 mm), and
the heading channel is separately noisy; the resulting decision is open and nothing has been
changed in code. The 2026-08-17 session (§6c) verified the perception-loss
fail-safe and the actuation sign convention on hardware.** This document is the bring-up checklist for taking
the verdict-bearing RL camera policy + safety cage from Gazebo to the physical
1:14 CobraFlex. Every sim-side component it reuses is validated; the hardware I/O
and the items flagged **[VERIFY]** are not, by construction — they need the car.

> **2026-08-05 bench review — five defects found and fixed, all silent.** The
> chain as scaffolded would have started, logged, and driven *wrongly* rather than
> failed. See §6b for the full list and the evidence. In short: the throttle
> reached the cage in the wrong domain; the speed map was the frozen 1-D one; the
> policy and cage ran at the camera's 20 Hz instead of the trained 10 Hz; one
> `msg.data = ...tobytes()` assignment capped the camera at ~8 Hz; and a camera
> that had failed to acquire the sensor still reported itself ready. After the
> fixes the bench chain holds **10 Hz** end to end with zero watchdog stops, on
> the real 550k checkpoint.

## 1. What changes from simulation, and what does not

The distributed node chain is the same as the F2 physical demo pattern, now
camera-driven and 2-D. Only the **image source**, the **actuation sink**, and the
**RL inference node** differ from sim; the safety-relevant logic is bit-identical.

| Stage | Sim (Gazebo) | Physical | Reused? |
| --- | --- | --- | --- |
| Image | `Lane Cam` gz sensor → `camera/image_raw_lane` | **`csi_camera_node`** (NEW) → same topic | geometry **identical** |
| **Policy inference** | in-process `GazeboLaneEnv.step` | **`rl_policy_node`** (NEW) | preprocessing + model |
| Cage perception (D-43) | `CagePerceptionSupervisor` in-process | `cv_lane_estimator_node` | **identical** |
| Cage rules (C-01..C-06) | `SafetyCageNode` in-process | `cage_ros_node` | **identical** |
| Actuation | `RosGazeboInterface` → sim `/cmd_vel` | `vehicle_control_node` → `cobraflex_ros_driver` | node reused + platform driver |
| Evidence | `cage_status.csv` | `cage_logger_node` → CSV | **identical** |

Two nodes are new, both in `src/cobraflex_rl/cobraflex_rl/`, both with host-side
unit tests for their pure logic:

* **`rl_policy_node`** — reuses `camera_pipeline.decode_image` + `to_observation`
  + a k=4 frame stack, the exact preprocessing the CNN trained on, so the policy
  sees the same observation on hardware (`policy/tests/test_rl_policy_node.py`).
* **`csi_camera_node`** — publishes the Jetson CSI lane camera on
  `camera/image_raw_lane` (`policy/tests/test_csi_camera_node.py`). See §1b.

### 1b. The lane camera: sim mirrors hardware, not the other way round

The camera the policy trained on is **the Jetson CSI cam**. The Gazebo `Lane Cam`
sensor (`cobraflex/urdf/robot.gazebo`) was explicitly built to mirror the hardware
pipeline — its own comment says *"proc frames 640×360, effective hfov 90 deg, timer
20 Hz; capture is 1280×720@60 but only the processed stream matters"* — and those
numbers are `lane_keeper_node`'s parameter defaults. So reproducing the hardware
path **is** reproducing the training distribution. Every number has one authority
and all three agree:

> **⚠ Falsified for HFOV, 17.08.2026 (M-6).** The three *code* locations below
> still agree with each other, but they no longer agree with the **camera**: the
> measured effective HFOV is **77.89°**, not 90° (`fx` 395.93 px, not 320). The
> agreement was circular — the sim mirrored a hardware *parameter default* that
> had never been measured. So for HFOV, reproducing this path is **not**
> reproducing the training distribution: real frames are ~24 % narrower in field
> of view than every frame the 550k policy trained on. Every other row of the
> table is unaffected. See §2 item 1.

| Quantity | Value | Authority |
| --- | --- | --- |
| Native frame | **640×360** | `Lane Cam <image>` · `camera_geometry.DEFAULT_WIDTH_PX/HEIGHT_PX` · `lane_keeper_node.proc_width/proc_height` |
| HFOV | **90°** (1.5707963 rad) — *assumed; the real camera measures 77.89°, M-6* | `Lane Cam <horizontal_fov>` · `CameraModel.hfov_rad` · `lane_keeper_node.camera_hfov_deg` |
| Rate | **20 Hz** | `Lane Cam <update_rate>` · `lane_keeper_node.timer_hz` |
| Capture | **1280×720@60**, `INTER_AREA` → 640×360 | `lane_keeper_node.capture_*` + `_process_frame` |
| Optical frame | `camera_link_optical_lane` | `Lane Cam <optical_frame_id>` |
| Mount | pitch 0.30 rad, height 0.07725 m | URDF `camera_joint_lane` → `camera_geometry` |
| Observation | 84×84 grey, `INTER_AREA`, k=4 | `camera_pipeline.OBS_*` |

`csi_camera_node` reuses `lane_keeper_node`'s GStreamer pipeline **byte-identically**
(asserted in the unit test) and its 640×360 `INTER_AREA` downsample, and derives the
published `CameraInfo` from the same `CameraModel` the cage's IPM uses, so the
advertised intrinsics cannot drift from the projection actually applied. It defaults
its output size *from* `camera_geometry`, because **640×360 is a hard contract**:
`cv_lane_estimator` falls back to `CameraModel()` and indexes its scan bands by
`camera.height_px`, so any other size silently mis-projects every `ey`/`epsi` the
cage acts on. It publishes `bgr8` where the sim sensor emitted `R8G8B8` — not a
difference, since `decode_image` normalises both to the same BGR array.

It is a separate node because the classical controller opens the CSI device
*inside* `lane_keeper_node`, which also publishes `/cmd_vel`. **Never run the two
at once**: they contend for the camera device *and* for actuation.

**Fail-safe chain (a dead camera stops the car).** No frames → `rl_policy_node`
publishes no `/raw_action` → `/raw_action` is `cage_ros_node`'s cycle trigger, so no
`/safe_action` → `vehicle_control_node`'s `safe_action_timeout_s` (0.5 s) publishes a
zero Twist → the driver's 50 ms keep-alive re-sends zeros. The e-stop is not needed
for this path.

**The ZED Mini is not in the loop.** It is a human monitoring view only; nothing in
the RL chain reads it. To see exactly what the policy sees, point rviz at
`camera/image_raw_lane`. Launch Layer 2 separately if you want the ZED view as well.

## 2. Hardware prerequisites (do these first)

1. **[MEASURED 17.08.2026 — the 90° HFOV is WRONG. Effective HFOV is 77.89°.]**
   This was the load-bearing unverified number of the whole sim-to-real transfer:
   a *parameter default* in `lane_keeper_node` (`camera_hfov_deg` 90.0) for an
   IMX219-**160** wide-angle lens, which the Gazebo sensor mirrored — so sim and
   hardware were wrong in the same way and no sim result could expose it.
   Checkerboard calibration on the car (rms 0.238 px, all conditioning
   checks passed over 58 views covering 16/16 image regions) measures
   **`fx` = `fy` = 395.93 px, not 320** — see
   [M-6](../experiments/calibration/M6_camera_hfov.md) and
   `experiments/calibration/M6_results.json`. Cause is coherent with the
   hardware: the "160°" is a *diagonal* figure for the full 3280×2464 sensor, but
   `csi_camera_node` captures the **1280×720 crop mode**, which throws field of
   view away rather than downscaling.
   **Consequences, none yet actioned in code (see the open decision in M-6):**
   * every `ey` the IPM reports is inflated by 395.93/320 = **1.237**, so C-01's
     a raw single-point `ey` is over-read. **But that is not the number that
     reaches C-01** — see the next bullet, which supersedes it. **The sim results
     stand** either way: Gazebo's sensor really was 90° and the IPM really assumed
     90°, so in sim C-01 fired at exactly 0.16 m. Only the *transfer* is broken.
   * **The cage fires LATE — CONFIRMED 18.08.2026 by hands-off measurement
     against a tape (M-7 §4, D-71).** The `ey` transfer, with the car parked on
     the ground at tape-measured offsets over ±100 mm, is
     **reported = 0.68…0.83 × true − 10 mm**, robust to every filtering of the 15
     points (r up to 0.99). M-6 predicted 0.72 and the measurement brackets it.
     **C-01's 160 mm therefore fires at a true 207–241 mm** and C-05's 120 mm at a
     true 172–212 mm, against a road half-width of 255 mm — 14–48 mm of margin
     where 95 mm was designed.
     *A retraction of this bullet, made earlier the same day on the strength of a
     lane-width measurement (252.9 mm against a ruler 250), is itself withdrawn:
     `lane_width` is a **difference** straddling the optical axis while `ey` is an
     **absolute** off-axis position, and the unmodelled barrel distortion
     (`k1 = −0.339`) compresses the second while preserving the first. At a true
     offset of 0 the width reads 0.975 of the ruler while `ey` reads −9.8 mm.*
   * **Second defect, independent of the gain: repeatability.** Re-placing the car
     at the same tape offset elsewhere along the track moves the reading by a mean
     of 13.2 mm and up to 29.4 mm (tape precision ~2 mm). The reading is not a
     function of lateral offset alone, and no scale correction removes this.
   * **Where the error does bite is the HEADING** — as **noise, not bias**. The
     slope is fitted across the scan band out to 1 m, where `X` is compressed and
     `Y` is not, so the cancellation above does not apply. Over the same 1521
     circuit frames, `joint_pair_quadratic`/1.6 — the estimator the 550k trunk was
     trained and scored with — is **unbiased (mean +0.04°) but has sd 14.29° and
     puts 7.8 % of frames past C-02's 25° limit**, against `near_secant`/1.0's
     sd 5.31° and 0.8 %; `numpy` reports `RankWarning: Polyfit may be poorly
     conditioned` on those fits. **This is the operative consequence of M-6 — not
     a gain on `ey`.** A stationary measurement at one pose showed +17.28° of
     apparent bias; the circuit says that was local, and a `heading_bias_rad`
     (D-57) correction is therefore **withdrawn** — there is no general bias to
     subtract. Undecided: `near_secant`/1.0 is markedly cleaner but rescales the
     observation the trunk trained with.
   * `cx` = 305.39 px (14.61 px off centre) adds a **lateral bias**, not just a
     gain, and measured barrel distortion is k1 = −0.339 against the IPM's
     assumed zero. Combining all of it with the measured pitch, the running IPM
     misplaces real lane points by **−57 mm to +167 mm** laterally — the worst
     case exceeding C-01's whole 160 mm `d_max_m`. See M-6 for the per-point table.
   * **Correcting `fx` alone would make the mean error worse** (49.4 → 52.2 mm):
     the scale error and the principal-point offset were partially cancelling.
     And with every scalar corrected, a pinhole IPM still leaves ~44 mm — closing
     it requires the estimator to **undistort**, not just to be re-parameterised.
   * the 550k trunk policy trained on 90° Gazebo frames but will see 77.89° ones,
     i.e. images ~24 % "zoomed in" relative to its entire training distribution —
     an observation-space domain shift no IPM correction touches.
   Note the published `CameraInfo` is deliberately the *ideal pinhole the cage
   assumes* — no distortion terms — because publishing measured intrinsics would
   contradict the IPM; reconcile both, do not just add distortion coefficients.
2. **[VERIFY] Camera extrinsics.** The IPM in `camera_geometry.py` is calibrated
   for pitch 0.30 rad, height 0.077 m (the URDF mount). Match the real mount to
   these, OR re-run the D-57 workflow to set `cage.perception_heading_bias_rad`
   for the real camera's near-field-slope offset. A wrong pitch corrupts the CV
   `ey`/`epsi` the cage acts on. **[MEASURED 17.08.2026 — the mount is
   essentially right.]** M-6 Part B fits the pitch at **0.3113 rad (17.84°)**
   against the URDF's 0.3000 rad — **+0.65°**, inside the 1° "confirmed" band, so
   **no physical adjustment of the mount is needed** and the D-57 heading-bias
   workflow is not called for on this account. The fit recovered the camera height
   as **77.9 mm** without being told it, against 77 mm measured by hand — a 0.9 mm
   agreement that independently validates `fx`, the pitch and the mark extraction
   at once. Note the intrinsic `cy` offset is worth a further +1.91° of *equivalent*
   pitch in the row→distance mapping, but it is **not** a mount error and the two
   must not be added: most of that error lives in the principal point.
3. **Chassis driver — reused, no work needed.** The platform's actuation
   interface is `cobraflex_ros_driver` (`cobraflex_driver.launch.xml`), launched
   as part of **Layer 1** (`cobraflex_bringup.launch.xml`, see §2b). It consumes
   `/cmd_vel` (`geometry_msgs/Twist`: `linear.x` m/s, `angular.z` yaw rate) and
   emits `{"T":13,"X":vx,"Z":wz}` on the serial port, clamped to ±0.53 m/s /
   ±6.0 rad/s — so the deployed 0.22 m/s contract is never clamped. The RL policy
   therefore actuates through *exactly* the same interface as the PD and CV
   controllers. It also publishes `/cobraflex/battery`, `/cobraflex/wheel_speeds`
   and `/cobraflex/feedback` — independent evidence channels, currently unused by
   the cage.
4. **[MEASURED 13.08.2026 — `steering_to_yaw_rate_gain` raised 0.8 → 1.615].**
   `vehicle_control_node` publishes `/cmd_vel.angular.z = safe_action.angular.z ×
   gain`; 0.8 was calibrated against the **Gazebo DiffDrive plugin's** reading of
   `angular.z`, whose plant tracks commanded yaw ~1:1. The platform team's bench
   calibration (*CobraFlex 1:14 Parameters_0813*; in-place rotation, 10 s per
   point, 0.20/0.40/0.53/0.80 rad/s) measured the real chassis delivering only
   **0.4954 × commanded yaw** — per-point gains 0.485/0.500/0.495/0.495, linear,
   no offset — while straight-line motion tracks at ~0.99. The deficit is purely
   rotational: the four fixed wheels scrub, giving an effective track of 0.309 m
   against a physical 0.153 m. The **deploy launch default is now
   `0.8 / 0.4954 = 1.615`**, so the *achieved* yaw on hardware matches the
   0.8 rad/s the trunk policy and the cage were verified against. Note the
   chassis is **skid-steer, not Ackermann** (four fixed wheels, no steering
   angle — docs/08 §11), which is *why* the deficit exists. Two things still
   gate this:
   - **Scrub is surface-dependent.** 0.4954 came from the platform team's bench
     surface, not the lane circuit. Re-run the in-place rotation test on the real
     track before a full run, and re-derive the gain if it moves.
   - **This turns the car ~2× harder than the previous default.** Bring it up at
     0.22 m/s with the e-stop in hand (item 5) and confirm C-02/C-03 do not
     chatter before trusting their margins. `steering_to_yaw_rate_gain:=0.8`
     restores the old behaviour.

   Consequence for the cage, now quantified — this is the **T2** transfer risk:
   at `steer = 1.0` the achievable yaw is 0.396 rad/s real vs 0.800 rad/s in
   Gazebo; the minimum turn radius at 0.22 m/s goes 0.275 m → 0.555 m; and C-06's
   `delta_max_steering_per_cycle = 0.15` bounds yaw acceleration at 2.40 rad/s² in
   sim but **1.19 rad/s² on hardware** (20 Hz). The tightest `complex_b` curve
   (driven `R_min ≈ 0.998 m`) needs 0.220 rad/s at 0.22 m/s = 27.6 % of full steer
   in sim, **55.6 % on hardware**. Feasible, but the headroom drops 3.6× → 1.8×.
5. **Hardware e-stop** wired to `/external_stop` (`std_msgs/Bool`). **Mandatory
   before any powered run** — it drives C-05 Trigger 6 (external stop). It is
   also the *only* mitigation for one gap: the driver has no `/cmd_vel` watchdog —
   `_resend_last_cmd` re-sends the last command every 50 ms as a firmware
   keep-alive. `vehicle_control_node` covers the cage dying
   (`safe_action_timeout_s` → zero Twist), but if `vehicle_control_node` itself
   dies the car keeps driving on its last command.
6. **Inference stack — installed and verified 2026-08-04, no action needed.**
   `torch` 2.13.0+cpu, `stable-baselines3` 2.9.0, `gymnasium` 1.3.0 and
   `numpy` 1.26.4 live in `~/rl_deploy_venv` (a `--system-site-packages`
   virtualenv), reached via `scripts/setup_deploy_env.sh`. Notes for whoever
   rebuilds this:
   * **CPU, not CUDA.** `rl_policy_node`'s `device` parameter is `"cpu"` by
     design, so the stock PyPI `manylinux_2_28_aarch64` wheel is the right one —
     the NVIDIA JetPack build is not required. Measured on this Jetson's CPU:
     the full cycle (`to_observation` → k=4 stack → `predict` → Twist mapping)
     is **17.6 ms ≈ 57 Hz**, against a 10 Hz control loop and a 20 Hz camera. That
     retires the "compute cadence" item in §5 for the inference half; the camera
     driver remains the untested part.
   * **Do not activate the venv.** The colcon-installed node scripts have a
     `#!/usr/bin/python3` shebang, so activation is silently ignored. `PYTHONPATH`
     is the mechanism that works.
   * **`LD_PRELOAD` of torch's bundled OpenBLAS is mandatory**, not a nicety. The
     system `libopenblas.so.0` (Ubuntu 22.04) lacks `sbgemm_`; torch's copy exports
     it; the first one loaded wins process-wide, and system OpenCV loads the system
     one — so `import cv2` before `import torch`, which is exactly what the node
     chain does, kills `import torch` with `undefined symbol: sbgemm_`. Preloading
     makes it order-independent. `LD_LIBRARY_PATH` is **not** a substitute: it also
     overrides `libgomp` and breaks numpy's own sanity check.
   * numpy 1.26.4 shadows the system's 1.21.5 inside this environment. Verified
     that `rclpy`, `cv_bridge` and `cv2` 4.5.4 all still import and run under it
     (C-extensions built against numpy 1.21 are forward-compatible within the 1.x
     ABI). The system Python is left untouched, so nothing outside the RL chain
     changes.
7. **The deployed checkpoint — ON THE CAR since 2026-08-05, hash verified.** It sits
   at the repo root as `ppo_gz2d_cap022_1M_2024_550000_steps.zip` (20 MB); `.gitignore`
   gained `/*_steps.zip` so it cannot be committed (the 25.07 rule only caught the
   `cobraflex_*` naming). Verified on arrival: sha256 exact, SB3 loads it,
   `num_timesteps` 550000, `ActorCriticCnnPolicy`, obs `Box(0,255,(4,84,84),uint8)`,
   action `Box(-1,1,(2,),float32)` — the deployed contract — and `predict()` is
   deterministic at **9.2 ms** median (p95 14.2 ms) against the 100 ms budget at
   10 Hz. SB3 warns `Could not deserialize object lr_schedule` on load: that is the
   training host's pickled schedule lambda, unused for inference; the weights load
   from `policy.pth` separately and the action output is deterministic and in range.

   | | |
   | --- | --- |
   | File | `ppo_gz2d_cap022_1M_2024_550000_steps.zip` |
   | Source | `policy/checkpoints/` on the training host |
   | SHA-256 | `0d4492461b24efce58fed4c53e3ada58385ffc7d6b0746863de14a6892a25867` |
   | Algorithm | `ppo` · `max_speed_mps` 0.22 · `throttle_deadband` 0.05 |
   | Provenance | `experiments/sim/runs/rl_ppo2d_cap022_550000_nom_4k4/metadata.json` |

   The hash is the only link between the car and the verdict of record — re-verify it
   after any copy. The observation contract the node reconstructs (84×84 grey, k=4) was
   checked against `train_ppo_camera_2d_cap022_1M.yaml` and matches.
8. **Odometry — Layer 2 must be running, or the cage loses half its rules.** The
   cage's `State.speed` comes from `cv_lane_estimator_node`'s odometry
   subscription. On this platform **nothing publishes `/odom`** (that is a Gazebo
   topic): `cobraflex_ros_driver` emits `/cobraflex/wheel_speeds` (a
   `geometry_msgs/Twist` carrying the raw `odl`/`odr` encoder fields, not a
   `nav_msgs/Odometry`), and the odometry proper is the ekf's `/odometry/filtered`,
   fused from the ZED's visual odometry in `cobraflex_sensors.launch.xml`. With no
   speed the chain still runs and still logs — but C-03 sees every TTLC as infinite
   (speed under `v_min_estimate_mps` 0.05), C-04 never finds an excess over
   `v_max_curve`, and C-05's high-energy variant (`v_warning_mps` 0.4) can never
   arm. Nothing errors. The launch now defaults `odom_topic:=/odometry/filtered`
   and the node logs an error if frames arrive but odometry does not.

## 2b. The platform's bring-up layering (what the RL launch must match)

The CobraFlex package is layered, and every controller follows the same pattern:

| Layer | Launch | Starts |
| --- | --- | --- |
| 1 — base | `cobraflex_bringup.launch.xml` | `cobraflex_description.launch.xml` (robot_state_publisher on **`my_robot_basic.urdf`**, joint_state_publisher, rviz `bot.rviz`; `use_sim_time:=false`) **+** `cobraflex_driver.launch.xml` (`cobraflex_ros_driver`) |
| 2 — sensors | `cobraflex_sensors.launch.xml` | SLLIDAR A2M8 (`frame_id:=lidar_link`) + ZED Mini (`camera_model:=zedm`, `publish_tf:=false` — the ekf owns `odom -> base_footprint`) + **the Jetson CSI lane camera** (`csi_camera_node`) + the **ekf** (`ekf_hw.yaml` → `/odometry/filtered`) |
| 3 — controller | `cobraflex_lane_keeper.launch.py` | `lane_keeper_node` + rviz `lane_keeper.rviz` — **no** Layer 1/2 include; it owns the CSI camera itself |
| 3 — controller | `cobraflex_automatic.launch.xml` | Layer 2 + `lidar_avoidance_node` |
| 3 — controller | **`deploy_cobraflex.launch.py`** | the RL chain (this document); `camera:=false` by default — Layer 2 publishes the frames |

The two Layer-3 lane controllers are **mutually exclusive**: both need the same CSI
device and both end up commanding `/cmd_vel`. Run `cobraflex_lane_keeper.launch.py`
only with Layer 2's `use_lane_camera:=false`, or without Layer 2 at all.

> **URDF correction (2026-08-05).** This table previously named
> `my_robot_gazebo_mesh.urdf` as Layer 1's description. It is not, and must not be:
> `cobraflex_description.launch.xml` defaults to `my_robot_basic.urdf`. The mesh
> variant is the sim description.
>
> **Frame-graph restructure (2026-08-06).** `my_robot_basic.urdf` used to be rooted
> at `zed_camera_link`, via a `footprint_joint` that hung `base_footprint` off the
> camera. It is now rooted at **`base_footprint`**, with the ZED attached by
> `zed_mount_joint` (`body_link` → `zed_camera_link`, offset `0.11 0 0.02`), and
> `ekf_hw.yaml` names `base_link_frame: base_footprint` to match. The constraint is
> hard: the ekf publishes `odom -> base_link_frame` while robot_state_publisher
> publishes the URDF from its root, so those two frames must be the same one or it
> gets two parents. Three things drove the direction chosen: `two_d_mode` pins
> z/roll/pitch of `base_link_frame` to zero, which is only meaningful for a
> ground-projected frame (rooted at the camera it sank `base_footprint` to
> z = −0.13725); the filter's velocity — the cage's **only** speed source — is
> reported at `base_link_frame`, and at the camera it picked up an ω·0.11 lever-arm
> term inflating speed ~8 % in curves at the 0.22 m/s contract; and `ekf_gazebo.yaml`
> plus the Gazebo descriptions already root at `base_footprint`, so the hardware
> frame graph now matches the one every recorded result was produced under.
> The ZED's hardcoded `<camera_name>_camera_link` odometry child frame does **not**
> constrain this — robot_localization transforms the measurement into
> `base_link_frame` via the static TF, which is precisely what `base_link_frame` is
> for. The wrapper's own TF broadcast stays off (`publish_tf:=false`).
> The two disagree on the lane camera's height: `my_robot_gazebo_mesh.urdf` carries
> a `-0.01` body offset that `my_robot_basic.urdf` lacks, so the hardware
> description places the camera at **0.08725 m** while the cage's IPM
> (`camera_geometry.DEFAULT_CAMERA_HEIGHT_M`) assumes **0.07725 m**. The IPM reads
> the constant, not the TF, so nothing breaks silently *because of* the URDF — but
> the platform's own description disagreeing with the IPM by 13 % is a concrete
> lead for the §2 item 2 [VERIFY]: measure the real mount and reconcile all three.

Three conventions follow from this, and the RL launch obeys all of them:

* **A controller launch attaches to a running Layer 1**; it does not start the
  driver itself. `deploy_cobraflex.launch.py` therefore defaults `bringup:=false`.
  Passing `bringup:=true` while Layer 1 is already up starts a **second**
  `cobraflex_ros_driver` on the same device; Linux does not lock `/dev/ttyACM*`,
  so the two would interleave JSON writes and 50 ms keep-alives with no error —
  silent corruption of the actuation channel. Use it only for a standalone start.
* **Layer 2 owns every sensor, including the lane camera** (changed 2026-08-05, so
  a bring-up is three commands and no sensor is left to a side script). The RL
  launch therefore defaults `camera:=false` and attaches to
  `camera/image_raw_lane`. `nvarguscamerasrc` does not share a sensor, so opening
  it twice simply fails — never run Layer 2's camera and `camera:=true` together.
* **Layer 2 IS a dependency of the RL chain**, unlike the classical lane keeper —
  not for the lidar or the ZED image, but because its ekf publishes
  `/odometry/filtered`, the only source of speed the cage has (§2 item 8).

## 3. Bring-up command

The car host (`admit14-cobraflex`, Jetson / L4T R36.4.7, aarch64) runs **ROS 2
Humble**, not the dev machine's Jazzy, and its workspace is `~/ros2_ws` — see §3b
for how the repo packages are wired into it.

**Three commands, three terminals**, in this order. Each attaches to the previous
layer; none of them re-starts what an earlier one already owns.

```bash
# In EVERY terminal: Humble + the colcon overlay + the inference venv (§2 item 6).
source ~/MT-SE4AI-Safe-RL-Cobraflex/scripts/setup_deploy_env.sh

# 1 · Layer 1 — description + ROS→JSON serial driver:
ros2 launch cobraflex cobraflex_bringup.launch.xml use_rviz:=false

# 2 · Layer 2 — lidar + ZED + the CSI lane camera + the ekf:
ros2 launch cobraflex cobraflex_sensors.launch.xml

# 3 · Layer 3 — the RL chain (policy + D-43 estimator + cage + actuation + evidence):
ros2 launch cobraflex_rl deploy_cobraflex.launch.py \
    checkpoint:=/abs/path/to/ppo_gz2d_cap022_1M_2024_550000_steps.zip \
    mode:=monitoring          # FIRST runs in monitoring (cage shadows, does not act)
```

With the car on the physical **complex_b** track and `mode:=enforcement`, that is
the whole deployment: every other parameter of the deployed contract is already a
launch default.

**What the launch defaults now encode** (all of them reproduce the 550k campaign;
see §6b for why three of them had to change):

| Argument | Default | What it fixes |
| --- | --- | --- |
| `algorithm` / `max_speed_mps` | `ppo` / `0.22` | the D-66/D-67 trunk. A wrong `algorithm` is not soft — SB3 refuses the zip |
| `control_rate_hz` | `10.0` | the trained `control_dt`; the policy + cage cycle here, NOT at the camera's 20 Hz |
| `throttle_deadband` | `0.05` | the 2-D contract's stop band |
| `odom_topic` | `/odometry/filtered` | the ekf, not Gazebo's `/odom` — the cage's only speed source |
| `heading_fit_mode` / `heading_gain` / `heading_temporal_window` | `joint_pair_quadratic` / `1.6` / `4` | the **posterior** D-43 estimator the trunk was scored with, not the frozen GE4 `near_secant`/1.0 the node defaults to |
| `camera` | `false` | Layer 2 owns the CSI device |
| `evidence_dir` | `<repo>/experiments/physical/runs` | physical evidence, not `experiments/sim/runs` relative to the shell's cwd |

Make sure `cobraflex_lane_keeper.launch.py` is **not** running: it holds the same CSI
device and commands `/cmd_vel`.

Variants:

* Standalone (no Layer 1/2 running): add `bringup:=true serial_port:=/dev/ttyACM1
  camera:=true` and skip commands 1–2 — never both. Note the cage then runs with
  **no speed** (nothing publishes odometry), so C-03/C-04 stay inert; the node logs
  an error saying so. Use it for camera/perception bench work only.
* External image source: `camera_topic:=<topic>` (the frame must still be 640×360
  at the HFOV the code assumes — see §1b, and note M-6 measured the real camera
  at 77.89°, so "matching the code" and "matching the car" are not yet the same
  requirement).
* Non-Jetson bench test: run `csi_camera_node` alone with a substitute source, e.g.
  `-p gst_pipeline:="videotestsrc ! videoconvert ! video/x-raw,format=BGR ! appsink"`.
* Watch what the policy sees: rviz on `camera/image_raw_lane`.

> **After a `kill -9`, clear the DDS state before relaunching.** A hard kill leaves
> `/dev/shm/fastrtps_*` segments behind, and the next launch then comes up
> *partially* connected: every node starts, the cage logs "loaded", and no image or
> `/cage_status` ever flows — observed on the car 2026-08-05. A clean Ctrl-C
> releases them. Recovery: `ros2 daemon stop && rm -f /dev/shm/fastrtps_*`.
> (Not dangerous — `vehicle_control_node`'s watchdog stops the car — but it looks
> exactly like a healthy start.)

## 3b. How the repo is wired into the car's `~/ros2_ws` (done 2026-08-04)

The four packages are **symlinks** into the repo checkout, not copies:

```text
~/ros2_ws/src/{cobraflex,cobraflex_rl,cobraflex_safety_msgs,safety_cage}
    -> ~/MT-SE4AI-Safe-RL-Cobraflex/src/<pkg>
```

Symlinks (plus `colcon build --symlink-install`) are load-bearing, not cosmetic:
`cage_ros_node._resolve_cage_yaml` and `_bootstrap_cage_import` both **walk up from
the node's own source file** to find the repo's `cage/`. A copied workspace has no
`cage/` above it, so the cage would either fail to import or fail to find
`cage.yaml`. With the symlink the node resolves the repo's own
`cage/cage.yaml` — verified at build time to hash
`4287fe71…`, i.e. **bit-identical to the cage that produced the 550k verdict of
record** (`experiments/sim/runs/rl_ppo2d_cap022_550000_nom_4k4/metadata.json`).

`cage` / `policy` are additionally put on the interpreter path by
`~/.local/lib/python3.10/site-packages/se4ai-thesis-repo.pth` (one line: the repo
root). This is the `pip install -e .` of CLAUDE.md by other means — the host's
pip 22.0.2 + setuptools 59.6 combination cannot do a PEP-660 editable install, and
upgrading setuptools on the car is not worth it (`colcon-core` pins `<80` and
Humble's `ament_python` builds are sensitive to setuptools ≥64).

Two `COLCON_IGNORE` markers keep the workspace buildable: `~/ros2_ws/warren/`
(rosbag test data colcon otherwise scans) and `~/ros2_ws/src_copies_backup_20260804/`
(the pre-symlink copies, kept until the first successful hardware run — delete
afterwards). The gitignored 87 MB `rplidar-a2m4-r1.stl` was moved into the repo's
`src/cobraflex/meshes/` so the Layer-1 description still has it.

## 4. Staged, safe bring-up sequence

0. **Camera first, nothing else.** Run `csi_camera_node` alone and check
   `ros2 topic hz camera/image_raw_lane` ≈ 20 Hz and
   `ros2 topic echo --once camera/image_raw_lane --field height` = 360 (width 640,
   encoding `bgr8`). Look at it in rviz: this is literally the policy's input.
   The HFOV scale-check of prerequisite 1 is **done** (M-6, 17.08.2026): it came
   back 77.89°, not 90°, and the resulting decision is still open — read §2 item 1
   before anything moves.
1. **Bench, wheels up.** `mode:=monitoring`. Confirm topics flow
   (`/raw_action`, `/state_obs`, `/perception_invalid`, `/cage_status`) and the
   CV estimator tracks a hand-moved lane. No actuation trusted yet.
2. **Throttle→speed, now on rails but still worth watching once.** The domain and
   the map were wrong and are fixed (§6b items 1–2); the equality with the sim is
   now asserted host-side
   (`test_deployed_chain_speed_equals_the_sim_speed`). What remains is to see it:
   with the wheels up, `ros2 topic echo /cmd_vel` while the policy runs — the
   commanded `linear.x` must span 0 … 0.22 m/s and reach a **true 0** when the
   cage's safe throttle drops below the 0.05 deadband.
3. **Low-speed enforcement, tethered.** `mode:=enforcement`, e-stop in hand,
   `max_speed_mps` reduced. Verify C-05 stops the car and the e-stop overrides.
4. **Full deploy** only after 1–3 pass.

## 5. Known gaps / sim-to-real (Ch.9, honest list)

- **Appearance gap** (CNN + CV estimator): the real camera image differs from the
  Gazebo render → both the policy and the D-43 estimator may degrade. Mitigations:
  H-10 domain randomisation (training-side), the D-57 calibration precedent.
- **`[provisional]` thresholds** (M-1..M-5) were calibrated on sim noise; the
  calibration campaign exists to re-derive them on hardware.
- **Compute cadence — measured end to end, 2026-08-05, and it now closes.** The
  loop is 10 Hz in sim. Inference was already measured at 17.6 ms/cycle ≈ 57 Hz
  (§2 item 6). The remaining unknown — the camera→inference→actuation path — was
  the bottleneck, and it was a software defect, not the CSI driver (§6b item 4).
  With it fixed, the bench chain sustains **10.0 Hz** of cage cycles (50 per 5 s,
  camera stamp gaps 50 ms median) with **zero** `/safe_action` watchdog stops,
  measured *while* a desktop session, AnyDesk and an IDE were competing for the
  same 6 cores. Residual: occasional single-cycle camera starvation (p90 stamp gap
  101 ms) which the fail-safe chain absorbs.
- **Which checkpoint**: deploy the rescued *peak* checkpoint of the final training
  (monitor the 25k-cadence learning curve), not necessarily the last step.
- **Yaw gain: the firmware turns through a wider track than the sim does — OPEN.**
  Waveshare published the Cobra Flex ESP32-S3 source after this model was built
  (`Cobra_Driver/ugv_config.h`, block `mainType:02 Cobra_Flex`). It declares
  `TRACK_WIDTH 0.159` and `WHEEL_D 0.0739`, and `rosCtrl` in
  `Cobra_Driver/movtion_module.h` uses both to turn **every** twist we send into
  wheel RPM: `setpointA = rosX - rosZ*TRACK_WIDTH/2`, then `*60/(pi*WHEEL_D)`.
  Gazebo's DiffDrive does the same job through **0.154**, and the tape says the
  real track is **0.153** — so the firmware constant sits 3.9 % above the
  measured track and the simulator does not. That is a systematic yaw gain
  offset in precisely the channel the policy controls, and a candidate
  contributor to whatever `perception_heading_bias_rad` is currently absorbing.
  **Not corrected**, because the two numbers are not the same quantity: 0.153 is
  geometry and belongs in the URDF, whereas 0.159 is a control constant with
  scrub compensation baked in and, if anything, belongs in the DiffDrive plugin.
  **MEASURED on the track 18.08.2026 (M-7 §5) — and the question as posed is not
  the dominant term.** `tools/measure_yaw_gain.py`, yaw integrated from
  `/odometry/filtered`:

  | `vx` (m/s) | `wz` cmd | `wz` achieved | ratio |
  | --- | --- | --- | --- |
  | 0.20 | 0.00 | −0.004 | — (**−1.0° drift over 4 s: the chassis tracks straight**) |
  | 0.00 | 1.00 | 0.150 | 0.150 |
  | 0.20 | 0.20 | 0.096 | 0.482 |
  | 0.20 | 0.40 | 0.174 | 0.436 |
  | 0.20 | 0.80 | 0.273 | 0.341 |

  Three readings. (i) The platform team's **0.4954 is confirmed while moving**
  (0.482/0.436/0.341 bracket it), and the deploy default
  `steering_to_yaw_rate_gain = 0.8/0.4954 = 1.615` already compensates it — so the
  policy is *not* driving an uncompensated deficit. (ii) The in-place 0.150 on this
  floor is far below their bench 0.4954: the surface-dependence warning above is
  real, and in-place is not the policy's regime. (iii) **New, and the part that
  matters: the plant is compressive** — marginal gain falls from 0.39 (0.2→0.4) to
  0.25 (0.4→0.8), so a single linear gain is calibrated at moderate demand and
  under-delivers at high demand, which is exactly when C-01/C-02 correct.

  **Resolution: neither 0.159 nor 0.154.** No 3.2 % constant fits a channel whose
  gain runs from 0.48 to 0.34 across the operating range; carry the compression as
  the open item instead.
- **Two driver defects the same source exposed — FIXED.** The `T=1001` frame is
  built by `base_info_feedback()` in `Cobra_Driver/ugv_advance.h`, which settles
  fields we had been reading by inference: `v` is `(int)(loadVoltage_V * 100)`,
  i.e. **centivolts**, so `/cobraflex/battery` had been publishing ~1180 where
  11.80 V was meant; and `odl`/`odr` are `(long int)(en_odom_l * 100)`, i.e.
  cumulative **integer centimetres** per side — odometers, not the speeds the
  `/cobraflex/wheel_speeds` topic name claims. The voltage scale is corrected;
  the odometry topic is left as-is on purpose, pending the wheel-geometry
  question above and a decision on wiring wheel odometry into the ekf at all.
  Also carried over from Waveshare's own ROS driver, but **shipped disabled**: a
  stiction floor for turning on the spot (`min_angular_in_place`, default 0.0).
  The chassis genuinely cannot break static friction below ~0.2 rad/s with no
  forward speed, so Nav2's `rotate_to_goal` stalls silently and the parameter
  exists to fix that — but it must not be on while the cage drives. The reason
  is `safe_action_to_cmd_2d`, which derives `linear_x` and `angular_z`
  independently: a throttle under `throttle_deadband` gives `linear_x == 0.0`
  while the steer still maps through `steering_to_yaw_rate_gain` (0.8), so a
  C-04 attenuation down to a true stall — which **SR-009 requires to be
  commandable** — reaches the driver as `vx == 0` with `|wz| < 0.2` for any
  steer inside a quarter of its range. A stiction floor would turn that
  deliberate stop into a 0.2 rad/s spin. Enable it for Nav2 or teleop bring-up
  only. Two further facts worth recording:
  `M1..M4` are always 0 in the shipped build (`ddsm_fb_*` is never assigned), and
  the IMU fields plus the whole `T=1002` frame are commented out — the chassis
  carries an ICM-20948, so the ekf's second source is a recompile away, not a
  wiring problem.

## 6. What is and isn't claimed

Prepared and host-verified: the inference node's preprocessing + action mapping,
the launch wiring, the reuse of the identical cage logic. **Bench-verified on the
car** (2026-08-05, `mode:=monitoring`, synthetic checkpoint, no track, wheels not
driven): the six nodes come up and stay up; the cage loads the repo's own
`cage.yaml` v0.6.1 through the symlink walk-up; the chain cycles at 10 Hz; the
recorded `/raw_action` throttle lands in the cage's [0, 1] domain; `/cage_status`
evidence is written to `experiments/physical/runs/<run_id>/` stamped with the
*actual* mode; and pointing the camera at a non-track scene produces exactly the
expected refusal (`C-02;C-05` + `perception_invalid`) rather than a command.
**Not** verified: any *driving* behaviour on the physical car. First bring-up on
the complex_b track is the Phase-5 experiment this plan scaffolds; the `[VERIFY]`
items are its explicit agenda.

## 6b. The 2026-08-05 bench review: four silent defects

Found by reading the chain against the sim it is supposed to reproduce, then
running it on the car. Every one of them would have produced a *running* system
with wrong behaviour — none would have raised.

1. **Throttle in the wrong domain** (`rl_policy_node`). `/raw_action.linear.x` is
   the cage's normalised throttle u ∈ [0, 1]; the node published the policy's raw
   action a ∈ [-1, 1]. `GazeboLaneEnv.step` applies
   `cage_bridge.policy_throttle_to_cage` (u = (a+1)/2) *before* the cage, so both
   C-04/C-06 and `vehicle_control_node` were reading a number in the wrong scale.
   Concretely: a = 0 — the middle of the policy's range, 0.11 m/s in sim — arrived
   as throttle 0, a commanded stop; the whole negative half of the action space
   collapsed onto "stop". Fixed by importing the sim's own mapping. Regression:
   `test_action_to_twist_matches_the_sim_bridge_across_the_range`.
2. **The frozen 1-D speed map on a 2-D contract** (`vehicle_control_node`). The
   node only implemented `target_speed_from_throttle` (scale a cruise speed by
   throttle/nominal, clamped to [0.35, 1]). Under it a 2-D checkpoint saturates at
   u = 0.5 instead of u = 1, and the cage can never command below 0.35·0.22 =
   0.077 m/s — so C-04's attenuation authority is truncated and SR-009's
   commandable stall is unreachable. Added `speed_map:=linear_2d`, which calls
   `cage_bridge.target_speed_from_throttle_2d` directly (no second implementation
   to drift). Regression: `test_deployed_chain_speed_equals_the_sim_speed`.
3. **The loop ran at camera rate, not control rate** (`rl_policy_node`). Inference
   sat in the image callback, so at 20 Hz camera the policy published 20 Hz of
   `/raw_action` — and `/raw_action` is `cage_ros_node`'s cycle trigger. That grants
   C-06's per-cycle `delta_max_steering_per_cycle` (0.15) twice as often, i.e.
   **doubles the steering slew the rate limiter allows**, on the rule the 550k
   analysis singles out as load-bearing (T2). It also halves the k=4 frame stack's
   horizon (0.2 s vs the trained 0.4 s). Added `control_rate_hz` (default 10.0):
   frames are buffered, a timer consumes the latest one — exactly what
   `GazeboLaneEnv.step` does.
4. **One line capped the camera at 8 Hz** (`csi_camera_node`, and the same defect
   in `lane_keeper_node`, `lane_keeper_gazebo_node`, `cage_viz`). `msg.data =
   frame.tobytes()` looks free. rclpy's generated setter for a `uint8[]` field
   fast-paths **only** `array.array('B')`; everything else falls into a `__debug__`
   assertion that walks all 691 200 elements in Python, twice
   (`all(isinstance(v, int) …) and all(0 <= val < 256 …)`). Measured per 640×360
   BGR frame on this Jetson:

   | assignment | cost | implied ceiling |
   | --- | --- | --- |
   | `msg.data = out.tobytes()` | **127.01 ms** | 7.9 Hz |
   | `msg.data = array.array('B', out.tobytes())` | **0.12 ms** | — |

   The node advertises 20 Hz, so it silently ran at ~8: measured publisher stamp
   gaps were **117 ms median** — not a multiple of 50 ms, which is what identified
   the *producer* rather than the transport as the cause. Downstream, the 10 Hz
   control loop starved on about a third of its cycles and tripped
   `vehicle_control_node`'s `/safe_action` watchdog. After the fix: 50 ms median
   stamp gap, `csi_camera_node` CPU 140 % → 62 % of a core, 10.0 Hz cage cycles,
   0 watchdog stops. Note this also affected the **classical CV lane keeper**,
   which publishes four debug image topics per cycle.

5. **A failed camera looked like a healthy one** (`csi_camera_node`) — found on the
   second pass, once the real checkpoint was on the car. When Argus refuses the
   capture session, `nvarguscamerasrc` logs `Failed to create CaptureSession` but
   the GStreamer pipeline still reaches PLAYING, so `cv2.VideoCapture.isOpened()`
   returns **True**. The node's only startup guard tested exactly that, so it
   announced `ready: 640x360 @ 20.0 Hz`, the launch printed six healthy nodes, and
   every `read()` then failed forever — 1141 of them in the observed run. Nothing
   was unsafe (no frames → no `/raw_action` → the watchdog stops the car), but
   nothing said *why*. The node now proves a first frame actually arrives
   (`open_timeout_s`, 4 s) before declaring itself a camera, and names the causes
   and the recovery in the error.

   **Why Argus refused it is worth knowing**, because it is a race, not a wedged
   daemon: the failure reproduced *only* when `csi_camera_node` started inside the
   RL launch (`camera:=true`) while `rl_policy_node` was unpickling the 20 MB
   checkpoint and initialising torch on the same six cores — the identical pipeline
   opened cleanly seconds before and seconds after, and never failed with the 7 MB
   synthetic checkpoint. Argus loses the session negotiation under that startup CPU
   spike. `open_retries` (3) wins it back. **The three-command bring-up avoids the
   race structurally**, which is an argument for the layering independent of tidiness:
   Layer 2 starts the camera long before Layer 3 loads any checkpoint. Verified both
   ways on the car with the real 550k checkpoint.

Two smaller ones fixed alongside:

* **Evidence was mislabelled and misplaced.** `cage_logger_node` defaults
  `output_dir` to `experiments/sim/runs` *relative to the shell's cwd* and
  `cage_mode` to `"enforcement"` regardless of the cage's actual mode — so a
  monitoring run on the car would have written physical evidence into a sim path,
  stamped as enforcement. The launch now passes `evidence_dir`, `run_id` and the
  real `mode`.
* **The D-43 perception contract was not applied.** `cv_lane_estimator_node`
  exposed only `heading_fit_mode`/`heading_gain` and defaulted to the frozen GE4
  `near_secant`/1.0, while the 550k trunk was trained and scored with
  `joint_pair_quadratic`, gain 1.6 and the T3 temporal window 4. The node now
  exposes the whole set (plus `heading_bias_rad` for the D-57 workflow and
  `perception_min_invalid_cycles`) and the launch forwards the trunk's values. The
  four `heading_temporal_*` tunables are deliberately *not* restated in the launch:
  the training config's values are already the `CvLaneEstimatorConfig` defaults.

One measured improvement that is not a defect fix: `csi_camera_node` now inserts
`videorate drop-only=true` at 1.5× its read rate *before* the CPU `videoconvert`,
so the pipeline stops colour-converting the frames the node was going to discard
(the sensor still runs at 60 fps, same mode, same exposure regime, same
`INTER_AREA` resize — no pixel of any delivered frame changes). Measured 72.3 % →
61.3 % of a core. Throttling exactly to the read rate saves a little more but makes
producer and consumer beat, and `read()` starts blocking inside the timer callback
(p95 0.8 ms → 6.6 ms) — hence 1.5×, not 1×.

## 6c. The 2026-08-17 bench session: the safety chain verified on hardware

Car on a platform, **wheels off the ground**, no track and no lane markings.
Layers 1–3 up, `mode:=monitoring`, on the hash-verified 550k trunk checkpoint
(`0d4492461b24efce…`, matching the verdict campaign). Driven by
`tools/preflight_deploy.py`, which turns §4's stages into PASS/FAIL.

**Stage 0 (camera) — all pass.** 640×360 `bgr8`; median stamp gap **50.0 ms
(20.0 Hz exactly)**, p90 52.6 ms. This retires an earlier suspicion: gaps at
100/200/400 ms seen while the Jetson was loaded were transport loss at an extra
subscriber, not the node publishing slowly.

**Stage 1 (chain) — all pass.** Five topics flowing; cage cycling at **9.8 Hz**,
i.e. the trained `control_dt` and not the camera's 20 Hz (the §6b item-3 defect
stays fixed); `cycles_since_last_state` max **0**; state vector finite and inside
`state_validity_ranges`; `ey` live (0.149 m span under a hand-moved target);
`cage.yaml 0.6.1` stamped. Evidence written to
`experiments/physical/runs/ros_run_20260817T194009Z/cage_status.csv` — 18 columns,
`mode` stamped, `safe_* == raw_*` as monitoring requires.

**The perception-loss fail-safe, demonstrated outside simulation for the first
time.** With no lane markings the estimator cannot produce a valid lane, so:

> `perception_invalid` → C-05 latches emergency → `/emergency` = true →
> `vehicle_control_node` (emergency-aware) commands a zero Twist → **97/97
> `/cmd_vel` samples exactly 0.0** on both axes → wheels never moved

while `action_raw.linear.x` stayed at ≈ 0.70, i.e. the policy *was* asking for
throttle throughout. That is H-11/H-12 → SR-005 → C-05 → actuation stop, end to
end, on the real platform. Note C-05's exit is deliberately asymmetric: it needs
the condition **cleared AND** a reset on `/cage_reset`, not either — so on a bare
bench there is no way out, by design. **Operational consequence for track work:
any momentary perception loss stops the car until `/cage_reset` is published.**

**Actuation sign — verified in both directions, previously untested.** Commanding
`angular.z = +0.5` with Layer 3 stopped turned the right wheels forward and the
left wheels backward: counter-clockwise, i.e. left, per REP-103, and matching the
firmware's `setpointA = rosX − rosZ·TRACK_WIDTH/2`. The cage's half of the same
convention was checked host-side: `ey` = +0.20 (left of centre) → steering
**−0.12** (right), `ey` = −0.20 → **+0.12**, centred → 0. The full chain
estimator → cage → `vehicle_control_node` → firmware → wheels is sign-correct.

**Other measurements.** `/odometry/filtered` alive at 14.6 Hz (the cage's only
speed source; without it C-03/C-04 are inert). `/cobraflex/battery` reads
**10.89 V**, confirming the §6b centivolt fix — but that is ~3.63 V/cell on 3S,
so charge before a track session.

**Not established here**, because they need a lane or the ground: §4 step 2's
throttle envelope (C-05 was latched, so `/cmd_vel` is identically zero and the
envelope cannot be exercised), step 3's e-stop test, and the §5 yaw-gain bench
number (`wz = 1.0`, 10 s, measure the angle turned — needs wheels down).


## 6d. The 2026-08-18 track session: the estimator held, the policy did not

First run of the deployed chain on the **physical lane circuit**. Full record:
[M-7](../experiments/calibration/M7_track_perception.md), decision D-71.

**Read M-7 §2 first.** Three conclusions drawn from a stationary rig at one spot were all
overturned by a 2-minute recording of the whole circuit replayed offline. A parked car
characterises a location, not a track, and each single-pose "fix" made the rest of the circuit
worse.

**1. The D-43 estimator transfers at its shipped settings — near the lane centre.** Over 1521
circuit frames the **default** `white_sat_max = 30` pairs **95.4 %** and reads a mean lane width
of **252.9 mm against a ruler-measured 250 — 2.9 mm of error, scale 1.012**. **That is a
centre-of-lane figure** (90 % of those frames sit within ±72 mm) and the qualification matters
more than the headline: swept deliberately across the lane, the share of width-sane frames falls
**18 % → 30 % → 87 % → 95 % rejected** over the 0–30 / 30–55 / 55–80 / 80–120 mm bands,
systematically (183.8 mm, sd 23.9, `n_lines` mostly 4 — both lanes in view, wrong pair) and not
through heading. **The estimator feeding C-01 (160 mm) and C-05 (120 mm) is trustworthy only
within roughly ±55 mm**, entirely inside the band where those rules act, and *pairing rate does
not detect this* — it pairs, the pair is wrong. Indicative rather than established: both sweeps
moved the car by hand and the IPM reads a constant pitch, so a hands-off measurement at
tape-measured offsets is the outstanding test (M-7 §3b). The value proposed mid-session
(45) pairs only 69.4 % and puts 37 % of frames within 15 mm of the `lane_width_tol_m` rejection
floor. `white_sat_max` / `white_val_min` are now node parameters and launch arguments (`-1` = not
set, defaults bit-identical) because an illuminant knob belongs on a physical platform — but
**their values stay at the defaults**. The one location that genuinely failed (lines at
V 228…255 with S 36…50, rejected on saturation) is a real localised limit of a global HSV gate;
the fix is a per-row adaptive threshold or exposure control, neither tested.

**2. M-6's propagated `ey` scale is retracted** — see §2 item 1. Measured scale is 1.01. What
survives on the heading is **noise, not bias**: on identical circuit frames
`joint_pair_quadratic`/1.6 has sd **14.29°** and puts **7.8 %** of frames past C-02's 25° limit,
against `near_secant`/1.0's 5.31° and 0.8 %.

**3. The trunk camera policy does not transfer.** With the car moved by hand across a 332 mm span
of `ey` and the chain running at `cmd_vel_topic:=/cmd_vel_dryrun`
(`experiments/physical/runs/policy_bias_probe/cage_status.csv`, 5665 cycles):
`steer = −0.000166·ey_mm + 0.1155`, `r² = 0.059`. The response keeps the correct sign but the
lane-dependent swing across the whole span is **0.055** against a **constant left offset of
+0.1155 — 2.1× the swing** — and only **0.5 %** of samples ever command a right turn. In closed
loop the bias dominates and the car departs left regardless of position.

**4. SR-007 rejected a real sensor fault.** Over 7721 cycles the speed reaching the cage carries
outliers to **6.960 m/s** on a 0.22 m/s car — ZED visual odometry through the ekf. 0.43 % of
cycles exceed the `state_validity_ranges.speed_mps` ceiling of 1.50 and **all of them are in
emergency**. A `[provisional]` parameter catching a hardware fault no simulation produced.

**What the session demonstrates.** On a track where the trained policy is ineffective, the
runtime cage kept the platform safe: C-05 stopped the car on every excursion, `/cmd_vel` reached
an exact zero Twist, no road-edge contact. Containment of a policy that fails outside its
training distribution is the cage's value proposition, demonstrated on hardware for the first
time.

**Operational notes.** A killed launch leaves an evidence CSV with only its header — the logger
flushes on clean shutdown, so `Ctrl-C` the launch. A dry run is genuinely safe: with
`cmd_vel_topic` redirected, `ros2 topic info /cmd_vel` reports **publisher count 0** while the
whole chain runs. `policy:=false` brings the chain up without `rl_policy_node`, leaving
`/raw_action` free for another controller behind the same cage. And recording raw 640×360 at
20 Hz is **13.8 MB/s** to eMMC: the session ended in a Jetson crash, the bag lost its
`metadata.yaml` (recovered with `ros2 bag reindex`) and one CSV lost its final block; treat
rates measured while recording as I/O-limited, not as chain capability.
