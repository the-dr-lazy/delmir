# PROTOTYPE (#42): per arm (seed 0 checkpoint) params, GFLOP per reading, desktop ONNX Runtime CPU
# latency (one pass; the 13-pass lead-ablation batch), and agreement between lead ablation and Captum
# integrated gradients summed per lead (Spearman rho, MI head, test-fold MI records).
#   python deploy.py runs/A_100_scratch_s0.pt [...]  > deploy.md
import os
import sys
import time

import numpy as np
import onnxruntime as ort
import pandas as pd
import torch
from captum.attr import IntegratedGradients
from scipy.stats import spearmanr
from torch.utils.flop_counter import FlopCounterMode

from layout import DESIGNS, window
from models import PerLead, XResNet1d
from prep import OUT, TARGETS

torch.backends.mha.set_fastpath_enabled(False)  # plain ops, so the transformer layer exports to ONNX
torch.set_num_threads(8)
MI = TARGETS.index("MI")
N_ATTR = int(os.environ.get("N_ATTR", 200))
df = pd.read_csv(os.path.join(OUT, "labels.csv"))


def build(design, fs, init):
    T, ks = (1000, 5) if fs == 100 else (5000, 25)
    w = window(T)
    if init == "ecgfounder":
        from net1d import Net1D
        return Net1D(in_channels=12, base_filters=64, ratio=1, filter_list=[64, 160, 160, 400, 400, 1024, 1024],
                     m_blocks_list=[2, 2, 2, 3, 3, 4, 4], kernel_size=16, stride=2, groups_width=16,
                     verbose=False, use_bn=False, use_do=False, n_classes=len(TARGETS)), T, w
    if design == "B":
        return PerLead(len(TARGETS), w, depth="xresnet1d18", ks=ks), T, w
    return XResNet1d({"S": 12, "A": 25, "C": 12}[design], len(TARGETS), ks=ks), T, w


class Reader(torch.nn.Module):
    """One forward pass on the design's own input tensor(s); for B a second input marks present leads."""

    def __init__(self, m, design):
        super().__init__()
        self.m, self.design = m, design

    def forward(self, x, present=None):
        return self.m(x, present) if self.design == "B" else self.m(x)


def design_input(design, init, x, present):
    if design == "S":
        z = DESIGNS["S"](x, present)
        return (z,)
    if design == "B":
        return DESIGNS["B"](x, present)
    z = DESIGNS[design](x, present)
    return (z[:, :12],) if (init == "ecgfounder" and design == "A") else (z,)


def latency(sess, feeds, n=30):
    for _ in range(3):
        sess.run(None, feeds)
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        sess.run(None, feeds)
        t.append(time.perf_counter() - t0)
    return 1000 * float(np.median(t))


