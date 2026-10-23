# PROTOTYPE (#50): is the garbage tied to the first use of a shape? In a fresh process, run the same
# batch several times per batch size and report the bad rows of each call against the CPU reference.
#   DELMIR_NO_MIOPEN=1 python probe_first.py A_100_scratch_s0 results/first_<cfg>.jsonl
import os
import sys
import time

import numpy as np
import torch

from common import RUNS42, build, env_info, jsonl, predict, test_fold

name, out = sys.argv[1], sys.argv[2]
SIZES = [int(s) for s in os.environ.get("SIZES", "256,150,135,7").split(",")]
CALLS = int(os.environ.get("CALLS", 4))
if os.environ.get("DELMIR_NO_MIOPEN"):
    torch.backends.cudnn.enabled = False
if os.environ.get("DELMIR_BENCHMARK"):
    torch.backends.cudnn.benchmark = True
m, design, fs, init, T, w = build(name)
m.load_state_dict(torch.load(os.path.join(RUNS42, name + ".pt"), map_location="cpu"))
x, _, _ = test_fold(fs, init)
ref = np.load(f"refs/{name}.cpu.npy")
jsonl(out, {"probe": "start", "model": name, **env_info(), "cudnn": torch.backends.cudnn.enabled,
            "benchmark": torch.backends.cudnn.benchmark})
dev = torch.device("cuda")
m.to(dev)
for bs in SIZES:
    for call in range(CALLS):
        t0 = time.time()
        p = predict(m, design, init, T, w, x[:bs], dev, bs)  # one batch, the first bs records
        d = np.abs(p - ref[:bs]).max(1)
        bad = np.where(~(d <= 1e-3))[0]
        rec = {"probe": "first", "model": name, "bs": bs, "call": call, "sec": time.time() - t0,
               "max_abs": float(np.nanmax(d)), "bad_rows": len(bad), "bad": bad[:40].tolist()}
        jsonl(out, rec)
        print(rec, flush=True)
