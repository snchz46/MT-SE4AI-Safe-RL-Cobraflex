#!/bin/bash
# Sim-to-real v2 training launch (D-72). Detached so no terminal or agent
# session can take it down; shutdown_on_train_exit reaps Gazebo on completion,
# which is what leaves orphaned `gz sim` processes behind when it is omitted.
# NOTE: no `set -u` — /opt/ros/jazzy/setup.bash dereferences unbound
# variables (AMENT_TRACE_SETUP_FILES) and dies instantly under it.
REPO=/home/admit/Samuel/thesis_repo
RUN=ppo_gz2d_sim2real_v2_2024
LOGS=$REPO/experiments/sim/training/$RUN/raw_logs
source /opt/ros/jazzy/setup.bash
source $REPO/install/setup.bash
CFG=$(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config
export GZ_PARTITION=sim2real_v2_$$
echo "GZ_PARTITION=$GZ_PARTITION" > $LOGS/partition.txt
exec ros2 launch cobraflex_rl train_lane.launch.py \
  train_config:=$CFG/train_ppo_camera_2d_sim2real_v2.yaml \
  run_id:=$RUN \
  shutdown_on_train_exit:=true
