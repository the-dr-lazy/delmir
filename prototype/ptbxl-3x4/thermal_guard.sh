#!/usr/bin/env bash
# PROTOTYPE (#42): pause GPU training when the RX 6600 XT junction reaches 105 C, resume below 90 C.
# SIGSTOP/SIGCONT the .venv-rocm train.py processes; every event goes to logs/thermal.log.
#   ./thermal_guard.sh &
cd "$(dirname "$0")"
mkdir -p logs
paused=0 peak=0
while true; do
  t=$(rocm-smi -d 0 --showtemp 2>/dev/null | sed -nE 's/.*junction\) \(C\): ([0-9]+).*/\1/p')
  t=${t:-0}
  [ "$t" -gt "$peak" ] && peak=$t
  pids=$(pgrep -f "^.venv-rocm/bin/python train.py")
  if [ "$paused" = 0 ] && [ "$t" -ge 105 ] && [ -n "$pids" ]; then
    kill -STOP $pids; paused=1; echo "$(date +%T) PAUSE junction=${t}C pids=$(echo $pids)" >> logs/thermal.log
  elif [ "$paused" = 1 ] && [ "$t" -le 90 ]; then
    [ -n "$pids" ] && kill -CONT $pids; paused=0; echo "$(date +%T) RESUME junction=${t}C" >> logs/thermal.log
  fi
  [ $(( $(date +%s) % 600 )) -lt 5 ] && echo "$(date +%T) status junction=${t}C peak=${peak}C paused=$paused" >> logs/thermal.log
  sleep 5
done
