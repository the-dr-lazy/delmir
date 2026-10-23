# PROTOTYPE (#50): odd eval shapes. For one #42 checkpoint, predict the whole test fold (2,198 records)
# on the GPU at each batch size, unpadded, so every size also ends on its own partial batch
# (2198 % 135 = 38, % 150 = 98, % 256 = 150), and compare each record with a CPU reference.
#   python probe_shapes.py A_100_scratch_s0 results/shapes_<stack>.jsonl [reps]
import os
import sys
import time

import numpy as np
import torch

from common import RUNS42, build, env_info, jsonl, predict, test_fold

name, out = sys.argv[1], sys.argv[2]
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 2
SIZES = [256, 150, 135, 7, 1]  # 256 first: #42's eval loop ran full batches before the odd one
torch.set_num_threads(16)
m, design, fs, init, T, w = build(name)
m.load_state_dict(torch.load(os.path.join(RUNS42, name + ".pt"), map_location="cpu"))
x, _, _ = test_fold(fs, init)
os.makedirs("refs", exist_ok=True)
ref_path = f"refs/{name}.cpu.npy"
if not os.path.exists(ref_path):
    t0 = time.time()
    np.save(ref_path, predict(m, design, init, T, w, x, torch.device("cpu"), 64))
    print(f"{name}: CPU reference in {time.time() - t0:.0f}s", flush=True)
ref = np.load(ref_path)
jsonl(out, {"probe": "start", "model": name, **env_info()})
dev = torch.device("cuda")
m.to(dev)
for rep in range(reps):
    for bs in SIZES:
        t0 = time.time()
        try:
            p = predict(m, design, init, T, w, x, dev, bs)
            err = None
        except Exception as e:  # noqa: BLE001 - a fault is a result here
            p, err = None, f"{type(e).__name__}: {e}"[:300]
        rec = {"probe": "shape", "model": name, "rep": rep, "bs": bs, "sec": time.time() - t0, "error": err}
        if p is not None:
            d = np.abs(p - ref).max(1)
            bad = np.where(~(d <= 1e-3))[0]  # NaN counts as bad
            rec |= {"max_abs": float(np.nanmax(d)), "nan_rows": int(np.isnan(p).any(1).sum()),
                    "bad_rows": len(bad), "bad_first": int(bad.min()) if len(bad) else None,
                    "bad_last": int(bad.max()) if len(bad) else None}
        jsonl(out, rec)
        print(rec, flush=True)
