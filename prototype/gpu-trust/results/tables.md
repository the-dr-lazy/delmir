## Odd eval shapes: whole test fold (2,198 records), unpadded

Cell: records off by > 1e-3 vs the CPU (worst |Δprob|), pass 1 / pass 2 over all five sizes.

A run with no rows died with a segfault before its first result (B: logs/shapes_B_100_*).

| model | stack | expandable_segments | AMD_SERIALIZE_KERNEL | bs 256 | bs 150 | bs 135 | bs 7 | bs 1 |
|---|---|---|---|---|---|---|---|---|
| A_100_scratch_s0 | nix | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| A_100_scratch_s0 | nix | on | unset | 356 (1e+00) / 0 | 155 (1e+00) / 0 | 162 (9e-01) / 0 | 0 / 0 | 0 / 0 |
| A_100_scratch_s0 | wheel | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| A_500_ecgfounder_s1 | nix | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| A_500_ecgfounder_s1 | nix | on | unset | 398 (1e+00) / 585 (1e+00) | 223 (1e+00) / 16 (1e+00) | 200 (1e+00) / 0 | 7 (8e-01) / 0 | 1 (5e-01) / 0 |
| A_500_ecgfounder_s1 | wheel | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| A_500_scratch_s0 | nix | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| A_500_scratch_s0 | nix | on | unset | 406 (1e+00) / 0 | 220 (9e-01) / 0 | 252 (1e+00) / 0 | 14 (9e-01) / 0 | 1 (7e-01) / 0 |
| A_500_scratch_s0 | wheel | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| B_100_scratch_s0 | nix | off | unset | segfault | | | | |
| B_100_scratch_s0 | nix | off | 3 | 0 / - | 0 / - | 0 / - | 0 / - | 0 / - |
| B_100_scratch_s0 | nix | on | unset | segfault | | | | |
| B_100_scratch_s0 | wheel | off | unset | segfault | | | | |
| B_100_scratch_s0 | wheel | off | 3 | 0 / - | 0 / - | 0 / - | 0 / - | 0 / - |
| S_500_scratch_s0 | nix | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| S_500_scratch_s0 | nix | on | unset | 374 (1e+00) / 0 | 67 (8e-01) / 0 | 131 (8e-01) / 0 | 0 / 0 | 0 / 0 |
| S_500_scratch_s0 | wheel | off | unset | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## Serialized launches, expandable segments on (A 100 Hz, how #42 ran)

| stack | AMD_SERIALIZE_KERNEL | bs 256 | bs 150 | bs 135 | bs 7 | bs 1 |
|---|---|---|---|---|---|---|
| nix | unset | 380 / 0 | 233 / 0 | 158 / 0 | 0 / 0 | 0 / 0 |
| nix | 3 | 373 / 0 | 171 / 0 | 248 / 0 | 0 / 0 | 0 / 0 |
| wheel | unset | 389 / 0 | 1818 / 0 | 1407 / 0 | 0 / 0 | 0 / 0 |
| wheel | 3 | 376 / 0 | 166 / 0 | 1425 / 0 | 7 / 0 | 0 / 0 |

## Training throughput, xresnet1d101 design A, bs 128, alone on the GPU (nix stack)

| input | AMD_SERIALIZE_KERNEL | first step (MIOpen tuning) | samples/s | peak GiB |
|---|---|---|---|---|
| 25 × 1000 | unset | 11 s | 884 | 1.28 |
| 25 × 1000 | 3 | 4 s | 605 | 1.28 |
| 25 × 5000 | unset | 61 s | 127 | 6.05 |
| 25 × 5000 | 3 | 5 s | 118 | 6.05 |

## 30-epoch training runs (nix stack, design A, seed 0, no padding, no serialization)

| run | expandable_segments | epochs | s/epoch | non-finite steps | val epochs with records off | worst val |Δprob| | test records off | best epoch | test mean4 AUC GPU / CPU |
|---|---|---|---|---|---|---|---|---|---|
| A_100_scratch-exp1_s0 | on | 30 | 21 | 0 | 1 (val records checked: all) | 9.6e-01 | 150 / 2198 | 27 | 0.9325 / 0.9413 |
| A_100_scratch_s0 | off | 30 | 21 | 0 | 0 (val records checked: all) | 7.7e-07 | 0 / 2198 | 26 | 0.9370 / 0.9370 |
| A_500_scratch_s0 | off | 30 | 138 | 0 | 0 (val records checked: first 300) | 2.8e-06 | 0 / 2198 | 28 | 0.9320 / 0.9320 |
