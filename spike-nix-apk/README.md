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

Results: see the resolution comment on #32.
