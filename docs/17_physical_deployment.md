# 17 · Physical deployment (Phase 5) — bring-up plan for the real CobraFlex

**Status: PHASE 5 IS CLOSED (2026-09-01). The evidence base is final; no further
track or bench measurement will be taken, and the project is in write-up.**
The sim-to-real v2 policy **transfers**, and what stops the vehicle is the
**measurement**, not the control. `verdict_phys` remains **open by design**: no
scenario has ever been scored on hardware, every physical figure is
`monitoring` / N = 1 / out-of-protocol, and **the cage has never modified an
action on hardware**. Nothing in Phase 5 re-scores a gate; all of it is posterior
evidence to the D-69 simulation verdict of record.

**Read §14 first** — the consolidated ledger of all thirteen measured gap terms,
and §14.1's scoring of the a-priori list of §5 against them. Everything above it
is the chronological record that produced those rows.

| Session | What it established | Where |
| --- | --- | --- |
| 2026-08-05 / 08-17 bench | Five silent defects fixed; the perception-loss fail-safe and the actuation sign convention verified on hardware | §6b, §6c |
| 2026-08-17 **M-6** | The "90° HFOV" was a default the simulator had **inherited** — the real optic is **77.89°**, plus an unmodelled `k1 = −0.339` | §2, M-6 |
| 2026-08-18 **M-7 / D-71** | First drive: the D-43 estimator transfers, **the 550k trunk policy does not**, and three single-pose conclusions are overturned by a recorded circuit | §6d |
| 2026-08-26 | **The v2 policy drives.** 18.05 m in one uninterrupted 101 s segment, 0 resets, C-06 the only rule (3.4 % vs 3.0 % in sim → T2 did not materialise). Ended 2.11 m short on one 400 ms perception pulse | §8, §8.10 |
| 2026-08-31 driving | Goal not met (best 14.56 m). **Eight single-component hypotheses refuted.** The M-7 §4 `ey` under-read **does not survive rectification** | §10 |
| 2026-08-31 capture | **D-79** — the estimator's accuracy is a property of **place**, not of motion; the mechanism is candidate generation. The one spot every earlier calibration used is the circuit's **best** point | §12 |
| 2026-08-31 evening | **D-80** — three ways the cage stops the car, all of them the measurement. D-74's 1 s hold is unsatisfiable in motion | §13 |
| 2026-09-01 | Audit of §13 against its own CSVs (four numbers corrected), the **bare-policy arm withdrawn**, and the gap ledger consolidated | §13.2, §13.5, §14 |

**Two classes of physical evidence, and they must stay labelled apart.**
Calibration and structural findings (M-6, M-7, D-71, the two controlled A/B pairs,
C-04's dead zone, D-79's place-dependence) are **results**. Driving figures and the
gap table's physical column are **PRELIMINAR, N = 1, `monitoring`, unscored**, and
a physical campaign would supersede them.

**Sections that are runbooks, not records.** §9 and §11 were written before their
sessions; both have executed (§10 and §12 are their records) and both carry a
banner saying so. §5 is the **a-priori** gap list, deliberately left unedited so
that what it did and did not anticipate can be scored — §14.1 does that.

This document is the bring-up record for taking the verdict-bearing RL camera
policy + safety cage from Gazebo to the physical 1:14 CobraFlex. Every sim-side
component it reuses is validated; the hardware I/O and the items originally
flagged **[VERIFY]** were not, by construction — they needed the car, and §2
records what happened when they got it.

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
> reproducing the training distribution. Every other row of the table is
> unaffected. See §2 item 1.
>
> **⚠ Corrected again, 19.08.2026.** The reading that real frames are "~24 %
> narrower in field of view" is **wrong in sign**. 77.89° is `2·atan(320/fx)` —
> a *pinhole-equivalent* that discards the barrel distortion, which displaces a
> mid-row edge pixel by **129 px**. The camera's actual angular coverage is
> **94.6° horizontal / 52.2° vertical**, i.e. *wider* than the 90° the policy
> trained on, not 24 % narrower. (Wider is what an IMX219-**160** read through
> the cropped 1280×720 mode should give; the standard 79.3°-diagonal optic would
> deliver ~50° here, off by a factor 1.88, so the lens identification is
> confirmed by the calibration.) The practical consequence is favourable:
> undistorting the real frame into the canonical 90° camera fills **93 %** of it
> overall and **100 %** across the estimator's scan band. What is *not* corrected
> is the conclusion — the geometry still has to be undistorted, and §2 item 1's
> "correcting `fx` alone makes it worse" is now measured rather than propagated
> (0.674 → 0.644 on a forward model of the whole chain; undistorting gives
> 0.998). See the 19.08 CHANGELOG entry.
>
> One caveat for later: the plumb-bob polynomial M-6 fitted folds back at
> `r_u = 1.483` (a 364 px image radius) and the frame corners reach 372 px, so
> the corners are extrapolation. It is adequate for this crop and for building
> the rectification maps, which use the *forward* model only. A full-FOV capture
> mode (`1640×1232`) would need `cv2.fisheye`, not `calibrateCamera`.

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
   * **The cage fires LATE on the UNRECTIFIED path — CONFIRMED 18.08.2026 by
     hands-off measurement against a tape (M-7 §4, D-71), and SUPERSEDED for the
     deployed path on 31.08.2026 (§10.2).** The `ey` transfer, with the car
     parked on the ground at tape-measured offsets over ±100 mm, is
     **reported = 0.68…0.83 × true − 10 mm**, robust to every filtering of the 15
     points (r up to 0.99). M-6 predicted 0.72 and the measurement brackets it.
     On that path **C-01's 160 mm fires at a true 207–241 mm** and C-05's 120 mm
     at a true 172–212 mm, against a road half-width of 255 mm — 14–48 mm of
     margin where 95 mm was designed.
     **This is why the deployment rectifies**, and the prescription worked: the
     same nine-point sweep repeated on the ground on the rectified path gives
     scale **1.058** left / **0.991** right with **no intercept**, so C-01 fires
     at a true **151/158 mm** with ~100 mm of margin (§10.2). **Do not tune
     C-01/C-05 from the figures in this bullet** — they characterise a path that
     is no longer deployed. What replaces them is not a gain error but
     **place-dependence** (D-79, §12).
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
     *Also measured unrectified; but unlike the gain, this one did not go away —
     it is the first sighting of what D-79 later isolated as **place-dependence**
     (§12.3), and it is the defect that survived rectification.*
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
     observation the trunk trained with. *Resolved in practice, never as a
     contract: everything that has driven since 26.08 used `near_secant` (§8.4),
     which is why no physical run is under the scored D-43 contract — ledger term
     12, §14. And `near_secant`'s 5.31° is itself a **start-of-the-straight**
     figure: driving off that spot the same configuration gives sd 17.2–19.1°
     and 6.8–11.6 % of cycles past C-02 (§13.1), the heading-channel face of
     D-79.*
   * `cx` = 305.39 px (14.61 px off centre) adds a **lateral bias**, not just a
     gain, and measured barrel distortion is k1 = −0.339 against the IPM's
     assumed zero. Combining all of it with the measured pitch, the running IPM
     misplaces real lane points by **−57 mm to +167 mm** laterally — the worst
     case exceeding C-01's whole 160 mm `d_max_m`. See M-6 for the per-point table.
   * **Correcting `fx` alone would make the mean error worse** (49.4 → 52.2 mm):
     the scale error and the principal-point offset were partially cancelling.
     And with every scalar corrected, a pinhole IPM still leaves ~44 mm — closing
     it requires the estimator to **undistort**, not just to be re-parameterised.
   * ~~the 550k trunk policy trained on 90° Gazebo frames but will see 77.89°
     ones, i.e. images ~24 % "zoomed in"~~ — **retracted 19.08.2026.** The real
     coverage is 94.6°, *wider* than 90° (see the §1b correction), and the
     geometric shift is not what breaks the policy: rectifying the real frames
     into the canonical camera moves its lane response by essentially nothing
     (steering swing 0.097 → 0.090). The observation-space shift that *does*
     break it is **photometric** — Gazebo renders the road at grey 27, the real
     hall floor sits at 106 — and it is reproducible in simulation by that one
     transform. See the 19.08 CHANGELOG entry and `tools/sim2real_probe.py`.
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

> **This list is a-priori, and it is kept unedited on purpose.** It was written before the platform
> was ever driven; what it anticipated and what it missed is itself a result, scored in §14.1. The
> **measured** ledger — every gap term Phase 5 quantified, with magnitude, evidence and status — is
> **§14**. Read that one for the current state; read this one for what was foreseeable in advance.

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


## 7. Deploying the sim-to-real v2 policy (prepared 20.08.2026, D-72)

This section is the runbook for the policy trained by
`config/train_ppo_camera_2d_sim2real_v2.yaml`. It is written **before** that run
finished, so everything below is a procedure, not a result. Nothing in it has
been executed on the car.

### 7.1 What is different about this policy

The 550k trunk failed on 18.08 for three separable reasons (D-71, D-72). This
policy was trained against all three, so the deployment differs in kind:

| Term | Trunk | v2 policy |
| --- | --- | --- |
| Handedness | complex_b only, 6.5:1 left → a constant +0.13 steering prior | mirrored per episode, p = 0.5 → the prior has no training signal to form |
| Photometry | Gazebo's black road (grey 27) only | 75 % of episodes in the measured hall band (road ≈ 99–123), 25 % at the Gazebo render |
| Camera geometry | canonical pinhole only | mount pitch ±1.5° and height ±10 % every episode, plus 10 % of episodes on the full measured lens |

The third one changes what the *car* must do, not only what the policy saw:
**the deployment is meant to run rectified.** The mount-pose randomisation covers
the residual rectification leaves behind (+8…+30 mm, session-dependent); it does
not cover the whole `k1 = −0.339` barrel, which rectification is there to remove.

### 7.2 Choosing the checkpoint — and the blocker that must be cleared first

100 checkpoints, and **the reward does not order them**. Use
`tools/select_sim2real_checkpoint.py`, which scores each one's lane response
through four conditions and ranks on `hall+lens+rect`, the deployment arm:

```bash
python tools/select_sim2real_checkpoint.py \
  --prefix ppo_gz2d_sim2real_v2_2024 \
  --sim-frames experiments/sim/runs/cv_probe_weak_sections_20260713T084230Z/raw_logs/frames \
  --real experiments/physical/datasets/circuit_export \
  --output experiments/sim/eval_gz2d/select_v2.json
```

> **~~BLOCKER~~ — CLEARED 26.08.2026. The frames were never lost; the 23.08 search
> ran on the wrong host.** `experiments/physical/datasets/circuit_export/frames`
> holds the **1521 PNG (439 MB)** of the 18.08 circuit recording on the **Jetson**
> (`admit14-cobraflex`), temporally ordered, `ey` span 505 mm, 95.3 % paired —
> together with `lane_00_firstpass` (1205) and `lane_A` (631), 3357 frames in all.
> They are invisible to `git` by the `experiments/physical/datasets/*/frames/`
> rule in `.gitignore`, which is exactly why the compute host's filesystem search
> found nothing and concluded they were gone. This is the failure mode CLAUDE.md's
> host note warns about: **say which host you searched before writing "the data is
> missing"**.
>
> The gate has now been run against that recording (§8.1) and **PASSES on both
> arms**. The paragraph below stands unchanged as the procedure; only its
> precondition is satisfied.
>
> Kept because it is still true: running the selector without `--real` narrows 100
> candidates to a handful but **does not authorise driving one**. The tool prints
> this itself and exits non-zero when nothing clears the floors. And the selector's
> `--real` path needs the other ~99 checkpoints, which live on the compute host,
> not on the Jetson — on the car only the chosen 1650k is present, so the Jetson
> can run the **gate** but not the **ranking**.

Then cross-check the shortlist by driving in simulation (`SC-NOM-01` nominal
eval) before the track. A checkpoint that transfers but cannot drive complex_b
is not a candidate.

**Once the frames exist, the whole gate is one command:**

```bash
bash tools/run_deploy_gate.sh experiments/physical/datasets/<name>
```

It ranks every checkpoint against the real recording, then runs the gate on the
chosen one raw and rectified. Verified end to end on 23.08.2026 against a
surrogate dataset built in `record_lane_dataset`'s exact layout — all three
stages, including the selector's `--real` path and the probe's PASS branch, which
until then had only ever been exercised by unit test.

**Two requirements on the recording, either of which will silently invalidate the
result if missed.** The frames must be in **temporal order**: the gate scores the
`k=4 history` arm, which stacks four *consecutive* frames the way
`rl_policy_node` does, and an unordered set stacks four unrelated views and reads
as noise. And the pass must **deliberately weave** — the probe refuses a
recording spanning under 60 mm of `ey`, because a centred pass cannot show a lane
response.

### 7.3 Bring-up, with rectification on

`rectify_calibration` is a **single launch argument feeding both**
`rl_policy_node` and `cv_lane_estimator_node`. That is deliberate: the policy did
not have the parameter before 20.08, so a rectified deployment would have had the
cage arbitrating a canonical world while the CNN saw the raw 160° lens. Give both
or neither — the launch makes that structural.

```bash
ros2 launch cobraflex_rl deploy_cobraflex.launch.py \
  checkpoint:=<abs>/ppo_gz2d_sim2real_v2_2024_<steps>_steps.zip \
  rectify_calibration:=<abs>/experiments/calibration/M6_results.json \
  mode:=enforcement
```

