#!/usr/bin/env bash
# PROTOTYPE (#50): after queue.sh, redo B's shape probe (its first attempt exited silently, no records).
cd "$(dirname "$0")"
until grep -q "queue done" logs/queue.log; do sleep 30; done
for cfg in "nix 0" "nix 1" "wheel 0"; do
  set -- $cfg
  tag=B_100_scratch_s0_$1_exp$2
  mv "logs/shapes_$tag.log" "logs/shapes_${tag}_attempt1.log" 2>/dev/null
  : > "results/shapes_$tag.jsonl"
  STACK=$1 EXPANDABLE=$2 ./run.sh -X faulthandler probe_shapes.py B_100_scratch_s0 "results/shapes_$tag.jsonl" 2 > "logs/shapes_$tag.log" 2>&1
  echo "$(date +%T) $tag rerun exit $?" >> logs/shapes_all.log
done
echo "$(date +%T) after done" >> logs/queue.log
