#!/bin/bash
# Samples host + process health every 60 s for the duration of the v2 run.
# Exists because the 19.08 fine-tune took the machine down after ~8 h and the
# cause was never established: no root for dmesg/journal, no OOM trace, and by
# the time anyone looked the evidence was gone. 2.5M steps is ~10x that
# exposure, so the data is collected up front rather than reconstructed after.
OUT=/home/admit/Samuel/thesis_repo/experiments/sim/training/ppo_gz2d_sim2real_v2_2024/raw_logs/health.csv
if [ ! -f "$OUT" ]; then
  echo "iso,uptime_s,load1,mem_used_mb,mem_avail_mb,swap_used_mb,train_rss_mb,gz_rss_mb,n_gz,gpu_mem_mb,gpu_util,gpu_temp,disk_avail_gb,timestep" > "$OUT"
fi
while true; do
  TPID=$(pgrep -f "lib/cobraflex_rl/train_ppo" | head -1)
  [ -z "$TPID" ] && break                      # trainer gone: stop sampling
  GPIDS=$(pgrep -x "gz" ; pgrep -f "^gz sim")
  TRSS=$(awk '/VmRSS/{print int($2/1024)}' /proc/$TPID/status 2>/dev/null)
  GRSS=0; NGZ=0
  for p in $GPIDS; do
    R=$(awk '/VmRSS/{print int($2/1024)}' /proc/$p/status 2>/dev/null)
    [ -n "$R" ] && GRSS=$((GRSS+R)) && NGZ=$((NGZ+1))
  done
  read -r MU MA <<< "$(free -m | awk '/^Mem:/{print $3, $7}')"
  SW=$(free -m | awk '/^Swap:/{print $3}')
  read -r GM GU GT <<< "$(nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ',')"
  TS=$(tail -1 /home/admit/Samuel/thesis_repo/experiments/sim/training/ppo_gz2d_sim2real_v2_2024/learning_curve.csv 2>/dev/null | cut -d, -f1)
  echo "$(date -Is),$(cut -d. -f1 /proc/uptime),$(cut -d' ' -f1 /proc/loadavg),$MU,$MA,$SW,${TRSS:-0},$GRSS,$NGZ,${GM:-0},${GU:-0},${GT:-0},$(df -BG --output=avail /home/admit | tail -1 | tr -dc '0-9'),${TS:-}" >> "$OUT"
  sleep 60
done
echo "$(date -Is),SAMPLER_STOPPED_trainer_absent" >> "$OUT"
