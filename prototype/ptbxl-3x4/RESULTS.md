# #42 results: what the 3×4 printout layout costs a PTB-XL classifier

PROTOTYPE, never merged. Raw tables: [`results_table.md`](results_table.md) (`evaluate.py`), [`deploy_table.md`](deploy_table.md) (`deploy.py`), [`verify_cpu_table.md`](verify_cpu_table.md) (`verify_cpu.py`).

## Answer

- **Input design: A, the masked canvas.** It costs nothing against the synchronous upper bound: the four-task mean AUC is +0.000 [−0.003, 0.004], and territory is +0.001 [−0.011, 0.013]. C (pseudo-synchronous) loses 0.051 [0.036, 0.068] of territory AUC. B (per-lead encoder) loses 0.030 [0.013, 0.046]. A beats B and C on territory by 0.031 and 0.052, CIs excluding 0.
- **Sampling rate: 100 Hz for the classifier.**
  - 500 Hz gives S nothing: −0.002 [−0.005, 0.001].
  - It helps only C, the design starved to 250 samples per lead: territory +0.017 [0.007, 0.029].
  - It costs about 13× the GFLOP and latency (C: 0.08 → 1.07 GFLOP; S: 0.58 → 7.5).
  - A at 500 Hz (1 seed) gains nothing either: −0.004 [−0.010, 0.001], territory −0.009 [−0.023, 0.002]. It costs 13× the GFLOP (0.33 → 4.29).
- **ECGFounder: not worth it as the default.**
  - It helps territory: S +0.015 [0.005, 0.026]; A, 500 Hz ECGFounder vs 100 Hz scratch, +0.013 [−0.001, 0.026].
  - It hurts the superclasses by 0.005–0.012.
  - It is 30.7 M parameters (123 MB fp32 per member, 615 MB for an ensemble of 5), against 1.9 M for xresnet1d101.
  - It costs 7× the GFLOP and 10× the ORT latency of A, and its ONNX export drifts by up to 0.15 logits under ORT graph optimisation (see below).
  - Re-test it in #23 on DELMIR's own OMI and culprit-vessel proxy labels (#21), where few labels may favour pretraining. PTB-XL statements are plentiful.
