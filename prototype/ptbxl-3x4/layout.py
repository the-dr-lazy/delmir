# PROTOTYPE (#42): turn synchronous 10 s PTB-XL records into the four input designs.
#
# The 3x4 printout (ECG-Image-Kit, extract_leads.py): column c holds leads 3c..3c+2 of PTB-XL's
# order (I II III | aVR aVL aVF | V1 V2 V3 | V4 V5 V6) for [2.5c, 2.5(c+1)) s, plus a 10 s lead II
# rhythm strip. Every function takes x: (B, 12, T) float tensor and present: (B, 12) bool.
import torch

LEAD_II = 1


def window(T):
    return T // 4


def roll(x, off):
    """Circular time shift per sample (training augmentation for A/B/C: new beats, same layout)."""
    T = x.shape[-1]
    idx = (torch.arange(T, device=x.device)[None, :] + off[:, None]) % T
    return torch.gather(x, 2, idx[:, None, :].expand(-1, x.shape[1], -1))


def column_mask(T, device=None):
    """(12, T) bool: where each lead is plotted on the 3x4 canvas."""
    w = window(T)
    m = torch.zeros(12, T, dtype=torch.bool, device=device)
    for lead in range(12):
        c = lead // 3
        m[lead, c * w:(c + 1) * w] = True
    return m


def design_S(x, present):
    return x * present[:, :, None]


def design_A(x, present):
    """Masked canvas: 12 lead channels zero outside their window, the rhythm strip, and 12 presence masks."""
    m = column_mask(x.shape[-1], x.device)[None] & present[:, :, None]
    canvas = x * m
    rhythm = x[:, LEAD_II:LEAD_II + 1]
    return torch.cat([canvas, rhythm, m.float()], 1)


def design_B(x, present):
    """Per-lead: lead i's own 2.5 s moved to [0, w), then the 10 s rhythm strip as channel 12.
    Returns (signal (B, 13, T), present (B, 13))."""
    w = window(x.shape[-1])
    out = torch.zeros(x.shape[0], 13, x.shape[-1], device=x.device)
    for lead in range(12):
        c = lead // 3
        out[:, lead, :w] = x[:, lead, c * w:(c + 1) * w]
    out[:, :12] *= present[:, :, None]
    out[:, 12] = x[:, LEAD_II]
    pres = torch.cat([present, torch.ones_like(present[:, :1])], 1)
    return out, pres


def design_C(x, present):
    """Pseudo-synchronous: every lead's 2.5 s shifted into one common window, (B, 12, w)."""
    w = window(x.shape[-1])
    out = torch.stack([x[:, lead, (lead // 3) * w:(lead // 3 + 1) * w] for lead in range(12)], 1)
    return out * present[:, :, None]


DESIGNS = {"S": design_S, "A": design_A, "B": design_B, "C": design_C}


def lead_dropout(B, gen, p=0.5, max_drop=4):
    """With probability p drop 1..max_drop random leads (CinC 2021 winner's recipe, milder)."""
    present = torch.ones(B, 12, dtype=torch.bool)
    for i in range(B):
        if torch.rand(1, generator=gen).item() < p:
            k = int(torch.randint(1, max_drop + 1, (1,), generator=gen))
            present[i, torch.randperm(12, generator=gen)[:k]] = False
    return present
