# PROTOTYPE (#42): table of test-fold AUCs with patient-bootstrapped 95% CIs, and the paired drop from S.
#   python evaluate.py [runs] > results.md
# For an arm with k seeds the point estimate is the mean of the k per-seed AUCs; each bootstrap
# resample (patients drawn with replacement, all their records kept) recomputes that mean, so the
# CI covers test-set sampling. "drop from S" is computed on the same resamples (paired), against the
# S arm with the same fs and init.
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from metrics import TASKS, task_aucs
from prep import OUT, TARGETS

runs = sys.argv[1] if len(sys.argv) > 1 else "runs"
NB = 1000
df = pd.read_csv(os.path.join(OUT, "labels.csv"))
te = df[df.strat_fold == 10].reset_index(drop=True)
Y, hs = te[TARGETS].values, te.has_super.values.astype(bool)
pats = te.patient_id.values
upat = np.unique(pats)
rows_of = {p: np.where(pats == p)[0] for p in upat}
rng = np.random.default_rng(0)
boots = [np.concatenate([rows_of[p] for p in rng.choice(upat, len(upat))]) for _ in range(NB)]

arms = defaultdict(list)
meta = {}
for f in sorted(glob.glob(os.path.join(runs, "*.json"))):
    r = json.load(open(f))
    arm = r["name"].rsplit("_s", 1)[0]
    # GPU-trained runs: use the CPU recomputation from the saved weights (verify_cpu.py), not the GPU's
    cpu = f[:-5] + ".cpu_test.npy"
    arms[arm].append(np.load(cpu) if os.path.exists(cpu) else np.load(f[:-5] + ".npz")["test"])
    meta.setdefault(arm, []).append(r)


def scores(P, idx=None):
    if idx is None:
        idx = np.arange(len(Y))
    a = task_aucs(Y[idx], P[idx], hs[idx])
    return np.array([a[t] for t in TASKS] + [np.mean([a[t] for t in TASKS])])


point, boot = {}, {}
for arm, Ps in arms.items():
    point[arm] = np.mean([scores(P) for P in Ps], 0)
    boot[arm] = np.array([np.mean([scores(P, b) for P in Ps], 0) for b in boots])
    seed_sd = np.std([scores(P) for P in Ps], 0)
    meta[arm] = {"seeds": len(Ps), "seed_sd": seed_sd, "params": meta[arm][0]["params"],
                 "sec_per_epoch": np.mean([m["sec_per_epoch"] for m in meta[arm]]),
                 "best_epoch": [m["best_epoch"] for m in meta[arm]]}


def ci(v):
    lo, hi = np.nanpercentile(v, [2.5, 97.5])
    return f"[{lo:.3f}, {hi:.3f}]"


cols = TASKS + ["mean4"]
print(f"Test fold 10: {len(te)} records, {len(upat)} patients; {NB} patient-bootstrap resamples.\n")
print("| arm | seeds | " + " | ".join(cols) + " | Δmean4 vs S [95% CI] | params | s/epoch |")
print("|---|---|" + "---|" * len(cols) + "---|---|---|")
for arm in sorted(point, key=lambda k: (k.split("_")[1], k.split("_")[2], k.split("_")[0])):
    d, fs, init = arm.split("_")
    ref = f"S_{fs}_{init}"
    cells = [f"{point[arm][i]:.3f} {ci(boot[arm][:, i])}" for i in range(len(cols))]
    if ref in point and ref != arm:
        diff = boot[arm][:, -1] - boot[ref][:, -1]
        drop = f"{point[arm][-1] - point[ref][-1]:+.3f} {ci(diff)}"
    else:
        drop = "—"
    m = meta[arm]
    print(f"| {arm} | {m['seeds']} | " + " | ".join(cells) + f" | {drop} | {m['params'] / 1e6:.2f} M | {m['sec_per_epoch']:.0f} |")