- **Signal contract (#22).**
  - Carry the 10 s, 12-lead canvas at 500 Hz, the native rate of PTB-XL, ECG-Image-Kit and the digitizers. Each stage resamples down; the classifier works at 100 Hz.
  - Mark every unplotted or unreadable sample as **NaN**, per lead and per sample.
  - Design A derives its 12 presence-mask channels from the NaNs (mask = not NaN) and zero-fills them. So the contract needs no separate mask, and it needs no layout field as long as the plotted windows are what the NaNs say they are.
  - Also carry the 10 s rhythm-strip lead (II on a standard 3×4) as its own channel. A uses it.

## Setup

- **Data.**
  - PTB-XL 1.0.3. All 87,196 record files were checked against PhysioNet's `SHA256SUMS`.
  - Folds 1–8 train, fold 9 selects the epoch, fold 10 tests: 2,198 records, 1,904 patients.
  - CIs are 95% patient-bootstrap intervals with 1,000 resamples, taking all of a patient's records together.
  - An arm's AUC is the mean of its per-seed AUCs. Δs are paired on the same resamples.
- **Tasks.** One multi-label model per arm with 12 sigmoid outputs, scored four ways:
  - `super`: macro-AUC over NORM/MI/STTC/CD/HYP.
  - `mi_norm`: MI vs NORM.
  - `territory`: macro-AUC over IMI/ASMI/AMI/ALMI/LMI/ILMI, within MI records only. This is the culprit-vessel proxy.
  - `injury`: INJ\*/STE\_ vs NORM.
  - `mean4`: the mean of the four.
  - Test positives: MI 550; within MI, IMI 267, ASMI 234, AMI 35, ALMI 27, LMI 20, ILMI 48; INJ\*/STE\_ 34, so its CIs are wide.
- **Layout.** ECG-Image-Kit's 3×4: I/II/III over 0–2.5 s, aVR/aVL/aVF over 2.5–5, V1–V3 over 5–7.5, V4–V6 over 7.5–10, plus a 10 s lead II strip.
  - **S:** synchronous 10 s. It trains on the benchmark's random 2.5 s crops and is read with 7 overlapping windows, max-aggregated.
  - **A:** 12 canvas channels, zero outside each lead's window, plus the rhythm strip and 12 presence masks, giving 25 channels × 10 s into xresnet1d101.
  - **B:** one shared xresnet1d18-style encoder over each lead's 2.5 s and over the strip, plus lead embeddings, fused by one transformer layer and masked mean/max pooling.
  - **C:** every lead's own 2.5 s shifted into one 12 × 2.5 s window, into xresnet1d101.
  - **Augmentation for A/B/C:** a random circular time shift of the whole record before the layout is applied, which gives new beats under the same plot geometry.
  - **Lead dropout for every arm:** with p = 0.5, 1–4 leads are zeroed and their masks cleared.
- **Training.**
  - **Scratch arms:** 30 epochs, one-cycle AdamW at max lr 1e-2, weight decay 1e-2, batch 128, benchmark kernels, ×5 at 500 Hz.
  - **B used max lr 1e-3.** At 1e-2 all 3 seeds collapsed at the one-cycle peak: loss jumped from 0.19 to 0.30 and never recovered. Those runs are kept in `runs_diverged/`.
  - **ECGFounder:** the 12-lead checkpoint, z-scored per record as in its `dataset.py`, at 500 Hz only. Fine-tuned for 10 epochs at max lr 1e-3, batch 64. A feeds it the 12-channel canvas without masks.
  - **Seeds:** 3 per arm. A at 500 Hz from scratch has 1: it was a spot check, with MIOpen off (see #50). B at 500 Hz from scratch was not run; it would take more than 10 GPU-hours per seed.

## Results (test fold 10, mean of 3 seeds, 95% patient-bootstrap CI)

| arm | super | MI vs NORM | territory | injury | mean4 | Δmean4 vs S (same rate and init) |
|---|---|---|---|---|---|---|
| S 100 Hz scratch (upper bound) | 0.932 [0.925, 0.939] | 0.970 [0.962, 0.976] | 0.884 [0.864, 0.902] | 0.962 [0.912, 0.999] | 0.937 [0.923, 0.948] | — |
| **A 100 Hz scratch** | 0.932 [0.925, 0.938] | 0.971 [0.963, 0.977] | 0.885 [0.864, 0.905] | 0.961 [0.908, 0.999] | 0.937 [0.923, 0.949] | +0.000 [−0.003, 0.004] |
| B 100 Hz scratch | 0.924 [0.917, 0.931] | 0.965 [0.957, 0.973] | 0.854 [0.828, 0.878] | 0.973 [0.917, 1.000] | 0.929 [0.913, 0.940] | −0.008 [−0.015, 0.002] |
| C 100 Hz scratch | 0.916 [0.908, 0.923] | 0.959 [0.950, 0.967] | 0.833 [0.809, 0.856] | 0.969 [0.915, 0.999] | 0.919 [0.904, 0.930] | −0.018 [−0.025, −0.009] |
| A 500 Hz scratch (1 seed) | 0.932 [0.925, 0.939] | 0.967 [0.959, 0.974] | 0.876 [0.849, 0.898] | 0.958 [0.898, 0.998] | 0.933 [0.916, 0.946] | −0.001 [−0.008, 0.005] |
| S 500 Hz scratch | 0.930 [0.923, 0.936] | 0.967 [0.958, 0.974] | 0.884 [0.863, 0.901] | 0.958 [0.908, 0.999] | 0.935 [0.921, 0.946] | — |
| C 500 Hz scratch | 0.918 [0.910, 0.925] | 0.961 [0.952, 0.969] | 0.851 [0.827, 0.872] | 0.975 [0.930, 0.999] | 0.926 [0.913, 0.936] | −0.009 [−0.016, 0.001] |
| S 500 Hz ECGFounder | 0.920 [0.913, 0.926] | 0.968 [0.960, 0.974] | 0.899 [0.884, 0.913] | 0.967 [0.924, 0.999] | 0.939 [0.927, 0.947] | — |
| A 500 Hz ECGFounder | 0.927 [0.920, 0.933] | 0.966 [0.958, 0.973] | 0.898 [0.879, 0.915] | 0.984 [0.964, 0.999] | 0.944 [0.936, 0.950] | +0.005 [−0.001, 0.012] |
| C 500 Hz ECGFounder | 0.905 [0.897, 0.913] | 0.958 [0.948, 0.967] | 0.868 [0.846, 0.886] | 0.970 [0.924, 0.999] | 0.925 [0.912, 0.935] | −0.013 [−0.021, −0.005] |

Seed SDs are ≤0.003, except territory, where they are ≤0.009 (`results_table.md`). S's superdiagnostic AUC of 0.932 matches the published PTB-XL benchmark for xresnet1d101, 0.925.

### Decision contrasts (first − second, paired)

| contrast | super | territory | mean4 |
|---|---|---|---|
| A vs S, 100 Hz | −0.000 [−0.003, 0.002] | +0.001 [−0.011, 0.013] | +0.000 [−0.003, 0.004] |
| B vs S, 100 Hz | −0.008 [−0.012, −0.005] | −0.030 [−0.046, −0.013] | −0.008 [−0.015, 0.002] |
| C vs S, 100 Hz | −0.017 [−0.020, −0.013] | −0.051 [−0.068, −0.036] | −0.018 [−0.025, −0.009] |
| A vs B, 100 Hz | +0.008 [0.005, 0.011] | +0.031 [0.015, 0.046] | +0.008 [−0.002, 0.016] |
| A vs C, 100 Hz | +0.016 [0.013, 0.020] | +0.052 [0.034, 0.071] | +0.018 [0.009, 0.026] |
| S: 500 vs 100 Hz | −0.002 [−0.004, −0.000] | −0.000 [−0.009, 0.008] | −0.002 [−0.005, 0.001] |
| C: 500 vs 100 Hz | +0.002 [0.000, 0.004] | +0.017 [0.007, 0.029] | +0.007 [0.003, 0.011] |
| A: 500 vs 100 Hz (1 vs 3 seeds) | +0.000 [−0.002, 0.002] | −0.009 [−0.023, 0.002] | −0.004 [−0.010, 0.001] |
| S: ECGFounder vs scratch, 500 Hz | −0.010 [−0.014, −0.006] | +0.015 [0.005, 0.026] | +0.004 [−0.000, 0.008] |
| C: ECGFounder vs scratch, 500 Hz | −0.012 [−0.018, −0.008] | +0.017 [0.002, 0.033] | −0.001 [−0.006, 0.005] |
| A: ECGFounder vs scratch, 500 Hz (3 vs 1 seeds) | −0.005 [−0.009, −0.001] | +0.022 [0.006, 0.041] | +0.011 [0.002, 0.022] |
| A: ECGFounder 500 Hz vs scratch 100 Hz | −0.005 [−0.009, −0.001] | +0.013 [−0.001, 0.026] | +0.006 [−0.001, 0.015] |

### Cost (seed-0 model; desktop ONNX Runtime 1.31 CPU, `ENABLE_EXTENDED`, median of 30 runs)

| arm | params | GFLOP per reading | ORT single pass, ms (1 / 8 threads) | ORT 13-pass ablation batch, ms (1 / 8 threads) | ablation vs IG, Spearman ρ, median [IQR] |
|---|---|---|---|---|---|
| S 100 Hz (7 windows) | 1.87 M | 0.58 | 5.0 / 3.3 | 64 / 22 | 0.59 [0.40, 0.77] |
| **A 100 Hz** | 1.88 M | 0.33 | 2.8 / 1.9 | 34 / 13 | 0.57 [0.42, 0.74] |
| B 100 Hz | 0.69 M | 0.51 | 4.7 / 2.6 | 64 / 26 | 0.36 [0.14, 0.54] |
| C 100 Hz | 1.87 M | 0.08 | 1.0 / 1.0 | 9 / 5 | 0.72 [0.54, 0.85] |
| S 500 Hz (7 windows) | 4.65 M | 7.47 | 59 / 12 | 800 / 141 | 0.57 [0.38, 0.74] |
| A 500 Hz | 4.66 M | 4.29 | 33 / 6.3 | 434 / 73 | 0.48 [0.22, 0.67] |
| C 500 Hz | 4.65 M | 1.07 | 8.5 / 2.8 | 111 / 22 | 0.64 [0.48, 0.78] |
| S 500 Hz ECGFounder (7 windows) | 30.68 M | 4.21 | 73 / 30 | 929 / 352 | 0.65 [0.46, 0.80] |
| A 500 Hz ECGFounder | 30.68 M | 2.34 | 28 / 10 | 329 / 86 | 0.59 [0.40, 0.72] |
| C 500 Hz ECGFounder | 30.68 M | 0.60 | 13 / 6.5 | 133 / 57 | 0.60 [0.39, 0.77] |

- **ONNX vs PyTorch.** The xresnet1d logits match to ≤4e-6.
- **ECGFounder's Net1D drifts by 0.05–0.15 logits** under any ORT level ≥ `BASIC`. Disabling the `ConstantFolding` optimiser alone restores 5e-7; plain `DISABLE_ALL` also matches. If ECGFounder is ever used, the model hand-off has to pin that optimiser off.
- **Lead ablation and integrated gradients agree only moderately,** with a median ρ of about 0.6 for A. They aren't interchangeable, so #6 and #26 should keep lead ablation, which is what ORT can run on the phone, as the attribution shown.
- **A on the phone.** The 13-pass ablation is a single batch of 13. For an ensemble of 5 it is about 170 ms on a desktop core, so a phone at 5–10× slower takes roughly 1–2 s. That matches #15's estimate.
- **Training time per epoch,** in medians. These are not comparable across arms, because the arms ran on different machines and under different load:
  - **CPU** (16 cores shared by 4–7 jobs): S/C 100 Hz 40–90 s, A 100 Hz 160–260 s, ECGFounder S/C 320–470 s, ECGFounder A 1,265 s.
  - **GPU** (RX 6600 XT, serialized launches, 1–2 jobs): B 100 Hz 130–170 s, S/C 500 Hz 80–95 s, ECGFounder A 150–160 s, A 500 Hz scratch ≈ 340 s (MIOpen off).

## Caveats

- **PTB-XL is not OMI data.** Its MI is mostly established infarcts (#10), and "territory" means the infarct-location statements, not an angiographic culprit. These numbers rank input designs; they don't estimate DELMIR's OMI performance.
- **The layout is simulated** from clean synchronous signals. Digitizer error from phone photos (#38) is not included.
- **Machines.** The 100 Hz S/A/C arms, ECGFounder S/C, and ECGFounder A seed 0 trained on the CPU. B, S/C at 500 Hz, ECGFounder A seeds 1–2, and A 500 Hz trained on the GPU.
  - **GPU test numbers come from the CPU.** Every GPU run's test predictions were recomputed on the CPU from its saved weights, and those are the numbers above.
  - **The GPU's own predictions were partly wrong** in 2 runs: the last 150-record batch.
  - **The smoke check agreed.** A GPU retrain of S 100 Hz seed 0 matched the CPU run within seed noise.
- **ROCm on this card is not trustworthy as-is.** It segfaulted, produced garbage on odd shapes and gave a transient NaN; it is now [#50](https://github.com/the-dr-lazy/delmir/issues/50). Epoch selection on the validation fold may have seen a bad last batch in two places: the S/C 500 Hz seed-0 runs (135 of 2,183 records) and the early epochs of B seeds 0–1 (7 records). Padding fixed every later epoch.
- **Settings not tuned per design.** Hyperparameters are the benchmark's for every design, except B's lr. A B with more tuning could close part of its gap.
