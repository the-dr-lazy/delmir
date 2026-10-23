# PROTOTYPE (#42, instrumented for #50): train one arm, keep the best-validation epoch, save val/test probabilities.
#   python train.py --design A --fs 100 --seed 0
#   python train.py --design C --fs 500 --seed 0 --init ecgfounder
# Folds 1-8 train, 9 validation (model selection), 10 test (strat_fold, patient-disjoint).
import argparse
import copy
import math
import subprocess
import json
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from layout import DESIGNS, lead_dropout, roll, window
from metrics import headline, task_aucs
from models import PerLead, XResNet1d
from prep import OUT, TARGETS

p = argparse.ArgumentParser()
p.add_argument("--design", choices="SABC", required=True)
p.add_argument("--fs", type=int, choices=[100, 500], default=100)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--init", choices=["scratch", "ecgfounder"], default="scratch")
p.add_argument("--epochs", type=int, default=30)
p.add_argument("--depth", default=None)
p.add_argument("--lr", type=float, default=None)
p.add_argument("--bs", type=int, default=128)
p.add_argument("--threads", type=int, default=8)
p.add_argument("--runs", default="runs")
p.add_argument("--tag", default="", help="appended to the init label, e.g. -e20")
p.add_argument("--pad", action="store_true", help="#42: pad every eval batch to full size")
p.add_argument("--parity", type=int, default=0, help="#50: val records recomputed on the CPU each epoch (0: all)")
a = p.parse_args()
torch.set_num_threads(a.threads)
torch.manual_seed(a.seed)
np.random.seed(a.seed)
gen = torch.Generator().manual_seed(a.seed)
name = f"{a.design}_{a.fs}_{a.init}{a.tag}_s{a.seed}"
os.makedirs(a.runs, exist_ok=True)

df = pd.read_csv(os.path.join(OUT, "labels.csv"))
X = np.load(os.path.join(OUT, f"X{a.fs}.npy"), mmap_mode="r")
Y = torch.tensor(df[TARGETS].values, dtype=torch.float32)
fold = df.strat_fold.values
tr, va, te = np.where(fold <= 8)[0], np.where(fold == 9)[0], np.where(fold == 10)[0]
T = X.shape[-1]
w = window(T)
ks = 5 if a.fs == 100 else 25

if a.init == "ecgfounder":
    from net1d import Net1D

    def norm(x):  # ECGFounder dataset.py: z-score over the whole record (all leads together)
        return (x - x.mean((1, 2), keepdim=True)) / (x.std((1, 2), keepdim=True) + 1e-8)
else:
    sub = np.asarray(X[tr[:2000]], dtype=np.float32)
    mu, sd = float(sub.mean()), float(sub.std())  # benchmark: one global StandardScaler

    def norm(x):
        return (x - mu) / sd


def build_model():
    if a.init == "ecgfounder":
        assert a.design in "SAC" and a.fs == 500, "ECGFounder is a 12-channel 500 Hz encoder"
        m = Net1D(in_channels=12, base_filters=64, ratio=1, filter_list=[64, 160, 160, 400, 400, 1024, 1024],
                  m_blocks_list=[2, 2, 2, 3, 3, 4, 4], kernel_size=16, stride=2, groups_width=16,
                  verbose=False, use_bn=False, use_do=False, n_classes=len(TARGETS))
        ck = torch.load(os.path.join(os.path.dirname(OUT), "..", "ecgfounder", "12_lead_ECGFounder.pth"),
                        map_location="cpu", weights_only=False)
        sd_ = {k: v for k, v in ck["state_dict"].items() if not k.startswith("dense.")}
        missing = m.load_state_dict(sd_, strict=False)
        print("ECGFounder load:", missing, flush=True)
        return m
    if a.design == "B":
        return PerLead(len(TARGETS), w, depth=a.depth or "xresnet1d18", ks=ks)
    c_in = {"S": 12, "A": 25, "C": 12}[a.design]
    return XResNet1d(c_in, len(TARGETS), depth=a.depth or "xresnet1d101", ks=ks)


model = build_model()
cpu_model = copy.deepcopy(model)  # #50: CPU twin for the parity checks
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # ROCm builds expose the GPU as cuda
if os.environ.get("DELMIR_NO_MIOPEN"):  # the ROCm wheel cannot JIT some MIOpen BatchNorm kernels (A at 500 Hz)
    torch.backends.cudnn.enabled = False
model.to(dev)
print("device:", dev, torch.cuda.get_device_name(0) if dev.type == "cuda" else "", flush=True)
n_params = sum(t.numel() for t in model.parameters())
is_ef = a.init == "ecgfounder"
# For ECGFounder arms A is the 12-channel masked canvas only (its first conv takes 12 channels).
design = DESIGNS[a.design]


def forward(x, present, mdl=model, d=dev):
    x, present = x.to(d, non_blocking=True), present.to(d)
    if a.design == "B":
        s, pr = design(x, present)
        return mdl(s, pr)
    z = design(x, present)
    if is_ef and a.design == "A":
        z = z[:, :12]
    return mdl(z)


def batch(idx):
    return norm(torch.from_numpy(np.asarray(X[np.sort(idx)], dtype=np.float32))), np.sort(idx)


