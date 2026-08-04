# 17 · Physical deployment (Phase 5) — bring-up plan for the real CobraFlex

**Status: scaffolding prepared, NOT yet run on hardware.** This document is the
bring-up checklist for taking the verdict-bearing RL camera policy + safety cage
from Gazebo to the physical 1:14 CobraFlex. Every sim-side component it reuses is
validated; the hardware I/O and the items flagged **[VERIFY]** are not, by
construction — they need the car.

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

| Quantity | Value | Authority |
| --- | --- | --- |
| Native frame | **640×360** | `Lane Cam <image>` · `camera_geometry.DEFAULT_WIDTH_PX/HEIGHT_PX` · `lane_keeper_node.proc_width/proc_height` |
| HFOV | **90°** (1.5707963 rad) | `Lane Cam <horizontal_fov>` · `CameraModel.hfov_rad` · `lane_keeper_node.camera_hfov_deg` |
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

1. **[VERIFY — highest priority] The 90° effective HFOV.** This is the
   load-bearing unverified number of the whole sim-to-real transfer. It originates
   as a *parameter default* in `lane_keeper_node` (`camera_hfov_deg` 90.0) for an
   IMX219-**160** wide-angle lens, and the Gazebo sensor mirrored it — so if it is
   wrong, both sim and hardware are wrong in the same way and no sim result
   exposes it. `CameraModel.fx = (w/2)/tan(hfov/2)` = 320 px at 640×360, and the
   IPM's metric output scales with it: a wrong HFOV means every `ey` in metres is
   mis-scaled and **C-01's 0.12 m threshold no longer means 0.12 m**. Calibrate the
   lens on the car (a known-width lane at known distances is enough to check the
   scale) before trusting any metric cage threshold. Note the published
   `CameraInfo` is deliberately the *ideal pinhole the cage assumes* — no
   distortion terms — because publishing measured intrinsics would contradict the
   IPM; reconcile both, do not just add distortion coefficients.
2. **[VERIFY] Camera extrinsics.** The IPM in `camera_geometry.py` is calibrated
   for pitch 0.30 rad, height 0.077 m (the URDF mount). Match the real mount to
   these, OR re-run the D-57 workflow to set `cage.perception_heading_bias_rad`
   for the real camera's near-field-slope offset. A wrong pitch corrupts the CV
   `ey`/`epsi` the cage acts on.
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
4. **[VERIFY] `steering_to_yaw_rate_gain` (0.8).** `vehicle_control_node`
   publishes `/cmd_vel.angular.z = safe_action.angular.z × 0.8`; that gain was
   calibrated against the **Gazebo DiffDrive plugin's** reading of `angular.z`.
   The firmware's `Z` is a nominally equivalent yaw rate on an Ackermann chassis,
   but the two have never been compared on the real car. Re-calibrate before
   trusting the cage's C-02/C-03 margins on hardware.
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
7. **[BLOCKER] The deployed checkpoint is not on the car.** Checkpoint binaries are
   gitignored, so the repo checkout carries the campaign's CSVs but not the `.zip`.
   Copy from the training machine:

   | | |
   | --- | --- |
   | File | `ppo_gz2d_cap022_1M_2024_550000_steps.zip` |
   | Source | `policy/checkpoints/` on the training host |
   | SHA-256 | `0d4492461b24efce58fed4c53e3ada58385ffc7d6b0746863de14a6892a25867` |
   | Algorithm | `ppo` · `max_speed_mps` 0.22 · `throttle_deadband` 0.05 |
   | Provenance | `experiments/sim/runs/rl_ppo2d_cap022_550000_nom_4k4/metadata.json` |

   Verify the hash on arrival — it is the only link between the car and the verdict
   of record. The observation contract the node reconstructs (84×84 grey, k=4) was
   checked against `train_ppo_camera_2d_cap022_1M.yaml` and matches.

## 2b. The platform's bring-up layering (what the RL launch must match)

The CobraFlex package is layered, and every controller follows the same pattern:

| Layer | Launch | Starts |
| --- | --- | --- |
| 1 — base | `cobraflex_bringup.launch.xml` | `cobraflex_description.launch.xml` (robot_state_publisher on `my_robot_gazebo_mesh.urdf`, joint_state_publisher, rviz `bot.rviz`; `use_sim_time:=false`) **+** `cobraflex_driver.launch.xml` (`cobraflex_ros_driver`) |
| 2 — sensors | `cobraflex_sensors.launch.xml` | SLLIDAR A2M8 (`frame_id:=lidar_link`) + ZED Mini (`camera_model:=zedm`, `publish_tf:=true`) |
| 3 — controller | `cobraflex_lane_keeper.launch.py` | `lane_keeper_node` + rviz `lane_keeper.rviz` — **no** Layer 1/2 include; it owns the CSI camera itself |
| 3 — controller | `cobraflex_automatic.launch.xml` | Layer 2 + `lidar_avoidance_node` |
| 3 — controller | **`deploy_cobraflex.launch.py`** | `csi_camera_node` + the RL chain (this document) |

The two Layer-3 lane controllers are **mutually exclusive**: both need the same CSI
device and both end up commanding `/cmd_vel`.

Two conventions follow from this, and the RL launch obeys both:

