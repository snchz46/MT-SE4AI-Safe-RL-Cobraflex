"""
tools.calibration_helpers — offline post-processing for the M-1..M-5 campaign.

Pure-Python helpers (no `rclpy` dependency) that take the CSV log files
produced by the ROS2 logger nodes under `cage/ros2/` and write the
corresponding `experiments/calibration/MN_results.json` files.

Modules:
    m1_from_csv — read the three position-labelled CSVs from M-1
                  and fill `positions[]` in M1_results.json.
    m2_from_csv — read the per-cycle latency CSV from M-2 and fill
                  `latency_obs_to_safe_action_ms.{...}` in M2_results.json.
"""