Rectification is **[provisional] and has never run on hardware.** Offline on 3357
real frames it restores the estimator to slope 0.998 and lane width 249.9 ± 1.5 mm
against a 250 mm ruler, but that is offline. Enable it behind
`preflight_deploy.py lanecheck` (§4), not blind: `lanecheck` compares the
estimator's `ey` against a tape measure on the track, which is exactly the
measurement that would catch a rectifier configured wrong.

### 7.4 Sequence

1. `select_sim2real_checkpoint.py` **with `--real`** → a shortlist that cleared the gate.
2. `SC-NOM-01` nominal eval in Gazebo on the shortlist → confirms it still drives.
3. `preflight_deploy.py stage0` → camera alone.
4. `preflight_deploy.py stage1`, **wheels up**, with the launch in `mode:=monitoring`
   → chain flowing. (`stage1` takes no `--mode`; the mode belongs to the launch.
   Corrected 26.08.2026 — the old wording failed mid-bring-up.)
5. `preflight_deploy.py stage2`, **wheels up** → actuation envelope.
6. `preflight_deploy.py lanecheck --true-ey <tape>` **on the track**, rectification on →
   this is where a bad rectifier is caught, and where M-7 §3b's outstanding
   hands-off tape measurement finally gets taken.
7. Drive in `enforcement`, tethered.

### 7.5 What would falsify the whole exercise

Stated in advance so the track session is a test and not a demonstration.
**All three were scored, and none fired** — appended after the fact, kept in the
order they were written:

* the lane-independent steering bias is still ≫ the lane-dependent swing (the
  18.08 failure, unchanged) → the mirroring did not transfer, or the bias has a
  second cause this work did not find.
  **Not falsified:** bias/swing **0.07–1.10** for v2 against **12.9–19.2** for
  the trunk as deployed on 18.08 (D-72), and the car drove (§8).
* the estimator's `ey` still reads 0.68–0.83 × true **with rectification on** →
  the residual is not mount pose, and M-6's model is wrong somewhere else.
  **Not falsified:** the rectified nine-point tape sweep of 31.08 gives scale
  **1.058 / 0.991** with no intercept (§10.2). M-6's model was right and
  rectification is what realises it. *What the criterion did not anticipate is
  the defect that actually bites — the error is not a gain at all, it is
  **place-dependent** (D-79, §12), which no single-location sweep could have
  seen.*
* the policy drives but the cage intervenes constantly on C-06 → the
  `delta_max_steering_per_cycle` coupling flagged as a physical-transfer risk in
  D-69 (T2) has materialised, and the rate limiter, not the policy, is driving.
  **Not falsified:** C-06 fires **3.4 %** of moving cycles on hardware against
  **3.0 %** in simulation at the same checkpoint (§8.10, ledger term 10). N = 1,
  monitoring.

### 7.6 Re-running the campaign on the new policy

The 27-scenario × 2-mode × seed-2024 matrix is **1890 runs** and is what produced
the D-69 verdict of record for the trunk. Re-running it on a v2 checkpoint is
worthwhile — the training distribution changed enough that the trunk's numbers do
not carry over — but it is **not a prerequisite for driving**, and it must not be
started before two things are true:

1. a checkpoint has been chosen by §7.2 (transfer), not by reward; and
2. the **D-43 preflight passes on that checkpoint's nominal eval trace**. Every
   scored 2-D campaign to date was authorised this way (`tools/d43_preflight.py`,
   PASS 7/7 for the 550k trunk); it is what catches a cage acting on a CV estimate
   that disagrees with ground truth on a centred vehicle.

The invocation follows `experiments/sim/campaign_2d_ppo550k/resume_campaign.sh`,
including its **`flock` guard** — that guard is not decoration. On 29.07 two
campaign processes touched the same run directory and 222 runs had to be
quarantined; the `ps`/`pgrep` check that was supposed to prevent it failed because
the checking process matched its own command line.

```bash
exec 9>experiments/sim/campaign_v2/.campaign.lock
flock -n 9 || { echo "ABORT: another campaign holds the lock"; exit 3; }

python tools/run_campaign.py \
  --scenario-dir scenarios_complex_b \
  --model-path policy/checkpoints/ppo_gz2d_sim2real_v2_2024_<steps>_steps.zip \
  --train-config src/cobraflex_rl/config/train_ppo_camera_2d_sim2real_v2.yaml \
  --seeds 2024 --modes enforcement,monitoring \
  --out experiments/sim/campaign_v2 --resume
```

Two things to expect, both consequences of D-72 rather than surprises:

* **SC-FRONT-07 is no longer an OOD probe** for this policy (§7.1, and the note in
  `docs/05`). Read its result as a regression test.
* **The `--train-config` matters.** It carries the mirror and geometric blocks, so
  the campaign's own evidence records what the policy was trained under. Passing
  the trunk's config instead would silently mislabel the run.

Do **not** re-score G4 with this. The simulation verdict of record is the 550k
trunk's 1890-run campaign (D-67/D-69), and a v2 campaign is posterior evidence
under Phase 5 — the same posture D-71 took.

## 8. The 2026-08-26 track session: v2 transfers, and four things stop it

**Status: the v2 policy DROVE the real circuit.** Across the session it covered
**19.28 m** — one circuit perimeter's worth (complex_b in simulation is 19.22 m) —
in six segments separated by five operator resets, plus two earlier drives of
14.45 m and 5.12 m. While moving it held **`|ey|` median ≈ 9 mm** and fired **no
safety rule at all**; the only cage rule it touched was C-06. This is the first
physical evidence that a track-'E' policy transfers, and it is what D-71 said the
550k trunk did not do.

It is *not* a clean lap, and must not be reported as one. Everything below
separates what was measured from what was inferred.

Evidence: `experiments/physical/runs/preflight_20260826_*` (7 runs) and
`track_v2_fulllap{,2,3}_20260826T*` (3 runs, the last two with an odometry rosbag).
Provenance for every one of them: commit `7de600fe`, `cage.yaml` v0.6.1
(`sha256 4287fe71…`), checkpoint `ppo_gz2d_sim2real_v2_2024_r2_1650000_steps.zip`
(`sha256 c67c3daf…`, identical to the hash the compute host recorded in
`d43_preflight_v2_1650000.json`), `M6_results.json` (`sha256 895b86cb…`), Jetson
`admit14-cobraflex`, ROS 2 Humble.

### 8.1 The deployment gate, run against real imagery — PASS both arms

`tools/run_deploy_gate.sh`'s probe stages, on the 1521-frame 18.08 circuit
recording (§7.2). Floors are retention ≥ 0.50, bias/swing ≤ 1.00, right ≥ 10 %:

| arm | n | swing retention | bias/swing | right | r² | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| sim control | 140 | — | 0.04 | 66.4 % | 0.373 | — |
| **raw optics** | 1447 | **1.29** | **0.10** | 23.2 % | 0.546 | **PASS** |
| **rectified** | 1447 | **1.21** | **0.17** | **66.6 %** | 0.539 | **PASS** |

Reports: `experiments/sim/eval_gz2d/sim2real_probe_v2_circuit_{raw,rectified}.json`.

Two readings. The **23.08 CHANGELOG's prediction is confirmed**: it recorded that
the `k=4 history` arm's BLOCKED verdicts on the surrogate were "an artefact of the
dataset, not a finding", and that "the real 18.08 recording is temporally ordered
and the arm will be valid there" — it is, and it passes. And **rectification
restores the turn distribution**: right-turn share goes 23.2 % → 66.6 %, against
the sim control arm's 66.4 %. That is the geometric correction doing exactly what
§7.3 predicted, and it is the first quantitative argument for deploying rectified
rather than an offline one.

> The committed `sim2real_probe_v2.json` / `_rectified.json` are **surrogate**
> results from the compute host (`.../scratchpad/surrogate_physical/frames`, n=417,
> both BLOCKED). They are the 23.08 end-to-end verification of the gate machinery,
> not a transfer result, and are easy to misread as one. The `_circuit_*` files are
> the real gate.

### 8.2 Staged preflight on the car — all four stages pass

`stage0` PASS (640×360 `bgr8`, camera stamp median 50.0 ms = 20.0 Hz, `fx` 320 as
the IPM assumes). `stage1` PASS. `stage2` PASS in **both** modes; enforcement is
the one that matters, because it closes the 2026-08-05 review's item 1 on
hardware: **235 exact-zero `/cmd_vel` samples alongside 235 sub-deadband cage
cycles**. Until now that invariant was asserted by unit test only.

`lanecheck` PASS with the car parked and `policy:=false` — `sd_ey` **5.3 mm**
(limit 10) and `sd_epsi` **0.80°** (limit 5) on `near_secant`; **5.7 mm / 0.25°**
on `joint_pair_quadratic`.

**`lanecheck` did NOT close M-7 §3b.** It was run without `--true-ey`, so only the
automatable half — "is the parked estimate quiet" — was answered. The number that
decides whether C-01 fires late still needs a tape measure and remains open.

### 8.3 Rectification, demonstrated on hardware

Two launches back to back, same mode, same fit mode, same 20 s window, car
untouched — the only difference is `rectify_calibration`:

| car stationary | raw | rectified |
| --- | --- | --- |
| perception-invalid cycles | 86/191 = **45 %** | 11/200 = **5.5 %** |
| `ey` mean (full CSV) | **−97.7 mm** | **+7.7 mm** |
| `ey` sd | 104.5 mm | **27.8 mm** |
| C-01 fires | **102** | **0** |
| `raw_steering` | +0.0116, sd 0.002 (frozen) | +0.103, sd 0.032, −0.137…+0.175 |

Unrectified, the estimator reads a centred car as ~100 mm off and fires C-01 102
times while stationary. `rectify_calibration` should stop being described as
`[provisional]` on the strength of this: it is the difference between a usable
and an unusable perception input. (It remains provisional as to *accuracy* — see
8.2 on the missing tape measurement.)

### 8.4 `heading_fit_mode` is decisive under motion and invisible at rest

Also a controlled pair — same rectification, same mode, sequential, differing only
in `heading_fit_mode` / `heading_gain`:

* `joint_pair_quadratic` / 1.6 (the launch default, the trunk's contract): the
  estimator flickers invalid, C-05 latches within seconds, the fail-safe stops the
  car. **1.08 m travelled.**
* `near_secant` / 1.0: 0 invalid cycles, 0 emergencies, only C-06. **14.45 m.**

And yet **parked, both are quiet** (8.2: 0.25° vs 0.80° sd, if anything favouring
the default). The failure is induced by motion and vibration, so a static bench
test cannot see it. This is D-71 §3's method lesson recurring: match the
measurement to the quantity — a single-pose check would have cleared a
configuration that cannot drive.

The launch default is still `joint_pair_quadratic`, deliberately, because it is
the D-43 perception contract the trunk was scored under. **Changing it is an open
decision**, not a bug fix: it would put the deployed cage on a different estimator
from the one every scored campaign used.

### 8.5 What stops the car — C-05 has no operational story on hardware

Measured, in the rosbag, on `track_v2_fulllap2`:

```
t=18,15 s   cage + policy start, car pulls away
            ── 20,5 s of clean driving, |ey| median 8,2 mm, zero safety rules ──
t=38,65 s   /perception_invalid True for 120 ms
t=38,68 s   C-05 latches  →  car stopped, and never recovers
```

C-05's exit is deliberately asymmetric (`require_explicit_reset`, STPA-informed
against oscillation at the trigger boundary, `cage.yaml` §c05_emergency). That is
correct in simulation, where a scenario ends anyway. **On a vehicle it means a
120 ms glitch — one the estimator recovered from by itself — stops the car
permanently, because nobody sends `/cage_reset`.** Confirmed live on the third
run: `/emergency` **true** while `/perception_invalid` was already **false**.

This is not a defect in the cage. It is a gap between an artefact validated
against simulated episodes and a vehicle that has to keep operating, and it is
the single most deployment-relevant finding of the session. **It needs a decision
(D-NN), not a patch** — the candidates are a bounded auto-recovery on the
perception trigger, an operator reset path, or removing the cause upstream (8.6).
Nothing has been changed.

> **Taken 27.08.2026 as D-74:** the second candidate, and outside the cage.
> C-05 is unchanged — in simulation `require_explicit_reset` is nearly inert
> because a scenario ends, so a bounded recovery inside the rule would be a
> change to the verified artefact whose entire effect is on hardware, verified
> by nothing. §9.5 is the operating posture; the recovery question itself is
> deferred, not answered.

Lap 3 was driven with the third option taken manually: **five `/cage_reset`
publications by the operator**, each with perception already healthy, no C-01…C-04
active and `v = 0`. Segments between resets: 29 s/+4.87 m, 29 s/+4.92 m,
6 s/+0.89 m, 24 s/+4.15 m, 1 s/+0.17 m, then the terminal event of 8.8.

### 8.6 The camera cannot feed the control loop

101 `no camera frame for 1 control cycles — publishing no /raw_action` warnings in
one run. It is what produces the ≥ 4 consecutive bad cycles the estimator's own
debounce (`min_invalid_cycles=4`) needs before it declares perception invalid —
i.e. **the starvation is upstream of 8.5**.

Cadence, measured over a whole driving run: **7.3 Hz** average against the trained
10 Hz, gaps median 111 ms / p90 207 / p99 579 / **max 995 ms**, 23.3 % of cycles
over 150 ms. At 0.172 m/s a 995 ms gap is **171 mm travelled open-loop** — more
than C-01's whole 160 mm threshold.

