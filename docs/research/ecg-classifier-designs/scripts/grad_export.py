import os, sys, time, numpy as np, torch, torch.nn as nn, onnxruntime as ort
sys.path.insert(0, os.getcwd())
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from xres_count import xresnet1d
base = xresnet1d(4, [3, 4, 23, 3], lin_ftrs=[128], n_out=1).eval()
class IGGraph(nn.Module):
    def __init__(s, m, steps=16): super().__init__(); s.m, s.steps = m, steps
    def forward(s, x):
        a = torch.linspace(1.0/s.steps, 1.0, s.steps).view(-1, 1, 1)
        xs = (a * x).requires_grad_(True)           # zero baseline
        y = s.m(xs).sum()
        g, = torch.autograd.grad(y, xs)
        return (x * g.mean(0, keepdim=True)).sum(-1)  # per-lead IG (1,12)
x = torch.randn(1, 12, 1000)
for dyn in (True, False):
    try:
        torch.onnx.export(IGGraph(base), (x,), f"ig_{dyn}.onnx", dynamo=dyn, **({"external_data": False} if dyn else {}))
        print("IG export dynamo=%s OK" % dyn)
    except Exception as e:
        print("IG export dynamo=%s FAILED: %s: %s" % (dyn, type(e).__name__, str(e).splitlines()[0][:200]))
# Lead ablation as one batched forward of 13 (original + 12 leads zeroed)
base.eval(); torch.onnx.export(base, (x,), "xres_b.onnx", dynamo=True, external_data=False,
                  dynamic_shapes=({0: torch.export.Dim("batch", min=1, max=64)},))
so = ort.SessionOptions(); so.intra_op_num_threads = 1
s = ort.InferenceSession("xres_b.onnx", so, providers=["CPUExecutionProvider"])
nm = s.get_inputs()[0].name
xb = np.repeat(x.numpy(), 13, 0)
for i in range(12): xb[i+1, i, :] = 0
for b in (1, 13):
    xi = xb[:b]
    for _ in range(3): s.run(None, {nm: xi})
    t = time.perf_counter(); n = 10
    for _ in range(n): s.run(None, {nm: xi})
    print(f"batch {b}: {(time.perf_counter()-t)/n*1000:.1f} ms")
