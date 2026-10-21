#!/usr/bin/env bash
# PROTOTYPE (#42): run a list of train.py argument lines, P jobs at a time, skipping finished runs.
#   ./run_grid.sh jobs_100.txt 2
set -u
cd "$(dirname "$0")"
P="${2:-2}"
mkdir -p runs logs
grep -v '^#' "$1" | grep . | while read -r line; do
  set -- $line
  name="$(echo "$line" | sed -E 's/--design ([SABC]) --fs ([0-9]+)( --init ([a-z]+))? --seed ([0-9]+).*/\1_\2_\4_s\5/; s/__s/_scratch_s/')"
  [ -s "runs/$name.json" ] || echo "$line"
done | xargs -P "$P" -I{} sh -c '.venv/bin/python train.py {} > "logs/$(echo "{}" | tr -c "a-zA-Z0-9\n" _).log" 2>&1'
