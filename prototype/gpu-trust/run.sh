#!/usr/bin/env bash
# PROTOTYPE (#50): run a python script under one of the two stacks.
#   STACK=nix|wheel SERIAL=0|1 ./run.sh probe_shapes.py ...
#   nix:   the #19 stack, nixpkgs torchWithRocm (torch 2.13, HIP 7.2) in this dir's devenv shell,
#          per-node override only (the host's global HSA_OVERRIDE_GFX_VERSION is dropped).
#   wheel: #42's .venv-rocm, PyTorch's torch 2.14.1+rocm7.2 wheel with the global override.
cd "$(dirname "$0")"
WHEEL=${WHEEL:-$HOME/workspaces/delmir/.claude/worktrees/epic-neumann-0e9eaf/prototype/ptbxl-3x4/.venv-rocm/bin/python}
export MALLOC_ARENA_MAX=2
# #42 ran with expandable_segments:True; EXPANDABLE=0 drops it.
[ "${EXPANDABLE:-1}" = 1 ] && export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
[ "${SERIAL:-0}" = 1 ] && export AMD_SERIALIZE_KERNEL=3
case "${STACK:-nix}" in
  nix) exec env -u HSA_OVERRIDE_GFX_VERSION devenv shell -q -- python "$@" ;;
  wheel) exec env HSA_OVERRIDE_GFX_VERSION=10.3.0 ROCR_VISIBLE_DEVICES=0 "$WHEEL" "$@" ;;
esac
