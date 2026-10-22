# Nix is the build system for everything reproducible

One flake builds the contract outputs, the training package and its CPU tests, the model fetches, the TypeScript checks and the unsigned Android APK; CI is `nix flake check` against Cachix with no path filters, because Nix's input hashing already knows what changed. devenv only provides the development shells, as profiles of one standalone `devenv.yaml` at the root, not as a flake module: that is devenv's supported mode, with an evaluation cache and a GC root. The shells and the flake evaluate the same Nix files under `nix/` against one nixpkgs revision, so a shell and the sandbox build get the same store paths. Generated files (JSON Schema, pydantic models) are derivations and are never committed, so they cannot drift from `contracts/`.

## Consequences

- Training runs and dataset fetches stay outside the sandbox: they need the GPU, the network, hours, or 90 GB of credentialed data.
- Models are fixed-output derivations: the manifest's sha256 is the fetch hash, so a build is also the integrity check.
- Every lockfile has to be one Nix can consume without a hand-maintained hash: npm via `importNpmLock`, Gradle via `gradle.fetchDeps` (gradle2nix stops at Gradle 8, and React Native 0.88 needs Gradle 9), Python via nixpkgs itself (ADR 0009).
- There are two lockfiles, `flake.lock` and `devenv.lock`. A flake check fails when their nixpkgs revisions differ, so bumping nixpkgs means bumping both.
- The Android SDK is unfree and its licence forbids redistribution, so it is built from Google's archives on every machine and never pushed to the public Cachix; the APK has no store references, so it can be.
- Gradle-side changes need a networked regeneration of `deps.json`, which runs in CI, not on the host.
