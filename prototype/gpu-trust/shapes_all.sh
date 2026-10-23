#!/usr/bin/env bash
# PROTOTYPE (#50): the odd-shape probe over every #42 model family, three configurations.
#   ./shapes_all.sh   (results/shapes_<model>_<cfg>.jsonl, exit codes in logs/shapes_all.log)
cd "$(dirname "$0")"
MODELS="A_100_scratch_s0 B_100_scratch_s0 S_500_scratch_s0 A_500_scratch_s0 A_500_ecgfounder_s1"
for model in $MODELS; do
  for cfg in "nix 0" "nix 1" "wheel 0"; do
    set -- $cfg
    tag=${model}_$1_exp$2
    : > "results/shapes_$tag.jsonl"
    STACK=$1 EXPANDABLE=$2 ./run.sh probe_shapes.py "$model" "results/shapes_$tag.jsonl" 2 > "logs/shapes_$tag.log" 2>&1
    echo "$(date +%T) $tag exit $?" >> logs/shapes_all.log
  done
done
