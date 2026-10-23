#!/usr/bin/env bash
# PROTOTYPE (#50): everything after the shape matrix, one GPU job at a time, on the nix (#19) stack.
#   1. throughput of serialized vs unserialized launches (and the 500 Hz MIOpen BatchNorm JIT);
#   2. 30-epoch xresnet1d101 runs (design A, seed 0) at 100 and 500 Hz: no padding, no serialization,
#      no expandable segments; CPU parity on validation every epoch and on the whole test fold at the end;
#   3. the same 100 Hz run with expandable segments on, to see what they do to a real training run.
cd "$(dirname "$0")"
while pgrep -f shapes_all.sh > /dev/null; do sleep 30; done
log() { echo "$(date +%T) $*" >> logs/queue.log; }
for fs in 100 500; do
  for s in 0 1; do
    STACK=nix EXPANDABLE=0 SERIAL=$s ./run.sh bench.py $fs results/bench.jsonl > logs/bench_${fs}_serial$s.log 2>&1
    log "bench fs=$fs serial=$s exit $?"
  done
done
COMMON="--design A --seed 0 --threads 16 --runs runs"
STACK=nix EXPANDABLE=0 ./run.sh train.py $COMMON --fs 100 > logs/train_A100.log 2>&1
log "train A100 exit $?"
STACK=nix EXPANDABLE=0 ./run.sh train.py $COMMON --fs 500 --parity 300 > logs/train_A500.log 2>&1
log "train A500 exit $?"
STACK=nix EXPANDABLE=1 ./run.sh train.py $COMMON --fs 100 --tag -exp1 > logs/train_A100_exp1.log 2>&1
log "train A100 exp1 exit $?"
log "queue done"
