# PyTorch on the RX 6600 XT inside devenv on NixOS

Research for [the-dr-lazy/delmir#8](https://github.com/the-dr-lazy/delmir/issues/8), carried out 2026-10-21. Versions are as of that date:

- nixpkgs `nixpkgs-unstable` at `5adc50831c259f87faeb09ddf930d43597197473` (2026-10-20); the host runs NixOS `26.11.20261005.494ce7f` with kernel 7.2.9 and systemd 261.3;
- devenv 2.4.0;
- PyTorch 2.14.1 stable;
- ROCm 10.1.0 upstream, 7.2.4 in nixpkgs.

Every claim links to its source. "Observed" means checked on this host or against the live index on that date. Estimates are marked as estimates.

**Nothing ran on the GPU.** The agent sandbox hides `/dev/kfd`, so the "prove it with a tensor op" step could not run. The spike [#41](https://github.com/the-dr-lazy/delmir/issues/41) does it on the host with the script in [Proof script](#proof-script-for-the-host).

## Answer

**Use nixpkgs' `python313Packages.torchWithRocm` in the `training` devenv shell, with a per-device override.**

**Why:**

- **It comes from the binary cache.** nixpkgs-unstable has torch 2.13.0 on ROCm 7.2.4, and cache.nixos.org holds its whole closure: 148 paths, about 6.6 GB to download and 15.7 GB unpacked (observed). Nothing compiles.
- **It contains gfx1030 code.** The build's `PYTORCH_ROCM_ARCH` includes gfx1030 (observed in the derivation). MIOpen ships its gfx1030 kernel database ([miopen/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/rocm-modules/miopen/default.nix)).
- **One nixpkgs pins everything.** It is the same nixpkgs that already pins the flake. The flake's CPU checks use plain `torch` from the same package set (also cached), so the GPU shell and the CPU check differ only in that one override.

**Settings the dGPU needs** (both are explained in [Selecting the dGPU](#selecting-the-dgpu-and-hiding-the-igpu)):

- `HSA_OVERRIDE_GFX_VERSION_1=10.3.0`, which reports KFD node 1, the RX 6600 XT, as gfx1030;
- `ROCR_VISIBLE_DEVICES=0`, which hides the Raphael iGPU.

**Host setup: none.** This host already gives every local user read-write access to `/dev/kfd` and `/dev/dri/renderD*` through systemd's default udev rules, so no NixOS option or group membership is needed.

**Fallback: AMD's native gfx1032 wheels through uv.** These are `torch 2.14.0+rocm10.1.0` from `https://stable.repo.amd.com/rocm/whl-next/`.

- **For:** they need no override and download about 1 GB.
- **Against:** gfx1032 is only "community-enabled". Its device wheel ships no MIOpen kernel database. uv has to resolve from a non-explicit AMD index, which is a trap because of look-alike placeholder packages on PyPI. And the lockfile lives outside Nix.
- **When to switch:** if the spike shows torchWithRocm misbehaving on the override, or when DELMIR needs ROCm 10 before nixpkgs has it.

**PyTorch's own ROCm wheels are the weakest option.** The rocm7.2 wheel is a single 6.2 GB file. The rocm7.14 wheel pulls about 25 device wheels. Both still need the override, and they give nothing over nixpkgs.

## Comparison

| | nixpkgs `torchWithRocm` | AMD `torch[device-gfx1032]` (uv) | PyTorch `whl/rocm7.2` / `rocm7.14` (uv) |
|---|---|---|---|
| torch / ROCm | 2.13.0 / 7.2.4 | 2.14.0 / 10.1.0 | 2.14.1 / 7.2 or 7.14 |
| Code for the 6600 XT | gfx1030, override needed | native gfx1032 | gfx1030, override needed |
| MIOpen kernel DB | gfx1030 shipped | none for gfx1032 (JIT on first use) | gfx1030 shipped |
| Download | ≈6.6 GB closure (15.7 GB unpacked) | ≈1 GB | 6.2 GB wheel / 1.4 GB + several GB device wheels |
| Source | cache.nixos.org | AMD index | download.pytorch.org |
| Pinned by | `flake.lock` / `devenv.lock` | `uv.lock` | `uv.lock` |
| Fits ADR 0004 (flake builds training + CPU tests) | directly: swap `torch` ↔ `torchWithRocm` | needs uv2nix, plus a separate CPU torch for checks | same as AMD |
| Host libraries needed | none (Nix closure) | glibc, `libstdc++`, `libgcc_s` (devenv adds them) | same; rocm7.2 bundles libdrm/libnuma/libelf |

## nixpkgs: `torchWithRocm`

### What it is

- **Definition.** `torchWithRocm = self.torch.override { triton = self.triton-no-cuda; rocmSupport = true; cudaSupport = false; }` ([python-packages.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/top-level/python-packages.nix)). It exists for `python313Packages` and `python314Packages`, both at 2.13.0. The default `python3` is now 3.14.8 (observed).
- **ROCm version.** `rocmPackages.*` are at 7.2.4: clr, rocblas, miopen, hipblaslt, rocm-runtime and the rest (observed).

**GPU targets.** If `gpuTargets` is left empty, torch builds for `rocmPackages.clr.gpuTargets` minus gfx1010 and gfx1012 ([torch/source/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/python-modules/torch/source/default.nix), `gpuTargetString`). That leaves:

```
PYTORCH_ROCM_ARCH="gfx900;gfx906;gfx908;gfx90a;gfx942;gfx950;gfx1030;gfx1100;gfx1101;gfx1102;gfx1103;gfx1150;gfx1151;gfx1200;gfx1201"
```

This was read from the evaluated derivation (observed). gfx1030 is in the list and gfx1032 is not, which is why the override is needed.

**Per-library target lists.** Each library intersects that list with its own supported targets:

- **MIOpen** supports gfx1030 and gfx1031 and ships the gfx1030 kernel database ([miopen/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/rocm-modules/miopen/default.nix), `kdbs.nix`).
- **rocBLAS** builds every clr target ([rocblas/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/rocm-modules/rocblas/default.nix)).
- **hipBLASLt** has no gfx103x ([hipblaslt/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/rocm-modules/hipblaslt/default.nix)). That is harmless, because PyTorch only prefers hipBLASLt on supported archs and otherwise uses hipBLAS/rocBLAS ([Context.cpp](https://github.com/pytorch/pytorch/blob/release/2.14/aten/src/ATen/Context.cpp), [CUDAHooks.cpp](https://github.com/pytorch/pytorch/blob/release/2.14/aten/src/ATen/cuda/detail/CUDAHooks.cpp)). So `TORCH_BLAS_PREFER_HIPBLASLT=0` is not needed.
- **AOTriton** (flash and memory-efficient attention) has no gfx103x either ([aotriton/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/rocm-modules/aotriton/default.nix)). `scaled_dot_product_attention` should fall back to the math kernel, which I inferred from [sdp_utils.cpp](https://github.com/pytorch/pytorch/blob/release/2.14/aten/src/ATen/native/transformers/hip/sdp_utils.cpp) and have not run. This matters only if the classifier uses attention.

**Single-arch scopes.** nixpkgs also exposes `rocmPackages.gfx1030` (and `gfx10`, `gfx11`, …), a scope whose `clr.localGpuTargets = [ "gfx1030" ]` ([rocm-modules/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/rocm-modules/default.nix)). Building torch against it would give a much smaller closure. But nothing in it is cached, so every ROCm library and torch would compile from source. Don't use it.

### Binary cache

All of these returned `200` from cache.nixos.org (observed):

| Store path | Download | Unpacked |
|---|---|---|
| `python3.13-torch-2.13.0` (ROCm, `out`) | 38.7 MB | 215 MB |
| `python3.13-torch-2.13.0-lib` (`libtorch_hip.so` is 521 MB) | 1.0 GB | 1.5 GB |
| `hipblaslt-7.2.4` | 1.6 GB | 1.9 GB |
| `miopen-7.2.4` | 354 MB | 1.9 GB |
| `rocblas-7.2.4` | 206 MB | 832 MB |
| `aotriton-0.12b` | 583 MB | 597 MB |
| whole closure (148 paths) | **6.6 GB** | **15.7 GB** |

The `python3.14` variant is cached too (observed).

**A cold `devenv shell` therefore downloads 6.6 GB once.** No `trusted-substituters` change is needed, because only cache.nixos.org is used. The nix-community / ROCm caches that older guides mention are not needed.

**Building from source is expensive.** The torch derivation says it "Builds in 2+h with 2 cores, and ~15m with a big-parallel builder" ([torch/source/default.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/pkgs/development/python-modules/torch/source/default.nix), `requiredSystemFeatures`). That covers torch alone. The ROCm libraries underneath (composable_kernel, rocBLAS/Tensile, MIOpen, hipBLASLt, rocFFT) would take several more hours on this 32-thread host. That is my estimate; I did not run it, as the ticket asked.

**When this bites:** after a nixpkgs bump that Hydra has not built yet. The channel advances even when a ROCm package fails. So before bumping, run `nix build --dry-run` on the shell, or check that the new torch path's `.narinfo` exists.

### Which ROCm versions still work with the gfx1030 override

**The override code is in nixpkgs' runtime.** The `HSA_OVERRIDE_GFX_VERSION` handling lives in libhsakmt's `topology.c`. nixpkgs' `rocm-runtime` 7.2.4 source has the per-node form, `HSA_OVERRIDE_GFX_VERSION_<node>`, which is checked first, and the global variable as fallback (observed in the source fetched from nixpkgs, `projects/rocr-runtime/libhsakmt/src/topology.c` lines 1243–1249).

**Upstream still accepts it.** The current upstream source ([topology.c](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/topology.c)) keeps both forms. Since May 2026 it rejects overrides that cross a major version ([commit 1fbff03f08](https://github.com/ROCm/rocm-systems/commit/1fbff03f08)). 10.3.0 on a gfx1032 stays inside gfx10, so it is allowed.

**Reports from other gfx103x cards on ROCm 7.x:**

- An RX 6700 XT (gfx1031) on torch 2.13.0+rocm7.2 with `HSA_OVERRIDE_GFX_VERSION=10.3.0` gives "bitwise-correct" compute; the bug filed there is about HIP-graph teardown ([pytorch#193668](https://github.com/pytorch/pytorch/issues/193668)).
- Random `hipErrorIllegalAddress` errors on gfx1031 across ROCm 7.0–10.1 were traced to a KFD SVM alignment bug ([TheRock#9189](https://github.com/ROCm/TheRock/issues/9189)). The fix is mainline commit [`b89d58b6595d`](https://github.com/torvalds/linux/commit/b89d58b6595d79dc3fe75e213e1f4c5efd0251d4), which v7.2 contains, so this host's 7.2.9 kernel has it. It matters if the host ever moves to an LTS kernel without the backport (6.18.y reportedly lacks it).

**Is RDNA2 still supported upstream?** Yes: ROCm 10.1.0 still lists gfx1030 cards (W6800, V620) as supported ([compatibility matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)). PyTorch 2.14 still builds gfx1030 into both ROCm wheel variants ([manywheel/build.sh](https://github.com/pytorch/pytorch/blob/release/2.14/.ci/docker/manywheel/build.sh)). gfx1032 itself appears in no official list.

**Open question: MIOpen tuning.** MIOpen's shipped gfx1030 find-DB is keyed `gfx1030_36`, for 36 CUs, while the 6600 XT has 32 CUs. Whether the perf/find DB still applies under the override is unverified. If it doesn't, MIOpen tunes or JIT-compiles on first use and caches the result in `~/.cache/miopen`.

## Selecting the dGPU and hiding the iGPU

**This host's KFD topology** (observed in `/sys/class/kfd/kfd/topology/nodes/*/properties`):

| KFD node | Device | `gfx_target_version` | render node |
|---|---|---|---|
| 0 | CPU | 0 | — |
| 1 | RX 6600 XT (Navi 23 "dimgrey_cavefish", PCI `03:00.0`, 64 SIMDs) | 100302 (gfx1032) | `renderD128` |
| 2 | Raphael iGPU (device `0x164e`, 4 SIMDs) | 100306 (gfx1036) | `renderD129` |

**A global override would also hit the iGPU.** `HSA_OVERRIDE_GFX_VERSION` applies to every GPU node. libhsakmt rewrites each node's version before ROCr filters devices ([topology.c](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/topology.c)), so with the global variable the iGPU would be reported as gfx1030 too. It would then look like a valid second device, and work could land on it. The per-node variable confines the override to the dGPU: `HSA_OVERRIDE_GFX_VERSION_1=10.3.0`. The upstream commit's own example uses `_1` for the first GPU ([commit ffafd46406](https://github.com/ROCm/rocm-systems/commit/ffafd46406)).

**Hiding the iGPU:**

- **`ROCR_VISIBLE_DEVICES` is the right variable on Linux.** ROCr reads it, so it applies to every ROCm program; `HIP_VISIBLE_DEVICES` affects HIP only. AMD's advice is "On Linux, use ROCR_VISIBLE_DEVICES" ([GPU isolation](https://rocm.docs.amd.com/en/latest/reference/system-optimization/gpu-isolation.html)).
- **Its index counts GPU nodes only, in KFD order**, so `0` is the RX 6600 XT here. I read this from [amd_topology.cpp](https://github.com/ROCm/rocm-systems/tree/develop/projects/rocr-runtime/runtime/hsa-runtime) and have not run it.
- **A UUID is more robust** if the BIOS or kernel ever reorders devices: use `ROCR_VISIBLE_DEVICES=GPU-<uuid>` with the UUID from `rocminfo`.
- **Unsupported GPUs no longer abort startup.** ROCr now skips them with a "Skipping unsupported GPU" message instead of failing (same source).

Set both variables: the per-node override and the visibility filter. Either alone would probably do, but each guards against a different failure. Without the filter, a gfx1036 iGPU can become `cuda:0` and the dGPU then fails with `hipErrorInvalidImage` ([TheRock#3392](https://github.com/ROCm/TheRock/issues/3392), reported on Windows).

## Host prerequisites

- **Device access is already open.** systemd 261's `50-udev-default.rules` sets `SUBSYSTEM=="kfd", GROUP="render", MODE="0666"` and `SUBSYSTEM=="drm", KERNEL=="renderD*", GROUP="render", MODE="0666"` (observed in `/nix/store/l5hiab…-systemd-261.3/lib/udev/rules.d/50-udev-default.rules`). Every local user can therefore open `/dev/kfd` and the render nodes. Joining `render` and `video` (AMD's instruction, [ROCm install](https://rocm.docs.amd.com/en/latest/install/rocm.html)) is harmless but not required. Today the user is in neither group (observed).
- **No NixOS option is needed for HIP.**
  - `hardware.amdgpu.opencl.enable` only adds `rocmPackages.clr` and its OpenCL ICD to `hardware.graphics.extraPackages` ([amdgpu.nix](https://github.com/NixOS/nixpkgs/blob/5adc50831c259f87faeb09ddf930d43597197473/nixos/modules/services/hardware/amdgpu.nix)). nixpkgs' torch finds its ROCm through its own closure, not `/run/opengl-driver` or `/opt/rocm`.
  - The other `hardware.amdgpu.*` options (`initrd`, `legacySupport`, `overdrive`, `zluda`) are unrelated. The host already sets `amdgpu.ppfeaturemask=0xfffd7fff` (observed in `/proc/cmdline`).
- **Kernel.** The in-tree `amdgpu` driver is loaded and KFD exposes both GPUs (observed). AMD documents its out-of-tree driver for Radeon and does not say whether in-tree is supported ([ROCm install](https://rocm.docs.amd.com/en/latest/install/rocm.html)); in practice in-tree is what nixpkgs ROCm users run. The kernel already has the KFD SVM fix (see above).
- **Multi-GPU.** AMD notes "Systems with multiple GPUs may require iommu=pt" ([system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html)). The host already boots with `amd_iommu=on iommu=pt` (observed).
- **In the agent sandbox `/dev/kfd` is missing**, both with and without the sandbox override (observed). So GPU work has to run in a normal terminal, not from an agent session in this app.

## devenv wiring

**Interpreter option.** devenv 2.4.0's `languages.python.package` accepts a `python.withPackages` environment. devenv wraps it to prefix `LD_LIBRARY_PATH` with `languages.python.libraries`, and always appends `stdenv.cc.cc.lib` ([python/default.nix at v2.4.0](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/languages/python/default.nix)). For nixpkgs' torch this wrapping is irrelevant, since its RPATHs are already complete, but it is what makes the wheel fallback work.

**Other options that matter:**

- `languages.python.uv.enable`;
- `languages.python.uv.sync.{enable,arguments,groups,…}`;
- `languages.python.venv.enable`;
- `languages.python.lsp.{enable,package}`, which defaults to `pkgs.pyright`;
- `languages.python.import`, a uv2nix import of a `pyproject.toml`.

Same source.

**Sketch of the `training` shell on route A** (not run; [#19](https://github.com/the-dr-lazy/delmir/issues/19) decides the real layout):

```nix
{ pkgs, ... }:
let
  python = pkgs.python313.withPackages (ps: [
    ps.torchWithRocm
    ps.numpy ps.scipy ps.pandas ps.scikit-learn ps.onnx ps.onnxscript ps.pydantic
    ps.pytest ps.hypothesis ps.ipykernel
  ]);
in {
  languages.python = {
    enable = true;
    package = python;
    lsp.package = pkgs.basedpyright;
  };
  packages = [ pkgs.ruff pkgs.basedpyright pkgs.rocmPackages.rocminfo pkgs.rocmPackages.rocm-smi ];
  env = {
    HSA_OVERRIDE_GFX_VERSION_1 = "10.3.0"; # KFD node 1 = RX 6600 XT (gfx1032 → gfx1030 code)
    ROCR_VISIBLE_DEVICES = "0";            # first GPU node; hides the gfx1036 iGPU
  };
}
```

**Python dependencies not in nixpkgs.** Of the likely dependencies, numpy 2.5.3, scipy 1.18.1, pandas 3.0.4, scikit-learn 1.9.0, onnx 1.23.2, onnxscript 0.7.2, pydantic 2.13.4, torchmetrics 1.9.0, neurokit2 0.2.12, hypothesis 6.168.1 and ipykernel 7.3.0 are all in nixpkgs. **`wfdb` is not** (observed, `python313Packages`). It is pure Python, so a small `buildPythonPackage` (or a uv2nix overlay) covers it. That choice belongs to #19's "how Python dependencies are managed".

**torchvision.** `python313Packages.torchvision` (0.28.0) is built against CPU `torch`. Pairing it with `torchWithRocm` would need an override that is probably not cached. A 1-D ECG classifier is unlikely to need it.

## Fallback: AMD's gfx1032 wheels with uv

**What the index has.** `https://stable.repo.amd.com/rocm/whl-next/` lists `amd-torch-device-gfx1030` … `gfx1036` and `rocm-sdk-device-gfx1030` … `gfx1036`, with `torch-2.14.0+rocm10.1.0` for cp313 and cp314 `linux_x86_64` (observed). AMD's install page documents the index and the `torch[device-<gfx>]` extras, but gives commands only for official targets ([PyTorch install](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html)).

**What it resolves to.** `torch[device-gfx1032]==2.14.0+rocm10.1.0` resolves to 17 packages, about 1 GB in total (observed with `uv pip compile`):

- torch 208 MB;
- `rocm-sdk-core` 419 MB;
- `rocm-sdk-libraries` 261 MB;
- `rocm-sdk-device-gfx1032` 70 MB;
- `amd-torch-device-gfx1032` 44 MB;
- triton 3.8.0+rocm10.1.0 and the rest.

**Host libraries.** The HIP and HSA runtimes in `rocm_sdk_core` need only glibc, `libstdc++.so.6` and `libgcc_s.so.1` from the host (observed with `readelf -d`). libdrm, libnuma and libelf ship inside the wheel under `rocm_sysdeps` and are found through RPATH. devenv's `stdenv.cc.cc.lib` covers what remains, so nix-ld is not needed.

**The uv trap.** PyPI has placeholder packages named `rocm`, `rocm-sdk-core`, `rocm-sdk-libraries`, `rocm-bootstrap` and `amd-torch-device-gfx1032`, at versions 0.1.0 / 0.0.1.dev0 with author "Your Name" (observed). The [uv PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/) pins `torch` to an `explicit = true` index, and that fails here. uv `sources` apply only to direct dependencies, so the transitive `triton`/`rocm*` pins are looked up on PyPI and are not found (observed with `uv lock`). What worked was listing the AMD index first and **not** explicit, so that uv's `first-index` strategy ([indexes](https://docs.astral.sh/uv/concepts/indexes/)) takes every name the AMD index has from it:

```toml
[project]
dependencies = ["torch[device-gfx1032]==2.14.0+rocm10.1.0"]

[[tool.uv.index]]
name = "amd-rocm"
url = "https://stable.repo.amd.com/rocm/whl-next/"
```

**The cost.** The gfx1032 device wheel ships no MIOpen kernel database, while the gfx1030 wheel ships a 745 MB `gfx1030.kdb` (observed). Convolutions therefore JIT-compile through hipRTC the first time they run. A gfx1032 hipRTC compile failure was closed as fixed on 2026-10-05 ([TheRock#6258](https://github.com/ROCm/TheRock/issues/6258)); which release carries the fix is unverified.

## Python tooling

These are the nixpkgs-unstable versions, all cached (observed):

| Tool | Version | Role |
|---|---|---|
| Python | 3.13.16 (3.14.8 is `python3`) | 3.13 keeps every scientific dependency on its most-built path. torchWithRocm is cached for both |
| uv | 0.13.1 | not needed on route A. On route B it is the resolver and lock (`languages.python.uv.*`) |
| ruff | 0.17.1 | lint and format |
| basedpyright | 1.39.8 | type checker and LSP. Stricter defaults than pyright (1.1.414), closer to the driver's TypeScript and Haskell habits. Set `languages.python.lsp.package` |
| ty | 0.0.87 | still pre-release. Not yet |
| pytest | 9.1.1 | tests, plus hypothesis 6.168.1 for the ADR 0003 round-trip properties |
| JupyterLab | 4.6.4 | with `ipykernel` in the env, or run as a separate tool against the shell's interpreter |
| rocminfo / rocm-smi / amdsmi | 7.2.4 | GPU diagnostics in the shell |
| nvtop (`nvtopPackages.amd`) | 3.3.2 | live GPU load |

## Proof script for the host

Run this in a normal terminal, not an agent session. It needs about 6.6 GB of downloads once.

```bash
mkdir -p /tmp/rocm-proof && cd /tmp/rocm-proof
cat > devenv.nix <<'EOF'
{ pkgs, ... }: {
  languages.python = {
    enable = true;
    package = pkgs.python313.withPackages (ps: [ ps.torchWithRocm ]);
  };
  packages = [ pkgs.rocmPackages.rocminfo ];
  env.HSA_OVERRIDE_GFX_VERSION_1 = "10.3.0";
  env.ROCR_VISIBLE_DEVICES = "0";
}
EOF
printf 'inputs:\n  nixpkgs:\n    url: github:NixOS/nixpkgs/5adc50831c259f87faeb09ddf930d43597197473\n' > devenv.yaml
devenv shell -- python - <<'EOF'
import torch, time
print(torch.__version__, torch.version.hip, torch.cuda.is_available(), torch.cuda.device_count())
print(torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).gcnArchName)
x = torch.randn(4096, 4096, device="cuda"); torch.cuda.synchronize(); t = time.time()
for _ in range(20): y = x @ x
torch.cuda.synchronize(); print("matmul TFLOP/s:", 20 * 2 * 4096**3 / (time.time() - t) / 1e12)
c = torch.nn.Conv1d(12, 64, 7).cuda(); print("conv1d:", c(torch.randn(32, 12, 5000, device="cuda")).shape)
EOF
```

**What to expect:**

- `torch.cuda.is_available()` is True, the device count is 1, and the arch name is `gfx1030` (the override).
- The matmul rate is in the RX 6600 XT's FP32 range, about 10 TFLOP/s at peak (my estimate).
- The Conv1d call exercises MIOpen.

**Then:**

- Repeat with `ROCR_VISIBLE_DEVICES` unset, to see the iGPU appear.
- Repeat with the global `HSA_OVERRIDE_GFX_VERSION=10.3.0`, to confirm the per-node form is what keeps the iGPU at gfx1036.

## Not verified

- No GPU run of any route; the sandbox has no `/dev/kfd`. This is spike [#41](https://github.com/the-dr-lazy/delmir/issues/41).
- That `ROCR_VISIBLE_DEVICES=0` means KFD node 1 here (read from source).
- SDPA's math fallback on gfx1030 (read from source).
- Whether MIOpen's `gfx1030_36` find-DB is used on a 32-CU card under the override.
- Source-build time of the ROCm stack (estimate only).
