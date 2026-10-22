# Python dependencies come from nixpkgs, not a Python lockfile

Training takes every Python dependency from the nixpkgs package set the flake already pins, with a small overlay for what nixpkgs lacks or has at the wrong version; there is no `uv.lock` and no uv2nix. The GPU build of PyTorch that works on the RX 6600 XT is nixpkgs' `torchWithRocm`, fully on cache.nixos.org, and every other dependency is already in nixpkgs, so a second resolver would add a lockfile and a second way to describe the same packages without supplying anything. The shell and the CPU checks share one dependency list and differ only in which `torch` they get.

## Considered options

- **uv with AMD's native gfx1032 wheels**: no override needed and about a sixth of the download, but gfx1032 is only community-enabled, its wheel has no MIOpen kernel database, PyPI has placeholder packages with the same names, and the CPU checks would need uv2nix and a second torch.
- **uv2nix or pyproject-nix over a `uv.lock`**: the usual Python workflow, but it re-solves what nixpkgs already resolves and cannot make the ROCm torch any more cached.

## Consequences

- Adding a dependency means finding it in nixpkgs or writing a `buildPythonPackage` for it in the overlay (`wfdb` already needs one); `pip install` is never part of the workflow.
- `pyproject.toml` still declares the dependencies, and nixpkgs' runtime-dependency check fails the build when a declared one is missing from the Nix list.
- Torch versions follow nixpkgs. If DELMIR needs a ROCm or torch release that nixpkgs does not have yet, the fallback is AMD's wheels, and this ADR is superseded.
- ONNX Runtime is the one wheel in the overlay: desktop and phone must run the same version, nixpkgs builds a different one, and the PyPI wheel matches the Android AAR.
