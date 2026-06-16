# 13 — Importing the CobraFlex URDF into Isaac Sim

Status: working (verified headless on Isaac Sim 6.0, RTX 5060 host, 2026-06-16).

## Why a dedicated URDF

The simulation robot used by the `cobraflex` package
(`src/cobraflex/urdf/my_robot_gazebo_mesh.urdf`) is **not a plain URDF**: it is a
xacro that depends on two external files and on ROS substitution syntax that
Isaac Sim cannot resolve:

| Dependency | Role | Isaac needs it? |
| --- | --- | --- |
| `urdf/inertial_macros.xacro` | material + inertia macros | **yes** — expanded inline |
| `urdf/robot.gazebo`          | Gazebo/`gz` plugins (DiffDrive, odometry, joint-state pub) + sensors (IMU, lidar, two cameras) | **no** — Gazebo-only, Isaac brings its own physics/sensors |

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

All kinematic, inertial and material attributes of the source: 13 links, 12
joints (4 `continuous` wheel joints + 8 fixed), the chassis/body/wheel/lidar/
camera STL visuals, box/cylinder collisions, computed inertia tensors, and the
named materials (black/grey/blue/yellow/orange). The camera mount frames
(`camera_link`, `camera_link_lane` with their pitched optical frames), the
`lidar_link` and `imu_link` frames are all kept — only the Gazebo *sensors* on
them are dropped (Isaac sensors are added in-engine, not via URDF).

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
articulation root, all 13 link frames, ≥5 mesh prims and the 4 revolute wheel
joints are present (exit 0 = PASS).

## Verified result

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
| OdometryPublisher | pub `odom` | `IsaacComputeOdometry` → `ROS2PublishOdometry` |
| (TF) | pub `tf` | `ROS2PublishTransformTree` |
| JointStatePublisher | pub `joint_states` | `ROS2PublishJointState` |
| (sim time) | pub `clock` | `IsaacReadSimulationTime` → `ROS2PublishClock` |
| IMU sensor | pub `imu` | IMU prim + `ROS2PublishImu` *(not wired in the bring-up script yet)* |
| gpu_lidar | pub `scan` | RTX/PhysX lidar + `ROS2RtxLidarHelper` / `ROS2PublishLaserScan` *(not wired yet)* |
| camera / lane camera | pub `camera/image_raw[_lane]` | `Camera` prim + `ROS2CameraHelper` *(not wired yet)* |

The drive train is the only non-trivial mapping: the Gazebo DiffDrive drove
`left = front_left+rear_left`, `right = front_right+rear_right`. A ScriptNode runs
the same kinematics (wheel_radius 0.03725 m, wheel_separation 0.154 m) and commands
all four wheels. **Velocity control in PhysX needs a drive with damping**, which the
imported `continuous` joints lack — the bring-up script applies a stiffness-0 /
high-damping angular drive to each wheel joint, otherwise a commanded velocity
produces no torque and the robot does not move.

### Bring-up script

`tools/isaac_ros2_bringup.py` loads the robot, applies the wheel drives, builds the
full ROS2 graph and runs:

```bash
source /opt/ros/jazzy/setup.bash          # bridge uses the system Jazzy (it vendors
                                          # jazzy+humble; sourcing ensures interop)
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
- Not yet wired in the script: IMU, lidar and the two cameras (sensors are added
  in-engine in Isaac, not via the URDF). Add the helper nodes from the table above
  when track-E perception needs them. Two deprecation warnings
  (`ROS2PublishTransformTree` targetPrims / `ROS2PublishJointState` targetPrim) are
  non-fatal; switch to the `IsaacComputeTransformTree` / `IsaacReadJointState`
  feeders to silence them.
