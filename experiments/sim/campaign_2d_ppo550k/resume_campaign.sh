#!/usr/bin/env bash
# Single serial driver for the campaign_2d_ppo550k resume.
#   Phase A: execute the 9 remaining PERT scenarios (settle 3 s).
#   Phase B: re-run the FULL 27-scenario matrix with --resume so
#            aggregate_campaign() sees all 1890 outcomes and writes the report.
# Both phases run sequentially in THIS shell: no exec, no background waiter,
# so two campaign processes can never touch the same run dir (29.07 incident).
set +u
cd /media/samuel/Fast_SSD/SE4AI/thesis_repo
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# Guard: a kernel lock on the campaign dir. Immune to the cmdline self-match
# that defeated the ps/pgrep-based checks on 29.07 (the matching process was the
# checker itself, because its own cmdline carried the search pattern).
exec 9>/media/samuel/Fast_SSD/SE4AI/thesis_repo/experiments/sim/campaign_2d_ppo550k/.campaign.lock
if ! flock -n 9; then
  echo "ABORT: another process holds the campaign_2d_ppo550k lock"; exit 3
fi

ALL="SC-EDGE-01,SC-EDGE-02,SC-EDGE-03,SC-EDGE-04,SC-EDGE-05,SC-FRONT-01,SC-FRONT-02,SC-FRONT-03,SC-FRONT-04,SC-FRONT-05,SC-FRONT-06,SC-FRONT-07,SC-NOM-01,SC-NOM-02,SC-NOM-03,SC-PERT-01,SC-PERT-02,SC-PERT-04,SC-PERT-05,SC-PERT-06,SC-PERT-07,SC-PERT-08,SC-PERT-09,SC-PERT-10,SC-PERT-11,SC-PERT-12,SC-PERT-13"
REMAIN="SC-PERT-05,SC-PERT-06,SC-PERT-07,SC-PERT-08,SC-PERT-09,SC-PERT-10,SC-PERT-11,SC-PERT-12,SC-PERT-13"

COMMON=(--scenario-dir scenarios_complex_b
        --model-path policy/checkpoints/ppo_gz2d_cap022_1M_2024_550000_steps.zip
        --train-config src/cobraflex_rl/config/train_ppo_camera_2d_cap022_1M.yaml
        --seeds 2024 --modes enforcement,monitoring
        --out experiments/sim/campaign_2d_ppo550k --resume)

echo "[A] execution pass start $(date -Is)"
python3 -u tools/run_campaign.py "${COMMON[@]}" --scenarios "$REMAIN" --settle 3
echo "[A] execution pass done $(date -Is) rc=$?"

MISSING=$(python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'tools')
import run_campaign as rc
sc = rc.load_scenarios(Path('scenarios_complex_b'))
m = [r for r in rc.build_matrix(sc,['rl'],[2024],['enforcement','monitoring'])
     if r.scenario_id != 'SC-PERT-03']
root = Path('experiments/sim/campaign_2d_ppo550k/runs')
print(sum(1 for r in m if not (root/rc.run_id_for(r)/'summary.json').is_file()))
PY
)
echo "[B] missing cells before aggregation: $MISSING"
SETTLE=3; [ "$MISSING" = "0" ] && SETTLE=0

echo "[B] aggregation pass start $(date -Is)"
python3 -u tools/run_campaign.py "${COMMON[@]}" --scenarios "$ALL" --settle "$SETTLE"
echo "[B] aggregation pass done $(date -Is) rc=$?"
