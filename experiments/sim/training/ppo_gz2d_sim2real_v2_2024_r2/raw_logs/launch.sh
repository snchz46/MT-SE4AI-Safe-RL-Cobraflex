#!/bin/bash
# Resume of the sim-to-real v2 run from its 600k checkpoint (INCIDENTS.md I-6).
# NOTE: no `set -u` — /opt/ros/jazzy/setup.bash dereferences unbound variables.
REPO=/home/admit/Samuel/thesis_repo
RUN=ppo_gz2d_sim2real_v2_2024_r2
LOGS=$REPO/experiments/sim/training/$RUN/raw_logs
source /opt/ros/jazzy/setup.bash
source $REPO/install/setup.bash
CFG=$(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config
export GZ_PARTITION=sim2real_v2r2_$$
echo "GZ_PARTITION=$GZ_PARTITION" > $LOGS/partition.txt
exec ros2 launch cobraflex_rl train_lane.launch.py \
  train_config:=$CFG/train_ppo_camera_2d_sim2real_v2_resume.yaml \
  resume_from:=$REPO/policy/checkpoints/ppo_gz2d_sim2real_v2_2024_600000_steps.zip \
  resume_vecnormalize:=$REPO/policy/checkpoints/ppo_gz2d_sim2real_v2_2024_vecnormalize_600000_steps.pkl \
  run_id:=$RUN \
  shutdown_on_train_exit:=true
