# PROTOTYPE: #50, can multi-hour training on the RX 6600 XT be trusted?

Throwaway spike for [#50](https://github.com/the-dr-lazy/delmir/issues/50). Never merged. The answer lives in the issue's resolution comment and in this file. The tables are in [`results/tables.md`](results/tables.md), built by `report.py` from `results/*.jsonl` and the per-run `results/*.json`.

## Answer

**Yes, with one rule: never enable `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.**

- **Cause of the silent errors.** #42's silent wrong outputs came from that allocator setting. #42's `run_grid.sh` exported it. It was not the GPU, the undervolt, the odd shapes or the ROCm build.
- **With the default caching allocator,** nixpkgs' `torchWithRocm` (#19) is exact:
  - eval forwards match the CPU to ≤1.1e-6 for every model family and every batch size, unpadded and unserialized;
  - two 30-epoch xresnet1d101 runs (100 Hz and 500 Hz, about 1.5 GPU-hours) had no crash, no non-finite step, and no validation or test record off the CPU.

## Setup

- **Host.** RX 6600 XT (gfx1032) at #42's validated 2500 MHz / −75 mV, which was the setting throughout. The probes recorded the `pp_od_clk_voltage` table each time.
- **Stacks.**
  - **nix:** this directory's `devenv.nix`. It is #19's stack: `torchWithRocm` 2.13.0, HIP 7.2.53211, nixpkgs `5adc508`, `HSA_OVERRIDE_GFX_VERSION_1=10.3.0`, `ROCR_VISIBLE_DEVICES=0`. The host's global `HSA_OVERRIDE_GFX_VERSION` is dropped.
  - **wheel:** #42's `.venv-rocm`, PyTorch's `torch 2.14.1+rocm7.2` with the global override. It is the positive control.
- **Code.** #42's spike code: `layout.py`, `models.py`, `net1d.py`, `prep.py`, `metrics.py` and `train.py`, plus #42's saved checkpoints.
  - **`train.py` changes:**
    - Padding is now opt-in (`--pad`).
    - Every epoch, it recomputes validation on a CPU twin (`--parity`, 0 = all records). It counts non-finite training losses and logs GPU temperature and clock.
    - At the end, it recomputes the whole test fold on the CPU.
- **`run.sh`** picks the stack (`STACK=nix|wheel`), the allocator (`EXPANDABLE=0|1`, default 1 as in #42) and serialization (`SERIAL=1` sets `AMD_SERIALIZE_KERNEL=3`).

| probe | what it does |
|---|---|
| `probe_shapes.py` | One #42 checkpoint. Predicts the whole test fold (2,198 records) at batch sizes 256, 150, 135, 7 and 1, unpadded, twice, and compares every record with the CPU. |
| `probe_first.py` | The same batch repeated within one process, to tie errors to first use. |
| `bench.py` | Training throughput of xresnet1d101 design A, serialized against unserialized. At 25 × 5000 it also exercises MIOpen's BatchNorm JIT. |
| `queue.sh`, `after.sh`, `shapes_all.sh` | The order the runs actually went in. |

## Findings

### 1. Silent garbage: `expandable_segments`, both stacks, every model

| model (#42 checkpoint) | expandable on: records off on pass 1 (worst \|Δprob\|) | expandable off (both stacks) |
|---|---|---|
| A 100 Hz xresnet1d101 | 356 / 155 / 162 at bs 256 / 150 / 135 (1.0) | 0, ≤ 6.9e-7 |
| S 500 Hz xresnet1d101 | 374 / 67 / 131 (1.0) | 0, ≤ 7.2e-7 |
| A 500 Hz xresnet1d101 (25 × 5000) | 406 / 220 / 252 / 14 / 1 at bs 256 / 150 / 135 / 7 / 1 (1.0) | 0, ≤ 6.0e-7 |
| A 500 Hz ECGFounder Net1D | 398 / 223 / 200 / 7 / 1 (1.0), and 585 / 16 on pass 2 | 0, ≤ 1.1e-6 |

- **When the errors happen.** Only on memory the allocator has just mapped:
  - the first pass over a new shape in a process, and its later passes are exact;
  - for Net1D, the second pass too, because its large activations keep growing the segment.
- **No NaN.** No probe returned NaN or reported an error.
- **Not fixed by serialization.** `AMD_SERIALIZE_KERNEL=3` does not fix it: 373 / 171 / 248 records off, against 380 / 233 / 158 unserialized (the triage table).
- **Padding only hid it.** Padding stopped new shapes after the first batch, so it fixed most of #42's later epochs.
- **Training run with it on.** The same 30-epoch 100 Hz run with expandable segments on (`A_100_scratch-exp1_s0`) reproduced #42's symptom exactly.
  - **Epoch 0:** 135 validation records were off by up to 0.96. That is the last, partial batch (2,183 = 8 × 256 + 135).
  - **Epochs 1–29:** exact, because their shapes were already mapped.
  - **Final test eval:** a new process state put the last 150-record batch (2,198 = 8 × 256 + 150) on fresh mappings, so 150 of 2,198 records were off.
  - **Result:** the GPU's own test mean AUC was 0.9325, against 0.9413 from the CPU, with no error and no NaN. The training itself had no non-finite step.
- **#42's transient NaN on a first validation** fits the same mechanism: first validation means a new shape and fresh mappings. It was not reproduced, and it is an inference.
- **Upstream.** This matches an open upstream report on RDNA4: [pytorch/pytorch#195202](https://github.com/pytorch/pytorch/issues/195202), where expandable_segments silently produces NaN on gfx1201 and the default allocator is finite. That issue lists sibling hang and crash reports.

### 2. Long runs on the default allocator: clean

| run | s/epoch | non-finite steps | val records off (any epoch) | test records off | test mean-of-4 AUC GPU / CPU | #42 reference |
|---|---|---|---|---|---|---|
| A 100 Hz, 30 epochs | 21 | 0 / 4,080 | 0 of 2,183 × 30 (≤ 7.7e-7) | 0 (4.2e-7) | 0.9370 / 0.9370 | CPU-trained, same seed: 0.9388, same best epoch (26) |
| A 500 Hz, 30 epochs | 138 | 0 / 4,080 | 0 of 300 × 30 (≤ 2.8e-6) | 0 | 0.9320 / 0.9320 | GPU-trained (serialized, MIOpen off), CPU-recomputed: 0.9333, same best epoch (28) |

- **Run settings.** No padding, no serialization, MIOpen on. Validation was 2,183 records, whose last batch has 135.
- **Not bitwise reproducible.** GPU training with the same seed isn't bitwise reproducible: the expandable-on control's CPU-recomputed AUC is 0.9413. Seed-level noise of that size is why #24 should compare arms over several seeds.
- **OOM warning.** The one warning in the 500 Hz log came at 12:35, while I ran a B probe on the same GPU. The allocator retried and the run carried on.

### 3. Crashes: one race, loud, in the per-lead B model only

- **Families with no crash.** xresnet1d (S/A, 100 and 500 Hz) and Net1D never crashed unserialized: in any shape probe, either training run, or the four benches.
- **B (#42's per-lead model) segfaults.** B runs xresnet1d18 over 12 × bs single-channel 2.5 s leads, then a transformer.
  - **Where and how often:** inside a GPU `conv1d` of its per-lead body, on the first full-fold eval in a fresh process. It died in 9 of 10 unserialized runs, across both stacks and either allocator setting.
    - The first three died with no traceback.
    - The one that survived ran while the 500 Hz training held about 6 GiB of the GPU.
  - **When it doesn't crash:**
    - `AMD_SERIALIZE_KERNEL=3`: 2 of 2 full-fold runs and 3 of 3 single-batch runs clean, all exact;
    - MIOpen logging on, which slows the launches;
    - single-batch calls (`probe_first.py`: 0 crashes in 4 runs, with 256 first or with ascending sizes).
  - **Diagnosis:** a kernel-launch race in ROCm or MIOpen, the class #42 saw. It is never silent: the process dies and the checkpoint survives.

### 4. MIOpen

- **No BatchNorm JIT gap on `torchWithRocm`.** xresnet1d101 at 25 × 5000 trains with MIOpen on. #42's wheel could not JIT this BatchNorm (missing `<type_traits>`). The first step spends 61 s tuning, and the cache lives in `~/.config/miopen` and `~/.cache/miopen`.
- **Don't turn MIOpen off.** `torch.backends.cudnn.enabled = False` segfaults on the first forward on `torchWithRocm` (`results/first_A100_nix_exp*_nomiopen.jsonl`).

### 5. The price of serialization

| input | unserialized | `AMD_SERIALIZE_KERNEL=3` | cost |
|---|---|---|---|
| 25 × 1000 (A 100 Hz) | 884 samples/s | 605 | −32% |
| 25 × 5000 (A 500 Hz) | 127 | 118 | −7% |

The serialized first steps are short only because the unserialized run had already warmed MIOpen's cache.

### 6. The undervolt

- **Everything ran at 2500 MHz / −75 mV.** Every fault seen has a reproducible software trigger:
  - the allocator setting, switched on and off at will;
  - B's race, which depends on launch order.
- **No fault looked random.** In about 2.5 GPU-hours of probes and training there was no lone mismatch, no NaN, and no fault that came and went. So the spike didn't need a stock-voltage rerun. The parity rule below would catch a marginal voltage anyway.

## Rules for #39 (run tracking) and #24 (evaluation)

1. **Allocator.** The training shell and the entry point never enable expandable segments. The training script refuses to start if `PYTORCH_CUDA_ALLOC_CONF` contains `expandable_segments:True`.
2. **No padding needed.** Eval may use any batch size, including a partial last batch.
3. **No serialization by default.** It costs 7–32%, and xresnet1d and Net1D don't need it.
   - **Crashes** are loud. Runs checkpoint every epoch and resume, as #42's `train.py` does.
   - **An architecture that crashes** is rerun with `AMD_SERIALIZE_KERNEL=3`, and the run record says so.
4. **Reported metrics come from a CPU recomputation of the test predictions from the saved weights.** The GPU's own test predictions are kept only for the parity check.
   - **Every run records** the worst |Δprob| between the two and the number of records off by more than 1e-3. It fails if that number is not 0.
   - **Cost:** seconds at 100 Hz, about 2 CPU-min at 500 Hz.
   - **Why the CPU numbers are canonical:** they don't depend on the GPU stack. The check also covers what this spike can't rule out for good: a ROCm or driver upgrade, a new architecture, or a marginal undervolt.
5. **Model selection may use GPU validation predictions.** Each epoch also recomputes a fixed sample of at least 300 validation records on the CPU as a canary. Any record off by more than 1e-3 fails the run.
6. **Every run records:**
   - the torch and HIP versions;
   - `HSA_OVERRIDE_GFX_VERSION_1`, `ROCR_VISIBLE_DEVICES`, `PYTORCH_CUDA_ALLOC_CONF` and `AMD_SERIALIZE_KERNEL`;
   - the GPU's `pp_od_clk_voltage` (clock and voltage offset);
   - non-finite training steps;
   - both parity numbers.
7. **Leave MIOpen on.** Keep its caches on disk between runs.

## Not covered

- **Mixed precision:** fp16 and bf16 autocast.
- **Anything beyond 30 epochs and one seed:** longer runs, or more than one seed per configuration.
- **Two concurrent training jobs** (#42 ran 2).
- **Stock voltage.**
- **Why B races.** No HIP-level trace.
- **`torch.compile`, SDPA kernels (beyond B's encoder layer) and other ROCm or driver versions.**
