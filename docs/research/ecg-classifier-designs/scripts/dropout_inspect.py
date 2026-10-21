import onnx, onnxruntime as ort, numpy as np
from onnx import numpy_helper
g = onnx.load("mc_dyn.onnx")
d = next(n for n in g.graph.node if n.op_type == "Dropout")
print("Dropout inputs:", list(d.input), "attrs:", [(a.name, onnx.helper.get_attribute_value(a)) for a in d.attribute])
inits = {i.name: numpy_helper.to_array(i) for i in g.graph.initializer}
consts = {n.output[0]: numpy_helper.to_array(n.attribute[0].t) for n in g.graph.node if n.op_type == "Constant"}
for name in d.input[1:]:
    print(" ", name, "=", inits.get(name, consts.get(name, "graph input / computed")))
# Force training_mode=True via a constant and test ORT stochasticity
t = onnx.helper.make_tensor("force_train", onnx.TensorProto.BOOL, [], [True])
g.graph.initializer.append(t)
ins = list(d.input)
while len(ins) < 2: ins.append("")
if len(ins) == 2: ins.append("force_train")
else: ins[2] = "force_train"
if ins[1] == "":
    g.graph.initializer.append(onnx.helper.make_tensor("ratio_c", onnx.TensorProto.FLOAT, [], [0.5])); ins[1] = "ratio_c"
del d.input[:]; d.input.extend(ins)
onnx.save(g, "mc_dyn_forced.onnx")
s = ort.InferenceSession("mc_dyn_forced.onnx", providers=["CPUExecutionProvider"])
x = np.random.randn(1, 12, 1000).astype(np.float32)
nm = s.get_inputs()[0].name
print("forced training_mode=True, 5 runs:", [float(s.run(None, {nm: x})[0].ravel()[0]) for _ in range(5)])
