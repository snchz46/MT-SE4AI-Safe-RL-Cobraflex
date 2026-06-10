#!/usr/bin/env bash
# Kill leftover Gazebo/ROS sim processes from manual evidence sessions.
# pgrep -f also matches shells whose *command-line text* contains the pattern
# (e.g. the invoking wrapper), so every candidate pid is verified by its
# actual executable name (comm) before being signalled.
set -u
ALLOWED_COMM="ruby|gz|python3|parameter_bridge|ekf_node|robot_state_publisher|rviz2"
reap() {
  local sig="$1"
  for pat in "gz sim" "ros2 launch" "parameter_bridge" "ekf_node" \
             "robot_state_publisher" "ruby /usr/bin/gz"; do
    for p in $(pgrep -f "$pat" 2>/dev/null); do
      [ "$p" = "$$" ] && continue
      comm=$(ps -o comm= -p "$p" 2>/dev/null)
      case "$comm" in
        ruby|gz|python3|parameter_bridge|ekf_node|robot_state_publisher|rviz2)
          kill "$sig" "$p" 2>/dev/null ;;
      esac
    done
  done
}
reap -TERM
sleep 2
reap -KILL
exit 0
