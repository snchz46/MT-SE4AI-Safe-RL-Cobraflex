#!/bin/bash
# Health sampler for the resumed v2 run. Every 60 s.
#
# The trainer check is by `comm`, NOT `pgrep -f`. The parent run's sampler used
# `pgrep -f "lib/cobraflex_rl/train_ppo"`, which matched its OWN bash wrapper, so
# it never noticed the trainer die and logged the wrapper's 1 MB RSS as the
# trainer's for four minutes (INCIDENTS.md I-6).
R=/home/admit/Samuel/thesis_repo/experiments/sim/training/ppo_gz2d_sim2real_v2_2024_r2
OUT=$R/raw_logs/health.csv
trainer_pid() { ps -eo pid=,comm= | awk '$2=="train_ppo"{print $1; exit}'; }
# The gz server's comm is `ruby` (it is launched through the gz_tools ruby
# wrapper), never `gz`. Match on the argv, but verify comm so a shell whose
# command line merely mentions "gz sim" cannot be counted — the cmdline-matching
# trap of I-6.
gz_pids()     { ps -eo pid=,comm=,args= | awk '$2=="ruby" && /gz sim/{print $1}'; }
[ -f "$OUT" ] || echo "iso,uptime_s,load1,mem_used_mb,mem_avail_mb,swap_used_mb,train_rss_mb,gz_rss_mb,n_gz,gpu_mem_mb,gpu_util,gpu_temp,disk_avail_gb,timestep" > "$OUT"
while true; do
  TPID=$(trainer_pid)
  [ -z "$TPID" ] && { echo "$(date -Is),TRAINER_ABSENT_sampler_stopped" >> "$OUT"; break; }
  TRSS=$(awk '/VmRSS/{print int($2/1024)}' /proc/$TPID/status 2>/dev/null)
  GRSS=0; NGZ=0
  for p in $(gz_pids); do
    Rm=$(awk '/VmRSS/{print int($2/1024)}' /proc/$p/status 2>/dev/null)
    [ -n "$Rm" ] && GRSS=$((GRSS+Rm)) && NGZ=$((NGZ+1))
  done
  read -r MU MA <<< "$(free -m | awk '/^Mem:/{print $3, $7}')"
  SW=$(free -m | awk '/^Swap:/{print $3}')
  read -r GM GU GT <<< "$(nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ',')"
  TS=$(tail -1 $R/learning_curve.csv 2>/dev/null | cut -d, -f1)
  echo "$(date -Is),$(cut -d. -f1 /proc/uptime),$(cut -d' ' -f1 /proc/loadavg),$MU,$MA,$SW,${TRSS:-0},$GRSS,$NGZ,${GM:-0},${GU:-0},${GT:-0},$(df -BG --output=avail /home/admit | tail -1 | tr -dc '0-9'),${TS:-}" >> "$OUT"
  sleep 60
done
