#!/usr/bin/env bash
# Launch the oval world headless, teleport the robot to the four canonical
# evidence poses (spawn / curve entry / mid curve / back straight) and save one
# camera frame per pose under experiments/sim/e_cam_visibility/<prefix>_<pose>/.
# Usage: tools/cam_evidence_session.sh <prefix> [world_file] [world_name]
set -e
PREFIX="${1:?usage: cam_evidence_session.sh <prefix> [world_file] [world_name]}"
WORLD_FILE="${2:-}"
WORLD_NAME="${3:-lane_following_oval}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

source /opt/ros/jazzy/setup.bash
source "$REPO/install/setup.bash"
export GZ_PARTITION="evid_$$"

LAUNCH_ARGS=(gui:=false rviz:=false)
if [ -n "$WORLD_FILE" ]; then
  LAUNCH_ARGS+=("world:=$WORLD_FILE")
fi
ros2 launch cobraflex gazebo_mesh.launch.py "${LAUNCH_ARGS[@]}" \
  > "$REPO/evidence_launch.log" 2>&1 &
LAUNCH_PID=$!
trap '"$REPO/tools/reap_sim.sh" >/dev/null 2>&1 || true' EXIT
sleep 25

while read -r x y yaw name; do
  hy=$(python3 -c "import math;print(math.sin($yaw/2))")
  hw=$(python3 -c "import math;print(math.cos($yaw/2))")
  gz service -s "/world/$WORLD_NAME/set_pose" --reqtype gz.msgs.Pose \
    --reptype gz.msgs.Boolean --timeout 2000 \
    --req "name: \"cobraflex_robot\" position { x: $x y: $y z: 0.05 } orientation { z: $hy w: $hw }" > /dev/null
  sleep 1.5
  python3 "$REPO/tools/capture_camera_frames.py" \
    --out "$REPO/experiments/sim/e_cam_visibility/${PREFIX}_${name}" \
    --frames 1 --interval 0.2 | tail -1
done <<'POSES'
0.0 -0.1225 0.0 spawn
1.504 -0.122 0.064 curve_entry
2.335 0.407 1.195 mid_curve
1.504 1.722 3.141 back_straight
POSES

kill "$LAUNCH_PID" 2>/dev/null || true
wait "$LAUNCH_PID" 2>/dev/null || true
echo "evidence session '$PREFIX' done"