* **A controller launch attaches to a running Layer 1**; it does not start the
  driver itself. `deploy_cobraflex.launch.py` therefore defaults `bringup:=false`.
  Passing `bringup:=true` while Layer 1 is already up starts a **second**
  `cobraflex_ros_driver` on the same device; Linux does not lock `/dev/ttyACM*`,
  so the two would interleave JSON writes and 50 ms keep-alives with no error —
  silent corruption of the actuation channel. Use it only for a standalone start.
* **Layer 2 is not a dependency of lane following.** Neither `lane_keeper_node`
  nor the RL chain needs the lidar or the ZED, so the RL launch omits Layer 2 —
  the same choice `cobraflex_lane_keeper.launch.py` makes. The lane camera is the
  CSI cam, published by `csi_camera_node` inside the Layer-3 launch (§1b), which is
  also where `cobraflex_lane_keeper.launch.py` gets its frames from (internally).

## 3. Bring-up command

The car host (`admit14-cobraflex`, Jetson / L4T R36.4.7, aarch64) runs **ROS 2
Humble**, not the dev machine's Jazzy, and its workspace is `~/ros2_ws` — see §3b
for how the repo packages are wired into it.

```bash
# Sources Humble + the colcon overlay AND wires the inference venv (§2 item 6).
# Use it in every terminal of the bring-up; plain `source install/setup.bash` is
# enough for the Layer-1 terminal but harmless everywhere.
source ~/MT-SE4AI-Safe-RL-Cobraflex/scripts/setup_deploy_env.sh

# Layer 1 (once, in its own terminal) — description + ROS→JSON serial driver:
ros2 launch cobraflex cobraflex_bringup.launch.xml use_rviz:=false

# Layer 3 — csi_camera_node + the RL chain (attaches to the bring-up above):
ros2 launch cobraflex_rl deploy_cobraflex.launch.py \
    checkpoint:=/abs/path/to/ppo_gz2d_cap022_1M_2024_550000_steps.zip \
    algorithm:=ppo \
    max_speed_mps:=0.22 \
    mode:=monitoring          # FIRST runs in monitoring (cage shadows, does not act)
```

`algorithm` and `max_speed_mps` are the launch defaults (`ppo`, `0.22`) because the
deployed trunk is the **2-D PPO cap-0.22 550k** checkpoint (D-66/D-67); they are
spelled out above only to make the contract explicit. A wrong `algorithm` is not a
soft failure — SB3 refuses to load the zip.

Make sure `cobraflex_lane_keeper.launch.py` is **not** running: it holds the same CSI
device and commands `/cmd_vel`.

Variants:

* Standalone (no Layer 1 running): add `bringup:=true serial_port:=/dev/ttyACM1`
  and skip the first command — never both.
* External image source instead of the CSI cam: `camera:=false camera_topic:=<topic>`
  (the frame must still be 640×360 at 90° HFOV — see §1b).
* Non-Jetson bench test: run `csi_camera_node` alone with a substitute source, e.g.
  `-p gst_pipeline:="videotestsrc ! videoconvert ! video/x-raw,format=BGR ! appsink"`.
* Watch what the policy sees: rviz on `camera/image_raw_lane`.

> Requires a `colcon build` of `cobraflex_rl` — `csi_camera_node`, `rl_policy_node`
> and the deploy launch all postdate the current `install/` tree.

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
   Then scale-check the HFOV (prerequisite 1) before anything moves.
1. **Bench, wheels up.** `mode:=monitoring`. Confirm topics flow
   (`/raw_action`, `/state_obs`, `/perception_invalid`, `/cage_status`) and the
   CV estimator tracks a hand-moved lane. No actuation trusted yet.
2. **[VERIFY] 2-D throttle→speed mapping.** The sim maps the cage's safe throttle
   via `cage_bridge.target_speed_from_throttle_2d` (max_speed·u, full stop below
   the deadband); `vehicle_control_node` scales `fixed_speed_mps` by the safe
   throttle. Confirm they agree (set `fixed_speed_mps` = `action.max_speed_mps`,
   check the deadband/stop) so commanded speeds match the campaign.
3. **Low-speed enforcement, tethered.** `mode:=enforcement`, e-stop in hand,
   `max_speed_mps` reduced. Verify C-05 stops the car and the e-stop overrides.
4. **Full deploy** only after 1–3 pass.

## 5. Known gaps / sim-to-real (Ch.9, honest list)

- **Appearance gap** (CNN + CV estimator): the real camera image differs from the
  Gazebo render → both the policy and the D-43 estimator may degrade. Mitigations:
  H-10 domain randomisation (training-side), the D-57 calibration precedent.
- **`[provisional]` thresholds** (M-1..M-5) were calibrated on sim noise; the
  calibration campaign exists to re-derive them on hardware.
- **Compute cadence**: the loop is 10 Hz in sim. The *inference* half is now
  measured on the car — 17.6 ms/cycle ≈ 57 Hz on the Jetson CPU with the deployed
  observation contract (§2 item 6) — so "CPU inference is ample" is no longer a
  guess. What is still unmeasured is the **camera→inference→actuation path end to
  end**; the CSI driver remains the likely bottleneck and can only be timed on the
  car.
- **Which checkpoint**: deploy the rescued *peak* checkpoint of the final training
  (monitor the 25k-cadence learning curve), not necessarily the last step.

## 6. What is and isn't claimed

Prepared and host-verified: the inference node's preprocessing + action mapping,
the launch wiring, the reuse of the identical cage logic. **Not** verified: any
behaviour on the physical car. First bring-up is the Phase-5 experiment this plan
scaffolds; the `[VERIFY]` items are its explicit agenda.
