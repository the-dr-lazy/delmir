# PROTOTYPE (#42): throwaway models for the 3x4 input-design spike. Never merged.
#
# xresnet1d follows helme/ecg_ptbxl_benchmarking (fastai xresnet1d, kernel 5, stem 32-32-64,
# concat-pool head with one 128 hidden layer). PerLead is design B: one shared CNN per lead's
# 2.5 s, plus a lead embedding, fused by one small transformer layer (Herman 2024 style).
import torch
import torch.nn as nn


def conv(ni, nf, ks, stride=1, act=True, zero=False):
    bn = nn.BatchNorm1d(nf)
    if zero:
        nn.init.zeros_(bn.weight)
    layers = [nn.Conv1d(ni, nf, ks, stride=stride, padding=(ks - 1) // 2, bias=False), bn]
    if act:
        layers.append(nn.ReLU(inplace=True))
    return nn.Sequential(*layers)


class ResBlock(nn.Module):
    def __init__(self, expansion, ni, nh, stride, ks):
        super().__init__()
        nf, ni = nh * expansion, ni * expansion
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


DEPTHS = {"xresnet1d101": [3, 4, 23, 3], "xresnet1d50": [3, 4, 6, 3], "xresnet1d18": [2, 2, 2, 2]}


def xresnet1d_body(c_in, layers, ks=5, expansion=4):
    stem = [c_in, 32, 32, 64]
    m = [conv(stem[i], stem[i + 1], ks, stride=2 if i == 0 else 1) for i in range(3)]
    bs = [64 // expansion, 64, 64, 64, 64]
    m.append(nn.MaxPool1d(3, 2, 1))
    for i, n in enumerate(layers):
        m.append(nn.Sequential(*[
            ResBlock(expansion, bs[i] if j == 0 else bs[i + 1], bs[i + 1], 1 if (i == 0 or j > 0) else 2, ks)
            for j in range(n)
        ]))
    return nn.Sequential(*m), bs[-1] * expansion


def head(nf, n_out, hidden=128):
    return nn.Sequential(
        nn.BatchNorm1d(nf), nn.Dropout(0.5), nn.Linear(nf, hidden), nn.ReLU(inplace=True),
        nn.BatchNorm1d(hidden), nn.Dropout(0.5), nn.Linear(hidden, n_out),
    )


class XResNet1d(nn.Module):
    """Designs S, A and C: an ordinary multichannel 1D CNN."""

    def __init__(self, c_in, n_out, depth="xresnet1d101", ks=5):
        super().__init__()
        self.body, nf = xresnet1d_body(c_in, DEPTHS[depth], ks)
        self.pool = ConcatPool()
        self.head = head(2 * nf, n_out)

    def forward(self, x):
        return self.head(self.pool(self.body(x)))


class PerLead(nn.Module):
    """Design B. x: (batch, 13, T) with leads 0..11 each holding its own 2.5 s in [:, :, :T_lead]
    and channel 12 the 10 s lead-II rhythm strip; present: (batch, 13) bool."""

    def __init__(self, n_out, t_lead, depth="xresnet1d50", ks=5, d=128):
        super().__init__()
        self.t_lead = t_lead
        self.body, nf = xresnet1d_body(1, DEPTHS[depth], ks)
        self.pool = ConcatPool()
        self.proj = nn.Linear(2 * nf, d)
        self.lead_emb = nn.Parameter(torch.zeros(13, d))
        nn.init.normal_(self.lead_emb, std=0.02)
        self.fuse = nn.TransformerEncoderLayer(d, 4, 2 * d, dropout=0.1, batch_first=True)
        self.head = head(2 * d, n_out)

    def forward(self, x, present):
        b = x.shape[0]
        leads = x[:, :12, : self.t_lead].reshape(b * 12, 1, self.t_lead)
        rhythm = x[:, 12:13, :]
        z = torch.cat([
            self.pool(self.body(leads)).reshape(b, 12, -1),
            self.pool(self.body(rhythm)).reshape(b, 1, -1),
        ], 1)
        z = self.proj(z) + self.lead_emb
        z = self.fuse(z, src_key_padding_mask=~present)
        m = present.unsqueeze(-1).float()
        mean = (z * m).sum(1) / m.sum(1).clamp(min=1)
        mx = z.masked_fill(~present.unsqueeze(-1), -1e4).amax(1)
        return self.head(torch.cat([mx, mean], 1))
