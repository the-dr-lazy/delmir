# SPIKE: bare React Native APK with ONNX Runtime, built by Nix (throwaway)

Answers [the-dr-lazy/delmir#32](https://github.com/the-dr-lazy/delmir/issues/32). Lives on the
`prototype/nix-apk` branch only and is never merged. Grown from the untested sketch in
[docs/research/nix-react-native-apk.md](https://github.com/the-dr-lazy/delmir/blob/research/nix-react-native-apk/docs/research/nix-react-native-apk.md).

- RN 0.88.0 template (New Architecture, Hermes), `onnxruntime-react-native` 1.24.3, `App.tsx` imports it.
- `package.nix`: `importNpmLock` + `gradle.fetchDeps` (mitm-cache) + `androidenv`, unsigned
  `arm64-v8a` release APK, `allowedReferences = [ ]`, plus in-sandbox disk/RSS sampling written
  to `$out/spike-metrics.txt`.
- `.github/workflows/spike-nix-apk.yml`: regenerates `deps.json` and runs a cold build on a stock
  GitHub-hosted runner.

```sh
nix build ./spike-nix-apk#apk -L                                          # from the repo root
nix build ./spike-nix-apk#apk.mitmCache.updateScript -o us && USE_BWRAP=0 ./us   # regenerate deps.json
```

## Results (2026-10-21)

Runner = stock `ubuntu-latest` (4 vCPU, 16 GB RAM, 147 GB disk with 87 GB free; GitHub documents 14 GB),
runs [39648665252](https://github.com/the-dr-lazy/delmir/actions/runs/39648665252) and
[39651255479](https://github.com/the-dr-lazy/delmir/actions/runs/39651255479). Local = this NixOS host (32 cores, 30 GB).

| Measure | Runner | Local |
|---|---|---|
| Cold `nix build .#apk` (SDK + Maven + npm + Gradle) | 400 s / 322 s | SDK 821 s + Maven fetch 223 s + APK 90 s |
| Gradle inside the build | 3m24s / 2m32s | 1m21s |
| Peak disk growth during cold build | +12.6 GiB (both runs) | n/a |
| Peak build dir / peak sandbox RSS | 3.7 GiB / 3.1 GiB | 2.0 GiB / 4.7 GiB |
| `/nix/store` after build | 8.9 GiB | n/a |
| Lockfile regeneration (`mitmCache.updateScript`, cold runner) | 343 s / 372 s | failed 5 of 5 attempts (host network: TLS EOF, DNS timeouts) |
| `deps.json` | 94 KB, 972 entries, 4 repositories | |
| Maven closure (`nix path-info -S` mitmCache) | 807 MB | 770 MiB |
| Android SDK composition (NAR) | 4.2 GB | 3.9 GiB |
| APK (unsigned, arm64-v8a) | 45.8 MB, `libonnxruntime.so` is 25.8 MB of it | same |
| `allowedReferences = [ ]` | holds | holds |
| `deps.json` stable across runners | yes (byte-identical) | |
| `zipalign -c -P 16 4` | | passes |
| Bit-reproducible (`--rebuild`) | no | no: only the GNU build-ID of `libappmodules.so` and `libonnxruntimejsi.so` differs |

Fixes the sketch needed: Gradle 9.4.1 via `mkGradle` (nixpkgs' 9.8.0 bundles Kotlin 2.4 metadata the RN
plugin's Kotlin 2.2 rejects); patch ORT 1.24.3's `VersionNumber` use (removed in Gradle 9); CMake 3.31.6 with
nixpkgs' ninja (androidenv's autoPatchelfed ninja segfaults in 3.22.1 and 3.31.6); `USE_BWRAP=0` for the update
script (bwrap needs user namespaces). `resolutionStrategy.force` pins ORT to 1.24.3; no `file://` rewriting and
no autolinking change were needed.
