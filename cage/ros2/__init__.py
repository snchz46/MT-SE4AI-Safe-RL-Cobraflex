"""
cage.ros2 — ROS2 runtime helpers for the safety cage.

This subpackage contains nodes that run alongside the simulator or the
physical platform. It depends on `rclpy` and is **not** imported by the
top-level `cage` package: importing `cage` does not bring `rclpy` into
the dependency surface of unit tests (`pytest cage/tests/`).

Available nodes:

- `m1_lidar_noise_logger` — logs `lateral_offset_m` from `/state_obs`
  while the vehicle is stationary. Produces a CSV consumed by
  `tools/calibration_helpers/m1_from_csv.py`.

- `m2_latency_logger` — logs the per-cycle latency between `/state_obs`
  arrival and `/safe_action` publication. Produces a CSV consumed by
  `tools/calibration_helpers/m2_from_csv.py`.

See `cage/ros2/README.md` for the workflow and message-type adaptation
notes.
"""
