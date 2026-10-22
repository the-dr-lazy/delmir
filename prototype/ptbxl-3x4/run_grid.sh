#!/usr/bin/env bash
# PROTOTYPE (#42): run train.py argument lines from a job file with P workers. Each worker claims a
# job with an atomic mkdir under runs/.claim, so several runners can share one queue (and finished
# or running jobs are never started twice). A killed run is retried and resumes from its checkpoint.
# MAXJOBS caps how many train.py run at once across all runners (8 GB GPU: 2).
#   PY=.venv-rocm/bin/python MAXJOBS=2 ./run_grid.sh jobs_gpu.txt 2
set -u
cd "$(dirname "$0")"
P="${2:-2}"
PY="${PY:-.venv/bin/python}"
MAXJOBS="${MAXJOBS:-99}"
export MALLOC_ARENA_MAX=2 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p runs/.claim logs
name() {
  local tag; tag="$(echo "$1" | sed -nE 's/.*--tag ([^ ]+).*/\1/p')"
  echo "$1" | sed -E "s/--design ([SABC]) --fs ([0-9]+)( --init ([a-z]+))? --seed ([0-9]+).*/\1_\2_\4${tag}_s\5/; s/_${tag}_s/_scratch${tag}_s/; s/__s/_scratch_s/"
}
running() { pgrep -fc "^${PY} train.py" || true; }
worker() {
  grep -v '^#' "$1" | grep . | while read -r line; do
    n="$(name "$line")"
    [ -s "runs/$n.json" ] && continue
    mkdir "runs/.claim/$n" 2>/dev/null || continue
    log="logs/$(echo "$line" | tr -c 'a-zA-Z0-9\n' _).log"
    for try in 1 2 3 4 5 6; do
      exec 9>runs/.slot.lock
      flock 9
      while [ "$(running)" -ge "$MAXJOBS" ]; do sleep 20; done
      $PY train.py $line >> "$log" 2>&1 &
      child=$!
      sleep 15
      flock -u 9
      wait $child && break
      echo "exit $? (try $try)" >> "$log"
      sleep 60
    done
  done
}
for i in $(seq "$P"); do worker "$1" & sleep 1; done
wait