Cause is CPU. Measured with **layer 3 not running**: load average 5.49 on 6 cores,
`csi_camera_node` 53.7 %, `rviz2` 52.1 %, `zed_node` 51.1 %, `nvargus` 15.9 %,
`anydesk` 11.9 %, `Xorg` 9.0 %. Killing `rviz2` alone took the loop from 7.3 Hz to
**9.5 Hz** and lengthened every driving segment. `use_rviz:=false` is already the
deploy default for Layer 1; **Layer 2's bring-up should not leave rviz running
either.** Freeing further headroom is the next work item.

> **Done the same afternoon — see §8.10.** `lane_camera_capture_fps` 60 → 30 took
> the delivered rate to 19.0 Hz at 96.5 % of a core (from 15.2 Hz at 134.3 %), and
> `/state_obs` now holds 9.84 Hz with a worst gap of 295 ms. It was **not enough to
> buy a lap on its own**: the run with the best loop rate of the session still died
> in 16 s, on §8.7.

### 8.7 ZED pose jumps, measured rather than inferred

`cobraflex_sensors.launch.xml` has warned since 06.08 that a ZED loop-closure jump
"enters the ekf as an absolute pose with ~1e-5 covariance and
`odom0_differential:false`, so the filter follows it hard and emits a spurious
velocity spike straight into the cage's speed". That is now measured:

* a **3621.8 mm pose displacement in a single frame** (17.81 m/s implied), driving
  `/odometry/filtered` `vx` to **−4.03 m/s**;
* ten smaller jumps (7–76 mm/frame, 0.5–1.7 m/s implied) *during* driving;
* on an earlier run a spike took the cage's speed to **5.479 m/s** — 25× the
  0.22 m/s contract — one cycle after a healthy 0.156 m/s, firing C-04 → C-03 →
  C-05 and braking to `safe_throttle −0.500`.

