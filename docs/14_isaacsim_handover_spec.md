# 14 — Isaac Sim Environment: RL Training Requirements

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
