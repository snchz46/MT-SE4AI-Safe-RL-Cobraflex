#!/usr/bin/env bash
# Full 27-scenario campaign on the sim-to-real v2 policy, checkpoint 1,650,000.
#
# CHECKPOINT CHOICE. Not the reward peak. 1.65M has the best transfer statistics
# of the run on the deployment arm (r^2 0.440, bias/swing 0.10, right-turn share
# 62.1 %) and intervenes on only 3.0 % of nominal steps against the reward peak's
# 35.0 % — and D-69 named that C-06 coupling to `delta_max_steering_per_cycle` a
# physical-transfer risk (T2). Authorised by a D-43 preflight PASS on its clean
# nominal trace (experiments/sim/eval_gz2d/d43_preflight_v2_1650000.json), max
# centred ey error 20.9 mm against a 50 mm threshold.
#
# The flock is not decoration: on 29.07 two campaign processes touched one run
# directory and 222 runs had to be quarantined.
set +u
REPO=/home/admit/Samuel/thesis_repo
source /opt/ros/jazzy/setup.bash
source $REPO/install/setup.bash
cd $REPO
ps -eo comm= | grep -qx train_ppo && { echo "ABORT: a trainer is alive"; exit 3; }
exec 9>$REPO/experiments/sim/campaign_v2/.campaign.lock
flock -n 9 || { echo "ABORT: another process holds the campaign_v2 lock"; exit 3; }
echo "campaign_v2 start $(date -Is)"
# SC-PERT-03 is excluded, exactly as in campaign_2d_ppo550k: it needs a two-arm
# manifest from sc_pert_03_protocol.py, and D-64 closed it. This is the same
# 27-scenario matrix the verdict of record was scored on.
ALL="SC-EDGE-01,SC-EDGE-02,SC-EDGE-03,SC-EDGE-04,SC-EDGE-05,SC-FRONT-01,SC-FRONT-02,SC-FRONT-03,SC-FRONT-04,SC-FRONT-05,SC-FRONT-06,SC-FRONT-07,SC-NOM-01,SC-NOM-02,SC-NOM-03,SC-PERT-01,SC-PERT-02,SC-PERT-04,SC-PERT-05,SC-PERT-06,SC-PERT-07,SC-PERT-08,SC-PERT-09,SC-PERT-10,SC-PERT-11,SC-PERT-12,SC-PERT-13"

python3 tools/run_campaign.py \
  --scenario-dir scenarios_complex_b \
  --scenarios "$ALL" \
  --model-path policy/checkpoints/ppo_gz2d_sim2real_v2_2024_r2_1650000_steps.zip \
  --train-config src/cobraflex_rl/config/train_ppo_camera_2d_sim2real_v2.yaml \
  --seeds 2024 --modes enforcement,monitoring \
  --out experiments/sim/campaign_v2 --resume
echo "campaign_v2 end $(date -Is)"
