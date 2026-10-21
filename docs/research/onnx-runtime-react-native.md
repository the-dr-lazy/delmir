# Running DELMIR's models with ONNX Runtime in a bare React Native Android app

Research for [the-dr-lazy/delmir#16](https://github.com/the-dr-lazy/delmir/issues/16), carried out 2026-10-21. Versions are as of that date: React Native 0.88.0, `onnxruntime-react-native` 1.24.3 (the newest on npm, published 2026-03-05), ONNX Runtime (ORT) 1.31.0 (Maven Central and PyPI, 2026-10-09), PyTorch 2.14.1, ONNX 1.20.1 (the version ORT 1.24.3 is built against). Nothing here has run on a phone. The build facts come from the closed spike on branch `prototype/nix-apk` (established by #31/#32). Every claim links to its source, and estimates are marked as estimates.

## Answer

**Yes for ONNX Runtime itself; only "with patches" for its React Native binding.** The Android runtime (`com.microsoft.onnxruntime:onnxruntime-android`) is actively released and its CPU execution provider has fp32 kernels for every operator a U-Net digitizer and a 1D-CNN classifier use. The weak link is the binding. `onnxruntime-react-native` has not been published since 1.24.3, its own maintainers say so, and its end-to-end tests still run on React Native 0.73. In 1.24.3 it is a JSI host object installed through a legacy bridge module. On React Native 0.88 that install path goes through a deprecated `CatalystInstance` shim, and an open PR reports it failing under bridgeless mode.

**Key caveats:**

- **Unpublished binding.** The fixes on `main` since March 2026 (buffer loading, float16 tensors, autolinking) are not on npm ([#32779](https://github.com/microsoft/onnxruntime/pull/32779)).
- **Bridgeless install.** `install()` calls `getCatalystInstance().getJSCallInvokerHolder()`. React Native 0.88 still returns a working shim with a logged warning, but [#33081](https://github.com/microsoft/onnxruntime/pull/33081) reports a crash on React Native 0.86 bridgeless. The one-line fix is unmerged. A device run must settle this.
- **Unpinned native runtime.** The Gradle file asks for `latest.integration` ([#32744](https://github.com/microsoft/onnxruntime/issues/32744)). Pinning it is established by #31/#32.
- **Options silently dropped.** In 1.24.3, loading a model from bytes ignores every session option. Load by file path.
- **Missing knobs.** The JS options cannot set session config entries or XNNPACK provider options. Thread spinning, KleidiAI and `mlas.*` switches are out of reach, and XNNPACK runs single-threaded.
- **CPU only.** For DELMIR, the CPU execution provider is the only one that pays off. NNAPI is deprecated by Android 15. XNNPACK only accelerates 2D convolutions. QNN is Snapdragon-only and needs quantised models.
- **Latency depends on the digitizer's size.** A plain base-32 U-Net at 1024 px is an estimated 6–13 s and up to 1 GB peak memory on a mid-range phone. A light encoder at 512 px is an estimated 0.1–0.8 s. The classifier is an estimated 10–100 ms.

**Recommendation:**

- **Runtime.** Use ORT's CPU execution provider with fp32 `.onnx` models. Do not quantise in v1.
- **Version.** Use one ORT version, pinned in one place, for both the desktop Python wheel and the Android AAR.
- **Binding.** Prefer a small app-owned native module (Kotlin, or C++ if transfers matter) over ORT's official Java/C API to `onnxruntime-react-native`. That module:
  - decodes and pre-processes the image natively;
  - runs both models;
  - returns the 12-lead signal and the classifier output across a narrow, typed interface.
- **Prototyping.** `onnxruntime-react-native` 1.24.3 is acceptable for a first device spike with three patches: the Maven pin, the Gradle 9 `VersionNumber` patch, and #33081.
- **Gate.** Gate either route on a device spike that measures install, latency, memory and numerical agreement ([Open questions](#open-questions--follow-ups)).

## The React Native binding

### Maintenance status

- **npm.** `onnxruntime-react-native` stops at 1.24.3. The `latest` tag still points there, and there are no 1.25–1.31 releases ([npm registry](https://registry.npmjs.org/onnxruntime-react-native)). Its siblings `onnxruntime-common`, `onnxruntime-web` and `onnxruntime-node` all moved on to 1.30.0 (2026-09-14). The npm maintainers are Microsoft accounts (`onnxruntime`, `erscor_msft`, `hanbitmyths`).
- **Acknowledged.** An ORT maintainer wrote on 2026-09-24: "we haven't published onnxruntime-react-native since 1.24" ([#32779](https://github.com/microsoft/onnxruntime/pull/32779)).
- **Source.** The code lives in [`js/react_native`](https://github.com/microsoft/onnxruntime/tree/main/js/react_native) in microsoft/onnxruntime. `main` keeps version bumps (1.32.0 on 2026-10-08) and some features ([commit history](https://github.com/microsoft/onnxruntime/commits/main/js/react_native)). Most recent changes are dependabot bumps of the e2e app.
- **Test coverage.** The e2e test app on `main` still pins `react-native` `^0.73.11` ([e2e/package.json](https://github.com/microsoft/onnxruntime/blob/main/js/react_native/e2e/package.json)), so the New Architecture is untested. A Copilot PR bumping it to 0.84.1 was closed without merging ([#27750](https://github.com/microsoft/onnxruntime/pull/27750)). "[rn] upgrade react native version to 0.76.x" is open ([#27307](https://github.com/microsoft/onnxruntime/issues/27307)).
- **Community fixes stall.** The JSI rewrite came from an outside contributor ([#25764](https://github.com/microsoft/onnxruntime/pull/25764), merged 2025-11-17). A JSI teardown segfault ([#29678](https://github.com/microsoft/onnxruntime/issues/29678)) got a maintainer reply asking for a PR, then was closed by the stale bot with no fix. The earlier PR for the same bug ([#29197](https://github.com/microsoft/onnxruntime/pull/29197)) is closed unmerged.
- **Other platforms.** On iOS, 1.24.3 does not compile against React Native 0.88 ([#33083](https://github.com/microsoft/onnxruntime/issues/33083)). That does not block Android-first DELMIR, but it shows nobody tracks new React Native releases.

### Architecture: a JSI host object installed by a legacy module

Since 1.24 the binding is JSI, not the old base64-over-the-bridge design ([#25764](https://github.com/microsoft/onnxruntime/pull/25764)). At [v1.24.3](https://github.com/microsoft/onnxruntime/tree/v1.24.3/js/react_native):

- **JS entry.** `lib/binding.ts` reads `NativeModules.Onnxruntime` and calls `Module.install()` once. That installs `globalThis.OrtApi` ([binding.ts](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/lib/binding.ts)).
- **Android module.** `OnnxruntimeModule` is a legacy `ReactContextBaseJavaModule`, not a TurboModule. `install()` is a `@ReactMethod(isBlockingSynchronousMethod = true)` ([OnnxruntimeModule.java](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/android/src/main/java/ai/onnxruntime/reactnative/OnnxruntimeModule.java)). It loads `libonnxruntimejsi.so`, takes the `jsi::Runtime` pointer and the JS `CallInvoker`, and installs C++ host objects. Any exception is swallowed (`catch (Exception e) { return false; }`).
- **C++ side.** The C++ (`cpp/`) uses ORT's C++ API against the headers and `libonnxruntime.so` extracted from the `onnxruntime-android` AAR ([CMakeLists.txt](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/android/CMakeLists.txt)). `loadModel` and `run` run on a `std::thread` and settle a JS promise through the `CallInvoker` ([InferenceSessionHostObject.cpp](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/cpp/InferenceSessionHostObject.cpp), [AsyncWorker.h](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/cpp/AsyncWorker.h)).

So under React Native 0.88 the module only works through the legacy-module interop layer. React Native 0.82 made the New Architecture the only architecture. It also promised to "keep the interop layers in the codebase for the foreseeable future" ([React Native 0.82 blog](https://reactnative.dev/blog/2025/10/08/react-native-0.82)).

### Does `install()` work under bridgeless on React Native 0.88?

Possibly; only a device can say.

- **The shim.** In React Native 0.88, `BridgelessReactContext.getCatalystInstance()` logs "[WARNING] Bridgeless doesn't support CatalystInstance" and returns a `BridgelessCatalystInstance` ([BridgelessReactContext.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/ReactAndroid/src/main/java/com/facebook/react/runtime/BridgelessReactContext.kt)). That shim's `getJSCallInvokerHolder()` forwards to the host, and the host returns a `CallInvokerHolderImpl`, so the cast succeeds ([BridgelessCatalystInstance.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/ReactAndroid/src/main/java/com/facebook/react/runtime/BridgelessCatalystInstance.kt), [ReactInstance.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/ReactAndroid/src/main/java/com/facebook/react/runtime/ReactInstance.kt)).
- **When it throws.** It throws only when `UNSTABLE_ENABLE_MINIFY_LEGACY_ARCHITECTURE` is set, which is `false` in React Native's build ([ReactAndroid/build.gradle.kts](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/ReactAndroid/build.gradle.kts)).
- **A reported failure.** [#33081](https://github.com/microsoft/onnxruntime/pull/33081) (open, 2026-10-03) reports that on a React Native 0.86 app with `newArchEnabled=true` "`install()` threw and `OrtApi` stayed uninitialized". It changes the call to `getReactApplicationContext().getJSCallInvokerHolder()`, which exists on `ReactContext` in both modes, and logs the exception.
- **What to do.** My reading of the source and that report disagree. Apply the #33081 patch anyway: it is one line, it removes a dependency on a deprecated shim, and it makes failures visible in logcat.

### How tensors cross the boundary

- **Inputs.** Inputs are zero-copy: `createOrtValueFromJSTensor` wraps the JS `ArrayBuffer`'s memory directly in an `Ort::Value` ([TensorUtils.cpp](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/cpp/TensorUtils.cpp)). It uses `buffer.data()` and ignores the typed array's `byteOffset`, so a `subarray()` view would feed the wrong bytes. Pass freshly allocated `Float32Array`s.
- **Outputs.** Outputs are copied once (`memcpy`) into a new typed array.
- **What crosses.** There is no base64 and no blob manager. A 1024×1024×3 float input is 12.6 MB of JS heap. The 12×5000 classifier input is 240 KB.

### Defects and gaps in 1.24.3 that matter to DELMIR

- **Session options silently dropped when loading from bytes.** `backend.ts` calls `loadModel(buffer, byteOffset, byteLength, options)` ([backend.ts](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/lib/backend.ts)). The 1.24.3 C++ reads `arguments[1]` (the byte offset, a number) as the options object, so `parseSessionOptions` returns at once. Execution providers, threads and the optimisation level are all ignored, and the byte offset is ignored too. `main` fixed this in [#32308](https://github.com/microsoft/onnxruntime/pull/32308) (merged 2026-10-06, unreleased). Workaround: copy the model to app storage and load it by path.
- **No session config entries.** The parsed options are threads, the optimisation level, arena, memory pattern, execution mode, profiling, logging, external data, free-dimension overrides and execution providers ([SessionUtils.cpp](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/cpp/SessionUtils.cpp)). Nothing maps to `AddConfigEntry`, on `main` either. Unreachable keys include `session.intra_op.allow_spinning`, `session.disable_prepacking`, `session.set_denormal_as_zero` and the `mlas.*` keys.
- **XNNPACK gets no provider options.** `"xnnpack"` maps to `AppendExecutionProvider("XNNPACK")` with no options. XNNPACK's own thread count therefore stays at its default of 1 ([XNNPACK EP docs](https://onnxruntime.ai/docs/execution-providers/Xnnpack-ExecutionProvider.html)).
- **Accepted execution provider names on Android:** `cpu`, `xnnpack`, `nnapi`, and `qnn` when built with `"onnxruntimeUseQnn": "true"` in the app's `package.json`, which switches the dependency to `onnxruntime-android-qnn` ([build.gradle](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/android/build.gradle), [SessionUtils.cpp](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/cpp/SessionUtils.cpp)). The AAR also contains a WebGPU execution provider, but the binding cannot select it.
- **Test libraries leak into the app.** `build.gradle` declares `api "org.mockito:mockito-core:2.28.2"` and `implementation "junit:junit:4.12"`.
- **Teardown race.** A static `Env` holds a `jsi::WeakObject` that can outlive the runtime ([#29678](https://github.com/microsoft/onnxruntime/issues/29678)). It is reported intermittent and mostly a reload/teardown hazard, so dev-mode reloads may crash.
- **Build issues** (`latest.integration`, `VersionNumber` under Gradle 9, AGP 7.4.2 classpath) are established by #31/#32. `main` still has `latest.integration` ([#32744](https://github.com/microsoft/onnxruntime/issues/32744)). A PR letting the app pin the version is open ([#32779](https://github.com/microsoft/onnxruntime/pull/32779)).

### What an app-owned module would use instead

ORT's Android AAR ships an official Java API that exposes everything the binding lacks ([OrtSession.java at v1.24.3](https://github.com/microsoft/onnxruntime/blob/v1.24.3/java/src/main/java/ai/onnxruntime/OrtSession.java)):

- `SessionOptions.addConfigEntry(key, value)`;
- `setDeterministicCompute`;
- `addXnnpack(Map)`, `addNnapi(EnumSet)`, `addQnn(Map)` and `addWebGPU(Map)`;
- `OnnxTensor.createTensor(env, FloatBuffer, shape)`, which is zero-copy for direct buffers ([OnnxTensor.java](https://github.com/microsoft/onnxruntime/blob/v1.24.3/java/src/main/java/ai/onnxruntime/OnnxTensor.java)).

The AAR also carries the C/C++ headers for a C++ TurboModule ([install docs](https://onnxruntime.ai/docs/install/)).

Sessions created inside `onnxruntime-react-native` live in its C++ host objects, and other native code cannot reach them. Mixing the two approaches means two ORT environments. If both depend on the AAR, there is one `libonnxruntime.so`.

## Runtime, packages and operators

### Which Android package

| Package | State (Maven Central) | What it is |
|---|---|---|
| `onnxruntime-android` | 1.24.3 … 1.31.0 (2026-10-09) | Full build: all operators, ONNX and ORT formats; CPU, NNAPI, XNNPACK and WebGPU execution providers |
| `onnxruntime-android-qnn` | up to 1.29.0 (2026-08-12) | Adds the Qualcomm QNN execution provider |
| `onnxruntime-mobile` | last 1.18.0 (2024-05-20) | Reduced-operator mobile package, removed in [#20941](https://github.com/microsoft/onnxruntime/pull/20941) ("Remove deprecated 'mobile' packages") |

Sources: Maven metadata for [onnxruntime-android](https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/maven-metadata.xml), [-qnn](https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android-qnn/maven-metadata.xml) and [-mobile](https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-mobile/maven-metadata.xml).

- **Build settings.** The full AAR is built with `--use_nnapi --use_xnnpack --use_webgpu`, `android_min_sdk_version` 24 and four ABIs ([default_full_aar_build_settings.json](https://github.com/microsoft/onnxruntime/blob/v1.24.3/tools/ci_build/github/android/default_full_aar_build_settings.json)).
- **KleidiAI.** KleidiAI (Arm's optimised kernels in MLAS) is on unless `--no_kleidiai` is passed ([build.py](https://github.com/microsoft/onnxruntime/blob/v1.24.3/tools/ci_build/build.py)), so the Android AAR has it.
- **What `onnxruntime-react-native` uses.** It extracts `onnxruntime-android` (or `-qnn`) at Gradle time. It cannot point at a custom AAR without patching `build.gradle`.

### Reduced builds and the ORT format

- **Custom builds.** These keep only the operators a model set needs: `--include_ops_by_config`, plus `--minimal_build` for ORT-format-only. The script is `build_custom_android_package.py` ([custom build docs](https://onnxruntime.ai/docs/build/custom.html)).
- **Size saving.** ORT's own example shrank `arm64-v8a/libonnxruntime.so` from 16.3 MB to 4.0 MB for a ResNet50 build, measured on 1.18 ([mobile deployment docs](https://onnxruntime.ai/docs/tutorials/mobile/)). The 1.24.3 full library is 25.8 MB (established by #32).
- **The `.ort` format.** It is produced by `python -m onnxruntime.tools.convert_onnx_models_to_ort`. A full build loads both `.onnx` and `.ort` ([ORT format docs](https://onnxruntime.ai/docs/performance/model-optimizations/ort-format-models.html)). The page warns the format has had "some breaking changes" across versions.
- **For DELMIR,** a minimal build saves APK megabytes but adds a second model format and a custom native build to the Nix pipeline. For a personal sideloaded app, keep the full AAR and plain `.onnx`. The ORT docs say to start with the full packages too.

### Operator coverage for U-Net and 1D-CNN models

- **Opset.** ORT 1.24.3 is built against ONNX 1.20.1 ([deps.txt](https://github.com/microsoft/onnxruntime/blob/v1.24.3/cmake/deps.txt)), which defines opsets up to 25 ([onnx helper.py](https://github.com/onnx/onnx/blob/v1.20.1/onnx/helper.py)).
- **Kernels.** The CPU execution provider has fp32 kernels for every operator these architectures produce ([OperatorKernels.md at v1.24.3](https://github.com/microsoft/onnxruntime/blob/v1.24.3/docs/OperatorKernels.md)):
  - `Conv`, 1D or 2D, opset 22+;
  - `ConvTranspose`, `MaxPool`, `AveragePool`, `GlobalAveragePool` and `BatchNormalization`;
  - `Resize` (nearest, linear, cubic) and `Upsample` (opset 9 only; exporters emit `Resize`);
  - `Relu`, `LeakyRelu`, `Sigmoid`, `Softmax` and `Gelu`;
  - `LSTM`, `GRU`, `Concat`, `Pad`, `Slice`, `Reshape`, `MatMul` and `Gemm`.
- **CPU fp16.** CPU `Conv` and `ConvTranspose` are registered for `float` only in 1.24.3. fp16 graphs therefore fall back or get casts ([Quantisation and fp16](#quantisation-and-fp16)).
- **Exporter.** `torch.onnx.export` defaults to the `torch.export`-based exporter (`dynamo=True`) since PyTorch 2.9 ([PyTorch 2.14 docs](https://docs.pytorch.org/docs/2.14/onnx.html)). Its default opset is 20, from `ONNX_DEFAULT_OPSET = 20` ([_constants.py](https://github.com/pytorch/pytorch/blob/v2.14.1/torch/onnx/_constants.py), [_compat.py](https://github.com/pytorch/pytorch/blob/v2.14.1/torch/onnx/_internal/exporter/_compat.py)). Opset 20 is well inside ORT 1.24's range.
- **Dynamic shapes.** These go through `dynamic_shapes`; `dynamic_axes` is deprecated. Prefer fixed input shapes for both models (one image size, 12×N samples). Static shapes let ORT plan memory and avoid shape-dependent paths. They also make the export simpler to check.
- **Checker.** `python -m onnxruntime.tools.check_onnx_model_mobile_usability model.onnx` reports operator and partition coverage for NNAPI and CoreML ([usability_checker.py](https://github.com/microsoft/onnxruntime/blob/v1.24.3/tools/python/util/mobile_helpers/usability_checker.py)). Run it once per model.

## Execution providers on Android

| Provider | Selectable from `onnxruntime-react-native` | Fit for DELMIR |
|---|---|---|
| CPU (MLAS, plus KleidiAI on supporting cores) | yes (`cpu`, default) | **Use this.** Every op, fp32, the reference for agreement checks |
| XNNPACK | yes (`xnnpack`), no options | Marginal. Only 2D `Conv`/`ConvTranspose` with constant weights, bilinear `Resize`, pools, `Softmax`, 2D `Gemm`/`MatMul` ([docs](https://onnxruntime.ai/docs/execution-providers/Xnnpack-ExecutionProvider.html)). The 1D classifier gets nothing. Its thread pool contends with ORT's unless ORT intra-op threads are 1 and XNNPACK's are set, which the binding cannot do |
| NNAPI | yes (`nnapi`) | No. "NNAPI is deprecated" and "was deprecated in Android 15", with Google pointing to the CPU backend or the LiteRT GPU runtime ([Android NNAPI guide](https://developer.android.com/ndk/guides/neuralnetworks)). `USE_FP16` "can also reduce accuracy". The ORT usability checker notes "NNAPI EP only supports 2D Conv" |
| QNN | yes, with `onnxruntime-android-qnn` | No for v1. Snapdragon only. Fast on the NPU: a 31M-parameter U-Net at 640×1280, w8a8, runs in 74.5 ms on a Snapdragon 7 Gen 4 ([Qualcomm AI Hub](https://huggingface.co/qualcomm/Unet-Segmentation/blob/main/README.md)). Needs quantised or fp16 models, which breaks numerical agreement with desktop |
| WebGPU (Vulkan on Android) | no | Not now. In the AAR and in ORT's Java API (`addWebGPU`), with Android/Vulkan listed as supported ([WebGPU EP docs](https://onnxruntime.ai/docs/execution-providers/WebGPU-ExecutionProvider.html)). No published Android phone results found |

The ORT mobile guide suggests starting non-quantised models on XNNPACK ([mobile docs](https://onnxruntime.ai/docs/tutorials/mobile/)). XNNPACK's operator list, though, covers only the digitizer's 2D convolutions. Measure CPU against XNNPACK in the device spike and keep XNNPACK only if it wins clearly. Its kernels are a second numerical path to validate.

## Quantisation and fp16

- **int8.** ORT recommends static quantisation for CNNs, with QDQ S8S8 as the default to try first ([quantisation docs](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)). Arm cores with dot-product instructions "can get better performance in general"; old hardware without them can get slower. There is a QDQ debugging tool (`qdq_loss_debug`) for finding where accuracy is lost.
- **fp16.** The float16 guide says the CPU build "doesn't support float16 ops" for its mixed-precision tool, and frames fp16 as a GPU optimisation ([float16 docs](https://onnxruntime.ai/docs/performance/model-optimizations/float16.html)). Newer releases added Arm64 fp16 GEMM and convolution through KleidiAI ([1.29.0 notes](https://github.com/microsoft/onnxruntime/releases/tag/v1.29.0)). They then gated CPU fp16 `Gemm`/`MatMul` on hardware acceleration, with fp32 fallback ([1.30.0 notes](https://github.com/microsoft/onnxruntime/releases/tag/v1.30.0)). fp16 on CPU is device-dependent and adds casts.
- **For DELMIR: stay fp32 in v1.** The models are small enough that size is not the problem. Quantisation adds a calibration set and a second oracle, because PyTorch fp32 no longer matches. It also needs an accuracy re-check on the validation and blog test sets. Revisit int8 only if the measured digitizer latency misses its budget. Even then, a lighter backbone or a smaller input is the cheaper fix.

## Size, memory and latency

There is no published ORT CPU benchmark for a U-Net on a current mid-range Android phone. The figures below are **estimates** built from first principles and one primary data point.

- **Throughput anchor.** XNNPACK reports fp32 MobileNetV2 at 55 ms single-threaded and 28 ms on two big cores on a Pixel 3a, a 2019 phone with Cortex-A75 cores ([XNNPACK README](https://github.com/google/XNNPACK)). MobileNetV2 is about 300M multiply-adds ([Sandler et al.](https://arxiv.org/abs/1801.04381)). That is about 11 GFLOP/s per core and 21 GFLOP/s on two cores. A 2023–2025 mid-range phone has 2–4 Cortex-A78/A715/A720-class big cores (Snapdragon 7-series, Dimensity 7000/8000-series). **Estimate: 30–60 GFLOP/s effective fp32 with 2–4 threads.**
- **Digitizer compute (estimate).** I counted a plain 4-level U-Net with base width 32 and two 3×3 convs per level. It is about 48 G multiply-adds, roughly 100 GFLOPs, at 512×512. That gives about 1.6–3.2 s at 512² and 6–13 s at 1024². Base width 16 cuts this about 4×. A MobileNet/EfficientNet-lite encoder U-Net is typically a few GFLOPs at 512², so 0.1–0.3 s.
- **Digitizer memory (estimate).** One fp32 32-channel feature map at 1024² is 128 MB. With skip connections held for the decoder, peak activation memory for the plain base-32 U-Net is roughly 0.5–1 GB at 1024² and 125–250 MB at 512². Prepacked weights and the model itself come on top.
- **Classifier (estimate).** A PTB-XL-style 1D ResNet over 12×1000 or 12×5000 samples is typically well under 2 GFLOPs: about 10–100 ms.
- **Model files (estimate).** fp32 weights are 4 bytes per parameter: about 8–120 MB for a 2–30M-parameter digitizer and 4–40 MB for the classifier. The full arm64 runtime adds 25.8 MB (established by #32).
- **Memory limits.** Android's documented hard limit is the ART (Java) heap ([memory overview](https://developer.android.com/topic/performance/memory-overview)). `android:largeHeap` only enlarges that heap, and "doesn't guarantee a fixed increase in available memory" ([manifest docs](https://developer.android.com/guide/topics/manifest/application-element)). ORT allocates tensors and its arena on the native heap, so the practical limit is device RAM and the system killing memory-heavy processes. `largeHeap` does not help ORT. Keep the image decode and the JS copies small.
- **Practical rule.** Pick the digitizer's input size and backbone against a measured budget on the target phone, not a desktop GPU. Run models one after the other and release the digitizer session before the classifier if memory is tight.

## Getting pixels to the model without JavaScript

DELMIR's input is a still image: a camera photo, a picked JPEG/PNG, or a rendered PDF page. One inference per reading means none of the video frame-processor machinery is needed. The aim is only to keep a 10–50 MB decoded bitmap from round-tripping through the JS heap.

- **Camera.** VisionCamera is at v5 (5.2.3, 2026-08-20) and built on Nitro Modules (peer dependencies `react-native-nitro-modules` and `react-native-nitro-image`) ([npm](https://registry.npmjs.org/react-native-vision-camera)). It offers `capturePhoto` (an in-memory `Photo` that must be `dispose()`d) and `capturePhotoToFile` (a plain filesystem path) ([docs](https://visioncamera.margelo.com/docs/guides/taking-photos)). For DELMIR, capture to a file. Then the camera, the file picker and the PDF renderer all hand the inference module the same thing: a path.
- **Native pre-processing.** An app-owned Kotlin module decodes the path with `ImageDecoder`/`BitmapFactory`, downsampling at decode time. It resizes and normalises into a direct `FloatBuffer` and calls `OnnxTensor.createTensor`, which is zero-copy. It runs the digitizer and returns the 12-lead signal, a few hundred KB of floats, to JS for the Effect Schema signal contract. The image never enters JS.
- **Alternative.** Native code decodes and pre-processes, then returns a `Float32Array` to JS, which feeds `onnxruntime-react-native`. That is one 12.6 MB copy at 1024² and works with the published binding. Kotlin TurboModules cannot take or return `ArrayBuffer`s directly. A C++ TurboModule, or Nitro, can.
- **Comparison.** `react-native-fast-tflite` 3.x is Nitro-based, uses "zero-copy ArrayBuffers", and calls the LiteRT C/C++ API directly ([README](https://github.com/mrousavy/react-native-fast-tflite)). That is the design an app-owned ORT module would copy.
- **Put pre-processing in the graph where possible.** Resize-to-model-size and normalisation can be ONNX ops (`Resize`, `Sub`, `Div`) exported with the model. Then the native side only decodes to RGB `uint8`, and desktop and phone share the pre-processing kernels.

## Numerical agreement with desktop ONNX Runtime

Desktop x86-64 ORT and Android arm64 ORT will not be bit-identical. These sources of difference are documented:

- **Different kernels per architecture.** MLAS has separate x86 (AVX2/AVX-512, FMA3) and Arm64 (NEON, dot-product, i8mm, SVE/SME via KleidiAI) code paths. Vector width and blocking change the order of summation. KleidiAI kernels are on by default when the core supports them. A switch to disable them, `mlas.disable_kleidiai`, only exists from 1.25 ([config keys at v1.31.0](https://github.com/microsoft/onnxruntime/blob/v1.31.0/include/onnxruntime/core/session/onnxruntime_session_options_config_keys.h), [1.25.0 notes](https://github.com/microsoft/onnxruntime/releases/tag/v1.25.0)). Two arm64 phones can therefore take different paths: one with SME, one without.
- **Layout optimisations differ by platform.** Graph optimisation levels are basic, extended and layout; "All optimizations are enabled by default" ([graph optimisation docs](https://onnxruntime.ai/docs/performance/model-optimizations/graph-optimizations.html)). Layout optimisations rewrite CPU convolutions to NCHWc, and an offline-optimised model "would require CPUs that support AVX2". The Android AAR is not built with `--enable_arm_neon_nchwc` (it is absent from its build settings), so the same `ORT_ENABLE_ALL` session likely runs a different graph on the phone than on the desktop.
- **Reduced precision paths are opt-in.** `mlas.enable_gemm_fastmath_arm64_bfloat16` defaults to `"0"` ([config keys at v1.24.3](https://github.com/microsoft/onnxruntime/blob/v1.24.3/include/onnxruntime/core/session/onnxruntime_session_options_config_keys.h)). NNAPI's `USE_FP16` and any fp16 or int8 model are also opt-in. Keep all of them off.
- **Determinism switches don't cover CPU.** `SetDeterministicCompute` / `session.use_deterministic_compute` "will enable deterministic compute for GPU kernels where possible" ([C API at v1.24.3](https://github.com/microsoft/onnxruntime/blob/v1.24.3/include/onnxruntime/core/session/onnxruntime_c_api.h)). It is not a CPU cross-platform guarantee. I found no ORT statement promising cross-architecture equality or a tolerance.
- **Denormals.** `session.set_denormal_as_zero` is off by default, and the header warns it "may hurt model accuracy". Leave it off on both sides.
- **Version drift.** `latest.integration` means the phone's ORT changes silently between builds ([#32744](https://github.com/microsoft/onnxruntime/issues/32744)). nixpkgs ships its own source-built ORT 1.27.1 ([search.nixos.org](https://search.nixos.org/packages?channel=unstable&query=onnxruntime)), which matches neither 1.24.3 nor 1.31.0.
- **Pre-processing outside the graph.** JPEG decoders and resize filters differ between Android (`BitmapFactory`) and Python (PIL/OpenCV). This difference is usually far larger than kernel noise.

The tolerances ORT and ONNX use for themselves are a starting point:

- The ONNX backend test loader defaults to `rtol=1e-3`, `atol=1e-7` ([loader](https://github.com/onnx/onnx/blob/v1.20.1/onnx/backend/test/loader/__init__.py)).
- ORT's runner of those tests uses `rtol_default: 1e-3`, `atol_default: 1e-5`, with per-test overrides up to `1e-3` absolute ([overrides](https://github.com/microsoft/onnxruntime/blob/v1.24.3/onnxruntime/test/testdata/onnx_backend_test_series_overrides.jsonc)).
- `onnx_test_runner` defaults to `1e-5`/`1e-5`, and to `1e-3`/`1e-3` without the overrides file ([main.cc](https://github.com/microsoft/onnxruntime/blob/v1.24.3/onnxruntime/test/onnx/main.cc)).

Those figures are per operator or for small models. Deep networks accumulate more error, so whole-model checks need a looser absolute tolerance.

## For the model hand-off

**Fix these settings on both sides:**

1. **One ORT version for desktop and phone,** pinned in one place in Nix. Use the official PyPI wheel at the same version as the Maven AAR (both carry 1.24.3 and 1.31.0), not nixpkgs' 1.27.1. If `onnxruntime-react-native` is used, the version is 1.24.3 unless the binding is built from source.
2. **CPU execution provider only** for both models in v1. No XNNPACK, NNAPI or QNN, and no fp16 or int8.
3. **Graph optimisation level `extended`** (`ORT_ENABLE_EXTENDED`) on both sides. That removes the NCHWc layout rewrite that only the desktop can do, so both sides run the same graph. Settle the phone-side cost in the spike; on Android it is likely zero, because the layout pass has no NCHWc target there.
4. **Fixed thread count:** the same `intraOpNumThreads` for the checks on both sides. Use 1 for the desktop flake check; on the phone, use the big-core count the app uses.
5. **Leave the `mlas.*` fast-math options, `set_denormal_as_zero` and the arena at their defaults.** Note that `use_deterministic_compute` does nothing for CPU, and `session.disable_prepacking` is a memory knob, not a numerical one; I found no statement that it changes results.
6. **Load models by file path.** On 1.24.3 that is required for options to apply at all.
7. **Fixed input shapes,** with opset 20 from the default `dynamo=True` export. Run ORT's usability checker on both models as part of the hand-off.

**Proposed tolerances:** a starting point, to be tightened after the first measurement.

| Check | Compared | Tolerance |
|---|---|---|
| CPU flake check (CI, generated inputs) | PyTorch fp32 `eval()` on CPU vs desktop ORT | Classifier logits and digitizer logits: `rtol=1e-3`, `atol=1e-4`. Every generated input must agree on the call and the culprit vessel, unless P(OMI) lies within 1e-3 of a threshold |
| Golden fixtures, tensor level (phone) | Phone ORT vs desktop ORT outputs stored with the fixture | Same `rtol=1e-3`, `atol=1e-4` on logits. \|ΔP(OMI)\| ≤ 1e-4. Identical call and culprit vessel |
| Golden fixtures, image level (phone) | Phone pipeline from a PNG fixture vs desktop pipeline | Decision level: same call, same culprit vessel, signal-quality verdict unchanged. Reconstructed leads within about 10 µV max abs, about one pixel at 300 dpi on 10 mm/mV paper |

How to set the numbers: run the flake check over about 1,000 generated inputs and record the maximum absolute difference. Set `atol` to about 10× that maximum, and write it down next to the model in the manifest. If the phone exceeds it, compare against desktop ORT on `linux-aarch64` (PyPI ships that wheel). That tells architecture effects apart from Android-specific ones.

**How to run the on-phone golden-fixture check:**

- **Fixtures.** Nix builds them at model hand-off. Each holds the pre-processed input tensor (raw little-endian float32 plus shape), the desktop-ORT and PyTorch outputs, and the source PNG for the image-level check. ADR 0007 already puts golden fixtures in the signal contract's own form.
- **Debug-only.** Ship fixtures only in a debug or `androidTest` APK, never the release APK.
- **Runner.** Make it an Android instrumented test (`./gradlew connectedDebugAndroidTest` against a USB-attached phone). It calls the same native inference module the app uses and writes a JSON report that `adb pull` collects. The report holds per-output max abs/rel error, decision agreement, latency, peak memory, the device model and SoC, `/proc/cpuinfo` features (for example SME), and the ORT version string.
- **With `onnxruntime-react-native`,** the runner has to live in JS behind a debug-only screen. That is weaker, because an instrumented test cannot drive it headlessly.
- **Cadence.** The check needs a device, so it cannot run in the Nix sandbox. Run it on every model, ORT-version or pre-processing change, and record the report against the model manifest entry.

## Alternatives if ORT falls short

Both alternatives replace ONNX as the hand-off format. ORT is the only one of the three that consumes `.onnx`. Choosing either would reverse the fixed choice "ONNX as the model format" and the desktop-ORT oracle along with it.

- **ExecuTorch.** Meta's on-device PyTorch runtime: v1.5.1 (2026-09-23) ([releases](https://github.com/pytorch/executorch/releases)). Models are exported with `torch.export` to `.pte`. The React Native binding is Software Mansion's `react-native-executorch` 0.10.7 (2026-10-21) ([npm](https://registry.npmjs.org/react-native-executorch)). It requires React Native 0.83+, the New Architecture and `react-native-worklets` 0.10–0.13. On Android it targets minSdk 26, with an XNNPACK CPU backend and Vulkan on the GPU ([README](https://github.com/software-mansion/react-native-executorch)). It is actively released and New-Architecture-native, but it is a second export path and drops ONNX.
- **LiteRT (TFLite).** Runtime v2.3.0 (2026-10-07) ([releases](https://github.com/google-ai-edge/litert/releases)). Conversion goes through `litert-torch` v0.10.0 (2026-10-20), whose "PyTorch converter is a Beta release" built on `torch.export` ([README](https://github.com/google-ai-edge/litert-torch)). The React Native binding is `react-native-fast-tflite` 3.0.1 (Nitro, zero-copy, GPU delegate; NNAPI marked deprecated) ([README](https://github.com/mrousavy/react-native-fast-tflite)). Google's NNAPI deprecation notice points to this GPU runtime for performance-critical work. There is no ONNX input path.

Neither is needed on present evidence. ORT's runtime is healthy; only its binding is not, and an app-owned module removes that dependency.

## Open questions / follow-ups

Only a measurement on a real phone settles these:

1. **Does `onnxruntime-react-native` 1.24.3 `install()` succeed under React Native 0.88 bridgeless, with and without the #33081 patch?** The source suggests yes, but the PR reports otherwise on 0.86.
2. **What are the digitizer's latency and peak native memory on a mid-range phone,** for a few candidate sizes (512/768/1024 px, base width 16/32 or a light encoder)? Measure CPU with 2 and 4 threads against XNNPACK. Include model load time, and prepacking on against off.
3. **What are the classifier's latency and memory?** These are expected to be small.
4. **How far apart are desktop x86 ORT, desktop aarch64 ORT and phone ORT on the golden fixtures?** Compare `extended` against `all` optimisation, and if possible a phone with SME against one without.
5. **Is there thermal throttling** over about 10 back-to-back readings?
6. **Do the image decode and resize on Android match the desktop pipeline,** or must pre-processing move into the ONNX graph?

Candidate tickets:

- **Spike: ORT inference on a mid-range phone.** Do stand-in digitizer and classifier models run on a mid-range Android phone within the latency and memory budget, and do their outputs match desktop ORT within the proposed tolerances?
- **Decision: ORT binding.** Should DELMIR call ONNX Runtime through `onnxruntime-react-native` or through its own native module over ORT's Java/C API? This may become an ADR next to 0002.
- **Digitizer budget.** What input resolution and backbone keep the digitizer within the latency and memory budget the spike measures?
- **One ORT version in Nix.** How does the Nix build pin one ONNX Runtime version for both the desktop Python check and the Android AAR?
- **Golden-fixture runner.** How does the on-phone golden-fixture check run (instrumented test or in-app), and what report does it record against the model manifest?
