# SETUP_ISAAC.md — running the CobraFlex Isaac Sim stack on a fresh machine

Step-by-step to reproduce the Isaac Sim bring-up (`tools/isaac_ros2_bringup.py`) on
another computer from a clone. Deep design details live in
[docs/13_isaacsim_urdf_import.md](13_isaacsim_urdf_import.md); this is the recipe.

> **The one that bites everyone:** `source` ROS2 **before** launching Isaac, or the
> ROS2 bridge fails to load (`libament_index_cpp.so: cannot open shared object file`
> → `ROS2 Bridge startup failed` → `Could not create node 'ROS2Context'`). See step 4.

## 1. Prerequisites (not in the repo)

| Need | Notes |
| --- | --- |
| **NVIDIA RTX GPU** + recent driver | Isaac/RTX requires it (≥ ~8 GB VRAM is tight but works). |
| **Isaac Sim 6.0** | Same major version — the bring-up uses 6.0 APIs (URDF importer, sensor nodes, experimental IMU, `RPLIDAR_S2E` lidar config). Other versions may break. Launcher: `<isaac>/python.sh`. |
| **ROS2 Jazzy** | For the bridge interop, `robot_state_publisher`, `teleop_twist_keyboard`, RViz. (Isaac also ships internal Jazzy libs — see step 4 option B if you have no system ROS2.) |
| Python: `numpy`, `pyyaml` | Already in Isaac's python; the system python needs them for the track generator / mesh export. |

## 2. Clone + fetch the gitignored meshes

```bash
git clone <repo> thesis_repo && cd thesis_repo
./scripts/download_meshes.sh        # the 91 MB lidar STL is gitignored; without it
                                    # the URDF import fails on rplidar-a2m4-r1.stl
```

The flat URDF (`src/cobraflex/urdf/cobraflex_isaac.urdf`) and the track files
(`experiments/sim/tracks/*`) are committed — no need to regenerate. The converted
USD package (`src/cobraflex/urdf/isaac_usd/`) is gitignored and **rebuilds itself on
first launch** (`ensure_robot_usd`, ~1–2 min the first time → the GUI looks
"not responding"; that's normal, wait for it).

## 3. (Only for the ROS2 nodes / safety cage) build the workspace

Not needed just to drive the robot in Isaac, but needed for `robot_state_publisher`
to find the package and for the cage/perception nodes:

```bash
pip install -e .                                   # cage import path (pyproject)
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 4. Launch — **source ROS2 first**

```bash
source /opt/ros/jazzy/setup.bash                   # <-- REQUIRED (bridge libs)
<isaac>/python.sh tools/isaac_ros2_bringup.py      # e.g. ~/isaacsim/python.sh
```

**Option B — no system ROS2?** Use Isaac's bundled libs instead of step-4 source:
```bash
export ROS_DISTRO=jazzy RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:<isaac>/exts/isaacsim.ros2.core/jazzy/lib
<isaac>/python.sh tools/isaac_ros2_bringup.py
```

If the bridge still didn't load the bring-up now **fails fast with the exact fix**
printed (instead of a cryptic OmniGraph error).

## 5. Smoke tests (in order)

```bash
<isaac>/python.sh tools/isaac_import_check.py          # URDF imports?  -> [RESULT] PASS
<isaac>/python.sh tools/isaac_ros2_bringup.py --test   # drivetrain?    -> [RESULT] PASS
source /opt/ros/jazzy/setup.bash
<isaac>/python.sh tools/isaac_ros2_bringup.py          # full GUI + sensors + track
```

Then, from another **sourced** terminal, drive / inspect exactly like with Gazebo:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard   # publishes /cmd_vel
ros2 topic list                                        # /cmd_vel /odom /scan /imu /camera/... /clock
```

## 6. Useful env vars (bring-up)

| Var | Default | Effect |
| --- | --- | --- |
| `TRACK` | `complex_a` | Track to load (`complex_a/b/c`, or `""` for empty ground). |
| `TRACK_MODE` | `geom` | `geom` = crisp USD vector geometry; `texture` = baked PNG quad. |
| `BRINGUP_SENSORS` | `1` | `0` to skip cameras+lidar+IMU (lighter). |
| `LIDAR_CONFIG` | `RPLIDAR_S2E` | RTX lidar profile (near 0.05 m, 10 Hz). |
| `WHEEL_FRICTION`/`GROUND_FRICTION` | `0.05` | Skid-steer turn tuning (lower = turns easier). |
| `BRINGUP_ROBOT_TF` | `0` | `1` to let Isaac publish the robot TF (else use robot_state_publisher). |
| `CAM_POSE` | — | `x,y,yaw` spawn override (used by `--cam-shot` lane-cam checks). |

## 7. RViz / TF (like Gazebo)

Isaac publishes `odom→base_footprint` + `/joint_states`; run
`robot_state_publisher` for the robot tree + RobotModel, RViz with `use_sim_time:=true`,
Fixed Frame `odom`. Full recipe in
[docs/13 §"RViz"](13_isaacsim_urdf_import.md).

## 8. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `ROS2 Bridge startup failed` / `Could not create node 'ROS2Context'` | ROS2 not sourced. Do step 4. |
| GUI segfaults at startup (~300 ms), `Segmentation fault` | GPU VRAM full from a leftover Isaac process. `nvidia-smi`; then `pkill -9 -f "kit/python.*isaac_ros2_bringup"`. Always close Isaac with the window X / Ctrl+C so it frees VRAM. |
| Window "not responding" for a minute on first launch | Normal: shader compile + first-time URDF→USD conversion. Wait. |
| URDF import errors on a mesh | Run `./scripts/download_meshes.sh` (lidar STL is gitignored). |
| Lidar `/scan` has no data in `--headless` | RTX lidar only streams with the GUI viewport rendering. |
| `no track 'complex_a'` | Track files not in this clone — `git pull` the latest, or copy `experiments/sim/tracks/`. |

Clean-slate one-liner if something is stuck:
```bash
pkill -9 -f "kit/python.*isaac_ros2_bringup|robot_state_publisher|gz sim" ; ros2 daemon stop
```
