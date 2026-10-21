import onnxruntime as ort, numpy as np
x = np.random.randn(1, 12, 1000).astype(np.float32)
for lvl in ("ORT_DISABLE_ALL", "ORT_ENABLE_BASIC"):
    so = ort.SessionOptions(); so.graph_optimization_level = getattr(ort.GraphOptimizationLevel, lvl)
    s = ort.InferenceSession("mc_dyn.onnx", so, providers=["CPUExecutionProvider"])
    nm = s.get_inputs()[0].name
    print(lvl, [round(float(s.run(None, {nm: x})[0].ravel()[0]), 4) for _ in range(5)])
