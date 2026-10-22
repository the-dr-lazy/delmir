# PROTOTYPE (#42): after an undervolt, load the GPU like training does and look for silent errors.
#   python gpu_stability.py [minutes]
# Training steps (xresnet1d101 on 25 x 1000, the A design) keep the GPU busy. Every ~20 s it checks
#   - a fixed eval-mode forward pass against its first GPU result and against the CPU result, and
#   - a 4096^2 fp32 matmul against a float64 CPU reference,
# logs junction temperature, power and clock, and aborts above 108 C.
import subprocess
import sys
import time

import torch

from models import XResNet1d

minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 10
torch.manual_seed(0)
dev = torch.device("cuda")


def smi():
    out = subprocess.run(["rocm-smi", "-d", "0", "--showtemp", "--showpower", "--showclocks"],
                         capture_output=True, text=True).stdout
    get = lambda key: next((l.split(":")[-1].strip() for l in out.splitlines() if key in l), "?")
    return float(get("junction")), get("Package Power"), get("sclk clock level").split("(")[-1].rstrip(")")


m = XResNet1d(25, 12).to(dev)
opt = torch.optim.AdamW(m.parameters(), 1e-3)
probe = XResNet1d(25, 12).eval()
xp = torch.randn(64, 25, 1000)
with torch.no_grad():
    ref_cpu = probe(xp)
probe_gpu = XResNet1d(25, 12).eval().to(dev)
probe_gpu.load_state_dict(probe.state_dict())
with torch.no_grad():
    ref_gpu = probe_gpu(xp.to(dev)).cpu()
a, b = torch.randn(4096, 4096), torch.randn(4096, 4096)
mm_ref = (a.double() @ b.double()).float()
ag, bg = a.to(dev), b.to(dev)
xb, yb = torch.randn(128, 25, 1000, device=dev), torch.rand(128, 12, device=dev).round()
print(f"start: GPU vs CPU forward max|d| = {(ref_gpu - ref_cpu).abs().max():.2e}", flush=True)

t0, last, steps, worst_t, bad = time.time(), 0, 0, 0.0, 0
while time.time() - t0 < minutes * 60:
    loss = torch.nn.functional.binary_cross_entropy_with_logits(m(xb), yb)
    opt.zero_grad()
    loss.backward()
    opt.step()
    steps += 1
    if not torch.isfinite(loss):
        print("NON-FINITE LOSS", flush=True)
        bad += 1
    if time.time() - last > 20:
        last = time.time()
        with torch.no_grad():
            out = probe_gpu(xp.to(dev)).cpu()
            mm = (ag @ bg).cpu()
        d_rep = (out - ref_gpu).abs().max().item()
        d_cpu = (out - ref_cpu).abs().max().item()
        d_mm = ((mm - mm_ref).abs().max() / mm_ref.abs().max()).item()
        temp, power, clk = smi()
        worst_t = max(worst_t, temp)
        ok = d_rep < 1e-5 and d_cpu < 1e-4 and d_mm < 1e-4
        bad += not ok
        print(f"{time.time() - t0:5.0f}s steps={steps:5d} junction={temp:.0f}C power={power}W sclk={clk} "
              f"repeat={d_rep:.1e} vsCPU={d_cpu:.1e} matmul_rel={d_mm:.1e} {'ok' if ok else 'MISMATCH'}", flush=True)
        if temp >= 108:
            print("ABORT: junction >= 108 C", flush=True)
            break
print(f"END steps={steps} worst_junction={worst_t:.0f}C mismatches={bad}", flush=True)
