#!/usr/bin/env bash
# run_physical_lap.sh — start ONE physical run: the evidence recorder and the
# Layer-3 RL chain, bound to a single run id, stopped together.
#
# WHY THIS EXISTS. The 26.08.2026 session was recorded by hand, and it shows.
# The `track_v2_cpufix` rosbag spans 598 s while its cage CSV spans 57.8 s, so
# every cross-topic statement about that run needs a caveat about which window
# it was measured in. The lane image topic was left out of the recording twice,
# although `docs/17` §8.9 asked for it after the first time. And the Layer-2
# settings that actually decided the session — the camera capture rate and the
# ZED loop-closure overrides — are recoverable only from the run's NAME.
#
# So: one run id for the CSV, the bag, the captured frames and the reset log;
# the Layer-2 configuration read off the RUNNING nodes rather than assumed; and
# a topic list that is a file, not a memory.
#
# The image topic is deliberately NOT in the bag. Raw 640x360 bgr8 at 20 Hz is
# 13.8 MB/s to eMMC and doing that alongside the deploy chain crashed the Jetson
# on 18.08.2026 (see experiments/physical/runs/circuit_survey/REPAIR_NOTE.md).
# `frame_capture_node`, started by the launch, keeps the frames around each
# perception event from a RAM ring buffer instead.
#
#   Layer 1 and Layer 2 must already be up (docs/17 §3), with rviz OFF.
#
# Usage:
#   tools/run_physical_lap.sh --label lap01 --checkpoint /path/to/ckpt.zip [...]
#   tools/run_physical_lap.sh --label lap01 --checkpoint ... --reset-proxy auto
#
# Everything after `--` is passed through to `ros2 launch` verbatim.
set -euo pipefail

LABEL="lap"
CHECKPOINT=""
MODE="monitoring"
RESET_PROXY="observe"
RECTIFY="${RECTIFY:-}"
HEADING_FIT_MODE="near_secant"
HEADING_GAIN="1.0"
EXTRA=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --label)          LABEL="$2"; shift 2 ;;
        --checkpoint)     CHECKPOINT="$2"; shift 2 ;;
        --mode)           MODE="$2"; shift 2 ;;
        --reset-proxy)    RESET_PROXY="$2"; shift 2 ;;
        --rectify)        RECTIFY="$2"; shift 2 ;;
        --heading-fit-mode) HEADING_FIT_MODE="$2"; shift 2 ;;
        --heading-gain)   HEADING_GAIN="$2"; shift 2 ;;
        --)               shift; EXTRA=("$@"); break ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$CHECKPOINT" ]]; then
    echo "--checkpoint is required" >&2
    exit 2
fi
if [[ ! -f "$CHECKPOINT" ]]; then
    echo "checkpoint not found: $CHECKPOINT" >&2
    exit 2
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Rectification defaults ON here, unlike the launch. §8.3 settled it on hardware
# by a controlled A/B with the car untouched: unrectified, the estimator reads a
# centred car as ~100 mm off and fires C-01 102 times while STATIONARY; rectified
# it fires 0, and perception-invalid cycles go 45 % -> 5.5 %.
if [[ -z "${RECTIFY}" && -f "${REPO}/experiments/calibration/M6_results.json" ]]; then
    RECTIFY="${REPO}/experiments/calibration/M6_results.json"
fi

RUN_ID="${LABEL}_$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${REPO}/experiments/physical/runs/${RUN_ID}"
mkdir -p "${RUN_DIR}"

# ---------------------------------------------------------------------------
# 1 · Layer-2 configuration, MEASURED off the running nodes.
#
# `deploy_cobraflex.launch.py` is a Layer-3 launch: it cannot know what Layer 2
# was started with, and recording a plausible default would put a lie in the
# evidence. These two settings are exactly the ones that separated the 26.08
# runs that drove from the ones that did not, so they are read, not assumed.
# ---------------------------------------------------------------------------
probe() {  # node param  -> value, or "unavailable"
    ros2 param get "$1" "$2" 2>/dev/null | sed 's/^[^:]*: //' || echo "unavailable"
}
echo "Probing Layer 2 ..."
CAPTURE_FPS="$(probe /csi_camera_node capture_fps)"
CAMERA_RATE="$(probe /csi_camera_node rate_hz)"
AREA_MEMORY="$(probe /zed/zed_node pos_tracking.area_memory)"
LOOP_CLOSURE="$(probe /zed/zed_node pos_tracking.reset_odom_with_loop_closure)"
ZED_PUB_RATE="$(probe /zed/zed_node general.pub_frame_rate)"
ZED_DEPTH_MODE="$(probe /zed/zed_node depth.depth_mode)"
# Nothing in the RL chain reads a LaserScan; the lidar is pure load here.
if ros2 node list 2>/dev/null | grep -q sllidar; then LIDAR="running"; else LIDAR="absent"; fi
cat > "${RUN_DIR}/layer2.json" <<JSON
{
  "run_id": "${RUN_ID}",
  "probed_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source": "ros2 param get, against the nodes running at start of run",
  "csi_camera_node.capture_fps": "${CAPTURE_FPS}",
  "csi_camera_node.rate_hz": "${CAMERA_RATE}",
  "zed_node.pos_tracking.area_memory": "${AREA_MEMORY}",
  "zed_node.pos_tracking.reset_odom_with_loop_closure": "${LOOP_CLOSURE}",
  "zed_node.general.pub_frame_rate": "${ZED_PUB_RATE}",
  "zed_node.depth.depth_mode": "${ZED_DEPTH_MODE}",
  "sllidar": "${LIDAR}"
}
JSON
echo "  capture_fps=${CAPTURE_FPS}  rate_hz=${CAMERA_RATE}"
echo "  zed area_memory=${AREA_MEMORY}  reset_odom_with_loop_closure=${LOOP_CLOSURE}"
echo "  zed pub_frame_rate=${ZED_PUB_RATE}  depth_mode=${ZED_DEPTH_MODE}  sllidar=${LIDAR}"