@torch.no_grad()
def predict(idx, mdl=model, d=dev):
    mdl.eval()
    out = []
    pbs = 64 if a.design == "B" else 256
    for i in range(0, len(idx), pbs):
        x, _ = batch(idx[i:i + pbs])
        n = x.shape[0]
        # ROCm 7.2 on the RX 6600 XT returns garbage for some odd batch shapes (the last, partial
        # batch); pad every batch to the full size and drop the padding.
        if a.pad:
            x = torch.cat([x, x.new_zeros(pbs - n, *x.shape[1:])])
        present = torch.ones(x.shape[0], 12, dtype=torch.bool)
        if a.design == "S":  # benchmark: 2.5 s windows, stride half a window, max over windows
            ps = [torch.sigmoid(forward(x[:, :, s:s + w], present, mdl, d)) for s in range(0, T - w + 1, w // 2)]
            out.append(torch.stack(ps).amax(0)[:n])
        else:
            out.append(torch.sigmoid(forward(x, present, mdl, d))[:n])
    return torch.cat(out).cpu().numpy()


def cpu_parity(gpu_pred, idx):
    """#50: the same records through the CPU twin; worst |dprob| and records off by > 1e-3."""
    cpu_model.load_state_dict({k: v.cpu() for k, v in model.state_dict().items()})
    c = predict(idx, cpu_model, torch.device("cpu"))
    dd = np.abs(gpu_pred - c).max(1)
    return c, {"max_abs": float(np.nanmax(dd)), "bad": int((~(dd <= 1e-3)).sum()),
               "nan": int(np.isnan(gpu_pred).any(1).sum())}


def gpu_stats():
    out = subprocess.run(["rocm-smi", "-d", "0", "--showtemp", "--showpower", "--showclocks"],
                         capture_output=True, text=True).stdout
    get = lambda key: next((l.split(":")[-1].strip() for l in out.splitlines() if key in l), "?")
    return {"junction": get("junction"), "power": get("Package Power"), "sclk": get("sclk clock level")}


lr = a.lr or (1e-3 if is_ef else 1e-2)
opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
steps = a.epochs * (len(tr) // a.bs)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps)
loss_fn = nn.BCEWithLogitsLoss()
hs = df.has_super.values.astype(bool)
Yn = df[TARGETS].values
best, best_state, best_ep, log, start = -1, None, -1, [], 0
ckpt = os.path.join(a.runs, name + ".ckpt")
if os.path.exists(ckpt):  # resume after a kill (the shared host OOM-kills under memory pressure)
    c = torch.load(ckpt, map_location="cpu", weights_only=False)
    model.load_state_dict(c["model"])
    opt.load_state_dict(c["opt"])
    sched.load_state_dict(c["sched"])
    gen.set_state(c["gen"])
    torch.set_rng_state(c["torch_rng"])
    best, best_state, best_ep, log, start = c["best"], c["best_state"], c["best_ep"], c["log"], c["ep"] + 1
    print(f"resumed at epoch {start}", flush=True)
for ep in range(start, a.epochs):
    model.train()
    t0 = time.time()
    perm = tr[torch.randperm(len(tr), generator=gen).numpy()]
    tot, nonfinite = 0.0, 0
    for i in range(len(tr) // a.bs):
        x, idx = batch(perm[i * a.bs:(i + 1) * a.bs])
        B = x.shape[0]
        if a.design == "S":  # benchmark: random 2.5 s crop of the synchronous 10 s
            st = torch.randint(0, T - w + 1, (B,), generator=gen)
            x = torch.gather(x, 2, (st[:, None] + torch.arange(w)[None])[:, None, :].expand(-1, 12, -1))
        else:  # same 3x4 layout over a circularly shifted record: new beats, same plot geometry
            x = roll(x, torch.randint(0, T, (B,), generator=gen))
        present = lead_dropout(B, gen)
        loss = loss_fn(forward(x, present), Y[idx].to(dev))
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        li = loss.item()
        nonfinite += not math.isfinite(li)
        tot += li
    t_ep = time.time() - t0
    pv = predict(va)
    pidx = va if a.parity == 0 else va[:a.parity]
    _, par = cpu_parity(pv[:len(pidx)], pidx)
    score = headline(Yn[va], pv, hs[va])
    log.append({"epoch": ep, "loss": tot / (len(tr) // a.bs), "val": score, "sec": t_ep,
                "nonfinite_steps": nonfinite, "val_parity": par, "gpu": gpu_stats()})
    print(json.dumps(log[-1]), flush=True)
    if best_state is None or score > best:
        best, best_state, best_ep = score, {k: v.clone() for k, v in model.state_dict().items()}, ep
    torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                "gen": gen.get_state(), "torch_rng": torch.get_rng_state(), "best": best,
                "best_state": best_state, "best_ep": best_ep, "log": log, "ep": ep}, ckpt + ".tmp")
    os.replace(ckpt + ".tmp", ckpt)

model.load_state_dict(best_state)
pv, pt = predict(va), predict(te)
pt_cpu, test_par = cpu_parity(pt, te)  # #50: the whole test fold recomputed on the CPU
torch.save(best_state, os.path.join(a.runs, name + ".pt"))
np.savez(os.path.join(a.runs, name + ".npz"), val=pv, test=pt, test_cpu=pt_cpu)
res = {"name": name, **vars(a), "params": n_params, "best_epoch": best_ep, "best_val": best,
       "sec_per_epoch": float(np.mean([r["sec"] for r in log])), "log": log,
       "env": {k: v for k, v in os.environ.items() if k.startswith(("HSA_", "ROCR_", "AMD_", "MIOPEN_", "PYTORCH_", "DELMIR_"))},
       "torch": torch.__version__, "test_parity": test_par,
       "test": {k: v for k, v in task_aucs(Yn[te], pt, hs[te]).items()},
       "test_cpu": {k: v for k, v in task_aucs(Yn[te], pt_cpu, hs[te]).items()}}
json.dump(res, open(os.path.join(a.runs, name + ".json"), "w"), default=float, indent=1)
print("TEST", json.dumps(res["test"], default=float), flush=True)
