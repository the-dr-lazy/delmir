# PROTOTYPE, throwaway: torchWithRocm on the RX 6600 XT inside devenv (#41)

Answers [#41](https://github.com/the-dr-lazy/delmir/issues/41) for [#19](https://github.com/the-dr-lazy/delmir/issues/19). Run on the owner's host on 2026-10-22 (Ryzen 9 7950X3D with its Raphael iGPU, RX 6600 XT 8 GB, NixOS, nix 2.34.8, devenv 2.4.0).

**Verdict: go.** nixpkgs' `python313Packages.torchWithRocm` (torch 2.13.0, HIP 7.2.53211), at the same nixpkgs pin as #8, trains on the RX 6600 XT inside a plain devenv shell. It sees only the dGPU, and the 5-minute run finished clean. It runs at about 2.6× the CPU's throughput in fp32 and about 3.7× with fp16 autocast. Everything comes from cache.nixos.org and nothing compiles. Two settings are required, and #19 should keep both:

- `ROCR_VISIBLE_DEVICES = "0"`. This one is **required**: if the iGPU is visible, the process crashes or runs on the wrong device.
- `HSA_OVERRIDE_GFX_VERSION_1 = "10.3.0"` (KFD node 1 is the dGPU). This one is also **required**. Without any override, the training steps themselves run, but the batch-1024 eval forward pass failed both times it was tried: once with an HSA hardware exception, and once, at the validated undervolt, with a bogus 7.94 GiB allocation.

## Run it

```bash
cd prototype/rocm-torch
devenv shell -- python probe.py            # devices, matmul, MIOpen conv1d
devenv shell -- python train.py cuda 120   # short training loop (also: cpu, --amp)
```

The host's `/etc/set-environment` exports a global `HSA_OVERRIDE_GFX_VERSION=10.3.0`, and it leaks into the shell. The runs below unset it (`env -u HSA_OVERRIDE_GFX_VERSION`) so that only the shell's per-node setting applies. The raw logs are `probe-*.txt` and `train*.txt`.

## Devices (`probe.py`, `probe-variants.txt`)

KFD topology on this host: node 0 is the CPU, node 1 the RX 6600 XT (`gfx_target_version 100302`, i.e. gfx1032), node 2 the iGPU (100306, gfx1036).

| Variant | Devices torch sees | Result |
|---|---|---|
| **A. per-node override + `ROCR_VISIBLE_DEVICES=0`** (the shell) | 1: RX 6600 XT as `gfx1030` | fp32 matmul 7.2–8.7 TFLOP/s, fp16 16.6; MIOpen Conv1d OK, max error vs CPU 1.4e-6 |
| B. per-node override, `ROCR_VISIBLE_DEVICES` unset | (crash) | `LLVM ERROR: CachedFileStream was not committed`, core dump at startup: the iGPU stays gfx1036 and breaks the process |
| C. global override, `ROCR_VISIBLE_DEVICES` unset | 2: the dGPU **and the iGPU, both as `gfx1030`** | the iGPU becomes `cuda:1` and runs gfx1030 code; its Conv1d differs from the CPU by 5e-5 (30× the dGPU's). Wrong-device risk |
| D. no override, `ROCR_VISIBLE_DEVICES=0` | 1: RX 6600 XT as `gfx1032` | probe works (fp16 matmul 13.5, Conv1d 3.1 ms vs 1.4 ms), **but the eval forward fails** (below) |
| host global override + `ROCR_VISIBLE_DEVICES=0` | same as A | same as A |

**Why D runs at all.** nixpkgs' `clr` carries the patch "rocclr: Extend HIP ISA compatibility checks" ([clr/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/rocm-modules/clr/default.nix)). With it, torch's gfx1030 kernels load on gfx1032: `AMD_LOG_LEVEL=4` logs `Using native code object for device: …gfx1032`, even though `PYTORCH_ROCM_ARCH` has no gfx1032 (checked by decompressing libtorch_hip's offload bundles). rocBLAS and MIOpen still choose kernels by the reported name, though. That explains the slower numbers and the hardware exception in D.

`rocminfo` inside the shell lists only the CPU and `gfx1030` (RX 6600 XT, 32 CUs; ISA `gfx1030` and `gfx10-3-generic`). torch reports `multi_processor_count` 16 (work-group processors), so MIOpen keys its user database as `gfx1030_16`.

## Training (`train.py`, `train.txt`, `train-5min.txt`)

A 0.92 M-parameter 1-D CNN shaped like DELMIR's classifier: 12 leads × 1000 samples (10 s at 100 Hz), 4 conv blocks, an OMI logit and a 3-way culprit vessel head masked with `ignore_index`. It trains with AdamW at batch size 256 on synthetic data with a planted signal, so the loss must fall. Every run reached 100 % held-out accuracy on the planted task, so the gradients are right.

| Run | Steady state (samples/s) | First step | Peak VRAM | Outcome |
|---|---|---|---|---|
| GPU fp32, override, 120 s | **1,882** | 24.4 s | 0.49 GiB | clean, loss 1.85 → 0.0008 |
| GPU fp16 autocast, override, 60 s | **2,676** | 26.2 s | 0.49 GiB | clean |
| GPU fp32, override, 300 s (MIOpen cache warm) | **1,926** | 3.0 s | 0.49 GiB | clean: 2,235 steps, no errors or hangs |
| GPU fp32, **no override**, 60 s | 1,910 | 3.1 s | — | training steps clean (≈425), then the batch-1024 eval forward **crashed**: `HSA_STATUS_ERROR_EXCEPTION … hardware exception, code 0x1016`, GPU core dump (≈04:27 UTC, already at −75 mV) |
| GPU fp32, **no override**, 120 s, rerun at the validated 2500 MHz / −75 mV | 1,860 | 3.1 s | — | training steps clean (≈830), then the eval forward **failed**: `OutOfMemoryError`, tried to allocate 7.94 GiB with 7.35 GiB free |
| GPU fp32, override, 120 s, rerun at the validated 2500 MHz / −75 mV | 1,858 | 3.0 s | 0.49 GiB | clean, eval included |
| CPU fp32, 32 threads, 60 s | 721 | 0.4 s | — | clean |

- **The first step takes about 25 s.** That is MIOpen compiling and searching kernels for each new conv and batch-norm shape, and fp16 needs its own set. The results persist in `~/.config/miopen` and `~/.cache/miopen` (keyed `gfx1030_16`), so later runs with the same shapes start warm: the 5-minute run's first step took 3.0 s. The shipped `miopen-gfx1030.kdb` evidently doesn't cover this card's key, which answers #8's open question on `gfx1030_36`.
- **The undervolt.** #42 found that this card runs an undervolt and validated 2500 MHz at −75 mV (10 min at full load, no mismatches). It briefly ran −100 mV, which gives wrong matmuls, at about 04:19 UTC. That was before all the training runs here. The probe variants ended at 04:21 and may overlap it, but their GPU results matched the CPU. Rerun at the validated setting, the override run was clean and the no-override run failed again in the same place, so the failure comes from leaving out the override, not from the undervolt. Without the override, training throughput is the same; what changes is which kernels rocBLAS and MIOpen pick.
- **Shared GPU.** At 0.49 GiB, a model of this size leaves most of the 8 GB free for a second job such as #42.

## Cost

| | |
|---|---|
| Builds locally | only the `python3-3.13.16-env` wrapper; every other path is substituted from cache.nixos.org (`nix build --dry-run`) |
| Cold download | 6.0 GiB in 76 paths (some of the 168 were already in the store; #8 measured 6.6 GB from empty) |
| Cold `devenv shell` | **40 min** wall time, at ≈4 MB/s from cache.nixos.org |
| Closure | **15.7 GiB** devenv profile, 168 paths; the Python env alone is 15.4 GiB. Largest: rocfft 2.0, composable_kernel 1.9, hipblaslt 1.8, miopen 1.8, torch-lib 1.4 GiB |
| Warm `devenv shell` | 0.1 s (devenv's eval cache) |

## Overrides needed

- **None to nixpkgs.** It is plain `python313.withPackages (ps: [ ps.torchWithRocm ps.numpy ])`. Add `numpy`, because torch doesn't propagate it and warns `Failed to initialize NumPy` without it.
- **Two env vars:** `HSA_OVERRIDE_GFX_VERSION_1 = "10.3.0"` and `ROCR_VISIBLE_DEVICES = "0"`.
- **No host changes:** `/dev/kfd` and `renderD*` are already 0666.

## Not covered

- Real ECG data, larger models, and multi-hour runs.
- AMD's uv fallback wheels, which weren't needed.
- SDPA/attention: AOTriton has no gfx103x, and it wasn't exercised.
- `torch.compile` and Triton on gfx1030.