`ekf_hw.yaml` fuses the ZED's **pose** (`odom0_config` x, y, yaw) and deliberately
not its twist, so velocity is obtained by differentiating a signal that teleports.
Restarting Layer 2 (fresh area memory) **delays but does not remove** the jumps:
the first attempt spiked at 4.3 s, the attempt after a restart drove 20.5 s clean
and its big jump came at 53 s. Partial support for the loop-closure hypothesis, not
proof. Candidate fixes, none applied: `odom0_pose_rejection_threshold`
(robot_localization's designed outlier gate), raising the pose covariance, or
turning off the wrapper's `reset_odom_with_loop_closure`.

> **The third one was applied the same afternoon, and it discriminates — §8.10.**
> `config/zed_deploy_overrides.yaml` (`area_memory:false`,
> `reset_odom_with_loop_closure:false`) against the run 13 minutes earlier without
> it: single-frame pose steps over 50 mm go **116 → 0** in 509 s, and the ekf's
> `vx` — the cage's only speed input — goes from 4.50 m/s to a maximum of 0.213
> against a commanded 0.22. "Partial support, not proof" is now proof, at the cost
> of unbounded slow drift (§9.4a). Recorded as **D-73**.

In `monitoring` this is survivable only because the cage does not apply
corrections — but `vehicle_control_node` is emergency-aware and zeroes `/cmd_vel`
on `/emergency` **in either mode**, so a spike still ends the run. **In
`enforcement` it would end a scored lap.**

### 8.8 C-04's dead zone, and the last curve

The session's terminal event, twice over: the car left the lane in the **first half
of the final curve, the re-entry to the straight** — the same curve the very first
drive of the day failed to complete. Unlike everything in 8.5, this was a **real
safety intervention**: `ey −118.5 mm`, `epsi −25.60°` (just past C-02's 25°),
**C-02 and C-03 firing together**, and then total loss of the lane —
`/state_obs` stopped publishing and the cage ran on a frozen state.

And the rule that exists to protect that case cannot act:

```
cage.yaml  c04_speed_ceiling.v_max_curve_mps = 0.25
launch     max_speed_mps                     = 0.22
```

**0.22 < 0.25, so C-04 cannot fire on commanded motion.** D-69's finding (ii)
recorded this as a coverage gap — "C-04 never fires (0/1890) … the ODD-3 speed
ceiling stays untested from above". It is no longer only a coverage gap: on the
physical circuit the vehicle enters its tightest curve at full contract speed
with no cage-side speed protection. That promotes the item from *rule without
test coverage* to *rule that does not protect a real physical case*.

> **Amended 01.09.2026 — the literal "can never fire" is false (§13.5).** C-04
> **did** fire on hardware: 58 and 40 cycles in the two surviving caged runs of
> 31.08, **100 % of them at a reported 0.25–1.30 m/s**, which is impossible under
> power at a 0.22 m/s cap. Those are ZED velocity artefacts (ledger term 8)
> entering the cage's only speed input, and in one run they enter the
> reset-withhold path — a sensor artefact blocking recovery from the rule it
> raised. The *argument* of this section stands unchanged; what changes is that
> the rule's dead zone is not the only thing wrong with it. D-75's decision
> (leave `cage.yaml` untouched; re-arming blocked on a capture session) stands.

Three candidate causes for the departure itself, none discriminated:

1. curvature — the real re-entry curve may exceed anything in complex_b;
2. loop starvation (8.6) — at 0.19 m/s a 995 ms gap is 180 mm of blind travel,
   and a curve is where that hurts;
3. M-7's measured **pairing collapse beyond ~±55 mm of `ey`**, which a tight curve
   drives the car into.

Lowering `max_speed_mps` would help *all three at once* and therefore **cannot
discriminate between them**. Fix the starvation first (8.6), then vary speed.

### 8.9 What this session did NOT establish

* **No clean lap.** 19.28 m of distance with five operator resets and a lane
  departure at the end. No scenario has been scored on hardware; `verdict_phys`
  stays open, exactly as CLAUDE.md's TBD note says.
* **No `--true-ey`**, so M-7 §3b is still open and the C-01-fires-late question is
  unanswered (8.2).
* **The failure locations are not localised.** Cross-referencing
  `/perception_invalid` against the ZED pose gave seven events, two pairs of which
  repeat within 5–6 cm — but the absolute coordinates are not comparable across the
  run, because the frame that measures them is the one that jumps (8.7). One event
  lands at the exact origin, which is a ZED odometry reset rather than a place. The
  measurement that would settle it is **recording `/camera/image_raw_lane` in the
  bag and looking at what the estimator saw**; do that next session.
* **`cage_logger_node` writes no reproducibility metadata.** `metadata.json` carries
  only `{mode, run_id, created_utc, cycles_logged}` — no commit, no cage-YAML hash,
  no checkpoint hash, contrary to CLAUDE.md's rule for `experiments/physical/runs/`.
  This is pre-existing (the 18.08 `track_first_drive` is identical), and it is why
  the provenance for this session is recorded at the head of §8 by hand.
* **Two contradictory D-43 preflights for the same checkpoint are committed side by
  side** with nothing distinguishing them: `d43_preflight_v2_1650000.json` (PASS,
  `nom_clean` trace) and `d43_preflight_v2_1650k.json` (BLOCKED, 35 centred-`ey`
  error steps, `nom_final` trace, 5 minutes earlier). The BLOCKED one is a trace
  **retracted by I-8** — it measured the randomisation, not the policy. It should be
  marked or removed.
* **docs/17 §7.4 step 4 names `preflight_deploy.py stage1 --mode monitoring`.**
  `stage1` has no `--mode`; the mode belongs to the launch.

### 8.10 The afternoon runs: both fixes applied, and the 18.05 m they bought

Two runs, 13 minutes apart, committed in `624fba1d` alongside §8 but not
described by it — so §8.6 still ends *"Freeing further headroom is the next work
item"* and §8.7 still lists candidate fixes *"none applied"*, and both sentences
were overtaken the same afternoon by the same commit. This closes that.

**The camera fix.** `lane_camera_capture_fps` 60 → 30 on Layer 2. `throttle_fps`
sits *after* `nvvidconv`, so every earlier measurement ran the sensor at 60 fps
and `nvargus-daemon` — a different process, doing the ISP work — never saw the
saving. Measured on the car with the real two-subscriber topology, as % of one
core: capture 60/read 20 delivered **15.2 Hz** at 134.3 % total; capture 30/read
20 delivered **19.0 Hz** at 96.5 %. Capturing at 60 was not merely wasteful but
*harmful* — 38 % of a core more for a worse rate. Rationale in
`csi_camera_node.gstreamer_pipeline`'s docstring.

**The ZED fix** (**D-73**). `config/zed_deploy_overrides.yaml` (new), applied
through the wrapper's `ros_params_override_path` from
`cobraflex_sensors.launch.xml`:
`area_memory: false` and `reset_odom_with_loop_closure: false`, plus object
detection and point clouds off — neither has a subscriber in this chain. The
trade is stated in the file: without area memory the odometry *drifts* more over
time, which is acceptable **here and would not be in a navigation case**, because
the cage reads velocity, not position, and a slow drift produces no spike. A jump
does.

| | `fulllap3` 08:37 (neither fix) | `cpufix` 09:51 (camera only) | `noloopclosure` 10:04 (both) |
| --- | --- | --- | --- |
| driving | 19.28 m, **6 segments, 5 resets** | died at t+16.2 s | **18.05 m, one segment, 0 resets** |
| control tick (`/cage_status`) | 8.18 Hz, p90 205 ms, max 618 | **9.59 Hz**, p90 131, max 244 | 8.68 Hz, p90 189, max 598 |
| `/state_obs` | 9.86 Hz, max 204 ms | 10.00 Hz, max 122 | 9.84 Hz, max 295 |
| ekf steps > 50 mm / frame | 75 (max 5074 mm) | 116 (max 4061 mm) | **0** (max 29.8 mm) |
| ekf `\|vx\|` max | 4.61 m/s | 4.50 m/s | **0.213 m/s** |
| perception-invalid samples | 7.7 % | — | **0.2 %** (11 of 5027) |
| rules while driving | C-02 ∧ C-03, C-04, lane departure | C-04 → C-03 → C-02 → C-01 | **C-06 only** |

Read the two fixes separately, because the runs separate them. `cpufix` has the
best loop rate of the session — 9.59 Hz, only 4.5 % of cycles over 150 ms — and
still died in 16 s, on a ZED pose jump that fired C-04 → C-03 → C-05. **The
camera fix alone does not buy a lap.** `noloopclosure` has a *worse* loop rate
than `cpufix` and drove for 101 s, because the thing that was ending runs was
never the loop rate.

**§8.7's hypothesis is now discriminated.** The two runs are the controlled A/B
the earlier evidence lacked — same checkpoint, same mode, same rectification, 13
minutes apart, differing in the override file. Pose jumps go **116 → 0** over
509 s, and the ekf's `vx`, the cage's only speed input, goes from 4.50 m/s to a
maximum of **0.213** against a commanded 0.22. §8.7 recorded "partial support for
the loop-closure hypothesis, not proof"; this is the missing arm.

**The lap.** `track_v2_noloopclosure_20260826T100450Z`, `monitoring`, rectified,
`near_secant`/1.0: **18.05 m in 101.1 s as a single uninterrupted segment**, no
operator reset, `|ey|` median **18.7 mm** (p90 44.7, max 98.7 — C-01's threshold
is 160), `|epsi|` median **6.54°** (max 18.91, C-02's is 25), speed ≤ 0.213 m/s,
and **`cycles_since_last_state` never above 0** — unlike §8.8, the cage never ran
on a frozen state. The only rule it touched was C-06, 30 times: **3.4 % of moving
cycles, against the 3.0 % nominal intervention that chose this checkpoint in
simulation** (D-72). That is the closest agreement between a sim and a hardware
figure anywhere in Phase 5, and it is a second confirmation that D-69's T2
transfer risk did not materialise.

**It is still not a closed lap, and it did not end the way a lap ends.** At
t+101.05 s `/perception_invalid` went true for **400 ms** — one event, the other
six of the run's seven all inside the first 3.1 s, before the car moved. C-05
latched on it, `require_explicit_reset` kept it latched, and the run was over:
0.80 m in the remaining 396 s. When it latched the car was **27 mm from the lane
centre**, heading error 10.3°, in the tightest curve on the circuit
(`kappa_ahead` 0.75 1/m, radius 1.34 m) — the same curve §8.8's departures
happened in. So the §8.5 finding is not merely unchanged, it is sharpened: one
perception glitch per lap is now the *whole* difference between a completed
circuit and a stopped car.

**What this run does NOT establish.**

* **Whether it closed the loop.** The odometry says it stopped **2.11 m** from
  the start point having turned **314°** of 360°, and never came back closer.
  But the fix that removed the jumps is the same one that removed the
  loop-closure correction, so slow drift is now unbounded and 2.11 m over 101 s
  is within what this odometry can invent. **This cannot be settled from
  `/odometry/filtered` at all** — it needs a mark on the floor and a tape
  measure (§9.4), which would simultaneously give the first measurement of what
  the ZED override costs in drift.
* **The capture-rate change under motion.** `csi_camera_node`'s own docstring
  flags it: the photometric check behind 30 fps (grey mean 101.96 → 101.69,
  Laplacian variance 667 → 762) was run with the **car stationary**, so it cannot
  see motion blur, which is the one thing a longer exposure would cause. §8.4's
  lesson exactly. Unverified.
* **Anything about enforcement.** Every run of the session was `monitoring`.
* **Why the estimator lost the lane.** §8.9's open item survives the session: no
  frames were kept, so the 400 ms that cost the lap is still an unexplained
  event. `frame_capture_node` (§9.2) exists to close it next time.
* **The loop rate is still short of the contract**, and the bottleneck has
  moved. `/state_obs` now holds 9.84 Hz with a worst gap of 295 ms, while
  `/cage_status` runs at 8.68 Hz with p90 189 ms — i.e. **12 % of estimator
  cycles never produce a control cycle**. `/cage_status` is published from
  `cage_ros_node._on_raw_action`, so that rate *is* `rl_policy_node`'s 10 Hz
  timer slipping. The camera starvation of §8.6 is fixed; CNN inference is what
  is left.

## 9. Next track session (prepared 27.08.2026): one complete monitoring lap

> **THAT SESSION HAS HAPPENED — it ran on 31.08.2026 and §10 is its record.** Read §9
> as the preparation it was, not as pending work. Its goal was **not** achieved (best
> 14.56 m, against the 18.05 m of 26.08), and §9.6's falsification criteria are scored
> in §10.1. The three nodes prepared here were all launched for the first time; two of
> them needed fixes on the spot (§10.4).

**Goal, stated narrowly:** one uninterrupted circuit of the physical track in
`mode:=monitoring`, with enough evidence recorded that whatever happens can be
explained afterwards *from the run itself*. Not a scored run — see §9.7 for what
it deliberately is not.

The 26.08 session came within **2.11 m** of that (§8.10) and lost the lap to a
single 400 ms perception event nobody can explain, because nothing kept the
frames. Everything below is aimed at those two facts: finish the lap, and be able
to say why if it does not.

### 9.1 The four evidence gaps, and what now closes them

| Gap, as found on 26.08 | Closed by |
| --- | --- |
| `metadata.json` carried `{mode, run_id, created_utc, cycles_logged}`, so §8's provenance is a hand-written paragraph (§8.9) | `cage_logger_node` `platform:=physical` — commit, `cage.yaml` hash, checkpoint hash, rectification hash and the deployed contract, written **at start-up** as well as on close |
| Layer-2 settings (`capture_fps`, the ZED overrides) recoverable only from a run's *name* | `tools/run_physical_lap.sh` probes the **running** nodes with `ros2 param get` → `layer2.json` |
| No frames from the perception events (§8.9, asked for after 18.08 and again after 26.08) | `frame_capture_node` — RAM ring buffer, dumps ±window around each event |
| Bag and CSV covering different windows; `/cage_reset` and `/emergency` not recorded at all | one run id for CSV, bag, frames and reset log; both topics now in the list |

None of this touches the cage. `cage.yaml` is unchanged and a test
(`test_deploy_evidence_contract.py::test_c05_itself_is_untouched`) fails if
`require_explicit_reset` is edited, so the §8.5 decision cannot be taken by
accident.

### 9.2 `frame_capture_node` — what it does and why it is not a bag

Steady state it appends the incoming `sensor_msgs/Image` to a deque and does
nothing else: no decode, no disk. On a rising edge of `/perception_invalid` or
`/emergency` (or a manual `std_msgs/Empty` on `/frame_capture_trigger`) it writes
the previous `pre_seconds` and the next `post_seconds` as PNG, on a **writer
thread**, into `<run>/frames/` with `<run>/capture_events.csv` naming each frame's
event, reason and stamp. The stamp is the join key to `/state_obs` in the bag.

`ros2 bag record` on the image topic is what must not be done here: raw 640×360
bgr8 at 20 Hz is 13.8 MB/s to eMMC, and running that alongside the deploy chain
crashed the Jetson on 18.08 and cost `circuit_survey` its bag index and the tail
of its CSV. At 26.08's event rate — one in-motion event in 101 s — the ring
buffer costs about 100 frames, ~20 MB, against ~1.4 GB for the naive bag.

Overlapping triggers **extend one event** rather than opening several: a
flickering estimator is one failure, and the alternative spends `max_events` on
the first second of the run. Defaults 3 s pre / 2 s post, 8 events, 4000 frames.

### 9.3 Bring-up

Same three layers as §3, with `use_rviz:=false` on Layer 1 **and rviz not left
running from anywhere else** — killing it alone took the loop from 7.3 Hz to
9.5 Hz on 26.08 (§8.6). Layer 2 must come up with the ZED overrides in force
(they are the launch default since `624fba1d`; the script checks and asks).

```bash
source ~/MT-SE4AI-Safe-RL-Cobraflex/scripts/setup_deploy_env.sh   # every terminal

# 1 · Layer 1
ros2 launch cobraflex cobraflex_bringup.launch.xml use_rviz:=false
# 2 · Layer 2 — without the lidar, which nothing in this chain reads
ros2 launch cobraflex cobraflex_sensors.launch.xml use_lidar:=false
# 3 · preflight, wheels OFF THE GROUND
python3 tools/preflight_deploy.py stage0
python3 tools/preflight_deploy.py stage1
python3 tools/preflight_deploy.py stage2
python3 tools/preflight_deploy.py lanecheck --true-ey 0.0     # see §9.4
# 4 · the lap — one command, bag and chain bound to one run id
tools/run_physical_lap.sh --label lap01 \
    --checkpoint /abs/path/to/ppo_gz2d_sim2real_v2_2024_r2_1650000_steps.zip
```

The script defaults to `mode:=monitoring`, rectification on
(`experiments/calibration/M6_results.json`), `near_secant`/1.0 and
`reset_proxy:=observe`, and prints every one of those choices before it starts.
Two of them are **departures from the launch defaults** and it says so on the
console each time: rectification, settled on hardware by §8.3's A/B (C-01 fires
102 → 0 with the car parked), and `heading_fit_mode`, which §8.4 records as an
**open decision** — `joint_pair_quadratic`/1.6 is the D-43 contract every scored
campaign used, `near_secant`/1.0 is the one that can drive this car (14.45 m
against 1.08 m). A diagnostic lap needs the second. A scored run may not use it
until that decision is taken.

### 9.3b The CPU budget, and why there is no separate "RL sensors" launch

The obvious move after §8.6 is a stripped Layer 2 that starts only what the RL
chain consumes. It was considered and **rejected**, for three reasons.

**Only one node in Layer 2 is unused, and it is one argument away.** The chain
reads the CSI camera and `/odometry/filtered`; `ekf_hw.yaml` fuses
`/zed/zed_node/odom` alone (its `imu0` block is commented out), and **no cage
rule reads a `LaserScan`** — C-01…C-06 are lane, heading, TTLC, speed, emergency
and rate. So the lidar is pure load in an RL run. It now has a `use_lidar`
argument (default `true`, because `cobraflex_automatic.launch.xml` is a
lidar-based Layer-3 controller). How much it saves is **not measured**: the A2M8
does not appear in §8.6's load table, which lists everything above 9 % of a core,
so it is somewhere below that.

**A second launch would duplicate three load-bearing settings.** The ZED include
carries `publish_urdf:=false`, `publish_tf:=false` (two publishers rooted at
`odom` would make `zed_camera_link` reachable by two paths — the ekf is the
single owner of that edge) and the documented NO-OP that explains why the loop
closure has to be turned off through the override file. A copy is a second place
for those to drift apart, and this repo already has one instance of that failure
mode on record (§8.9's two contradictory D-43 preflight reports, committed side
by side with nothing to distinguish them).

**The CPU that matters is inside `zed_node`, not in the node list.** §8.6 measured
it at **51.1 % of a core** with Layer 3 not even running, and the lever for it is
`config/zed_deploy_overrides.yaml` — which already turns off object detection and
point clouds, and now also drops three publications with no subscriber at all:
`general.pub_frame_rate` 15 → 5 Hz (the chain reads no ZED image),
`sensors.sensors_pub_rate` 100 → 30 Hz (the ekf's IMU input is commented out) and
`pos_tracking.publish_3d_landmarks` → false.

**The big lever is deliberately not pulled.** `depth.depth_mode` is
`NEURAL_LIGHT` — a neural depth network per frame whose only consumer here is
positional tracking — and `depth.depth_stabilization` is 30. Dropping to
`PERFORMANCE` / 1 is the obvious saving and it is written into the override file
**as a commented block, not as a change**, because both alter tracking quality
and the tracking pose is the **cage's only source of speed**: C-03's TTLC,
C-04's ceiling and C-05's high-energy trigger all read `/odometry/filtered`. A
CPU saving that degrades that signal is not a saving. Decide it the way §8.10
decided the loop closure — two runs back to back, one line different, comparing
`zed_node`'s CPU **against** pose drift and per-frame steps.

**And keep the expectation honest.** After the 26.08 camera fix the bottleneck is
no longer Layer 2: `/state_obs` holds 9.84 Hz and `/cage_status` runs at 8.68 Hz,
so what is missing a control cycle is `rl_policy_node`'s inference timer (§8.10).
Freeing Layer-2 CPU gives that timer headroom; it is not the thing that puts the
loop back at 10 Hz.

`tools/run_physical_lap.sh` records all of it — `pub_frame_rate`, `depth_mode`
and whether the lidar is running — into the run's `layer2.json`, so a future
session can attribute a rate change to a configuration instead of guessing.

### 9.4 The two measurements nothing automates

> **Outcome (01.09.2026): (b) was done, (a) was not.** (b) is the 31.08 offset
> sweep (§10.2) — and it **overturned** the figures this item was written to
> check. (a) — floor mark plus tape — was never taken, and it is the reason
> whether 26.08's best run closed its loop **cannot be settled**: D-73 removed
> the loop-closure correction, so odometry cannot answer it. Physical work is
> closed; (a) stays as a named future-work item, not as a pending action.

**(a) Mark the start position.** Tape a cross on the floor, put the car on it,
and after the run measure the distance from the cross to where it stopped. This
answers two things at once that `/odometry/filtered` no longer can: whether the
lap actually closed, and **what the ZED override costs in drift**. §8.10's 2.11 m
end-to-start gap is not interpretable without it — with `area_memory:false` the
odometry has no loop-closure correction, so slow drift is unbounded, and 2.11 m
over 101 s is within what it can invent. Record it in the run directory.
**Not done.**

**(b) `lanecheck --true-ey`.** Open from M-7 §3b when this was written, and the
number that was thought to decide whether C-01 fires late: on the **unrectified**
path the estimator read `ey` at 0.68–0.83 × true − 10 mm, putting C-01's 160 mm
threshold at a true 207–241 mm. 26.08's `lanecheck` ran **without** `--true-ey`,
so it answered only "is the parked estimate quiet" (5.3 mm sd — yes).
**Done on 31.08** as a nine-point hands-off tape sweep on the ground, rectified:
scale **1.058 / 0.991**, **no intercept**, C-01 at a true **151/158 mm** with
~100 mm of margin (§10.2). Two corollaries this item did not foresee: the 5.3 mm
sd it treats as a PASS is probably a **false negative** — a dispersion gate
cannot see a stable bias, and `preflight_deploy.py lanecheck` was given a span
check afterwards (§10.5) — and the sweep, like every `lanecheck`, was taken at
the **start of the straight**, which D-79 later established is the estimator's
best point (§12.3). One location cannot close a circuit-wide property.

### 9.5 The reset policy for the day

C-05 has no operational story on hardware and §8.5 says that needs a **decision,
not a patch**. **D-74 is that decision**: C-05 is unchanged, and the reset path
lives outside the cage in `cage_reset_proxy_node`, which offers three postures:

* `reset_proxy:=observe` (**default**) — it watches, logs to
  `<run>/reset_events.csv` what a reset path *would* have done and when it would
  have withheld, and publishes nothing. The operator still resets by hand
  (`ros2 topic pub --once /cage_reset std_msgs/msg/Empty {}`), and `/cage_reset`
  is now in the bag, so hand resets are finally distinguishable from recoveries.
* `reset_proxy:=auto` — it publishes, under the same three conditions the
  operator applied by eye five times on 26.08 (perception healthy, no C-01…C-04
  active, car stopped), held **continuously for 1 s**, rate-limited to one per
  3 s, hard-capped at 6.
* `reset_proxy:=off` — not started.

**Start in `observe`.** Run the lap; if it dies on a single glitch again, the log
will already say whether `auto` would have recovered it, and the second attempt
can turn it on knowing the answer. A run with `auto` is a **diagnostic run and
can never be a scored one** — part of the stopping behaviour is then the proxy's,
not the cage's, and the node warns as much on start-up.

The 1 s healthy hold is not arbitrary: C-05's asymmetric exit is STPA-informed
against oscillation at the trigger boundary (`cage.yaml` §c05_emergency), and a
hold requirement is that same argument expressed in time rather than in latching.
D-74's last consequence lists what would have to exist before C-05 itself could
be changed; none of it does yet.

### 9.6 What counts as success, and what would falsify the preparation

Success is **one continuous segment that returns to the marked start**, with the
provenance block populated and `frames/` either empty (no event — best case) or
holding the frames of whatever stopped it.

Falsifiers, in the order they would matter:

1. **`frames/` empty after a perception event.** Then the ring buffer or its
   triggers are wrong and §8.9 is open for a third session.
2. **The loop drops below ~8 Hz, or `/cage_status` falls further behind
   `/state_obs` than 26.08's 12 %.** The remaining deficit is `rl_policy_node`'s
   inference timer (§8.10), and PNG encoding on a dump is the one new CPU cost
   in this session — it happens on a stopped car, but check it.
3. **Pose jumps return.** `layer2.json` says whether the overrides were actually
   in force; if they were and the jumps came back, §8.7's mechanism is not the
   only one.
4. **The car leaves the lane in the final curve again** (§8.8, twice). That
   curve is `kappa ≈ 0.75 1/m` and the car enters it at the full 0.22 m/s with
   C-04 unable to fire (`v_max_curve_mps` 0.25 > 0.22). Do **not** lower
   `max_speed_mps` to fix it in the same run: §8.8's three candidate causes are
   all helped by a lower speed, so it cannot discriminate between them.

### 9.7 What this session cannot be

It is `monitoring`, on `near_secant` rather than the scored D-43 contract, and
possibly with an out-of-cage reset proxy. **None of that can produce
`verdict_phys`**, and no result from it re-scores G4 or touches the D-69 verdict
of record. It is Phase-5 posterior evidence, like everything else since 08.2026.
What it *can* produce, and what nothing before it has, is a physical run that
explains itself.

---

## 10. The 2026-08-31 track session: the goal is not met, and eight hypotheses die

Second driving session, first use of the §9 instrumentation. **Goal — one complete
monitoring lap — NOT achieved.** Full record:
`experiments/physical/runs/SESSION_20260831.md`; CHANGELOG `[31.08.2026]`.

### 10.1 The runs

| run | start | distance | \|ey\| med/max moving | C-02 moving | resets | ended by |
| --- | --- | --- | --- | --- | --- | --- |
| lap01 | mark | 3.11 m | 8.8 / 58.8 mm | 1.4 % | 0 (observe) | one-cycle −37° spike latched C-05 |
| lap02 | mid-curve | **14.56 m** | 42.0 / 150.3 | 6.8 % | 4 | left the lane, final curve |
| lap03 | mark | 5.47 m | 29.4 / 181.9 | 11.6 % | 6, exhausted | budget gone |
| lap04 | mark | 10.92 m | **0.8** / 119.7 | — | 6 of 30, **deadlock** | proxy deadlock, 250 s stopped |

lap01's excellent numbers are the **straight only** (`|kappa|` p90 0.21 against 1.81 and
1.18) and are not a comparable baseline. Against §9.6: the lap was not completed, and the
run *did* explain itself — which was the second half of the goal and is the half that held.

### 10.2 The offset sweep — M-7 §4 does not survive rectification

The clean test M-7 §3b asked for, run at last: car on the ground, hands off, tape-measured,
**rectified**, `near_secant`/1.0, `policy:=false`, 10 s per point, nine points.

* **Scale 1.058 (car left, r² 0.999) / 0.991 (car right, r² 0.977)** against M-6's propagated
  0.72 and M-7's measured 0.68–0.83. The ≈ −10 mm intercept also disappears. **C-01 fires at
  a true 151/158 mm with ~100 mm of margin**, not at 207–241 mm with 14–48 mm. M-7 §4 now
  carries a superseded banner: it characterised the **raw** path, and its own prescription —
  *undistort, do not just re-parameterise* — is what this measurement vindicates.
* **The ±55 mm pairing collapse does not reproduce**: 0/440 invalid cycles out to ±100 mm.
* **A different defect, in the same band.** Right of centre the estimator is unstable:
  **43.3 mm of swing on a stationary car** at −60 mm, sd 6.2–8.4 mm against 0.5–0.9 mm
  mirrored, the point ratio swinging 0.963–1.143, reproducible across two consecutive runs
  with the car untouched — the signature of a pairing flipping between candidate line pairs.
  `/perception_invalid` stayed False for **all 705 cycles**: the estimator does not fail
  here, it is **confidently wrong** (H-12 / D-43). That measurement **predicted lap01's stop
  before it happened** — −58.8 mm was the run's max |ey|, and the spike fired there.
* **Limit:** one location (start of the straight), where the scene is asymmetric. Whether the
  right-side instability generalises around the circuit is **not** established.

`experiments/physical/runs/lanesweep_20260831T094110Z/SWEEP_NOTE.md`.

### 10.3 Eight hypotheses, eight refuted by measurement

Starting position (lap03 made 5.47 m from the mark); heading error scaling with curvature
(r = 0.045 over 1208 moving cycles); a degenerate frame stack after reset (0.0 % vs 21.8 %
between runs); `white_sat_max` mis-set for the hall (M-7's own sweep: 30 wins every column);
a heading-rate plausibility gate (catches 12 of 102 C-02 — **99 % of C-02 cycles are
sustained**, in episodes of ≥ 2, one of them 45 cycles); a tighter `lane_width_tol_m` (width
error 59.5 vs 56.0 mm — does not separate); a narrowed reset-proxy guard (bag replay: 6 → 30
resets, deadlock becomes **livelock**); a better `heading_fit_mode`/gain (M-7 §4b:
`near_secant`/1.0 is already the best of four).

**The diagnosis that survives.** M-7 measured 0.8 % of frames past C-02 in this exact
configuration, on a circuit recording of a car **pushed by hand** near the centre. Driving
itself, the same configuration gives **6.8–11.6 %**. The policy runs wide in curves; the
estimator is trustworthy near the centre. **The estimator's reliable envelope and the
policy's driving envelope do not overlap well enough.** Neither component is individually
defective — which is why eight single-component hypotheses all failed.

### 10.4 Two more things settled, and two fixed on the spot

* **C-04's dead zone is TOTAL, and measured (D-75).** The ceiling is
  `max(0.25, 0.5 − 0.3·|κ|)`, so **0.25 m/s is a floor no curvature can push it below**, against a
  deployed cap of 0.22. Over the day's **2484 moving cycles** the speed was median 0.166, p99 0.209,
  **max 0.228 m/s**, and cycles reaching 0.25: **zero**. C-04 fired 0/1890 in the D-69 campaign and
  has now never arbitrated on hardware either. **It stays that way on purpose** — see §10.4b for why
  its input cannot yet be trusted to arm it.
* **§10.4b — `kappa_ahead` over-reads by ~3×, which is why C-04 is not simply re-tuned (D-75/D-76).**
  On a closed circuit `∮κ·ds = 2π` per lap. Integrating the logged `|κ|` (an *upper* bound — `|κ|`
  cannot cancel) over the logged distance gives ratios of **3.04** (lap02, 14.46 m) and **2.92**
  (lap04, 10.64 m) against geometry; lap03 is 1.05 and lap01, almost all straight, 0.33. Pooled `|κ|`
  reads median 0.89, p90 1.52, **max 2.88 m⁻¹** against `ODD-3.KAPPA_MAX` 1.14 (centre) / 1.00
  (driven) and the ≈ 0.75 of §8.8 — and the circuit was built to the complex_b perimeter (19.28 m vs
  19.22 m), so geometry does not explain it. The over-read's tail grows with offset: the share of
  cycles reading `|κ| > 1.14` goes **8.4 % → 28.0 % → 38.9 % → 38.0 % → 53.9 %** across `|ey|` bins of
  0–20/20–40/40–60/60–80/80–120 mm. **Consequence for this document:** any physical analysis binned on
  `κ` is binned on a corrupted signal — including §8.8's "tightest curve" attribution and the session
  note's "|ey| grows monotonically with curvature" (26 → 32 → 33 → 43 → 63 mm). Both should be
  re-derived after the capture session of §10.6.
* **`monitoring` does not mean the cage cannot stop the car.** `vehicle_control_node` forces
  `/cmd_vel.linear.x = 0` on a latched `/emergency` in **both** modes, by design. A lap
  "without stops" would require disabling that fail-safe — which would void the lap, since
  the cage is what the thesis evaluates. §9.6's success criterion was, in that sense,
  partly ill-posed.
* `cage_logger_node` **died in its constructor** on `platform:=physical`, the first time the
  §9.1 provenance block was ever launched: `ros2 launch` types numeric-looking parameters,
  and `.string_value` on a DOUBLE returns `""`, so the numeric contract fields would have
  vanished from `metadata.json` **in silence**. Fixed, with a regression test verified to
  fail against the previous HEAD.
* `cage_reset_proxy_node` gained `blocking_rules` as a parameter, **default unchanged**,
  documenting both the measured deadlock and the fact that the obvious narrowing livelocks.

### 10.5 What was closed afterwards on the compute host

Four items the Jetson could not do, all in CHANGELOG `[31.08.2026 · later]`, none touching
`cage.yaml`: 962 MB of event PNGs untracked (`.gitignore` covered
`datasets/*/frames/` but not `runs/*/frames/`); `frame_capture`'s budget repriced from
4000 frames (~1.2 GB at the measured 301 KB/PNG) to 600 (~185 MB), with budget saturation
now reported at shutdown — **all four driving runs saturated the 8-event cap**, which makes
the frames a *truncated* sample as well as a biased one; `preflight_deploy.py lanecheck`
given a span check (`≤ 12 mm`) and a retightened `sd_ey ≤ 3 mm`, because **`sd` alone
returned PASS on the 43.3 mm swing** of §10.2 — replayed offline the new gate fails all three
unstable points and passes all five healthy ones, and **it also fails the 5.3 mm reading
§8.2 records as a PASS**, which should now be read as a probable false negative; and
`rl_policy_node` re-seeding its k=4 frame stack on `/cage_reset`, closing a contract
deviation the session had already refuted as a cause.

**None of those three ROS nodes has been launched since.** Logic only — runtime unverified.

### 10.6 What would actually unblock a lap

**A capture session, not a driving one.** Event frames cannot answer §10.3:
`frame_capture_node` dumps ±3 s around events, so its 2513 frames are failure
*neighbourhoods*, and their statistics do not generalise — their median lane width reads
193 mm against the same estimator's 252.9 mm over a full circuit. What is needed is a
**full-circuit recording with true position**, of the kind M-7 §3 used, to see which pair the
estimator picks at each point of the track. The two hand measurements of §9.4 remain
outstanding, and `lanecheck --true-ey` should now be run at −60 and −100 mm, not only at centre.

`verdict_phys` remains open: no scenario has been scored on hardware.

### 10.7 Widening the estimator, and the offline harness that made it possible (D-77)

**D-76's blocker was half wrong.** `experiments/physical/datasets/circuit_export/labels.csv` is
**tracked**, and its `line_c0_m` column carries the per-frame lateral intercepts of every detected
line — the exact input to the pair-selection decision. Replaying the pairing from that column alone
**reproduces the recorded `ey` on 1450/1450 paired frames** (max deviation 0.01 mm). So the
*consistency* question can be answered offline, on a full circuit, on the compute host, with no frames
and no Jetson. Only the *accuracy* question still needs true position.

**The recording contains 42 unphysical relocations** in 1401 transitions — the selected pair's centre
moving > 60 mm at > 1.0 m/s apparent lateral rate — the worst a **364 mm jump in one frame, 47× the
car's top speed**.

**Three fixes tried and refuted first.** (i) *Temporal continuity in the selection* — nearest to the
previous centre instead of nearest to the vehicle: **no effect at all**, because **90 % of the
relocations had only ONE plausible pair**. Nothing to choose between; the candidate line *set* changed.
This is also why D-48's `ruta-2b` was reverted as unnecessary — now with a mechanism. (ii) *Tightening
`lane_width_tol_m`*: actively harmful, frames left with no pair go **41 → 110 → 231 → 483** as it goes
0.08 → 0.04, since that parameter gates pair *acceptance*. (iii) *Tightening SR-014's width window
alone*: forbidden — the supervisor derives it from the estimator's pair window precisely to avoid the
**E2 dead zone** that deadlocked the cage.

**What was actually wrong: SR-014's gate is mis-scaled, not missing.** It is already rate-based —
`allowed_dey = |v|·dt + jump_tol_m` — but at 0.22 m/s and a 50 ms cycle the physical term is **11 mm**
against a `jump_tol_m` of **100 mm**: the tolerance is **nine times** the motion it bounds, admitting a
111 mm relocation as "temporally consistent".

| `jump_tol_m` | relocations caught | good frames suppressed | no pair | added C-05 rejects |
| --- | --- | --- | --- | --- |
| 0.10 (frozen, sim) | 10 / 42 | 0.00 % | 0 | 0 |
| **0.05 (physical default)** | **30 / 42** | 0.57 % | 0 | 5 |

`perception_jump_tol_m` is now a node parameter (`< 0` keeps the default, the
`perception_min_invalid_cycles` precedent) and the physical launch defaults to **0.05**. Simulation
keeps 0.10, so the D-69 verdict path is bit-identical.

**This does not make the estimator read correctly off-centre.** The pairing is unchanged and §10.2's
diagnosis stands. It converts a **silent wrong answer into a declared unavailability**: a caught frame
suppresses `/state_obs` via the cage's missing-state path **without** raising `/emergency` (C-05 still
needs `min_implausible_cycles`). That is the right direction for H-12, whose difficulty is precisely
that a wrong estimate is self-consistent.

**Limits.** `circuit_export` was pushed by hand, so the replay assumes `speed_mps = 0.22` as an upper
bound on the physical term — the most permissive assumption. `labels.csv` has no curvature, so
`curvature_max` is untested here. The availability numbers come from that recording, not a driving run;
since a C-05 latch ends a segment on hardware (D-74), **the next session should watch the reject count
first**, with 0.06 as the fallback. **Nothing here has been launched** — host logic and tests only.

---

## 11. The true-position capture session (prepared 31.08.2026, D-78)

**Goal, stated narrowly:** answer the one question 31.08 left open — **which line pair is the
true one at each point of the track** — and score D-75's closed-loop curvature test. This is a
**capture** session, not a driving one. The policy does not run. Nothing here can produce
`verdict_phys`.

### 11.1 Why this shape, and not another driving session

Eleven single-component hypotheses have now been refuted against data: eight against driving logs
(§10.3) and three against the offline replay (§10.7). What has never existed is a measurement of the
estimator's **accuracy** around the circuit — every physical `ey` label so far was produced by the
estimator being tested, and the one clean tape measurement (31.08) covered **one location**. A
circuit average cannot substitute: the estimator paired 95.4 % of circuit frames while being unusable
right-of-centre at that one spot.

### 11.2 What to prepare on the floor

1. **Numbered stations.** Mark 4–8 points around the circuit and tape-measure their arc-length along
   the lane **centreline** from station 1 (e.g. `0, 4.8, 9.6, 14.4` on the 19.28 m circuit). These
   are the ground truth for arc length, and they are what makes D-75's `∮κ·ds` computable **with no
   odometry at all** — which matters, because D-73 turned loop closure off precisely because the
   odometry could not be trusted.
2. **Offset guide lines.** Chalk lines parallel to the lane centreline at **0, ±60, ±100 mm**. Same
   offsets as the 31.08 sweep, so the results are directly comparable to `SWEEP_NOTE.md`. Push the
   car with a fixed chassis reference mark tracking the guide line; the offset is then constant by
   construction rather than by hand-eye.

**Sign convention, as everywhere else:** `+` = the car is **LEFT** of the lane centreline.

### 11.3 The runs

Camera only — no deploy launch, no policy, no cage. **Rectified**, because that is the deployed
configuration since 26.08 (§8.3) and because unrectified numbers are the ones M-7 §4 measured and
31.08 superseded.

```bash
# one measurement lap per offset; ENTER as the car passes each station
python3 tools/record_lane_dataset.py \
    --out experiments/physical/datasets/truepos_<offset> \
    --true-ey 0.060 --station-arc 0,4.8,9.6,14.4 \
    --rate 20 --no-frames \
    --rectify experiments/calibration/M6_results.json
```

* **`--rate 20`, not the 5 Hz default.** The relocation test compares consecutive frames; at 5 Hz a
  dt of 200 ms makes the 1.0 m/s criterion mean "> 200 mm", which is blind to most of what §10.7
  measured. `circuit_export` was 20 Hz and that is the rate the figures are calibrated on.
* **`--no-frames`.** Every statistic comes from the CSV, so a lap costs ~400 kB instead of ~600 MB.
  This is the 18.08 eMMC lesson applied: record the measurement, not the imagery. Take **one**
  separate lap with frames at 5 Hz only if the appearance-gap work wants imagery.
* **`--true-ey` switches the tool into measurement mode**, which keeps *every* frame — including
  unpaired and bad-width ones. Those are the failures being counted; dropping them would rebuild the
  selection bias that made the event frames unusable (§10.6).
* **Heading fit.** The estimator's own defaults are `near_secant` / gain 1.0, which is the deployed
  pair — nothing to pass. **Caution:** `deploy_cobraflex.launch.py` still declares
  `heading_fit_mode` default `joint_pair_quadratic`, while every run that actually drove used
  `near_secant` (§8.4: 14.45 m against 1.08 m). That launch default is misleading and should be
  revisited separately; it does not affect this session, which does not use that launch.

### 11.4 Scoring — and the acceptance criteria, fixed in advance

```bash
python3 tools/score_lane_capture.py experiments/physical/datasets/truepos_<offset>
```

Three blocks, and every statistic is reported **per station segment** with the **worst** segment
named — never a circuit mean, for the reason in §11.1.

| test | criterion | what a failure means |
| --- | --- | --- |
| **Accuracy** (D-76) | mean \|ey error\| and "right pair" share per segment | a segment where the right-pair share collapses is a **location**, not a global defect — that is the actionable output |
| **Consistency** (D-77) | unphysical relocations, and whether they move **away** from the tape | still-high count ⇒ the *selection* is wrong, which D-77 declared but did not fix |
| **Closed loop** (D-75) | `∫\|κ\|ds / (laps·2π)` within **0.75–1.35** | FAIL ⇒ `κ` still over-reads, D-75 stays blocked and **C-04 stays un-armable** |

The closed-loop criterion is the one that unblocks something concrete: it is the precondition D-75
named for ever revisiting `v_max_curve_mps`.

### 11.5 What this session cannot do

It cannot produce `verdict_phys`, re-score G4 or touch D-69 — the policy does not even run. It cannot
settle whether a lap closes (that is §9.4's floor mark and tape, still outstanding). And it does not
fix anything: it is the measurement that tells you **where** to fix, which is what every previous
session has been guessing at.

### 11.6 Provenance note, and a gap this closed

`circuit_export/labels.csv` carries a `line_c0_m` column that **no tracked tool wrote** — the column
D-77's entire offline replay depends on. It came from an untracked variant on another host. The
replay is still trustworthy (it reproduces the recorded `ey` on 1450/1450 frames, which is strong
internal validation), but it was **not reproducible from the repo**. `record_lane_dataset.py` now
writes `line_c0_m`, `curvature_1pm`, `true_ey_m`, `station` and `s_m`, so the next capture is.


---

## 12. The capture session as executed (31.08.2026): it is the place, not the motion, and the defect is candidate generation

§11 is the runbook; this is what it produced, the same afternoon it was written. **Camera only** —
`csi_camera_node` at `capture_fps:=30`, measured 19.38 Hz and 45.5 % of a core, no policy, no cage, no
ZED, no launch file — rectified, `near_secant` / 1.0, labels computed inline by `CvLaneEstimator` at
its shipped thresholds. Four measurement laps and four parked probes, ~11 500 frames, ~1.4 MB total
because `--no-frames` was used throughout. Full tables and raw-data pointers:
[`CAPTURE_NOTE_20260831.md`](../experiments/physical/datasets/CAPTURE_NOTE_20260831.md); the decision
is **D-79**.

Two protocol notes before the results, because both changed what was measured. There was **no chalk**,
so the offset was held with a **fixed pointer on the chassis at the camera's longitudinal station**,
read against the centre of a painted lane line (250 mm apart, so centred = 125 mm). That is one
transfer error *fewer* than §11.2's chalk lines, which would have had to be measured off the same
paint. And the fifth ENTER — back at station 1 — is what closes the lap for `∮κ·ds`; without it the
scorer has no arc length past the last anchor.

### 12.1 D-78's acceptance criterion fails, and now it owes nothing to odometry

The band was fixed at **0.75–1.35** before the session. Four laps land at **1.97–2.37**, and
restricting the integral to right-pair frames only moves it to **1.78–2.22**:

| lap | true `ey` | frames | paired | `single_line` | usable | arc | ratio | right-pair ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `truepos_000` | 0 | 2704 | 55.4 % | 44.1 % | 15.2 % | 18.04 m | 2.37 | 2.22 |
| `truepos_000_ctrl` | 0 | 2069 | 70.0 % | 28.9 % | 21.8 % | 18.51 m | 1.97 | 1.90 |
| `truepos_000_ctrl_3` | 0 | 2459 | 68.2 % | 31.3 % | 35.8 % | 16.19 m | 2.01 | 1.85 |
| `truepos_m065` | −65 mm | 2415 | 46.6 % | 44.9 % | 25.7 % | 15.56 m | 2.25 | 1.78 |

(*usable* = plausible width **and** |ey − true| ≤ 40 mm.)

This is the first measurement of the `κ` over-read with the arc length taken **off the floor with a
tape** — no odometry, no policy, no cage, and (in the `ctrl` laps) no operator over the lane. D-75's
~3× from driving logs becomes **~2×** once those are out of the chain: the same defect, smaller.
**C-04 stays un-armable** and D-75 stays blocked; its precondition is now measured rather than
assumed. D-76's suspicion about offset is also confirmed — from 0 to −65 mm, paired frames fall
68.2 → 46.6 % and the ratio rises 2.01 → 2.25.

### 12.2 The operator's shadow, and the confound it leaves on earlier captures

`truepos_000` was pushed with the operator walking alongside at 0.13 m/s; the two `ctrl` laps were
pushed from outside the lane. Same offset, same circuit, 40 min apart: paired 55.4 → 69.1 %,
`single_line` 44.1 → 30.1 %, usable 15.2 → 28.8 %, `|ey|` error 54.6 → 31.9 mm and its p95
213 → 91 mm. **A third of the pairing failures and half the offset error of the first lap were the
operator.**

Two consequences. Every hand-pushed capture in this project inherits the risk, so the protocol is now
*push from outside the lane*. And the 18.08 `circuit_export` dataset (1521 frames, 95.3 % paired) was
also hand-swept: not comparable directly — unrectified, different hour — but no longer above
suspicion.

### 12.3 The parked probes: it is the place, not the motion

Each lap's fifth segment sits at the **start of the straight**, which is where the 31.08 sweep and
every `lanecheck` were taken. That segment is excellent and the moving segments are not — so motion
and location were confounded. The car was therefore parked *inside* the bad stretches at true `ey` = 0
and held still for 20 s:

| parked probe | n | paired | right pair | `ey` mean | sd | span | error | mean \|κ\| |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `parked_seg23_a` | 370 | **17.3 %** | 21.9 % | +7.9 mm | 84.3 | **711 mm** | 50.5 mm | 0.08 |
| `parked_seg23_b` | 273 | **0.0 %** | — | — | — | — | **blind** | — |
| `parked_seg34_a` | 314 | 99.4 % | 54.5 % | **+43.7 mm** | 14.0 | 46 mm | 43.7 mm | **0.88** |
| `parked_seg34_b` | 231 | 100 % | 91.3 % | **−39.7 mm** | **3.1** | 13 mm | 39.7 mm | 0.14 |
| start straight, `ey` = 0 | 524 | 92.7 % | 85.4 % | −4.8 mm | 38.0 | — | **15.9 mm** | 0.08 |
| start straight, `ey` = −65 | 448 | 96.7 % | 98.2 % | −59.1 mm | 5.9 | — | **7.2 mm** | 0.03 |

Parked in the bad places is as bad as driving through them, or worse. **The variable is where the car
is, not what it is doing.** The location every earlier conclusion was drawn from is the estimator's
best point by a wide margin — exactly the limitation `SWEEP_NOTE.md` declared about itself, now
measured rather than suspected. Note `parked_seg34_a` reporting mean |κ| **0.88 m⁻¹ standing still**:
the over-read is not an artefact of integrating a moving signal.

### 12.4 The mechanism: candidate generation, not pair selection — which inverts the obvious fix

`line_c0_m` (the column D-78 added) records every detected line's intercept, so each probe's failure
reads directly. For a car at true 0 the correct pair is ≈ ±125 mm.

* **`parked_seg23_b`** sees **exactly one line** in 273/273 frames. Nothing to pair — a **detection**
  failure.
* **`parked_seg23_a`** sees three lines at ≈ −200, −150, +250 mm. The first two are 50 mm apart:
  **the two edges of one painted stripe**. No pair has a plausible separation (50 / 400 / 450 mm), so
  the estimator refuses — `single_line` in 306/370. Correct behaviour on bad candidates.
* **`parked_seg34_a`** pairs ≈ (−200, +100) → width 300.6 mm, midpoint +50 → reports **+43.7 mm**: the
  **outer edge** of a stripe instead of its centre.
* **`parked_seg34_b`** pairs ≈ (−100, +200) → width 279.2 mm, midpoint −50 → reports **−39.7 mm**.

At these places the candidate set is not "the two stripe centres" — it is stripe *edges*, adjacent
markings, or one stripe. The surviving pair carries a plausible width (279–301 mm) with a midpoint
displaced 40–50 mm, which is H-12 in its purest form: confident, repeatable and wrong, with
`/perception_invalid` never firing.

**This inverts the fix D-76 would naturally have reached for.** A temporal continuity prior on pair
selection would track the wrong pair happily — `parked_seg34_b` is stable to **3.1 mm** while being
39.7 mm wrong. The widening must act on **line extraction** (stripe edge vs centre, threshold
behaviour at these spots), not on the tie-break. D-76's order of work stands; its target moves.

### 12.5 No stability gate can catch a bias

`parked_seg34_b`: 39.7 mm wrong, sd 3.1 mm, span 13.3 mm. The old `lanecheck` gate `sd_ey ≤ 10 mm`
**passes** it comfortably; the span gate added on 31.08 (`≤ 12 mm`) **fails** it by 1.3 mm, which is a
coin flip. No dispersion statistic can detect an offset bias. Only
`preflight_deploy.py lanecheck --true-ey` can, and it must be run **at more than one location** —
§10.5's item "lanecheck at −60 and −100 mm" is necessary but not sufficient as written, because at the
start of the straight it will keep passing.

### 12.6 What this session did not do, and what the per-segment map does not say

* **No `verdict_phys`**, no gate re-scored, no hazard / SR / cage rule / scenario / metric / verdict
  added or re-valued. The policy never ran. Posterior evidence.
* **`+60`, `−100` and `+100` laps are still owed** — the offset dependence is established in one
  direction only.
* **No cause named for the bad places.** What is physically different there (stripe width, a mat join,
  the adjacent red carriageway entering frame, local lighting) was not inspected; the session ran out
  of time. Cheap, and the next thing worth doing.
* **The per-segment map does not reproduce.** Across the three offset-0 laps only two things repeat:
  the 2→3 stretch is always poor (paired 50.2 / 51.4 / 46.7 %, error 58.5 / 57.0 / 79.3 mm) and the
  start straight is always good. Segments 1, 3 and 4 swing — 3→4 goes 75.4 / 98.6 / 70.7 % paired. An
  early reading of the first lap called 3→4 a located defect; three laps do not support that, and it
  is recorded here so the claim is not inherited.

---

## 13. The 2026-08-31 driving session: three ways the cage stops the car, and the bare-policy arm that explains all of them

The session §12's capture was meant to inform, run the same evening. **Ten Layer-3 launches**, of
which six produced data and four wrote a CSV header and nothing else. Three of the six are the
experiment and are analysed below; a fourth — the bare-policy run — is **withdrawn** (see the notice
in §13.2), and the other two are a concurrency incident, recorded in §13.5 with the rest of the
01.09 audit. All are `monitoring` + rectified + `near_secant`/1.0, on the v2 1650k
checkpoint (`ppo_gz2d_sim2real_v2_2024_r2`), behind `run_physical_lap.sh`. Layer 2 was brought up
with `use_lidar:=false`; the loop ran at **9.6 Hz** against 8.68 Hz on 26.08 (§8.10), and the
inference venv is **torch 2.13.0+cpu**, so §8.10's "the bottleneck moved to `rl_policy_node`'s timer"
is now explained rather than merely located.

| run | proxy | cycles | s | emergency | commanding motion¹ | distance² | max \|steer\| | dominant rules |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `lap_mon_…T143913Z` | `auto`, defaults (hold 1.0 s) | 3051 | 333 | 80 % | 31 % | 12.5 m | 0.381 | C-05 2448, C-02 573 |
| `lap_mon_escape_…T144533Z` | `auto`, `blocking_rules:=C-03,C-04` **and** `healthy_seconds:=0.3` | 1927 | 210 | 95 % | 16 % | 7.9 m | 0.264 | **C-01 1341**, C-05 1831 |
| `lap_mon_hold03_…T144938Z` | `auto`, `healthy_seconds:=0.3`, default `blocking_rules` | 4512 | 479 | 87 % | 32 % | 19.1 m | 0.456 | **C-02 1066**, C-05 3938 |
| ~~`lap_bare_…T150050Z`~~ | ~~off, emergency detached~~ | — | — | — | — | — | — | **WITHDRAWN 01.09 — §13.2** |

¹ `|speed| > 0.01 m/s`, a deliberately low bar because what the column asks is *whether the throttle
reached the wheels at all*. At a 0.05 m/s threshold the same column reads 22 / 10 / 21 / **97 %**:
the bare arm does not move, the three caged runs halve. ² `Σ speed·dt` over the run, `dt` clipped at
0.5 s; for `lap_bare` this agrees with the odometry path length to about 1 % (§13.5).

Two launches produced nothing and both are worth recording, because both are the repo's own rule —
*pytest is not evidence a node runs* — collecting again. The first died on
`Unrecognized data type: <class 'list'>`: `deploy_cobraflex.launch.py` passed `value_type=list` to
`ParameterValue`, which accepts scalars or `typing.List[...]` but not a bare `list`. That line is
D-74's `blocking_rules` guard, written on 31.08 and **never launched**. The second died on
`ModuleNotFoundError: stable_baselines3` — `scripts/setup_deploy_env.sh` had not been sourced.

### 13.1 Three blockers, none of them the policy

**Run 1 — the 1 s healthy hold is not satisfiable in motion.** D-74/§9.5 requires perception healthy,
no C-01…C-04 active and the car stopped, held **continuously for 1 s**, before the proxy publishes a
reset. Against **9 resets issued** the log records **623 withholds**: 302 `healthy for X s of 1.00`,
134 `perception still invalid`, 123 `still moving`, 51 `cage rules active: C-02`, 12 `rate limited`
and 1 `cage rules active: C-03`. The dominant cause is the hold itself — **48 % of every withhold** —
because the estimator's health flickers faster than a second. That threshold was fixed by STPA
argument against oscillation at the trigger boundary and had **never been exercised in motion**; this
is the first measurement, and it says the argument's number is unreachable on this track. Longest
stretch with the cage unlatched: **4.7 m in 28 s**, one of ten such stretches totalling 9.9 m of the
run's 12.5 m.

> The first write-up of this run reported **453** withholds broken down as 197 / 121 / 83 / 51. That
> is a **prefix** of the log — at the 197th `healthy` withhold the running totals are exactly
> 197 / 121 / 82 / 51 — read from a console scrollback rather than from the CSV. The numbers above are
> the full population from `reset_events.csv` and they move the conclusion in its own direction: the
> hold is 48 % of withholds, not 43 %. Corrected 01.09.2026 (§13.5).

**Run 2 — removing C-01 from `blocking_rules` does not escape the deadlock, it wastes the budget.**
The launch's own note offers `C-03,C-04` to escape the lap04 case where "a car stopped outside the
lane holds C-01 active forever and no reset can ever be issued". Tried: the proxy issued **30 of 30
resets in about a minute**, each re-latching immediately because the condition that raises C-05 was
still present. The car sat reading **`ey` = −296 mm**, stable, with C-01 active in 1341 cycles and
`perception_invalid` at 6 % — the estimator seeing clearly and reporting the car at nearly twice
C-01's 160 mm. The escape converts a withheld reset into a wasted one; it is not an escape.

**Two variables moved here, not one.** This run also carried `healthy_seconds:=0.3` — its withhold
log reads `healthy for X s of 0.30` — so it is *not* run 1 plus a `blocking_rules` change; it is the
run in which the shortened hold was introduced, and run 3 kept 0.3 s while restoring the default
blocking set. The conclusion survives, because burning 30 resets in a minute is a budget failure and
not a hold failure, but **(run 1, run 2) is not a controlled pair** and must not be read as one.

**Run 3 — with the hold still at 0.3 s and the default blocking set restored, C-02 becomes the
blocker, and it fires on noise.** Over the whole population of **1066 C-02 cycles** the car sits at a
mean **`ey` = −20 mm**, comfortably inside the lane, while `epsi` carries **sd 19.1°** across a range
of **−45.2°…+42.8°** against C-02's 25° threshold — blocking resets, car crawling at 0.035 m/s. The
window quoted in the first write-up (`ey` −32 mm, `epsi` −25.3°…+18.2°, sd 17.2°) is one stretch of
that population and is, if anything, its mild end.
M-6 measured `near_secant`/1.0 at **sd 5.3°, 0.8 % of frames past C-02**; the same configuration on
the same car gives **17.2°** here. The difference is *where*: M-6 measured at the start of the
straight, which §12.3 established is the estimator's best point. **The heading channel degrades off
that spot exactly as the offset and curvature channels do** — a fourth independent confirmation of
D-79, and the first in the heading channel while driving.

### 13.2 The bare-policy arm — WITHDRAWN

> **WITHDRAWN 01.09.2026 — the run this section rests on is disowned by its author.**
> `lap_bare_20260831T150050Z` (641 s, the 31.08 evening run with `/emergency` detached) was driven
> with the operator **repositioning the car by hand throughout**, placing it at other points on the
> circuit precisely because nothing was stopping it. The run therefore has no interval whose start
> conditions the operator did not set, and the author's instruction is that **nothing from it is
> usable**. The text below is kept struck rather than deleted, because the repo records what it
> retracted; **do not cite any figure from it.**

**What fell with it.** The inversion this section reported — *the cage latched for 99 % of cycles
while the car drove for 97 % of them*, the ≈ 109 m covered, the single latch at t + 6.4 s, and the
claim that the policy circulated the circuit in both directions — all rest on that run and are
withdrawn. So does the **positive control** the section supplied for D-76's ordering: widening the
estimator before narrowing the policy is again an argument from architecture, as it was before
31.08, and it keeps the support D-79 gives it (the estimator's accuracy is a property of place) and
loses the support this arm gave it.

**What does not fall.** The three caged runs of §13.1 are untouched — the 1 s hold unsatisfiable in
motion, the reset budget burned by the documented escape, and C-02 firing at `ey` = −20 mm with
sd(`epsi`) 19.1° are all measured on runs the author has not disowned, and the last of them remains
the fourth independent confirmation of D-79 and the first in the heading channel while driving.
`control_emergency_topic` (§13.3) also stays: it is a launch argument in the tree, and the reason it
exists — that killing a node by hand leaves no trace in the evidence — is unaffected by the quality
of the one run that used it.

### 13.3 `control_emergency_topic`, and why it is a launch argument

`vehicle_control_node` zeroes `/cmd_vel` on a latched `/emergency` in **both** modes by design
(§10.4) and its `emergency_topic` was not exposed, so there was no way to run the bare-policy arm
without editing code or killing a node by hand. Killing a node by hand leaves **no trace in the run's
evidence**, which is not acceptable in a repo whose defining commitment is traceability. The argument
defaults to `/emergency` — pointed at a topic nobody publishes, it detaches that one link and nothing
else. It carries its own warning in the launch description: *DIAGNOSTIC ONLY — with it set, nothing in
software stops the car.*

### 13.4 The yaw-rate ceiling — WITHDRAWN, and the question reopened

> **WITHDRAWN 01.09.2026 — the run this section rests on is disowned by its author.**
> `lap_bare_20260831T150050Z` (641 s, the 31.08 evening run with `/emergency` detached) was driven
> with the operator **repositioning the car by hand throughout**, placing it at other points on the
> circuit precisely because nothing was stopping it. The run therefore has no interval whose start
> conditions the operator did not set, and the author's instruction is that **nothing from it is
> usable**. The text below is kept struck rather than deleted, because the repo records what it
> retracted; **do not cite any figure from it.**

**What fell.** The whole of it: the 5327-cycle commanded-versus-achieved table, the plateau at
≈ 0.10 rad/s, the ratio collapsing 0.85 → 0.18, the least-squares gains 0.226 / 0.191, and the
arithmetic that turned them into `R_min` = 2.2 m against ODD-3's ≈ 1.0 m. The conclusion that **the
platform cannot negotiate the tightest curve of its own ODD** was the strongest claim Phase 5 had
produced and it is **withdrawn in full** — it reached the manuscript as a numbered finding and an
abstract clause, and both were removed the same day.

**What survives, and it is not nothing.** The *shape* of the actuation deficit was measured on
18.08 by M-7 §5, on a different day and a different protocol: the ratio of achieved to commanded yaw
falls **0.482 → 0.436 → 0.341** as the command grows from 0.2 to 0.8 rad/s. So the plant being
**compressive** — no single linear gain fitting the channel — stands on M-7 and does not depend on
the withdrawn run. What is now unknown again is **where that compression ends**: whether it is a soft
compression or a hard saturation, and therefore what `R_min` the platform can actually achieve.

**The discriminator is cheap, and it no longer needs the track.** The chassis is **skid-steer** (four
`continuous` wheel joints under a DiffDrive plugin, no steering angle), so yaw comes from a
left/right wheel-speed differential.
[`tools/measure_yaw_authority.py`](../tools/measure_yaw_authority.py) sweeps the command and reports
that differential beside the achieved yaw — on blocks, where the operator cannot contaminate
anything, and then on the floor. A differential that saturates puts the ceiling in the driver or the
firmware; one that stays linear while the achieved yaw saturates puts it in the contact patch. Either
answer re-earns the finding legitimately; neither needs a driven lap.

### 13.5 The 01.09 audit of this session, and four things it found that the write-up did not

Every number in §13 was re-derived from the committed evidence — `cage_status.csv`,
`reset_events.csv`, `capture_events.csv` and `lap_bare`'s `bag_export.csv` — before this session was
allowed to feed the manuscript. For the three caged runs **the core replicates**: cycles, durations,
`emergency` percentages, `max |steer|` and every rule count in the table are exact. (The audit also
reproduced §13.4 to the digit — but that section's run was withdrawn hours later, so the
reproduction establishes only that the arithmetic was right about a contaminated input, which is
worth exactly nothing.) Four corrections are folded into the text above (§13.1's withhold population,
run 2's second variable, run 3's window, the run inventory). Two further findings survive the
withdrawal.

**1. C-04 does fire — 58 and 40 cycles in the two caged runs that survive — and every one of them is
an artefact.** D-75 established C-04 as un-armable because `v_max_curve_mps` 0.25 exceeds the
deployed 0.22 m/s, on morning laps where **0 of 2484 moving cycles** reached the floor. In
`lap_mon_escape` and `lap_mon_hold03` C-04 appears in `rules_fired`, and in **100 % of those cycles
the logged speed is between 0.25 and 1.30 m/s** — speeds the platform cannot produce under its own power (median 0.5–1.05 m/s, in
1–5 s episodes, consistent with the operator carrying the car and with residual pose noise; these
logs cannot separate the two). D-75's decision is unchanged and so is its cost argument — C-04 never
fires on commanded motion — but the literal claim *"it can never fire"* is false, and the consequence
is operational: **in `lap_mon_escape` the spurious firings enter the reset-withhold path**
(`cage rules active: C-03,C-04` ×7, `cage rules active: C-04` ×6). A velocity artefact does not merely
raise a rule; it **blocks the recovery from the rule it raised**. That is a concrete mechanism joining
§8.7's velocity channel to §13.1's deadlock, and it stayed invisible while C-04 was discussed only as
a coverage gap.

**2. `frame_capture_node` saturated its budget in all six runs.** Every run wrote exactly **600
frames** — the cap the 31.08 repricing set (4000 → 600, CHANGELOG `[31.08.2026 · later]`) — and five
of the six also hit the 8-event cap. The repricing fixed the disk cost and **did not fix the sampling
problem**: the evening frames are as truncated and as biased towards failure neighbourhoods as the
morning's, and `hold03` is the extreme case, spending its whole budget on three events (224 / 356 /
20 frames). Any future session meant to *characterise* rather than *illustrate* needs §12's
full-circuit recording, not event frames. The PNGs are on the Jetson — `runs/*/frames/` is gitignored
— so this host holds only `capture_events.csv`.

**3. Two of the ten launches were alive at the same time.** `lap_mon_…T140749Z` and
`lap_mon_…T141134Z` cover the **same wall-clock window** (14:12:07 → 14:15:26), share 2197 message
timestamps, and carry a bimodal inter-arrival distribution — **36 % of gaps below 20 ms** against a
median of 87 ms, where the clean runs later that evening give 0.1 % and 101 ms. That is two Layer-3
stacks publishing `/cage_status` concurrently, with two loggers each recording the union; both
`metadata.json` files confirm it from the other end (`status: running`, `cycles_logged: 0` — neither
logger ever reached its clean shutdown). The car was stationary throughout (max 0.023 m/s), so nothing
unsafe happened and the §13 table is right to exclude both — but **the two CSVs interleave two cage
instances and cannot be analysed**, and the incident joins I-1 and the 29.07 campaign incident as a
third instance of one failure: nothing in the tooling stops a second stack being launched over a live
one. `run_physical_lap.sh` could refuse to start while `/cage_status` already has a publisher; it does
not.

**4. What did *not* regress.** Across the three caged runs `cycles_since_last_state` never exceeds
**0** and the loop holds 9.2–9.4 Hz: the camera starvation that dominated 26.08 (§8.6) did not
reappear, and the CPU work of §8.10 plus a lidar-less Layer 2 is why.

### 13.6 The anatomy of the latch and the frozen-estimate signature — WITHDRAWN

> **WITHDRAWN 01.09.2026 — the run this section rests on is disowned by its author.**
> `lap_bare_20260831T150050Z` (641 s, the 31.08 evening run with `/emergency` detached) was driven
> with the operator **repositioning the car by hand throughout**, placing it at other points on the
> circuit precisely because nothing was stopping it. The run therefore has no interval whose start
> conditions the operator did not set, and the author's instruction is that **nothing from it is
> usable**. The text below is kept struck rather than deleted, because the repo records what it
> retracted; **do not cite any figure from it.**

**What fell.** Everything measured on the run: the latch at t + 6.39 s with the car 27 mm off centre
and no C-01…C-04 firing; the frozen-estimate signature (17.4 % baseline against 35–75 % in the four
seconds before each of ten operator interventions); the C-01-at-0 % observation; and the estimate of
what enforcement would do, which was built from those same windows. The *question* it asked — does
the lane leave the image, or only the estimator's candidate set? — is untouched and unanswered.

**Two things in it did not depend on the run, and stand.**

**(i) The cage has never modified an action on hardware.** In `monitoring` the node returns
`final_action = raw_action`, and the three surviving caged runs show **0 modified cycles each**, with
C-06 flagged and never applied. That is measured on runs nobody has disowned.

**(ii) "Enforcement with the emergency detached" is not a configuration that exists.** In
`enforcement` the node returns `current_action`, and C-05's correction *is* a controlled stop
travelling on **`/safe_action`**; `control_emergency_topic` detaches only the `/emergency` topic. The
configuration that isolates the question is `c05_emergency.perception_trigger_enabled: false` — C-05's
Trigger 8 — in a **copy** of `cage.yaml` passed through the launch's `cage_yaml` argument, so the
artefact under verification is untouched and the run's `cage_yaml_hash` records what ran. That is a
property of the code, not of any run.

## 14. The sim-to-real gap, as measured (consolidated ledger, 01.09.2026)

§5 is the gap list as it stood **before** the platform was driven — an a-priori list, kept unedited
because what it did and did not anticipate is itself a result. This section is the **posterior**
ledger: every gap term Phase 5 actually measured, in one place, with its magnitude, its evidence and
its status. It re-scores nothing — `verdict_phys` is open, no scenario has been scored on hardware —
and it is the source the manuscript's gap chapter draws on.

Terms are ordered by what they cost, not by when they were found.

| # | Gap term | What simulation assumed | What hardware measured | Status |
| --- | --- | --- | --- | --- |
| 1 | **Turning authority** | Commanded yaw is achieved; a single linear gain corrects any deficit | Achieved/commanded falls **0.482 → 0.436 → 0.341** as the command grows (M-7 §5, 18.08): the plant is **compressive**, so no constant gain fits it | **OPEN.** Where the compression ends — soft or hard — and therefore the achievable `R_min` is **unmeasured**: the run that claimed to measure it is withdrawn (§13.4). Discriminator is a bench sweep of the wheel differential |
| 2 | **Lane-estimator accuracy is place-dependent** | One estimator quality everywhere the lane is visible | Start of the straight: 96.7 % paired, **7.2 mm** error. Elsewhere: 37.9–60.2 % paired; parked probes give **0.0 % paired**, **+43.7 mm**, and **−39.7 mm at sd 3.1 mm** | **OPEN — binding.** D-76 / D-79; the target is line extraction |
| 3 | **Heading channel under motion** | `epsi` noise as measured at rest (**sd 5.3°**, 0.8 % of frames past C-02) | Driving off the good spot: **sd 17.2–19.1°**, **6.8–11.6 %** of cycles past C-02's 25° | **OPEN.** Same defect as #2 in a third channel (§13.1 run 3) |
| 4 | **Curvature channel** | `kappa_ahead` usable; C-04 and every κ-binned analysis rest on it | Integrated turning comes to **~2×** what a lap can contain (floor-truth), **~3×** odometry-binned; 0.88 m⁻¹ on a *stationary* car | **OPEN.** D-75 / D-79; every κ-binned physical analysis is corrupted |
| 5 | **Training-distribution handedness** | Track layout is a scenario property, not a policy property | complex_b is **6.5:1 left** → a constant **+0.13** steering prior; the trunk policy shows bias/swing **12.9–19.2** and turns right in 0.5 % of samples | **CLOSED** by per-episode mirroring: v2 gives **0.07–1.10**, `mirror_rate` 0.527 (D-72) |
| 6 | **Camera intrinsics** | HFOV 90° — a default the simulator *inherited*, so no simulation could falsify it | Effective HFOV **77.89°**, plus an unmodelled `k1 = −0.339` | **CLOSED** by rectifying towards the canonical model: perception-invalid **45 % → 5.5 %**, C-01 **102 → 0** firings at rest (M-6, §8.3) |
| 7 | **Control cadence** | 10 Hz, the rate the policy was trained at | 7.3 Hz (26.08 first run) → 8.68 Hz (best caged lap) → **9.6 Hz** (31.08, lidar-less Layer 2, torch CPU). The bottleneck is `rl_policy_node`'s CNN timer, not the camera | **OPEN, narrowing.** §8.6, §8.10, §13 |
| 8 | **State-estimation velocity** | Velocity is trustworthy; it is the cage's only speed input | ZED pose jumps of **3.62 m in one frame** → ekf `vx` −4.03 m/s, and a spike to 5.5 m/s against a 0.22 m/s contract | **MITIGATED** by disabling loop closure (D-73): steps > 50 mm **116 → 0** in a controlled A/B. Residual artefacts still fire C-04 (§13.5); the price is unbounded slow drift |
| 9 | **Rule operational semantics** | Rules are validated against episodes, and episodes end | C-05's explicit-reset latch has no operational story on a vehicle that must keep going — it latches on the estimator's **validity signal**, once, with the car 27 mm off centre and no other rule firing (§13.6); D-74's **1 s healthy hold is unsatisfiable in motion** (48 % of 623 withholds); C-04's 0.25 m/s threshold sits **above** the 0.22 m/s operating point | **OPEN by decision.** D-74 (reset path outside the cage), D-75 (C-04 un-armable, `cage.yaml` untouched) |
| 10 | **Policy–rate-limiter coupling (T2)** | Named in advance as the top transfer risk: the pair *(policy, C-06)* may not survive hardware | C-06 fires **3.4 %** of moving cycles on hardware against **3.0 %** in simulation at the same checkpoint | **DID NOT MATERIALISE.** N = 1, monitoring (§8.10) |
| 11 | **Appearance / photometry** | Gazebo render, with H-10 randomisation as the mitigation | Deployment gate on real circuit imagery: **PASS raw** (retention 1.29, bias/swing 0.10) and **PASS rectified** (1.21, 0.17); right-turn share **66.6 %** against the sim arm's 66.4 % | **CLOSED for the deployed policy** (§8.1) |
| 12 | **Heading-fit contract** | `joint_pair_quadratic`, the D-43 contract the campaigns were scored under | Under motion it manages **1.08 m** before stopping; `near_secant` manages **14.45 m** — and the difference is **invisible at rest** | **OPEN — a contract conflict.** Everything that has driven used `near_secant`, so no physical run is yet under the scored contract (§8.4) |
| 13 | **Evidence capture** | Not considered | A full bag crashes the Jetson (13.8 MB/s); the event-frame replacement **saturates its 600-frame budget in every run**; frames live only on the Jetson | **OPEN.** §13.5 — characterisation needs §12's full-circuit recording, not event frames |

### 14.1 What the a-priori list got right, and what it missed

§5 anticipated four terms and was right about all four in kind: appearance (#11), the provisional
thresholds, compute cadence (#7) and the yaw-gain channel (#1). On the last of them it was right
about the channel and **wrong about the shape**: §5 framed yaw as a *constant* 3.9 % offset between
the firmware's `TRACK_WIDTH` 0.159 and the tape's 0.153, and M-7 §5 measured a **compressive** plant
instead — 0.482 → 0.436 → 0.341 as the command grows, which no constant corrects. A parameter error
was anticipated; a non-linearity was not. Where that compression ends is still unmeasured (#1).

Everything that actually stopped the vehicle is absent from §5: the handedness of the training track
(#5), an intrinsics error the simulator had inherited and therefore could never expose (#6), an
estimator whose accuracy depends on **where the car is** rather than on what it is doing (#2–#4), the
missing operational story for a correctly-specified latch (#9), and a velocity sensor whose failure
mode enters the cage's only speed input (#8). **Three of those five live in the measurement chain**
— the camera's intrinsics, the lane estimator and the velocity sensor — one is a property of the
training distribution and one is a rule's operational semantics. **None of the five is the control
policy.**

That asymmetry is the ledger's methodological result, and it is stronger than any single row:
**the gap terms a simulation-trained team can enumerate in advance are the ones simulation can model
— appearance, timing, gains. The terms that stopped this vehicle are the ones simulation had no
representation of at all**, either because it had inherited the same wrong assumption (#6), because
the quantity has no simulated counterpart (#2's place-dependence, #9's unbounded episode), or because
the simulated plant was better than the real one (#1). A5's demand — characterise the gap rather than
only reduce it — is what turned each of these into a measurement instead of a surprise during a
scored run.

### 14.2 The one-line summary, and what it is not

**The v2 policy transfers, and what stops it is the measurement.** The evidence for the first half is
26.08's 18.05 m in a single uninterrupted segment with no safety rule firing (§8.10). The evidence
for the second half is D-79 — the estimator's accuracy is a property of **where the car is**, with
parked probes at a true offset of zero giving 0 % paired at one spot and −39.7 mm at sd 3.1 mm at
another — together with §13.1's three blockers, each of which is the reset path or a rule acting on
that measurement rather than on the vehicle's actual state.

**That claim was briefly stronger and is no longer.** The 31.08 bare-policy arm appeared to supply a
positive control — the policy circulating freely while the cage sat latched — and it is **withdrawn**
(§13.2): the operator repositioned the car by hand throughout. D-76's ordering is back to an argument
from architecture supported by D-79, which is where it stood before that evening.

Nothing here is a safety result. No physical run has used the scored perception contract, none has
been executed under the scenario protocol, and **the cage has never modified an action on hardware at
all** — `monitoring` returns the raw action, and the surviving runs show 0 modified cycles each. So
Phase 5 measures what the cage *would have said*, plus what C-05's latch costs in availability. It
cannot be `verdict_phys`, and neither can anything else Phase 5 has produced so far.

**And one scope limit outranks all the others, because it applies to every physical run without
exception: the cage has never enforced on hardware.** Every session to date ran `monitoring`, in
which `SafetyCageNode` returns `final_action = raw_action` — measured, not assumed: **0 modified
cycles** in each of the three surviving caged runs of 31.08, with C-06 flagged and applied zero. So nothing in Phase 5 measures what the cage *does to a vehicle*; it measures what the
cage *would have said*, plus what C-05's latch does to availability. The rate limiter the policy was
trained alongside — the D-69 finding-(i) dependency, the T2 transfer risk — has **never been in the
physical loop**. That is the largest single gap between what the simulation campaigns scored and what
the hardware has shown, and closing it needs an enforcement run, which needs the estimator work of
D-76 first (§13.6).
