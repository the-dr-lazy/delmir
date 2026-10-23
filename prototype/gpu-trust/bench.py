# PROTOTYPE (#50): training throughput of xresnet1d101 on design A, alone on the GPU, to price
# AMD_SERIALIZE_KERNEL=3. MIOpen stays on, so at 500 Hz (25 x 5000) the first step also shows
# whether the stack can JIT its BatchNorm kernels (the #42 wheel could not).
#   python bench.py 100|500 results/bench.jsonl [steps]
import sys
import time

import torch

from common import env_info, jsonl
from models import XResNet1d

fs, out = int(sys.argv[1]), sys.argv[2]
steps = int(sys.argv[3]) if len(sys.argv) > 3 else 150
T, ks, bs = (1000, 5, 128) if fs == 100 else (5000, 25, 128)
torch.manual_seed(0)
dev = torch.device("cuda")
m = XResNet1d(25, 12, ks=ks).to(dev)
opt = torch.optim.AdamW(m.parameters(), 1e-3)
x, y = torch.randn(bs, 25, T, device=dev), torch.rand(bs, 12, device=dev).round()
t0 = time.time()
times = []
for i in range(steps):
    t = time.time()
    loss = torch.nn.functional.binary_cross_entropy_with_logits(m(x), y)
    opt.zero_grad()
    loss.backward()
    opt.step()
    torch.cuda.synchronize()
    times.append(time.time() - t)
warm = times[10:]
rec = {"probe": "bench", "fs": fs, "bs": bs, "steps": steps, "first_step_s": times[0],
       "samples_per_s": bs * len(warm) / sum(warm), "loss_finite": bool(torch.isfinite(loss)),
       "peak_gib": torch.cuda.max_memory_allocated() / 2**30, **env_info()}
jsonl(out, rec)
print({k: rec[k] for k in ("fs", "first_step_s", "samples_per_s", "loss_finite", "peak_gib")}, flush=True)
