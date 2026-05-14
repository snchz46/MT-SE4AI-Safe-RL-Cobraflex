# cage/ros2 — ROS2 helpers for the M-1/M-2 calibration measurements

This subpackage provides two ROS2 logger nodes that run alongside the
simulator stack and produce the CSV input expected by the offline
post-processing helpers under `tools/calibration_helpers/`. The end
result fills `experiments/calibration/M{1,2}_results.json` so that
`tools/apply_calibration.py` can validate the data and propagate
parameter updates to the SRS and `cage/cage.yaml`.

The subpackage requires `rclpy` and is **not** imported by the
top-level `cage` package, so `pytest cage/tests/` continues to run
without a ROS2 installation.

## Pipeline

```text
                ┌──────────────────────────────────────────────────────┐
                │                Simulator (ROS2 + Gazebo)             │
                │   /state_obs  /safe_action  (provided by your repo)  │
                └──────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                                                 ▼
┌──────────────────────────┐                ┌──────────────────────────┐
│ cage/ros2/               │                │ cage/ros2/               │
│   m1_lidar_noise_logger  │                │   m2_latency_logger      │
│  per-position CSV        │                │  per-cycle latency CSV   │
└──────────────────────────┘                └──────────────────────────┘
       │                                                 │
       ▼                                                 ▼
┌──────────────────────────┐                ┌──────────────────────────┐
│ tools/calibration_helpers│                │ tools/calibration_helpers│
│   m1_from_csv.py         │                │   m2_from_csv.py         │
└──────────────────────────┘                └──────────────────────────┘
       │                                                 │
       └────────────────────────┬────────────────────────┘
                                ▼
              experiments/calibration/M{1,2}_results.json
                                │
                                ▼
              tools/apply_calibration.py --measurement M-N
                                │
                                ▼
        SRS edits (manual) + cage.yaml edits (--apply-yaml)
```

## M-1 — Static LiDAR noise on lateral offset

### 1. Run the simulator with the vehicle **stationary**

Launch the perception pipeline at nominal rate. Disable the policy
(throttle = 0 stub or skip the policy node) so the vehicle does not
move. Spawn the vehicle at the first ground-truth position (`y = 0`).

### 2. Launch the logger node, one position at a time

```bash
ros2 run <your_pkg> m1_lidar_noise_logger.py --ros-args \
    -p position_label:=y0 \
    -p output_dir:=/tmp/m1 \
    -p duration_s:=300.0
```

The node writes `/tmp/m1/y0_samples.csv`. After 5 minutes it
self-terminates. Move the vehicle to `y = +0.10 m` and repeat with
`position_label:=y_pos100`; then `y = -0.10 m` with
`position_label:=y_neg100`. You should end up with three CSVs in
`/tmp/m1/`.

### 3. Post-process and fill `M1_results.json`

```bash
python tools/calibration_helpers/m1_from_csv.py \
    --input-dir /tmp/m1 \
    --executed-by "Samuel Sanchez" \
    --perception-version "<git SHA of perception stack>"
```

The helper computes mean, std, p95 absolute deviation and lag-1
autocorrelation per position and writes them into
`experiments/calibration/M1_results.json`.

### 4. Validate and propagate M1

```bash
python tools/apply_calibration.py --measurement M-1
```

Read the decision, apply the SRS edits manually if any, and re-run
with `--apply-yaml` if `cage.yaml` parameters need updating.

## M-2 — End-to-end control latency

### 1. Run the simulator with the full stack

Perception + policy (or PD stub) + cage in enforcement mode, moving
on `odd1_straight_road`. The vehicle should be operating normally so
that `/safe_action` is emitted continuously.

### 2. Launch the logger node

```bash
ros2 run <your_pkg> m2_latency_logger.py --ros-args \
    -p output_csv:=/tmp/m2_latency.csv \
    -p duration_s:=120.0
```

After 2 minutes the node self-terminates with a CSV of per-cycle
latencies in `/tmp/m2_latency.csv`. The protocol asks for >= 2000
cycles; at the nominal 20 Hz this is met by the default 120 s.

### 3. Post-process and fill `M2_results.json`

```bash
python tools/calibration_helpers/m2_from_csv.py \
    --input-csv /tmp/m2_latency.csv \
    --platform sim \
    --executed-by "Samuel Sanchez"
```

The helper computes median, p05, p95, p99, max and writes them into
`experiments/calibration/M2_results.json`. If you also collected a
second leg (`/safe_action → actuator response`) as a separate CSV,
pass it with `--actuator-latency-csv` and the actuator block will be
filled too.

### 4. Validate and propagate M2

```bash
python tools/apply_calibration.py --measurement M-2
```

## Message-type adaptation

The logger nodes try to import `sim_interfaces.msg.{StateObservation,
SafeAction}` first; if those are not available they fall back to
generic ROS2 message types (`Float64MultiArray` for M-1,
`geometry_msgs/PoseStamped` for M-2) so the source compiles without
the simulator workspace on the `PYTHONPATH`. **In the actual
simulator workspace**, you should replace the fallback imports with
the real project-specific message types and verify that the field
access in each `state_cb()` / `safe_action_cb()` matches your
message schema:

| File | Adaptation lines |
| ---- | ---------------- |
| `m1_lidar_noise_logger.py` | the `try / except ImportError` block at the top, and the `state_cb()` field extraction |
| `m2_latency_logger.py` | the `try / except ImportError` block at the top, and the calls to `msg.header.stamp` inside `state_cb()` / `safe_action_cb()` |

If your `/safe_action` message exposes an explicit
`input_state_stamp` field (i.e., the cage attaches the stamp of the
state observation it consumed), switch `safe_action_cb()` in
`m2_latency_logger.py` to use that field instead of the
"most-recently-received" approximation — it gives a more accurate
latency for cages whose callback is decoupled from the subscription
queue.

## QoS

Both loggers subscribe with
`reliability=BEST_EFFORT, durability=VOLATILE` to match a typical
sensor / control stream. If your project uses RELIABLE QoS on these
topics, modify `qos = QoSProfile(...)` accordingly to avoid
publisher–subscriber mismatch warnings.
