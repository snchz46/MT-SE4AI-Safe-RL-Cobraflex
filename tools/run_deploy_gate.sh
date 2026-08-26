#!/usr/bin/env bash
# THE DEPLOYMENT GATE, in one command, for the moment the physical frames exist.
#
#   bash tools/run_deploy_gate.sh <dataset-dir> [checkpoint.zip]
#
# <dataset-dir> must hold frames/*.png plus labels.csv, the layout
# tools/record_lane_dataset.py writes.
#
# The 23.08.2026 note here said the 18.08 circuit frames were lost. They were not:
# they are on the JETSON at experiments/physical/datasets/circuit_export/frames
# (1521 PNG, 439 MB), gitignored by experiments/physical/datasets/*/frames/, which
# is why a search of the compute host found nothing. Run on 26.08.2026 against that
# recording: PASS raw and PASS rectified (docs/17 §8.1).
#
# NOTE the Jetson holds only the deployed checkpoint, so stage 1 below (ranking all
# ~100 candidates) needs the compute host; the Jetson can run stages 2-3, the gate
# proper. To record a fresh dataset instead:
#       python tools/record_lane_dataset.py --out experiments/physical/datasets/<name> \
#         --rate 5 --seconds 120
#     DELIBERATELY WEAVING — the probe refuses a recording spanning under 60 mm
#     of ey, and a centred pass cannot show a lane response.
#
# The frames must be in TEMPORAL ORDER. The gate scores the k=4 history arm,
# which stacks four *consecutive* frames the way rl_policy_node does; an
# unordered pose set stacks four unrelated views and the arm reads as noise.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATASET="${1:?usage: run_deploy_gate.sh <dataset-dir> [checkpoint.zip]}"
CKPT="${2:-$REPO/policy/checkpoints/ppo_gz2d_sim2real_v2_2024_r2_1650000_steps.zip}"
SIM="$REPO/experiments/sim/runs/cv_probe_weak_sections_20260713T084230Z/raw_logs/frames"

echo "== 1/3  rank every checkpoint against the real recording =="
python3 "$REPO/tools/select_sim2real_checkpoint.py" \
  --prefix ppo_gz2d_sim2real_v2_2024 --sim-frames "$SIM" --real "$DATASET" \
  --learning-curve "$REPO/experiments/sim/training/ppo_gz2d_sim2real_v2_2024/learning_curve.csv" \
  --learning-curve "$REPO/experiments/sim/training/ppo_gz2d_sim2real_v2_2024_r2/learning_curve.csv" \
  --top 8 --output "$REPO/experiments/sim/eval_gz2d/select_v2_gated.json"

echo; echo "== 2/3  the gate on the chosen checkpoint, raw optics =="
python3 "$REPO/tools/sim2real_probe.py" --checkpoint "$CKPT" --real "$DATASET" --sim "$SIM" \
  --output "$REPO/experiments/sim/eval_gz2d/sim2real_probe_v2.json" || true

echo; echo "== 3/3  the same, rectified — the deployment is meant to run this way =="
python3 "$REPO/tools/sim2real_probe.py" --checkpoint "$CKPT" --real "$DATASET" --sim "$SIM" --rectify \
  --output "$REPO/experiments/sim/eval_gz2d/sim2real_probe_v2_rectified.json" || true

cat <<'EOF'

A PASS is necessary, not sufficient: the probe is open-loop on recorded frames,
so it can falsify transfer but never establish it. Before driving, still do
docs/17 §7.4 — SC-NOM-01 in Gazebo, then preflight_deploy.py stage0/1/2 and
lanecheck ON THE TRACK with rectification on.
EOF
