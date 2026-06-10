#!/usr/bin/env bash
# Kill leftover Gazebo/ROS sim processes from manual evidence sessions.
# Lives in a file so the kill patterns never appear in the caller's cmdline
# (a pgrep -f from an inline shell matches its own wrapper and kills it).
set -u
for pat in "gz sim" "ros2 launch" "parameter_bridge" "ekf_node" \
           "robot_state_publisher" "ruby /usr/bin/gz"; do
  for p in $(pgrep -f "$pat" 2>/dev/null); do
    [ "$p" = "$$" ] && continue
    kill "$p" 2>/dev/null
  done
done
sleep 2
for pat in "gz sim" "ruby /usr/bin/gz"; do
  for p in $(pgrep -f "$pat" 2>/dev/null); do
    [ "$p" = "$$" ] && continue
    kill -9 "$p" 2>/dev/null
  done
done
exit 0