if [[ "${AREA_MEMORY}" != "False" || "${LOOP_CLOSURE}" != "False" ]]; then
    echo
    echo "  !! ZED loop closure appears to be ON."
    echo "     On 26.08 that produced a 3621.8 mm single-frame pose jump, an ekf"
    echo "     vx of -4.03 m/s and a cage speed of 5.479 m/s — 25x the contract —"
    echo "     which fired C-04 -> C-03 -> C-05 and ended the run. Bring Layer 2"
    echo "     up with zed_overrides (docs/17 §8.7) before driving."
    echo
    read -r -p "     Continue anyway? [y/N] " reply
    [[ "${reply}" == "y" || "${reply}" == "Y" ]] || exit 1
fi
if [[ "${LIDAR}" == "running" ]]; then
    echo
    echo "  .. the lidar is running and nothing in this chain reads it."
    echo "     Bring Layer 2 up with use_lidar:=false to drop it. Not a"
    echo "     blocker — the measured bottleneck is rl_policy_node's inference"
    echo "     timer, not Layer 2 (docs/17 §8.10)."
fi
if pgrep -x rviz2 >/dev/null 2>&1; then
    echo
    echo "  !! rviz2 is running. On 26.08 killing it alone took the control loop"
    echo "     from 7.3 Hz to 9.5 Hz (§8.6). Kill it before driving."
    echo
    read -r -p "     Continue anyway? [y/N] " reply
    [[ "${reply}" == "y" || "${reply}" == "Y" ]] || exit 1
fi

# ---------------------------------------------------------------------------
# 2 · Evidence bag. Light topics only — see the header on why the image topic
#     is not here. /cage_reset and /emergency are new to this list: without
#     them the 26.08 analysis could not tell an operator reset from a recovery.
# ---------------------------------------------------------------------------
TOPICS=(
    /cage_status
    /state_obs
    /raw_action
    /safe_action
    /cmd_vel
    /emergency
    /cage_reset
    /external_stop
    /perception_invalid
    /odometry/filtered
    /zed/zed_node/odom
    /cobraflex/wheel_speeds
)

BAG_DIR="${RUN_DIR}_bag"
# `heading_fit_mode` is the one setting here that departs from the launch
# default, and §8.4 is explicit that changing it is an OPEN DECISION rather than
# a bug fix: `joint_pair_quadratic`/1.6 is the D-43 perception contract every
# scored campaign used, and `near_secant`/1.0 is the one that can actually drive
# this car (14.45 m against 1.08 m, in a controlled pair — and parked, both are
# quiet, so no bench test can see the difference). A diagnostic lap needs the
# second; a scored run cannot use it until that decision is taken.
if [[ "${HEADING_FIT_MODE}" != "joint_pair_quadratic" ]]; then
    echo
    echo "  NOTE heading_fit_mode=${HEADING_FIT_MODE} (launch default is"
    echo "       joint_pair_quadratic). This run is therefore NOT on the D-43"
    echo "       contract the simulation campaigns were scored under — docs/17"
    echo "       §8.4. Fine for a diagnostic lap, not for verdict_phys."
fi
if [[ -z "${RECTIFY}" ]]; then
    echo
    echo "  !! No rectification calibration. §8.3: unrectified, C-01 fires 102"
    echo "     times with the car PARKED. Pass --rectify <M6_results.json>."
fi

echo
echo "Run id     : ${RUN_ID}"
echo "Evidence   : ${RUN_DIR}"
echo "Bag        : ${BAG_DIR}"
echo "Mode       : ${MODE}    reset_proxy: ${RESET_PROXY}"
echo "Rectify    : ${RECTIFY:-<none>}"
echo "Heading    : ${HEADING_FIT_MODE} / ${HEADING_GAIN}"
echo

ros2 bag record -o "${BAG_DIR}" "${TOPICS[@]}" &
BAG_PID=$!
cleanup() {
    if kill -0 "${BAG_PID}" 2>/dev/null; then
        echo "Stopping the recorder ..."
        kill -INT "${BAG_PID}" 2>/dev/null || true
        wait "${BAG_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

LAUNCH_ARGS=(
    "checkpoint:=${CHECKPOINT}"
    "mode:=${MODE}"
    "run_id:=${RUN_ID}"
    "reset_proxy:=${RESET_PROXY}"
    "heading_fit_mode:=${HEADING_FIT_MODE}"
    "heading_gain:=${HEADING_GAIN}"
)
[[ -n "${RECTIFY}" ]] && LAUNCH_ARGS+=("rectify_calibration:=${RECTIFY}")

echo "ros2 launch cobraflex_rl deploy_cobraflex.launch.py ${LAUNCH_ARGS[*]} ${EXTRA[*]-}"
echo
ros2 launch cobraflex_rl deploy_cobraflex.launch.py \
    "${LAUNCH_ARGS[@]}" ${EXTRA[@]+"${EXTRA[@]}"}
