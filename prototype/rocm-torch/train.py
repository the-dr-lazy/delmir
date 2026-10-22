# PROTOTYPE for #41, throwaway: a short real training loop of a small 1-D CNN,
# shaped like DELMIR's classifier (12 leads x 1000 samples, 10 s at 100 Hz,
# an OMI logit plus a 3-way culprit head), on synthetic data with a planted signal
# so the loss must fall. Usage: python train.py <cpu|cuda> <seconds> [--amp]
import sys, time
import torch, torch.nn as nn, torch.nn.functional as F

device, seconds, amp = sys.argv[1], float(sys.argv[2]), "--amp" in sys.argv
torch.manual_seed(0)

def block(i, o, s):
    return nn.Sequential(nn.Conv1d(i, o, 7, s, 3, bias=False), nn.BatchNorm1d(o), nn.ReLU(),
                         nn.Conv1d(o, o, 5, 1, 2, bias=False), nn.BatchNorm1d(o), nn.ReLU())

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.body = nn.Sequential(block(12, 64, 2), block(64, 128, 2), block(128, 128, 2), block(128, 256, 2))
        self.omi, self.vessel = nn.Linear(256, 1), nn.Linear(256, 3)
    def forward(self, x):
        h = F.adaptive_avg_pool1d(self.body(x), 1).flatten(1)
        return self.omi(h).squeeze(1), self.vessel(h)

def batch(n):
    x = torch.randn(n, 12, 1000, device=device)
    omi = (torch.rand(n, device=device) < 0.5)
    vessel = torch.randint(0, 3, (n,), device=device)
    # planted signal: an OMI raises a lead group's mean between samples 300 and 400
    for v, leads in enumerate(([1, 2, 3], [4, 5], [6, 7, 8])):
        m = (omi & (vessel == v)).float()[:, None, None]
        x[:, leads, 300:400] += 1.5 * m
    return x, omi.float(), torch.where(omi, vessel, torch.full_like(vessel, -100))

net = Net().to(device)
print("params", sum(p.numel() for p in net.parameters()))
opt = torch.optim.AdamW(net.parameters(), 1e-3)
scaler = torch.amp.GradScaler(enabled=amp)
bs = 256
while True:
    try:
        steps, seen, t0 = 0, 0, time.perf_counter()
        while time.perf_counter() - t0 < seconds:
            x, y, v = batch(bs)
            with torch.autocast(device_type="cuda" if device != "cpu" else "cpu", enabled=amp, dtype=torch.float16):
                lo, lv = net(x)
                loss = F.binary_cross_entropy_with_logits(lo.float(), y) + F.cross_entropy(lv.float(), v, ignore_index=-100)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            steps += 1; seen += bs
            if steps % 50 == 0 or steps == 1:
                if device != "cpu": torch.cuda.synchronize()
                print(f"step {steps} loss {loss.item():.4f} elapsed {time.perf_counter() - t0:.1f}s", flush=True)
            if not torch.isfinite(loss): raise SystemExit("non-finite loss")
        if device != "cpu": torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        break
    except torch.OutOfMemoryError:
        bs //= 2; torch.cuda.empty_cache(); print("OOM, batch size ->", bs)
        if bs < 8: raise
net.eval()
with torch.no_grad():
    x, y, v = batch(1024)
    lo, lv = net(x)
    acc = ((lo > 0).float() == y).float().mean().item()
    m = v >= 0
    vacc = (lv[m].argmax(1) == v[m]).float().mean().item()
print(f"RESULT device={device} amp={amp} bs={bs} steps={steps} seconds={dt:.1f} "
      f"samples/s={seen / dt:.0f} final_loss={loss.item():.4f} omi_acc={acc:.3f} vessel_acc={vacc:.3f}"
      + (f" peak_mem={torch.cuda.max_memory_allocated() / 2**30:.2f}GiB" if device != "cpu" else ""))
