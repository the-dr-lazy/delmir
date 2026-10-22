# PROTOTYPE (#42): belt and braces for GPU-trained runs. Recompute each run's test-fold probabilities on
# the CPU from its saved best weights and compare them with the probabilities the GPU run saved.
# A silent GPU fault (seen under an unstable undervolt, and a ROCm race on this card) would show here.
#   python verify_cpu.py runs/B_100_scratch_s0.pt [...]
import os
import sys

import numpy as np
import pandas as pd
import torch

from deploy import build, design_input
from metrics import TASKS, task_aucs
from prep import OUT, TARGETS

torch.backends.mha.set_fastpath_enabled(False)
torch.set_num_threads(8)
df = pd.read_csv(os.path.join(OUT, "labels.csv"))
te = np.where(df.strat_fold.values == 10)[0]
tr = np.where(df.strat_fold.values <= 8)[0]
Y, hs = df[TARGETS].values[te], df.has_super.values.astype(bool)[te]
print("| run | max abs Δprob GPU vs CPU | mean4 AUC GPU | mean4 AUC CPU |")
print("|---|---|---|---|")
for ck in sys.argv[1:]:
    name = os.path.basename(ck)[:-3]
    design, fs, init = name.rsplit("_s", 1)[0].split("_")
    fs = int(fs)
    m, T, w = build(design, fs, init)
    m.load_state_dict(torch.load(ck, map_location="cpu"))
    m.eval()
    X = np.load(os.path.join(OUT, f"X{fs}.npy"), mmap_mode="r")
    if init == "ecgfounder":
        def norm(x):
            return (x - x.mean((1, 2), keepdim=True)) / (x.std((1, 2), keepdim=True) + 1e-8)
    else:
        sub = np.asarray(X[tr[:2000]], dtype=np.float32)
        mu, sd = float(sub.mean()), float(sub.std())

        def norm(x):
            return (x - mu) / sd
    out = []
    with torch.no_grad():
        for i in range(0, len(te), 128):
            x = norm(torch.from_numpy(np.asarray(X[te[i:i + 128]], dtype=np.float32)))
            pr = torch.ones(x.shape[0], 12, dtype=torch.bool)
            f = (lambda *z: m(*z))
            if design == "S":
                ps = [torch.sigmoid(f(*design_input("S", init, x[:, :, s:s + w], pr))) for s in range(0, T - w + 1, w // 2)]
                out.append(torch.stack(ps).amax(0))
            else:
                out.append(torch.sigmoid(f(*design_input(design, init, x, pr))))
    cpu = torch.cat(out).numpy()
    gpu = np.load(ck[:-3] + ".npz")["test"]
    np.save(ck[:-3] + ".cpu_test.npy", cpu)
    a_g, a_c = task_aucs(Y, gpu, hs), task_aucs(Y, cpu, hs)
    bad = np.abs(gpu - cpu).max(1) > 1e-3
    rows = np.where(bad)[0]
    print(f"| {name} | {np.abs(gpu - cpu).max():.1e} | {np.mean([a_g[t] for t in TASKS]):.4f} | "
          f"{np.mean([a_c[t] for t in TASKS]):.4f} | {bad.sum()}/{len(bad)} records off; "
          f"rows {rows.min() if len(rows) else '-'}..{rows.max() if len(rows) else '-'} |", flush=True)
