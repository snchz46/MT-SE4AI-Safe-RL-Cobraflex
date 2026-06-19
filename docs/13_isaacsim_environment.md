# 13 — Isaac Sim utilities: building, driving & training the CobraFlex env

Status: URDF import + ROS2 bring-up working (verified headless on Isaac Sim 6.0, RTX 5060
host, 2026-06-16). The **in-process RL training** path is authored but **host-deferred**
(D-44) — see [RL training — in-process](#rl-training--in-process-gazebo-free-d-44).

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
| `src/cobraflex_rl/cobraflex_rl/isaac_interface.py` | `IsaacSimInterface`: in-process env I/O (teleport / step / camera) | imported by `isaac_train.py` |

Flow below: URDF rationale & generation → import → **ROS2 bring-up** (drive / SLAM / RViz)
→ physics tuning → sensors → track → **RL training in-process**.

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
all four wheels. **Velocity control in PhysX needs a drive with damping**, which the
imported `continuous` joints lack — the bring-up script applies a stiffness-0 /
high-damping angular drive to each wheel joint, otherwise a commanded velocity
produces no torque and the robot does not move.

### Bring-up script

`tools/isaac_ros2_bringup.py` builds the physics scene — robot, wheel drives, track —
via the shared `tools/isaac_scene.py` (the same module the RL trainer uses, so the two
can't drift on drivetrain/scene parameters), wires the full ROS2 graph on top and runs:

```bash
source /opt/ros/jazzy/setup.bash          # bridge uses the system Jazzy (it vendors
                                          # jazzy+humble; sourcing ensures interop)
# PC CAST
/home/admit/isaac_sim_6.0.0/isaac-sim-standalone-6.0.0-linux-x86_64/python.sh tools/isaac_ros2_bringup.py                                 

~/isaacsim/python.sh tools/isaac_ros2_bringup.py            # GUI window
~/isaacsim/python.sh tools/isaac_ros2_bringup.py --headless # no window
~/isaacsim/python.sh tools/isaac_ros2_bringup.py --test     # headless self-test, exits
```

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
# PC CAST
/home/admit/isaac_sim_6.0.0/isaac-sim-standalone-6.0.0-linux-x86_64/python.sh tools/isaac_ros2_bringup.py 

# 1) Isaac bring-up (publishes odom, joint_states, sensors, clock)
~/isaacsim/python.sh tools/isaac_ros2_bringup.py

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
- `complex_b` — a ~2.8 m **pure straight** along the bottom + a tight, scalloped
  technical run of closed left/right curves on the opposite side (min radius 0.26 m).
  Built **single-lane** (`--lanes 1`: two edges, no centre line, 0.30 m wide) so the
  camera-CV PD lane keeper has no adjacent lane to confuse on the tight curves; the
  two-lane confusion (centre + opposite-lane markings) made the PD pick the wrong
  pair and stop. `--lanes 2` (default) keeps the two-lane road.
- `complex_c` — top sweep + right-hander + a gentle bottom chicane (0.54 m).

```bash
python scripts/generate_complex_track.py --name all   # build all presets
python scripts/track_to_gazebo_world.py --name complex_b   # + a Gazebo .world
```

The bring-up loads it as a textured ground quad (visual only; the GroundPlane keeps
physics) and spawns the robot at the start line:

```bash
TRACK=complex_a ~/isaacsim/python.sh tools/isaac_ros2_bringup.py   # default
TRACK= ...                                                          # empty ground
~/isaacsim/python.sh tools/isaac_ros2_bringup.py --shot /tmp/t.png  # headless top-down render
```

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

Isaac's bundled python must have `stable-baselines3` + `gymnasium` installed; re-import the
cached USD on first run (`BRINGUP_REIMPORT=1`). `TRACK` selects the *visual* scene track;
`--centerline-config` selects the env *geometry* — **they must correspond**.

```bash
# F3 state-vector PPO (oval, the train_ppo.yaml defaults)
~/isaacsim/python.sh tools/isaac_train.py

# Track 'E' camera PPO on complex_b
TRACK=complex_b BRINGUP_REIMPORT=1 ~/isaacsim/python.sh tools/isaac_train.py \
    --train-config           src/cobraflex_rl/config/train_ppo_camera.yaml \
    --centerline-config      src/cobraflex_rl/config/complex_b_right_lane_centerline.yaml \
    --road-centerline-config src/cobraflex_rl/config/complex_b_centerline.yaml

# resume from a checkpoint
~/isaacsim/python.sh tools/isaac_train.py --resume-from policy/checkpoints/<ckpt>.zip
```

Outputs mirror the Gazebo trainer: `experiments/sim/training/<run_id>/` (learning curve,
action samples, `metadata.json` with `platform: sim-isaac`) + periodic checkpoints under
`policy/checkpoints/`. No ROS, no `gz` CLI — training never needs a running bring-up.

> **Host-deferred (not yet run on Isaac).** Authored on a Windows host without Isaac:
> `py_compile` + an rclpy-free import check pass, but the live `world.step` /
> `set_world_pose` / `get_linear_velocity` / Replicator annotator flow and
> SB3-in-Isaac-python must be confirmed on the Ubuntu + Isaac host. The in-process camera
> renders once per control step (~10 Hz at `control_dt` 0.10), which is what the env
> samples (below the ≥20 Hz steady-state target the ROS bridge publishes).