print("\nSeed SD of each AUC (between-seed spread):\n")
print("| arm | " + " | ".join(cols) + " | best epochs |")
print("|---|" + "---|" * len(cols) + "---|")
for arm in sorted(point):
    print(f"| {arm} | " + " | ".join(f"{v:.3f}" for v in meta[arm]["seed_sd"]) + f" | {meta[arm]['best_epoch']} |")

print("\nPer-task drop from S, paired bootstrap:\n")
print("| arm | " + " | ".join(TASKS) + " |")
print("|---|" + "---|" * len(TASKS))
for arm in sorted(point):
    d, fs, init = arm.split("_")
    ref = f"S_{fs}_{init}"
    if ref in point and ref != arm:
        print(f"| {arm} | " + " | ".join(
            f"{point[arm][i] - point[ref][i]:+.3f} {ci(boot[arm][:, i] - boot[ref][:, i])}" for i in range(len(TASKS))) + " |")

# Per-head AUCs of the seed-mean probabilities (for the territory statements and superclasses).
print("\nPer-head AUC, seed-averaged probabilities:\n")
heads = None
for arm in sorted(point):
    per = task_aucs(Y, np.mean(arms[arm], 0), hs)["per"]
    if heads is None:
        heads = list(per)
        print("| arm | " + " | ".join(heads) + " |")
        print("|---|" + "---|" * len(heads))
    print(f"| {arm} | " + " | ".join(f"{per[h]:.3f}" for h in heads) + " |")
n_mi = int(Y[:, TARGETS.index("MI")].sum())
print(f"\nTest positives: MI {n_mi}; " + ", ".join(
    f"{t} {int(Y[Y[:, TARGETS.index('MI')] == 1, TARGETS.index(t)].sum())}" for t in TARGETS[5:11])
      + f" (within MI); INJSTE {int(Y[:, -1].sum())}; NORM {int(Y[:, 0].sum())}.")

# Decision contrasts: paired patient bootstrap of (first − second), per task and mean4.
PAIRS = [
    ("A_100_scratch", "S_100_scratch", "masked canvas vs synchronous upper bound"),
    ("B_100_scratch", "S_100_scratch", "per-lead encoder vs upper bound"),
    ("C_100_scratch", "S_100_scratch", "pseudo-synchronous vs upper bound"),
    ("A_100_scratch", "B_100_scratch", "A vs B"),
    ("A_100_scratch", "C_100_scratch", "A vs C"),
    ("S_500_scratch", "S_100_scratch", "500 vs 100 Hz, S"),
    ("C_500_scratch", "C_100_scratch", "500 vs 100 Hz, C"),
    ("A_500_scratch", "A_100_scratch", "500 vs 100 Hz, A"),
    ("S_500_ecgfounder", "S_500_scratch", "ECGFounder vs scratch at 500 Hz, S"),
    ("C_500_ecgfounder", "C_500_scratch", "ECGFounder vs scratch at 500 Hz, C"),
    ("A_500_ecgfounder", "A_500_scratch", "ECGFounder vs scratch at 500 Hz, A"),
    ("S_500_ecgfounder", "S_100_scratch", "ECGFounder 500 Hz vs scratch 100 Hz, S"),
    ("C_500_ecgfounder", "C_100_scratch", "ECGFounder 500 Hz vs scratch 100 Hz, C"),
    ("A_500_ecgfounder", "A_100_scratch", "ECGFounder 500 Hz vs scratch 100 Hz, A"),
]
print("\nDecision contrasts (first − second), paired patient bootstrap:\n")
print("| contrast | " + " | ".join(cols) + " |")
print("|---|" + "---|" * len(cols))
for a1, a2, label in PAIRS:
    if a1 in point and a2 in point:
        print(f"| {label} ({meta[a1]['seeds']} vs {meta[a2]['seeds']} seeds) | " + " | ".join(
            f"{point[a1][i] - point[a2][i]:+.3f} {ci(boot[a1][:, i] - boot[a2][:, i])}" for i in range(len(cols))) + " |")