print("| arm | params | GFLOP/reading | ORT 1 pass ms (1 thr / 8 thr) | ORT 13-pass ablation ms (1 thr / 8 thr) | ablation-vs-IG Spearman ρ median [IQR] |")
print("|---|---|---|---|---|---|")
for ck in sys.argv[1:]:
    arm = os.path.basename(ck).rsplit("_s", 1)[0]
    design, fs, init = arm.split("_")
    fs = int(fs)
    m, T, w = build(design, fs, init)
    m.load_state_dict(torch.load(ck, map_location="cpu"))
    m.eval()
    R = Reader(m, design).eval()
    X = np.load(os.path.join(OUT, f"X{fs}.npy"), mmap_mode="r")
    tr = np.where(df.strat_fold.values <= 8)[0]
    if init == "ecgfounder":
        def norm(x):
            return (x - x.mean((1, 2), keepdim=True)) / (x.std((1, 2), keepdim=True) + 1e-8)
    else:
        sub = np.asarray(X[tr[:2000]], dtype=np.float32)
        mu, sd = float(sub.mean()), float(sub.std())

        def norm(x):
            return (x - mu) / sd

    # S reads a 10 s record as 7 overlapping 2.5 s windows (max-aggregated); the others in one pass.
    passes = 7 if design == "S" else 1
    x1 = torch.randn(1, 12, w if design == "S" else T)
    ins = design_input(design, init, x1, torch.ones(1, 12, dtype=torch.bool))
    with FlopCounterMode(display=False) as fc:
        R(*ins)
    gflop = passes * fc.get_total_flops() / 1e9
    path = os.path.join("onnx", arm + ".onnx")
    os.makedirs("onnx", exist_ok=True)
    names = ["x", "present"][:len(ins)]
    torch.onnx.export(R, ins, path, input_names=names, output_names=["logits"], opset_version=17,
                      dynamic_axes={n: {0: "b"} for n in names + ["logits"]}, dynamo=False)
    # 13-pass ablation batch: the full reading plus each of the 12 leads dropped.
    pres13 = torch.ones(13, 12, dtype=torch.bool)
    for i in range(12):
        pres13[i + 1, i] = False
    x13 = torch.randn(13, 12, w if design == "S" else T)
    ins13 = design_input(design, init, x13, pres13)
    if design == "S":
        ins13 = (ins13[0].repeat(passes, 1, 1),)
        ins1 = (ins[0].repeat(passes, 1, 1),)
    else:
        ins1 = ins
    lat = {}
    for thr in (1, 8):
        so = ort.SessionOptions()
        so.intra_op_num_threads = thr
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
        sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
        f1 = {n: t.numpy() for n, t in zip(names, ins1)}
        f13 = {n: t.numpy() for n, t in zip(names, ins13)}
        lat[thr] = (latency(sess, f1), latency(sess, f13, 10))
    # ORT agrees with PyTorch?
    with torch.no_grad():
        ref = R(*ins1).numpy()
    got = sess.run(None, {n: t.numpy() for n, t in zip(names, ins1)})[0]
    agree = np.abs(ref - got).max()

    # Lead ablation vs integrated gradients, MI logit, on test MI records (first window for S).
    te = np.where((df.strat_fold.values == 10) & (df.MI.values == 1))[0][:N_ATTR]
    x = norm(torch.from_numpy(np.asarray(X[te], dtype=np.float32)))
    if design == "S":
        x = x[:, :, :w]
    rhos = []
    for i in range(0, len(te), 25):
        xb = x[i:i + 25]
        B = xb.shape[0]
        full = torch.ones(B, 12, dtype=torch.bool)
        with torch.no_grad():
            base = R(*design_input(design, init, xb, full))[:, MI]
            abl = []
            for lead in range(12):
                p = full.clone()
                p[:, lead] = False
                abl.append(base - R(*design_input(design, init, xb, p))[:, MI])
            abl = torch.stack(abl, 1).numpy()
        z = design_input(design, init, xb, full)
        if design == "B":
            ig = IntegratedGradients(lambda s, pr: R(s, pr)[:, MI]).attribute(
                z[0], additional_forward_args=(z[1],), n_steps=32, internal_batch_size=25)
            per = ig[:, :12].sum(-1)
        else:
            ig = IntegratedGradients(lambda s: R(s)[:, MI]).attribute(z[0], n_steps=32, internal_batch_size=25)
            per = ig[:, :12].sum(-1)
            if design == "A" and init != "ecgfounder":
                per = per + ig[:, 13:25].sum(-1)  # ablation also clears the lead's presence mask
        per = per.detach().numpy()
        rhos += [spearmanr(abl[j], per[j]).statistic for j in range(B)]
    q = np.nanpercentile(rhos, [25, 50, 75])
    n_params = sum(t.numel() for t in m.parameters())
    print(f"| {arm} | {n_params / 1e6:.2f} M | {gflop:.2f} | {lat[1][0]:.1f} / {lat[8][0]:.1f} | "
          f"{lat[1][1]:.1f} / {lat[8][1]:.1f} | {q[1]:.2f} [{q[0]:.2f}, {q[2]:.2f}] |  <!-- ORT max|Δlogit| {agree:.1e} -->",
          flush=True)
