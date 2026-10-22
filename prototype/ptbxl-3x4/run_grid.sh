#!/usr/bin/env bash
# PROTOTYPE (#42): run train.py argument lines from a job file with P workers. Each worker claims a
# job with an atomic mkdir under runs/.claim, so several runners can share one queue (and finished
# or running jobs are never started twice). A killed run is retried and resumes from its checkpoint.
#   ./run_grid.sh jobs_rest.txt 2
set -u
cd "$(dirname "$0")"
P="${2:-2}"
export MALLOC_ARENA_MAX=2
mkdir -p runs/.claim logs
name() {
  local tag; tag="$(echo "$1" | sed -nE 's/.*--tag ([^ ]+).*/\1/p')"
  echo "$1" | sed -E "s/--design ([SABC]) --fs ([0-9]+)( --init ([a-z]+))? --seed ([0-9]+).*/\1_\2_\4${tag}_s\5/; s/_${tag}_s/_scratch${tag}_s/; s/__s/_scratch_s/"
}
worker() {
  grep -v '^#' "$1" | grep . | while read -r line; do
    n="$(name "$line")"
    [ -s "runs/$n.json" ] && continue
    mkdir "runs/.claim/$n" 2>/dev/null || continue
    for try in 1 2 3 4 5 6; do
      .venv/bin/python train.py $line >> "logs/$(echo "$line" | tr -c 'a-zA-Z0-9\n' _).log" 2>&1 && break
      echo "exit $? (try $try)" >> "logs/$(echo "$line" | tr -c 'a-zA-Z0-9\n' _).log"
      sleep 60
    done
  done
}
for i in $(seq "$P"); do worker "$1" & sleep 1; done
wait
