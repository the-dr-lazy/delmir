# PROTOTYPE for #41, throwaway: which devices does torch see, and do BLAS and MIOpen run?
import os, sys, time
import torch

print("env:", {k: os.environ.get(k) for k in ("HSA_OVERRIDE_GFX_VERSION", "HSA_OVERRIDE_GFX_VERSION_1", "HSA_OVERRIDE_GFX_VERSION_2", "ROCR_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES")})
print("torch", torch.__version__, "hip", torch.version.hip)
print("is_available", torch.cuda.is_available(), "device_count", torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(f"  cuda:{i}", p.name, p.gcnArchName, f"{p.total_memory / 2**30:.1f} GiB", "CUs", p.multi_processor_count)
if not torch.cuda.is_available():
    sys.exit(0)

def timed(f):
    torch.cuda.synchronize(); t = time.perf_counter(); r = f(); torch.cuda.synchronize()
    return r, time.perf_counter() - t

for i in range(torch.cuda.device_count()):
    d = f"cuda:{i}"
    try:
        x = torch.randn(4096, 4096, device=d)
        timed(lambda: x @ x)
        _, s = timed(lambda: [x @ x for _ in range(20)])
        print(f"{d} matmul fp32 TFLOP/s: {20 * 2 * 4096**3 / s / 1e12:.2f}")
        xh = x.half()
        timed(lambda: xh @ xh)
        _, s = timed(lambda: [xh @ xh for _ in range(20)])
        print(f"{d} matmul fp16 TFLOP/s: {20 * 2 * 4096**3 / s / 1e12:.2f}")
        c = torch.nn.Conv1d(12, 64, 7).to(d)
        b = torch.randn(32, 12, 5000, device=d)
        y, s1 = timed(lambda: c(b))
        _, s2 = timed(lambda: c(b))
        print(f"{d} conv1d {tuple(y.shape)} first {s1 * 1e3:.0f} ms, second {s2 * 1e3:.1f} ms")
        ref = torch.nn.functional.conv1d(b.cpu(), c.weight.cpu(), c.bias.cpu())
        print(f"{d} conv1d max |gpu - cpu|: {(y.cpu() - ref).abs().max().item():.2e}")
    except Exception as e:
        print(f"{d} FAILED: {type(e).__name__}: {e}")
