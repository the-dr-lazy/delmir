# Nix is the build system for everything reproducible

One flake builds the contract outputs, the training package and its CPU tests, the model fetches, the TypeScript checks and, if research shows it is affordable, the Android APK; CI is `nix flake check` against Cachix with no path filters, because Nix's input hashing already knows what changed. devenv only provides the `training` and `app` development shells. Generated files (JSON Schema, pydantic models) are derivations and are never committed, so they cannot drift from `contracts/`.

## Consequences

- Training runs and dataset fetches stay outside the sandbox: they need the GPU, the network, hours, or 90 GB of credentialed data.
- Models are fixed-output derivations: the manifest's sha256 is the fetch hash, so a build is also the integrity check.
- Every lockfile has to be one Nix can consume without a hand-maintained hash (npm via `importNpmLock`, Gradle via `gradle.fetchDeps` or gradle2nix).
