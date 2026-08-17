# 13 — Isaac Sim utilities: building, driving & training the CobraFlex env

Status: URDF import + ROS2 bring-up working (verified headless on Isaac Sim 6.0, RTX 5060
host, 2026-06-16). The **in-process RL training** path is **live-validated on the Isaac host**
(03.07.2026, D-44 deferral closed) — see
[RL training — in-process](#rl-training--in-process-gazebo-free-d-44). Since
02.07.2026 (G4 closed) the trainer defaults to the **full-authority D-50 configuration**:
**2-D action (steering + throttle)** + **multi-circuit per-episode sampling** on
`complex_b,complex_d,complex_e` — **live-validated end-to-end 03.07.2026** with the 20k pilot
`experiments/sim/training/isaac2d_pilot_20k/` — see
[Full-authority training](#full-authority-training--2-d-action--multi-circuit-d-50).

> **Scope — this is posterior work, not the thesis verdict path.** The Isaac migration is a
> **bridge toward sim-to-real / the physical platform**; it is **orthogonal** to the F/E
> track distinction (the Isaac trainer can carry either modality). The **E-track verdict
> closed in Gazebo** — GE4-V2 on the complex_b 297k E-main (28.06.2026; **G4 closed
> 02.07.2026**), with evidence in [docs/11](11_camera_rl_training.md) §8.4,
> [docs/07](07_traceability_matrix.md) and ch.8 §8.9 — and Isaac **does not supersede** it. A
> checkpoint trained in Gazebo is **not transferable to Isaac** (different physics + renderer;
> see [Speed and fidelity](#speed-and-fidelity--same-logic-different-environment)), so every
> Isaac-based E policy is an **independent retrain from scratch**, never a re-run of the current
> result. Those independent Isaac retrains now exist as posterior experiments; they still do
> not enter GE4. Read this doc as the *next-stage* toolbelt, not as a change to the frozen
> verdict.

Keep the three contracts separate when reading results:

| Contract | Algorithm/action | Speed authority | Evidence role |
| --- | --- | --- | --- |
| Gazebo GE4-V2 | PPO, 1-D steering | fixed 0.20 m/s | **Verdict of record** |
| Gazebo posterior E5 | PPO/SAC, 1-D and 2-D | current 2-D cap 0.25 m/s (historical PPO run used 0.5) | algorithm/action probes in docs/11; not GE4 |
| Isaac posterior | independently trained PPO, 2-D | 0.5 m/s under the Isaac-specific calibration | sim-to-real/backend study; not GE4 |

> Running it on a fresh machine? See **[docs/SETUP_ISAAC.md](SETUP_ISAAC.md)** for the
> step-by-step recipe (deps, `download_meshes.sh`, **source ROS2 first**, smoke tests).

This doc is the Isaac Sim toolbelt for CobraFlex: how the env is built from the URDF, the
tools that run it, and the command to launch each.

| Tool / module | Role | Run / import |
| --- | --- | --- |
| `tools/build_isaac_urdf.py` | regenerate the flat `cobraflex_isaac.urdf` from the source xacro | `python tools/build_isaac_urdf.py` (sourced ROS2) |
| `tools/isaac_import_check.py` | headless smoke-test: URDF→USD import + assert frames/joints | `~/isaacsim/python.sh tools/isaac_import_check.py` |
| `tools/isaac_scene.py` | **shared** physics-scene builder (URDF→USD, track, robot, wheel drives/materials + drivetrain constants); imported, not run | `import isaac_scene` |
| `tools/isaac_ros2_bringup.py` | drive over the **ROS2 bridge** — same nodes as Gazebo (SLAM, perception, teleop, RViz, eval) | `~/isaacsim/python.sh tools/isaac_ros2_bringup.py` |
| `tools/isaac_train.py` | **in-process** RL (PPO) training — drives the gym env directly, no ROS | `~/isaacsim/python.sh tools/isaac_train.py …` |
| `tools/isaac_eval.py` | **in-process** nominal evaluator (laps / \|ey\| / per-rule interventions / emergencies) + CV-parity probes (`--controller cv`, D-52/D-54) | `~/isaacsim/python.sh tools/isaac_eval.py …` |
| `tools/isaac_dr.py` | per-episode **physics + scene domain randomization** (sim-to-real levers #2/#3/#4); attached by the trainer on each reset | `import isaac_dr` |
| `src/cobraflex_rl/cobraflex_rl/isaac_interface.py` | `IsaacSimInterface`: in-process env I/O (teleport / step / camera + latency buffer) | imported by `isaac_train.py` |

Flow below: URDF rationale & generation → import → **ROS2 bring-up** (drive / SLAM / RViz)
→ physics tuning → sensors → track → **RL training in-process**.

## Command reference (what launches what)

Everything runnable, in one place — the sections below give the *why*. Two conventions:

- `$ISAAC` = the Isaac Python launcher. On this host `~/isaacsim/python.sh`; on **PC CAST**
  `/home/admit/isaac_sim_6.0.0/isaac-sim-standalone-6.0.0-linux-x86_64/python.sh`. Export it
  once: `ISAAC=~/isaacsim/python.sh`.
- **Source ROS2 first** for anything touching the bridge or `xacro`:
  `source /opt/ros/jazzy/setup.bash`. Run every ROS2 client (teleop / RViz / RSP) with
  `use_sim_time:=true` (Isaac drives `/clock`).

```bash
# ── Build & import (sourced ROS2) ──────────────────────────────────────────────
python tools/build_isaac_urdf.py                         # regen src/cobraflex/urdf/cobraflex_isaac.urdf
check_urdf src/cobraflex/urdf/cobraflex_isaac.urdf       # validate it
$ISAAC tools/isaac_import_check.py                       # URDF→USD smoke-test (exit 0 = PASS)

# ── Track assets (plain python) ────────────────────────────────────────────────
python scripts/generate_complex_track.py --name all      # build all presets (complex_a/b/c)
python scripts/track_to_gazebo_world.py --name complex_b  # + a Gazebo .world

# ── Bring-up: drive / SLAM / RViz / eval over the ROS2 bridge (defaults to GUI) ─
$ISAAC tools/isaac_ros2_bringup.py                       # GUI viewport
$ISAAC tools/isaac_ros2_bringup.py --headless            # no window
$ISAAC tools/isaac_ros2_bringup.py --test                # headless drivetrain self-test, exits
$ISAAC tools/isaac_ros2_bringup.py --turn                # headless yaw-rate test, exits
$ISAAC tools/isaac_ros2_bringup.py --shot /tmp/t.png     # headless top-down render, exits
CAM_POSE=x,y,yaw $ISAAC tools/isaac_ros2_bringup.py --cam-shot /tmp/cam.png   # lane-cam view, exits
TRACK=complex_b $ISAAC tools/isaac_ros2_bringup.py       # pick the track (TRACK= → bare ground)
WHEEL_FRICTION=0.1 GROUND_FRICTION=0.1 $ISAAC tools/isaac_ros2_bringup.py     # tune skid-steer turning

# ── Drive / visualise it (each in its own sourced terminal, use_sim_time:=true) ─
ros2 run teleop_twist_keyboard teleop_twist_keyboard     # publish /cmd_vel
ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=true \
    -p robot_description:="$(xacro src/cobraflex/urdf/my_robot_gazebo_mesh.urdf)"   # robot TF + RobotModel
ros2 run rviz2 rviz2 -d src/cobraflex/rviz/<config>.rviz --ros-args -p use_sim_time:=true

# ── In-process RL training (no ROS, no bring-up) ───────────────────────────────
# DEFAULT (D-50): full-authority 2-D action (steering + throttle) camera PPO on the
# multi-track scene complex_b,complex_d,complex_e (train_isaac_2d.yaml; one circuit
# sampled per episode). First run only: re-import the USD.
BRINGUP_REIMPORT=1 $ISAAC tools/isaac_train.py                                      # full-authority 2-D run (1st run)
$ISAAC tools/isaac_train.py                                                         # subsequent runs (USD cached)
$ISAAC tools/isaac_train.py --resume-from policy/checkpoints/<ckpt>.zip             # resume a checkpoint
$ISAAC tools/isaac_train.py --render gui --show-obs                                 # watch (slower)
# 1-D single-track (the frozen Gazebo E-main recipe, for backend comparison):
$ISAAC tools/isaac_train.py --track complex_b \
    --train-config src/cobraflex_rl/config/train_ppo_camera.yaml
# Hard-section spawn curriculum (D-58): 2-D + yaw 0.8 champion recipe + random_start_s,
# single complex_b — practises the under-visited U-turn from step 0 (cracked the wall):
$ISAAC tools/isaac_train.py --track complex_b \
    --train-config src/cobraflex_rl/config/train_isaac_kin2_curric.yaml
# Other track/config: override the defaults, keeping --track in sync with the centerlines, e.g.
$ISAAC tools/isaac_train.py --track oval \
    --train-config           src/cobraflex_rl/config/train_ppo.yaml \
    --centerline-config      src/cobraflex_rl/config/oval_right_lane_centerline.yaml \
    --road-centerline-config ''                                                     # F3 state-vector on the oval
```

**In-process eval + CV-parity probes** (`tools/isaac_eval.py`, no ROS, no bring-up; D-52/D-54):

```bash
# Nominal eval of a checkpoint (deterministic, DR + spawn-perturbation off):
$ISAAC tools/isaac_eval.py --checkpoint policy/checkpoints/<ckpt>.zip \
    --track complex_b,complex_d,complex_e --episodes 3 --mode enforcement    # laps / |ey| / per-rule / emergencies
# CV baseline (non-learned pure-pursuit) through the SAME in-process env — the RL-vs-environment control:
$ISAAC tools/isaac_eval.py --controller cv --track complex_b --cv-speed 0.2
# Yaw-authority / perception probe: boost the CV yaw command, dump the death frames (D-54/D-55):
$ISAAC tools/isaac_eval.py --controller cv --track complex_b --cv-yaw-boost 3 --dump-frames 200
# Graceful early stop of a TRAINING run (SIGINT hard-kills the kit before Python's finally, D-52):
touch experiments/sim/training/<run_id>/STOP    # ends learn() at the next rollout — model + metadata saved
```

**Environment variables** (`isaac_scene.py` is shared, so its vars apply to **both** the
bring-up and the trainer):

| Var | Read by | Effect | Default |
| --- | --- | --- | --- |
| `BRINGUP_REIMPORT` | both | re-import the cached USD (do this on first run / after a URDF change) | `0` |
| `TRACK` | both | visual track preset(s) (`complex_a`..`complex_e`; empty = bare ground; a **comma list** builds a multi-track scene, D-50); the trainer sets it from `--track` | bring-up `complex_a`; trainer `complex_b,complex_d,complex_e` |
| `TRACK_MODE` | both | track build: `geom` (USD meshes) or `texture` (baked PNG quad) | `geom` |
| `CAM_POSE` | both | `x,y,yaw` pose for `--cam-shot` / camera-visibility checks | robot pose |
| `WHEEL_FRICTION` / `GROUND_FRICTION` | both | skid-steer wheel/ground friction (see [physics tuning](#physics-tuning--skid-steer-turning)) | `0.05` |
| `BRINGUP_SENSORS` | bring-up | `0` skips all sensor graphs (physics only) | `1` |
| `BRINGUP_ZED` | bring-up | `0` skips both ZED-eye camera graphs | `1` |
| `BRINGUP_ROBOT_TF` | bring-up | `1` enables Isaac's own (partial) standalone TF tree | `0` |
| `LIDAR_CONFIG` | bring-up | RTX-lidar profile name | `RPLIDAR_S2E` |
| `ISAAC_RENDER` | train | `gui` or `headless` (same as `--render`) | `headless` |

**CLI flags** — bring-up: `--headless`, `--test`, `--turn`, `--shot PNG`, `--cam-shot PNG`
(the last four force headless and exit). Trainer: `--train-config`, `--centerline-config`,
`--road-centerline-config`, `--track` (visual scene; a **comma list** = multi-track scene
with per-episode circuit sampling, D-50; defaults to `complex_b,complex_d,complex_e` / the
`TRACK` env), `--model-path`, `--run-id`, `--resume-from`, `--render {headless,gui}`,
`--show-obs`, `--obs-preview-every N`. With a multi-track `--track` the two centerline flags
are **ignored** — per-track geometry comes from the config-dir naming convention
(`<name>_right_lane_centerline.yaml` + `<name>_centerline.yaml`, shifted by the scene
offsets via `isaac_scene.load_circuits`). A bare `isaac_train.py` is the complete
full-authority run (train_isaac_2d.yaml + the CV-safe trio). Evaluator (`isaac_eval.py`):
`--checkpoint`, `--controller {ppo,cv}`, `--cv-speed`, `--cv-yaw-boost`, `--dump-frames N`,
`--train-config`, `--track`, `--episodes`, `--mode {enforcement,monitoring}`, `--seed`, `--out`.

## Why a dedicated URDF

The simulation robot used by the `cobraflex` package
(`src/cobraflex/urdf/my_robot_gazebo_mesh.urdf`) is **not a plain URDF**: it is a
xacro that depends on two external files and on ROS substitution syntax that
Isaac Sim cannot resolve:

| Dependency | Role | Isaac needs it? |
| --- | --- | --- |
| `urdf/inertial_macros.xacro` | material + inertia macros | **yes** — expanded inline |
| `urdf/robot.gazebo`          | Gazebo/`gz` plugins (DiffDrive, odometry, joint-state pub) + sensors (IMU, lidar, three cameras: ZED stereo pair + lane) | **no** — Gazebo-only, Isaac brings its own physics/sensors |

On top of that the file uses `$(find cobraflex)` substitutions, xacro math /
property expansion, and `<visual>`/`<collision>` elements with no `<geometry>`
on `base_footprint` — all of which the Isaac URDF importer rejects or cannot
resolve.

The solution is a single self-contained URDF: **`src/cobraflex/urdf/cobraflex_isaac.urdf`**.

## How it is generated (re-derivable)

`tools/build_isaac_urdf.py` produces the Isaac URDF from the source xacro:

```bash
source /opt/ros/jazzy/setup.bash      # provides `xacro`
python tools/build_isaac_urdf.py
```

It performs four steps:

1. **Expand xacro** — resolves macros, properties, math and `$(find …)`.
2. **Strip `<gazebo>`** — removes every Gazebo plugin and sensor block.
3. **Rewrite mesh paths** — `file://$(find cobraflex)/meshes/x.stl` →
   `../meshes/x.stl`, so meshes resolve **relative to the URDF file** with no
   ROS / ament index. (The URDF lives in `urdf/`, meshes in `../meshes/`.)
4. **Drop empty visual/collision** — removes the geometry-less elements on
   `base_footprint` that violate the URDF schema.

The output is flagged `GENERATED … do not edit by hand` — change the source
xacro and re-run. Validate with `check_urdf src/cobraflex/urdf/cobraflex_isaac.urdf`.

### What is preserved

All kinematic, inertial and material attributes of the source: 17 links, 16
joints (4 `continuous` wheel joints + 12 fixed), the chassis/body/wheel/lidar/
ZED STL visuals, box/cylinder/mesh collisions, computed inertia tensors, and the
named materials (black/grey/blue/yellow/orange + the ZED's inline `zed_mat`). The
ZED Mini stereo frames (`zedm_camera_link` → `zedm_camera_center` →
`zedm_{left,right}_camera_frame` with their optical children), the Lane Cam
(`camera_link_lane` + pitched `camera_link_optical_lane`), the `lidar_link` and
`imu_link` frames are all kept — only the Gazebo *sensors* on them are dropped
(Isaac sensors are added in-engine, not via URDF).

## Importing into Isaac Sim

### Option A — GUI

`File ▸ Import`, select `src/cobraflex/urdf/cobraflex_isaac.urdf`. In the import
options keep **Merge Fixed Joints off** and **Base Fixed off** for a faithful,
free-base articulation. Meshes load from `../meshes/` automatically.

### Option B — headless / scripted (Isaac Sim 6.0 API)

```python
from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig
cfg = URDFImporterConfig(
    urdf_path=".../cobraflex_isaac.urdf",
    usd_path=".../isaac_usd",       # output package dir
    merge_fixed_joints=False,
    fix_base=False,
)
usd_path = URDFImporter(cfg).import_urdf()   # writes a USD package, returns its path
```

`tools/isaac_import_check.py` is a runnable smoke-test of exactly this path:

```bash
~/isaacsim/python.sh tools/isaac_import_check.py
```

It converts the URDF, loads the resulting USD with payloads, and asserts the
articulation root, all 17 link frames, ≥5 mesh prims and the 4 revolute wheel
joints are present (exit 0 = PASS).

## Verified result

> **Note (2026-06-19):** the run below was on the **mono-ZED** URDF (13 links).
> The source xacro since switched the front camera to a **ZED Mini stereo pair**
> (`zedm_*` frames, 17 links / 16 joints), so `cobraflex_isaac.urdf` was
> regenerated. The committed `isaac_usd/` package is therefore stale — re-import
> it (`BRINGUP_REIMPORT=1`, or delete `isaac_usd/` then run
> `isaac_import_check.py` / the bring-up) before relying on the figures here.

Headless conversion on Isaac Sim `6.0.0-rc.59` produced a valid USD package
under `src/cobraflex/urdf/isaac_usd/cobraflex_isaac/`:

- `cobraflex_isaac.usda` — articulation root + payload references
- `payloads/geometries.usd` (~39 MB) — the converted STL geometry
- `payloads/materials.usda`, `payloads/Physics/{physics,physx,mujoco}.usda`,
  `payloads/robot.usda`

The 9 mass-bearing links become PhysX rigid bodies; the 4 massless frames
(`base_footprint`, the two `*_optical` frames, `imu_link`) become Xform frames
(no inertia/geometry → no rigid body, as expected); the 4 wheel joints import as
`UsdPhysics.RevoluteJoint`. The wheel joints have no drive gains in the URDF, so
Isaac creates actuators without stiffness/damping (warning only) — add a drive
controller in-engine if you need to actuate them.

> The `isaac_usd/` output package is a generated artifact (re-derivable from the
> URDF) and should be treated like `build/` — regenerate rather than hand-edit.

## Driving it over ROS2 — the Gazebo → Isaac transition

Goal: replace Gazebo while keeping the **same ROS2 nodes** (lane perception, PD
baseline, safety cage, vehicle control, `teleop_twist_keyboard`). In Isaac the
ROS2 link is **not** a plugin inside the URDF — it is the **ROS2 Bridge** wired as
an **OmniGraph Action Graph**. Reproduce the topic contract and every existing
node works unchanged.

### What replaces each Gazebo plugin / sensor

| `robot.gazebo` element | Topic | Isaac OmniGraph node(s) |
| --- | --- | --- |
| DiffDrive plugin | sub `cmd_vel` | `ROS2SubscribeTwist` → ScriptNode (diff-drive kinematics) → `IsaacArticulationController` driving the 4 wheel joints |
| OdometryPublisher | pub `odom` (encoder), `odom_truth` (ground truth) + `odom→base_footprint` TF | `IsaacComputeOdometry` → `ROS2PublishOdometry` ×2 + `ROS2PublishRawTransformTree` |
| (TF) | pub `tf` | `robot_state_publisher` (URDF + `/joint_states`); Isaac `ROS2PublishTransformTree` off by default |
| JointStatePublisher | pub `joint_states` | `ROS2PublishJointState` |
| (sim time) | pub `clock` | `IsaacReadSimulationTime` → `ROS2PublishClock` |
| IMU sensor | pub `imu` | `IsaacImuSensor` prim → `IsaacReadIMU` → `ROS2PublishImu` |
| gpu_lidar | pub `scan` | RTX lidar (`RPLIDAR_S2E`) + `IsaacCreateRenderProduct` → `ROS2RtxLidarHelper` |
| ZED stereo / lane camera | pub `camera/{left,right}/image_raw`, `camera/image_raw_lane` (+ `camera_info`) | `Camera` prim + `ROS2CameraHelper` + `ROS2CameraInfoHelper` (one graph each) |

The drive train is the only non-trivial mapping: the Gazebo DiffDrive drove
`left = front_left+rear_left`, `right = front_right+rear_right`. A ScriptNode runs
the same kinematics (wheel_radius 0.03725 m, wheel_separation 0.154 m) and commands
all four wheels. (`wheel_radius` is confirmed by physical measurement;
`wheel_separation` 0.154 m is in fact the measured *wheelbase* — the measured
*track* is 0.153 m. Deliberately left as-is: 0.65 %, versus the 2× yaw error in
docs/14 §2.3a. See the note there.) **Velocity control in PhysX needs a drive with damping**, which the
imported `continuous` joints lack — the bring-up script applies a stiffness-0 /
high-damping angular drive to each wheel joint, otherwise a commanded velocity
produces no torque and the robot does not move.

### Bring-up script

`tools/isaac_ros2_bringup.py` builds the physics scene — robot, wheel drives, track —
via the shared `tools/isaac_scene.py` (the same module the RL trainer uses, so the two
can't drift on drivetrain/scene parameters), wires the full ROS2 graph on top and runs.
Invocations (GUI / `--headless` / `--test`) and env vars are in the
[Command reference](#command-reference-what-launches-what); source ROS2 first so the
bridge talks to the system Jazzy.

> **gui/headless convention (note the asymmetry between the two tools).** The
> bring-up **defaults to the GUI viewport** (it is an interactive drive/SLAM/RViz
> tool) and you opt *out* with `--headless`. The RL trainer
> ([below](#rl-training--in-process-gazebo-free-d-44)) is the opposite: it
> **defaults to headless** (the fast/reproducible path) and you opt *in* with
> `--render gui`. So GUI-on is `isaac_ros2_bringup.py` (no flag) vs
> `isaac_train.py --render gui`; headless is `isaac_ros2_bringup.py --headless` vs
> `isaac_train.py` (no flag). `--test`/`--turn`/`--shot`/`--cam-shot` force
> headless regardless.

Then drive it from another sourced terminal — exactly like with Gazebo:

```bash
source /opt/ros/jazzy/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# your stack works unchanged: any node publishing geometry_msgs/Twist on /cmd_vel
# (e.g. vehicle_control_node) drives the robot.
```

> Sim time: Isaac publishes `/clock`. Run your nodes with
> `use_sim_time:=true` so timestamps line up with the simulator.

### Physics tuning — skid-steer turning

The cobraflex is a **4-wheel skid-steer** (it yaws by spinning the left vs right
wheels at different speeds, scrubbing all four tyres sideways). The Gazebo URDF set
`mu1=mu2=0.8` on the wheels, but those were `<gazebo>` tags dropped for Isaac, so
the wheels fell back to the default (grippy) PhysX material. PhysX grips harder
laterally than Gazebo's ODE, so the four wheels lock the yaw and **the robot barely
turns** — the symptom you saw.

Two things matter and the bring-up applies both:

1. **Wheel velocity drives** (stiffness 0, damping 1e4) — without them a commanded
   wheel velocity makes no torque and the robot doesn't move at all.
2. **Lowered wheel + ground friction** (`combine="min"`, bound to the wheel
   *collider* prims, with an explicit ground material) — this frees the lateral
   scrub so the robot yaws again.

Measured yaw rate against an aggressive in-place test command (ideal 2.9 rad/s),
`tools/isaac_ros2_bringup.py --turn`:

| friction (wheel = ground) | yaw achieved | forward (of ideal) |
| --- | --- | --- |
| 0.5 (PhysX default-ish) | 0.09 rad/s | — (barely turns) |
| 0.10 | 0.26 rad/s | 80% |
| **0.05 (default)** | **0.53 rad/s** | 65% |

It is a genuine trade-off: lower friction turns better but slips more on
straights; higher friction tracks straights better but resists turning. The
default 0.05 prioritises responsive turning (the reported problem). Tune live with
env vars, no rebuild:

> **Calibration target added 2026-08-17 — the real car measures 0.4954.** The
> platform team's in-place rotation test (*CobraFlex 1:14 Parameters_0813*, docs/14
> §2.3a) puts the physical chassis at **0.4954 × commanded yaw, and 0.99 × commanded
> forward speed**. Against the ideal 2.9 rad/s of the `--turn` test that is a target
> of **≈1.44 rad/s achieved** — well above the 0.53 rad/s the default 0.05 delivers.
> Two things follow:
>
> 1. **Isaac is ~2.75× pessimistic on yaw**, Gazebo ~2× optimistic (its DiffDrive
>    tracks ~1:1). The truth sits between them, closer to Gazebo. D-54's
>    `cage.yaw_gain 2.4` was compensating a plant that is too slippery; the
>    physically-correct fix is to tune friction until `--turn` returns ≈1.44 rad/s
>    and then restore `yaw_gain` to the Gazebo 0.8.
> 2. **One friction knob probably cannot match both axes.** The real car is
>    0.99 forward / 0.495 yaw. At 0.05 Isaac is already down to 65 % forward while
>    still only reaching 0.18 yaw — the knob trades the two against each other in the
>    wrong proportion, and extrapolating the table toward 1.44 rad/s would push
>    forward tracking further from 0.99. Expect to need **anisotropic wheel friction**
>    (low lateral / high longitudinal) rather than a lower isotropic `mu`. Not yet
>    attempted; recorded so the next Isaac session does not re-derive it.

```bash
WHEEL_FRICTION=0.1 GROUND_FRICTION=0.1 ~/isaacsim/python.sh tools/isaac_ros2_bringup.py
```

An asymmetric low-friction-front / grippy-rear split was tried and made the yaw
*unstable* (it fishtailed) — avoid it. If you later need both crisp turning **and**
faithful straight-line traction, the correct (heavier) fix is anisotropic tyre
friction via the PhysX Vehicle model, or modelling the platform as a 2-wheel
differential drive + passive casters.

### Verified (Isaac Sim 6.0.0-rc.59, RTX 5060, 2026-06-16)

- `--test` builds the graph, applies 4 wheel drives, and commands the wheels:
  **base translates 3.33 m → `[RESULT] PASS`** (drive train works end-to-end).
- Live ROS2 check from a sourced host terminal against `--headless`:
  `ros2 topic list` shows `/clock /cmd_vel /odom /tf /joint_states`;
  `ros2 topic info /cmd_vel` → **Subscription count: 1** (Isaac subscribes), and the
  bridge loads the system `rclpy` ("system rclpy loaded"). So a `teleop_twist_keyboard`
  publisher reaches the robot.
- Two deprecation warnings (`ROS2PublishTransformTree` targetPrims /
  `ROS2PublishJointState` targetPrim) are non-fatal; switch to the
  `IsaacComputeTransformTree` / `IsaacReadJointState` feeders to silence them.

### Sensors (lidar + three cameras: ZED stereo + lane)

Isaac sensors are created **in-engine** (not in the URDF) and published over the
bridge with helper OG nodes. `add_sensors()` mirrors the Gazebo `<sensor>` blocks,
on the same ROS2 topics + frame ids so existing perception nodes (e.g.
`lane_keeper_node`) consume them unchanged:

| Gazebo sensor | link | ROS2 topic(s) | Isaac graph |
| --- | --- | --- | --- |
| ZED Mini stereo (640×480/eye, hfov 80°) | `zedm_{left,right}_camera_frame_optical` | `camera/{left,right}/image_raw` + `…/camera_info` | `IsaacCreateRenderProduct` → `ROS2CameraHelper` (rgb) + `ROS2CameraInfoHelper`, one graph per eye (skip both with `BRINGUP_ZED=0`) |
| Lane Cam (640×360, hfov 90°) | `camera_link_optical_lane` | `camera/image_raw_lane` + `camera/camera_info` | same, own graph |
| RPLiDAR (360°, 2D) | `lidar_link` | `scan` | `IsaacSensorCreateRtxLidar` → `IsaacCreateRenderProduct` → `ROS2RtxLidarHelper` (laser_scan) |
| IMU (200 Hz) | `imu_link` | `imu` | `IsaacImuSensor` prim (`IMU.create`) → `IsaacReadIMU` → `ROS2PublishImu` |

Plus ground-truth odometry on **`/odom_truth`** (a second `ROS2PublishOdometry` off
the same `IsaacComputeOdometry`, which already reads the true sim pose) mirroring the
Gazebo OdometryPublisher that RL training consumed.

A USD `Camera` is created under each ROS optical frame with a 180°-about-X offset
(USD looks down −Z, ROS optical is +Z forward) and focal length set from the
Gazebo hfov, so `camera_info` intrinsics match (verified fx≈381 px for the ZED cam,
320 px for the lane cam). The cameras/lidar render off-screen, so the run loop
renders every frame (even `--headless`); they are skipped in the physics-only
`--test`/`--turn` paths. Toggle with `BRINGUP_SENSORS=0`.

**Verified (mono-ZED build, 2026-06-16)** (sourced host terminal vs `--headless`):
`ros2 topic list` showed `/scan /camera/image_raw /camera/camera_info
/camera/image_raw_lane`; `/camera/image_raw_lane` echoed height 360 × width 640.
After the ZED→stereo switch the front-camera topics become
`/camera/{left,right}/image_raw` (+ `…/camera_info`) and the lane info topic is
`/camera/camera_info` — re-verify after re-importing the URDF.

The lidar uses the shipped **`RPLIDAR_S2E`** config (SLAMTEC, the RPLiDAR maker;
already on Isaac's default profile search path): 360° 2D rotary, **near-range
0.05 m, 10 Hz** — close-range like the Gazebo RPLiDAR (`Example_Rotary_2D`, the
first choice, only detected from 1 m). Override with `LIDAR_CONFIG=<name>` (any
profile under `app.sensors.nv.lidar.profileBaseFolder`; a *custom* JSON must sit in
one of those default folders, since the Python create-command's config list is
built at extension load and ignores folders added at runtime).

**Verified** IMU + ground-truth odometry (`--headless`, rclpy sensor-QoS subscribers):
`/imu` reports `linear_acceleration.z ≈ 9.81` (gravity, at rest) and zero angular
velocity; `/odom_truth` reports the chassis pose. Both on the Gazebo topic names.

### RViz (same as Gazebo)

RViz is simulator-agnostic — it just reads ROS2 topics, so the **same workflow as
Gazebo** applies. The bring-up publishes `/scan`, `/camera/image_raw[_lane]`,
`/odom`, `/joint_states` and `/clock` (verified monotonic, single publisher, 60 Hz).

TF ownership mirrors the Gazebo stack: **`robot_state_publisher`** publishes the
robot tree (it reads the URDF, so it includes `base_footprint` and the empty
`*_optical` frames — which the image `frame_id`s reference), driven by Isaac's
`/joint_states`; Isaac publishes only `odom → base_footprint`. Isaac's own
`ROS2PublishTransformTree` is **off by default** (`BRINGUP_ROBOT_TF=1` to enable a
partial standalone tree) because it rejects the massless `base_footprint` and skips
the `*_optical` frames, giving a broken tree.

Run it (each terminal sourced, **`use_sim_time:=true`** everywhere because Isaac
drives `/clock`):

```bash
# 1) Isaac bring-up (publishes odom, joint_states, sensors, clock)
$ISAAC tools/isaac_ros2_bringup.py

# 2) robot_state_publisher = robot TF tree + RobotModel (/robot_description)
ros2 launch cobraflex cobraflex_description.launch.xml   # your existing launch, add use_sim_time
#   or directly:
ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=true \
    -p robot_description:="$(xacro src/cobraflex/urdf/my_robot_gazebo_mesh.urdf)"

# 3) RViz with your existing config
ros2 run rviz2 rviz2 -d src/cobraflex/rviz/<your_config>.rviz --ros-args -p use_sim_time:=true
```

In RViz set **Fixed Frame = `odom`** and add LaserScan (`/scan`), Image
(`/camera/image_raw_lane`), TF and Odometry displays — exactly as before. Use the
xacro (not `cobraflex_isaac.urdf`) for `robot_description` so the RobotModel mesh
paths (`package://`/absolute) resolve; the flat URDF's `../meshes` paths won't.

> A burst of `robot_state_publisher: Moved backwards in time` warnings at startup is
> the sim-clock settling as Isaac begins playing — benign; TF resolves once running.

### Track (lane-following circuit)

The Gazebo lane worlds (`src/cobraflex/worlds/lane_following_oval_*`) were tile-based
ovals. For Isaac, `scripts/generate_complex_track.py` builds a **complex closed
circuit** as a single top-down road texture, so the camera sees the same road look
the perception was trained on (black asphalt, 1 cm white solid edges, 10/10 cm dashed
white centreline, 0.52 m road width — mirrors `road_tiles/make_road_tiles.py`).

The centreline is a closed Catmull-Rom spline through hand-placed waypoints (the
`TRACKS` presets), giving curves of **both handedness** and a range of radii (tight
~0.4 m + open ~5 m) so an agent can't overfit one turn. The texture is rendered at
500 px/m with 2× supersampling (LANCZOS downsample) so lane lines aren't jagged.
Outputs (under `experiments/sim/tracks/<name>/`): `<name>.png` (texture),
`<name>_centerline.yaml` (cage / lane_perception schema), `<name>_meta.yaml`
(size/centre/start-pose for placement). Presets:

- `complex_a` — kidney loop with a bottom right-hand S (min radius 0.40 m).
- `complex_b` — a ~2.8 m **pure straight** along the bottom + the softened two-hump "M"
  technical run on the opposite side (centre R_min 0.86 m / driven right lane 0.998 m —
  the geometry the GE4-V2 verdict ran on). The committed asset is the **two-lane** build
  (road 0.52 m, lane 0.245 m, dashed centre; `lanes: 2` in its meta) driven on the
  **right lane** (`complex_b_right_lane_centerline.yaml`, offset 0.1225 m).
- `complex_c` — top sweep + right-hander + a gentle bottom chicane (0.54 m).
- `complex_d` / `complex_e` — the **CV-safe** presets added for D-50 multi-track camera
  training: complex_b's philosophy (long straight + wide U-turn ends + counter-steer
  features, both handedness) with driven right-lane R_min ≥ 0.90 m, respecting the
  monocular **curvature boundary** (docs/12 §4.7). `complex_d` = bottom straight + wide
  single-valley "V" top (0.884 / 0.932 m), CCW like complex_b. `complex_e` (v2, **D-51**)
  = the **clockwise** member: top straight, wide R = 1.4 m end U-turns (the driven right
  lane runs INSIDE them on a CW circuit), cosine-"W" bottom (1.079 / 0.956 m) — it flips
  the per-lap steering handedness so the trio trains right-turn-dominant laps too
  (driven turning arc balance 28.3 m left / 14.2 m right ≈ 2:1; it was 8:1 when all
  three were CCW). Waypoints come from the analytic dense builder
  `_complex_e_cw_waypoints()` (sparse Catmull-Rom kinks at curvature sign flips — D-51).

> **Curvature-boundary caveat (docs/12 §4.7).** `complex_a` and `complex_c` have
> driven-lane radii far below ~0.9 m, where the cage's monocular CV heading over-read
> (`≈ κ·0.225`) exceeds C-02's `theta_max` and latches **false emergencies** while the
> car tracks the lane. Use them only for ground-truth-cage (state-vector) or
> monitoring-mode runs — the camera-track training set is `complex_b,complex_d,complex_e`.

```bash
python scripts/generate_complex_track.py --name all   # build all presets
python scripts/track_to_gazebo_world.py --name complex_b   # + a Gazebo .world
```

The bring-up loads the selected track (visual only; the GroundPlane keeps physics) and
spawns the robot at the start line — pick it with `TRACK=<preset>` (empty `TRACK=` → bare
ground) and snapshot it with `--shot`; both are in the
[Command reference](#command-reference-what-launches-what).

The bring-up builds the track as **USD geometry by default** (`TRACK_MODE=geom`): asphalt ribbon + white edge/centre-line meshes from the centreline — crisp at any camera distance, no texture aliasing or resolution ceiling (the better choice for Isaac vs a baked PNG). `TRACK_MODE=texture` falls back to the PNG quad (what the Gazebo `.world` uses). Camera-visibility of any pose: `CAM_POSE=x,y,yaw ... --cam-shot out.png`.

**Verified**: `--shot` renders the textured circuit (green off-road, dark asphalt,
white dashed centre + solid edges) — the material binds correctly in Isaac.

## RL training — in-process (Gazebo-free, D-44)

The ROS2 bring-up reproduces the *steady-state* topic contract, but RL **training** also
needs a per-episode **reset/teleport**. Against Gazebo that went through
`gz service /world/<name>/set_pose` (a Gazebo Transport service) — which has **no Isaac
equivalent** (no `gz` server runs alongside Isaac), so training cannot run over the
bring-up. Instead it runs **in-process inside the Isaac Python app**, driving the gym env
directly against the live `World` (option 2 of the migration; full rationale in
[D-44](DECISIONS.md), the RL-side contract in [docs/14 §3](14_isaacsim_handover_spec.md)).

### How it is built

The bring-up and the trainer **share one physics scene**, so they can never drift on the
drivetrain/scene parameters that define what the policy was trained against:

```
tools/isaac_scene.py        # SHARED: world, lights, ground, track geometry, robot spawn,
                            # wheel velocity drives + low-friction materials, and the single
                            # source of WHEEL_RADIUS / WHEEL_SEPARATION / WHEEL_JOINTS order /
                            # WHEEL_SCRIPT + the Lane Cam spec. (omni/pxr imports deferred
                            # into functions, so it is safe to import before SimulationApp.)
  │
  ├─ tools/isaac_ros2_bringup.py   # + ROS2-bridge graph + sensor graphs  (deploy / eval / SLAM)
  └─ tools/isaac_train.py          # + Lane Cam render product + IsaacSimInterface + SB3 PPO
```

`IsaacSimInterface` (`src/cobraflex_rl/cobraflex_rl/isaac_interface.py`) duck-types the
exact surface `GazeboLaneEnv` already calls, so the **gym env is unchanged** — each
operation is a direct Isaac call instead of a ROS round-trip:

| Env call | Gazebo path (ROS) | In-process Isaac path |
| --- | --- | --- |
| `set_vehicle_pose` (per-episode reset) | `gz service set_pose` | `articulation.set_world_pose` + zeroed velocities |
| `send_action` (actuation) | publish `/cmd_vel` | diff-drive twist → 4 wheel `ArticulationAction` (same `WHEEL_SCRIPT` kinematics) |
| `step_ros` (advance) | wait on `/odom_truth` sim-time | `world.step()` × `control_dt / physics_dt` sub-steps |
| `get_pose` / `get_speed` | `/odom_truth` subscriber | articulation root (ground truth → no odom→world calibration) |
| `get_camera_frame` | `/camera/image_raw_lane` subscriber | Replicator `rgb` render product on the Lane Cam (640×360, RGBA→BGR) |

`GazeboLaneEnv`'s only hard `rclpy` import (the `RosGazeboInterface` type hint) is now
under `TYPE_CHECKING`, so the env imports on the Isaac host **without `rclpy`**.

### Launch commands

The exact invocations (state-vector, track-'E' camera, resume, `--render gui`) live in the
[Command reference](#command-reference-what-launches-what). Two requirements that bite if
missed: Isaac's bundled python must have `stable-baselines3` + `gymnasium` installed and the
cached USD must be re-imported on first run (`BRINGUP_REIMPORT=1`); and `TRACK` selects the
*visual* scene track while `--centerline-config` selects the env *geometry* — **they must
correspond** (multi-track runs enforce this automatically via the naming convention).

### Full-authority training — 2-D action + multi-circuit (D-50)

The trainer's default config ([`train_isaac_2d.yaml`](../src/cobraflex_rl/config/train_isaac_2d.yaml))
is the **full-authority** setup — the D-49 deferral taken up now that G4 is closed:

- **2-D action** (`action.type: steer_throttle`): the policy commands `[steer, throttle]`
  in `[-1, 1]²`; throttle maps to the cage scale `u ∈ [0, 1]` and actuates as
  `speed = 0.5 m/s · u` (full stop below the 0.05 deadband; `cage_bridge`
  `target_speed_from_throttle_2d`). `max_speed_mps 0.5` equals C-04's `v_max_straight`
  (= ODD-1.V_MAX), so — unlike the 1-D path, whose actuation capped speed at 0.20 m/s,
  *below every C-04 ceiling* — the cage's speed rules (C-04 attenuation, C-05 Trigger B,
  C-06 throttle rate) **genuinely arbitrate against the policy**. C-06 then bounds
  commanded acceleration to 0.5 m/s² (platform limit 0.53, docs/14 §2.3). A true stop is
  commandable, so SR-009's stall/liveness sub-mode (M-P6, SC-PERT-03) is **well-posed**
  on this action space. Reward adds a `throttle_delta` raw-delta smoothness term
  (longitudinal mirror of the v1.2 steering term). The frozen 1-D contract is the
  default everywhere else — no `action:` block means `steer`, bit-identical.
- **Multi-circuit sampling** (`--track complex_b,complex_d,complex_e`): the scene builds
  all listed circuits **15 m apart** (`TRACK_GAP_M` = the Lane-Cam far clip, so a
  neighbouring circuit never enters the frustum), one shared grass backdrop, and the
  track materials at the shared DR prim paths (one `isaac_dr` draw re-colours all
  circuits coherently). The env pre-builds per-circuit trackers and **samples one
  circuit per episode** (seeded; `options={"circuit_index": i}` pins it for
  deterministic eval; `info["circuit_name"]` tags every step). Per-track geometry
  YAMLs are resolved by convention and shifted by the exact scene offsets
  (`isaac_scene.load_circuits`), and the run metadata records per-circuit paths +
  hashes. Training across three track shapes + physics/scene/visual DR is what "follows
  the lane markings of *any* circuit" operationally means for this stage.

A policy trained here is a **new baseline** (new action space, simulator and circuits) —
it does not reopen the Gazebo verdicts (D-49/D-50). Unit coverage on the authoring host:
16 env tests drive the real cage through a fake interface (C-04 fires on overspeed, C-06
clips throttle jumps, stall reachable, sampling reproducible). **Live-validated on the
Ubuntu + Isaac host (03.07.2026):** the three-circuit scene builds at offsets
(+0.0 / +24.766 / +49.724 m at pilot time; the D-51 complex_e re-cut shifts its offset
to +49.92 m — the 15 m bbox gaps and one union grass backdrop hold) and per-circuit
Lane-Cam renders confirm the far-clip isolation (no neighbour in frame, including the
tightest case — complex_e's start looking at complex_d's bbox ~16.2 m away). The 20k
full-authority pilot `isaac2d_pilot_20k` (seed 2024) completed end-to-end: per-circuit
YAML hashes + the `action` block in `metadata.json`, `raw_throttle` in
`action_samples.csv`, episodes well past spawn priming (`ep_len_mean` 13.5 → 35.6), and
the cage speed rules **measurably active in-training** (C-04 on 0.7–1.8 % of steps —
the structurally-latent-in-1-D finding flips exactly as D-50 predicted). Measured
throughput on this scene (multi-track + physics/scene/visual DR + 2-D action, RTX 5060):
**~25 env-steps/s** steady-state headless — below the ~33 of the single-track 1-D pilot
(table below), so budget **~11 h for the 1M run** on this class of GPU.

### Hard-section spawn curriculum — `random_start_s` (D-58)

`spawn_perturbation.random_start_s` (config-gated, default **False** → bit-identical) makes a
training episode with no explicit `start_s` spawn at a **uniform random arc-length** along the
driven centreline instead of always the start line. Rationale (Isaac U-turn diagnostic): a
tight section reached only after surviving the preceding track gets almost no early-training
visits → **no gradient at the hardest corner → the policy never learns it** (chicken-and-egg).
Random along-track spawn practises every part — including that corner — from step 0. General,
reusable curriculum lever (any circuit with an under-visited apex/chicane); composes with DR
and multi-circuit sampling; cheaper than reward shaping. **Judge only by deterministic nominal
eval (laps from the start line)** — the flag shifts the training-time episode-length/return
distribution, so `ep_rew_mean`/`ep_len_mean` are NOT comparable across it. Deterministic eval
and F4 scenarios (explicit `start_s`/`circuit_index`) are unaffected. See D-58.

### Domain randomization (sim-to-real)

Beyond the image-level visual degradation (`domain_randomization` — the H-10 trio that
corrupts the *rendered frame*, shared with the Gazebo path), the in-process Isaac trainer
adds **per-episode physics + scene randomization** so the policy sees a *distribution* of
dynamics and appearances instead of a single un-calibrated nominal. It is applied by
`tools/isaac_dr.py` (`IsaacDomainRandomizer`), attached in `build_isaac_interface` and
re-sampled on every reset, seeded by the PPO seed for a reproducible episode-parameter
stream. **Isaac-only** — the Gazebo path and deterministic eval ignore these blocks; every
`pxr` import is deferred per the `isaac_scene` import-order contract, so the module is safe
to import off the Isaac host (pytest, the campaign runner) — it pulls in only `numpy`.

Three independent, config-gated aspects (each inert unless `enabled`), set in the train
YAML (e.g. `train_ppo_camera.yaml`):

| Block | Lever | What it randomizes per episode |
| --- | --- | --- |
| `dynamics_randomization` | #2 dynamics + #3 latency | wheel+ground `friction_range`, `mass_scale_range` (best-effort link-mass scale), `yaw_scale_range` (gain on commanded angular velocity), `latency_steps_range` (actuation delay in control cycles — the interface buffers wheel commands and applies the N-steps-old one) |
| `scene_randomization` | #4 scene appearance (camera only) | dome/sun light intensity scales, `light_tint`, and asphalt / lane-line / grass diffuse-colour jitter — shadows, exposure and surface-colour shifts the frame-level degradation cannot reproduce |

```yaml
dynamics_randomization:           # sim-to-real lever #2/#3
  enabled: true
  friction_range:      [0.04, 0.07]   # effective wheel+ground friction (both equal; combine=min)
  mass_scale_range:    [0.85, 1.15]   # multiply explicit link masses (no-op if density-derived)
  yaw_scale_range:     [0.8, 1.2]     # gain on commanded angular velocity (yaw uncertainty)
  latency_steps_range: [0, 2]         # actuation delay in control cycles (0.10 s/step → up to 0.2 s)

scene_randomization:              # sim-to-real lever #4 (camera only)
  enabled: true
  dome_intensity_scale: [0.6, 1.4]
  sun_intensity_scale:  [0.5, 1.5]
  light_tint:    0.1                   # ± per-channel multiplicative tint on the lights
  asphalt_jitter: 0.08                 # near-black asphalt: brighten-only lift up to this
  line_jitter:   0.15                  # lane-line grey jitter (±)
  grass_jitter:  0.10                  # off-road colour jitter (±)
```

> **Friction/yaw ranges are placeholders.** They are centred on the current sim nominal
> (friction 0.05; cf. the `WHEEL_FRICTION` note above) because the skid-steer yaw response
> is **not yet calibrated against the real platform** — re-centre once real-platform
> system-ID lands. The scene blocks also enabled the `p_degrade` 0.25→0.5 / `level_range`
> ceiling 0.5→0.8 widening of the image-level `domain_randomization` that the newcam 425k
> run used (§7.7.8).

**Watching training (at the cost of compute).** Headless is the default and the fast path.
For human visual assessment two independent switches are available:

| Flag | What you see | Cost |
| --- | --- | --- |
| `--render gui` (or `ISAAC_RENDER=gui`) | the native Isaac viewport — the car driving the track in 3D | renders the full viewport once per control step (forces a render even on the camera-less state-vector path, which otherwise never renders) |
| `--show-obs` | a live OpenCV window of the **exact frame the CNN sees** this step (the degraded 84×84 grayscale obs), refreshed every `--obs-preview-every` steps (default 15) | one resize + `imshow` per refresh; auto-disables if OpenCV or a display is missing; camera obs only |

`--render` is parsed before `SimulationApp` (it sets `headless`), so it also works as the
`ISAAC_RENDER` env var. The two combine — `--render gui --show-obs` shows both the 3D scene
and the CNN input. Neither changes the training math; they only add render/I-O work, so the
fast/reproducible runs stay headless. (Mind the convention flip vs the bring-up: the trainer
**defaults to headless** and opts *into* the viewport with `--render gui`, whereas
`isaac_ros2_bringup.py` defaults to the GUI and opts *out* with `--headless` — see the
[bring-up note](#bring-up-script).)

Outputs mirror the Gazebo trainer: `experiments/sim/training/<run_id>/` (learning curve,
action samples, `metadata.json` with `platform: sim-isaac`) + periodic checkpoints under
`policy/checkpoints/`. No ROS, no `gz` CLI — training never needs a running bring-up.

> **Validated on the Isaac host (03.07.2026; previously host-deferred).** The live
> `world.step` / `set_world_pose` / `get_linear_velocity` / Replicator annotator flow and
> SB3-in-Isaac-python (sb3 2.8.0, gymnasium 1.2.3, torch cu130) are confirmed on the
> Ubuntu + Isaac 6 host — the D-50 full-authority 20k pilot (`isaac2d_pilot_20k`) ran
> end-to-end with status `completed`. The in-process camera renders once per control step
> (~10 Hz at `control_dt` 0.10), which is what the env samples (below the ≥20 Hz
> steady-state target the ROS bridge publishes).

### Speed and fidelity — same logic, different environment

In-process Isaac training runs **markedly faster than the Gazebo trainer with the
identical config**. Measured on the same host (RTX 5060), identical config (camera-obs
`complex_b` pilot, same `control_dt`):

| Backend / mode | Throughput | vs Gazebo |
| --- | --- | --- |
| Gazebo trainer | **~8 env-steps/s** | 1× |
| Isaac, headless (`--render headless`) | **~33 env-steps/s** | ~4.1× |
| Isaac, `--render gui` (viewport) | **~23 env-steps/s** | ~2.9× |

So the GUI viewport costs ~10 steps/s (33 → 23) — the quantified price of human visual
monitoring. The speed-up is purely a property of *how the sim is stepped*, not of any
RL/config change:

| Source | Gazebo trainer | In-process Isaac |
| --- | --- | --- |
| Process boundary | env ⇄ simulator over **DDS/ROS2** (serialise/deserialise + spin each cycle) | one Python process; `step_ros` → `world.step()` directly, zero round-trips |
| Real-time lock | physics paced to wall clock (RTF ≈ 1) | `set_real_time_factor` is a **deliberate no-op** — integrates as fast as the host allows |
| Rendering | render path active | `headless` renders nothing; `--render gui` renders the viewport once per control step |

**Fidelity caveat (important).** The *agent logic is byte-for-byte the same code* — the gym
env (`GazeboLaneEnv`), the safety cage (`SafetyCageNode` + the same `cage.yaml`, rules
C-01..C-06, enforcement/monitoring), the CV lane-estimator feeding the cage
(`CagePerceptionSupervisor`, D-43) and the camera obs pipeline (`CameraPipeline`, 84×84
grayscale) are all shared and unchanged across backends. **Same code does not mean same
environment**, because the *inputs* to that code are generated by a different sim:

- **Physics:** PhysX (Isaac) vs ODE/DART (Gazebo) — contacts, friction and integration
  differ even at identical `control_dt` and drivetrain geometry.
- **Vision:** the RTX renderer (Isaac) vs the Gazebo render produce different pixels
  (lighting, shadows, textures, AA, USD vs URDF camera intrinsics) for the *same* nominal
  camera. This shifts the **observation distribution** the CNN sees, and likewise the CV
  estimator's output (its Gazebo-calibrated thresholds are not guaranteed on Isaac).

Consequence: a checkpoint trained under Gazebo is **not transferable to Isaac without
retraining/re-validation**, and vice-versa — the same reason the camera switch forced a
retrain-from-scratch (§7.7.8). When comparing the two backends, the meaningful axis is
**steps-to-convergence and the resulting policy/cage behaviour**, never env-FPS.
