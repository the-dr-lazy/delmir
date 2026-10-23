#!/usr/bin/env bash
# PROTOTYPE (#50): one model's shape probe under both stacks, unserialized and serialized, with
# expandable segments on (run.sh's default; how #42 ran). Produced results/triage_*.
#   ./triage.sh A_100_scratch_s0 [reps]
cd "$(dirname "$0")"
MODEL=$1 REPS=${2:-2}
for cfg in "nix 0" "nix 1" "wheel 0" "wheel 1"; do
  set -- $cfg
  f=results/triage_${MODEL}_$1_exp1_serial$2.jsonl
  : > "$f"
  STACK=$1 SERIAL=$2 ./run.sh probe_shapes.py "$MODEL" "$f" "$REPS" > "logs/shapes_${MODEL}_$1_$2.log" 2>&1
  echo "=== $MODEL $1 serial=$2 exit $?"
  python3 summarize.py "$f"
done
