# PROTOTYPE (#50): shared bits for the GPU-trust probes. Build a #42 arm from its checkpoint name,
# load the test fold normalised the way #42 trained it, and run eval forwards at a chosen batch size.
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import torch

from layout import DESIGNS, window
from models import PerLead, XResNet1d
from prep import OUT, TARGETS

torch.backends.mha.set_fastpath_enabled(False)
RUNS42 = os.environ.get("RUNS42", os.path.expanduser(
    "~/workspaces/delmir/.claude/worktrees/epic-neumann-0e9eaf/prototype/ptbxl-3x4/runs"))


def env_info():
    """Stack, env vars and the GPU's clock/voltage table, for every results file."""
    od = open("/sys/class/drm/card1/device/pp_od_clk_voltage").read().split()
    return {"python": sys.executable, "torch": torch.__version__, "hip": torch.version.hip,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "env": {k: v for k, v in os.environ.items()
                    if k.startswith(("HSA_", "ROCR_", "AMD_", "HIP_", "MIOPEN_", "DELMIR_", "PYTORCH_"))},
            "od": " ".join(od)}


def build(name):
    """name like A_100_scratch_s0 -> (model, design, fs, init, T, w)."""
    design, fs, init = name.rsplit("_s", 1)[0].split("_")
    fs = int(fs)
    T, ks = (1000, 5) if fs == 100 else (5000, 25)
    w = window(T)
    if init == "ecgfounder":
        from net1d import Net1D
        m = Net1D(in_channels=12, base_filters=64, ratio=1, filter_list=[64, 160, 160, 400, 400, 1024, 1024],
                  m_blocks_list=[2, 2, 2, 3, 3, 4, 4], kernel_size=16, stride=2, groups_width=16,
                  verbose=False, use_bn=False, use_do=False, n_classes=len(TARGETS))
    elif design == "B":
        m = PerLead(len(TARGETS), w, depth="xresnet1d18", ks=ks)
    else:
        m = XResNet1d({"S": 12, "A": 25, "C": 12}[design], len(TARGETS), ks=ks)
    return m, design, fs, init, T, w


def test_fold(fs, init):
    df = pd.read_csv(os.path.join(OUT, "labels.csv"))
    te = np.where(df.strat_fold.values == 10)[0]
    tr = np.where(df.strat_fold.values <= 8)[0]
    X = np.load(os.path.join(OUT, f"X{fs}.npy"), mmap_mode="r")
    x = torch.from_numpy(np.asarray(X[te], dtype=np.float32))
    if init == "ecgfounder":
        x = (x - x.mean((1, 2), keepdim=True)) / (x.std((1, 2), keepdim=True) + 1e-8)
    else:
        sub = np.asarray(X[tr[:2000]], dtype=np.float32)
        x = (x - float(sub.mean())) / float(sub.std())
    return x, df[TARGETS].values[te], df.has_super.values.astype(bool)[te]


def design_input(design, init, x, present):
    if design == "B":
        return DESIGNS["B"](x, present)
    z = DESIGNS[design](x, present)
    return (z[:, :12],) if (init == "ecgfounder" and design == "A") else (z,)


@torch.no_grad()
def predict(m, design, init, T, w, x, dev, bs, pad=False):
    """#42's eval loop: batches of bs over x in order, the last one partial unless pad."""
    m.eval()
    out = []
    for i in range(0, len(x), bs):
        xb = x[i:i + bs]
        n = xb.shape[0]
        if pad:
            xb = torch.cat([xb, xb.new_zeros(bs - n, *xb.shape[1:])])
        xb = xb.to(dev)
        pr = torch.ones(xb.shape[0], 12, dtype=torch.bool, device=dev)
        if design == "S":  # 2.5 s windows, stride half a window, max over windows
            ps = [torch.sigmoid(m(*design_input("S", init, xb[:, :, s:s + w], pr))) for s in range(0, T - w + 1, w // 2)]
            out.append(torch.stack(ps).amax(0)[:n].cpu())
        else:
            out.append(torch.sigmoid(m(*design_input(design, init, xb, pr)))[:n].cpu())
    return torch.cat(out).numpy()


def jsonl(path, rec):
    with open(path, "a") as f:
        f.write(json.dumps(rec, default=float) + "\n")
