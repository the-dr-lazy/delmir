# Re-implementation of helme/ecg_ptbxl_benchmarking xresnet1d (per WebFetch description) to count params/FLOPs.
import torch, torch.nn as nn
from torch.utils.flop_counter import FlopCounterMode

def conv(ni, nf, ks, stride=1, act=True, zero=False):
    bn = nn.BatchNorm1d(nf)
    if zero: nn.init.zeros_(bn.weight)
    layers = [nn.Conv1d(ni, nf, ks, stride=stride, padding=(ks-1)//2, bias=False), bn]
    if act: layers.append(nn.ReLU(inplace=True))
    return nn.Sequential(*layers)

class ResBlock(nn.Module):
    def __init__(self, expansion, ni, nh, stride, ks):
        super().__init__()
        nf, ni = nh*expansion, ni*expansion
        if expansion == 1:
            self.convs = nn.Sequential(conv(ni, nh, ks, stride), conv(nh, nf, ks, act=False, zero=True))
        else:
            self.convs = nn.Sequential(conv(ni, nh, 1), conv(nh, nh, ks, stride), conv(nh, nf, 1, act=False, zero=True))
        self.idconv = nn.Identity() if ni == nf else conv(ni, nf, 1, act=False)
        self.pool = nn.Identity() if stride == 1 else nn.AvgPool1d(2, ceil_mode=True)
        self.act = nn.ReLU(inplace=True)
    def forward(self, x):
        return self.act(self.convs(x) + self.idconv(self.pool(x)))

class ConcatPool(nn.Module):
    def forward(self, x):
        return torch.cat([x.amax(-1), x.mean(-1)], 1)

def xresnet1d(expansion, layers, c_in=12, n_out=1, ks=5, ks_stem=5, stem=(32, 32, 64), lin_ftrs=None, widen=1.0):
    st = [c_in, *stem]
    m = [conv(st[i], st[i+1], ks_stem, stride=2 if i == 0 else 1) for i in range(3)]
    bs = [int(o*widen) for o in [64, 64, 64, 64] + [32]*(len(layers)-4)]
    bs = [64//expansion] + bs
    m.append(nn.MaxPool1d(3, 2, 1))
    for i, l in enumerate(layers):
        blocks = [ResBlock(expansion, bs[i] if j == 0 else bs[i+1], bs[i+1], 1 if (i == 0 or j > 0) else 2, ks) for j in range(l)]
        m.append(nn.Sequential(*blocks))
    nf = bs[-1]*expansion
    head = [ConcatPool(), nn.Flatten()]
    ftrs = [2*nf] + (lin_ftrs or []) + [n_out]
    for a, b in zip(ftrs[:-1], ftrs[1:]):
        head += [nn.BatchNorm1d(a), nn.Dropout(0.5), nn.Linear(a, b)]
        if b != n_out: head.append(nn.ReLU(inplace=True))
    m += head
    return nn.Sequential(*m)

def act_elems(model, x):
    tot = [0]
    hooks = [mod.register_forward_hook(lambda mod, i, o: tot.__setitem__(0, tot[0] + o.numel()))
             for mod in model.modules() if isinstance(mod, (nn.Conv1d, nn.BatchNorm1d, nn.ReLU, nn.AvgPool1d, nn.MaxPool1d))]
    model(x)
    for h in hooks: h.remove()
    return tot[0]

cfgs = {
    "xresnet1d101": (4, [3, 4, 23, 3], 5),
    "xresnet1d50": (4, [3, 4, 6, 3], 5),
    "xresnet1d101_ks25": (4, [3, 4, 23, 3], 25),
}
for name, (e, layers, ks) in cfgs.items():
    m = xresnet1d(e, layers, ks=ks, ks_stem=ks, lin_ftrs=[128], n_out=4).eval()
    p = sum(t.numel() for t in m.parameters())
    print(f"{name}: params={p:,}  fp32={p*4/1e6:.2f} MB  int8~{p/1e6:.2f} MB")
    for L, label in [(250, "2.5s@100Hz"), (1000, "10s@100Hz"), (2500, "5s@500Hz"), (5000, "10s@500Hz")]:
        x = torch.randn(1, 12, L)
        with FlopCounterMode(display=False) as fc:
            m(x)
        a = act_elems(m, x)
        print(f"  L={L:5d} ({label}): FLOPs={fc.get_total_flops()/1e9:.3f} GFLOP (MACs={fc.get_total_flops()/2e9:.3f} G), activation elems/sample={a/1e6:.2f}M -> {a*4/1e6:.1f} MB fp32/sample")
