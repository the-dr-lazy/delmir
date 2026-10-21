import time, numpy as np, onnxruntime as ort, onnx
from collections import Counter
for f in ("xres101.onnx", "xres101_qdq.onnx"):
    so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.optimized_model_filepath = f.replace(".onnx", ".opt.onnx")
    s = ort.InferenceSession(f, so, providers=["CPUExecutionProvider"])
    nm = s.get_inputs()[0].name; x = np.random.randn(1, 12, 1000).astype(np.float32)
    for _ in range(3): s.run(None, {nm: x})
    t = time.perf_counter(); n = 20
    for _ in range(n): s.run(None, {nm: x})
    ops = Counter(n.op_type for n in onnx.load(so.optimized_model_filepath).graph.node)
    print(f, f"{(time.perf_counter()-t)/n*1000:.1f} ms", dict(ops.most_common(6)))
