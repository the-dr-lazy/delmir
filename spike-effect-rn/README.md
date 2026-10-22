# THROWAWAY SPIKE: Effect 4 + encrypted op-sqlite registry in a bare RN 0.88 APK (delmir#43)

Answers [delmir#43](https://github.com/the-dr-lazy/delmir/issues/43). Never merge. Grown from the
[#32](https://github.com/the-dr-lazy/delmir/issues/32) spike (`prototype/nix-apk`, `spike-nix-apk/`), with
onnxruntime-react-native dropped (not under test here).

What is in it:

- `effect`, `@effect/atom-react`, `@effect/sql-sqlite-react-native` 4.0.5, imported only by subpath.
- `babel-plugin-import-meta.js`: rewrites `import.meta` to `{}`; added to `@react-native/babel-preset` in `babel.config.js`.
- `react-native-get-random-values` 2.0.0, imported first in each entry file.
- `@op-engineering/op-sqlite` 17.2.0 with `"op-sqlite": { "sqlcipher": true }` (root `package.json`); `op18/` holds
  the 18.2.5 variant (an npm `overrides` entry gets past the driver's `<18` peer range).
- Key: 32 random bytes made on first run, stored with `react-native-keychain` 10.0.0, passed to SQLCipher as a raw key (`x'…'`).
- Migrations: `src/MigratorRunner.ts` (`Migrator.fromRecord`, needs `patch-migrator.sh`, which `package.nix` runs on
  `node_modules` in the Nix build) and `src/LocalRunner.ts` (never imports `effect/sql/Migrator`).
- UI: React Navigation 7 static native-stack, case list + case, driven by one `Atom.runtime(RegistryLayer)`.
- Stand-in data: `src/Case.ts`, a 30-field struct with nested arrays; `delmirspike://seed?n=1000` writes 1,000 cases.
- `android/app/src/main/res/xml/data_extraction_rules.xml`: excludes every domain from cloud backup and device transfer;
  `allowBackup="false"`.

Entry files: `index.js` (Effect, Migrator runner, plus both runners on scratch DBs), `index.local.js` (local runner,
`effect` unpatched), `index.baseline.js` (no Effect, no registry), `index.arbitrary.js` (size check only).

```sh
nix build ./spike-effect-rn#apk -L        # also: #apk-op18 #apk-local #apk-baseline #apk-debug
nix build ./spike-effect-rn#apk.mitmCache.updateScript -o us && USE_BWRAP=0 ./us   # from the repo root
cd spike-effect-rn && nix shell nixpkgs#android-tools nixpkgs#sqlcipher nixpkgs#bc nixpkgs#jdk17_headless -c ./device.sh   # phone on USB
```

`device.sh` signs each APK with the debug keystore, installs it, and drives the app with `delmirspike://` links
(`checks`, `migrations`, `seed`, `bench?mode=sync|async`, `cipher`). The app logs every result as a
`SPIKE {json}` logcat line; `device.sh` writes them to `results/`.

## Results (2026-10-22)

Builds: GitHub `ubuntu-latest`, run [39849973441](https://github.com/the-dr-lazy/delmir/actions/runs/39849973441)
(`.github/workflows/spike-effect-rn.yml`). Device: the x86_64 KVM emulator from `#emulator`
(Android 16 / API 36, `sdk_gphone64_x86_64`) on the same runner. **No physical phone was available,** so the
timings below are emulator numbers, good for comparing variants, not absolute phone numbers. Raw data: `results/`.

| Measure | Result |
|---|---|
| Release build, sandboxed Nix (`hermesc`) | all 10 variants build (arm64-v8a and x86_64), 6–7 min each |
| Dev build (Metro + Hermes from source) | debug APK runs `index.js` served by Metro: `dev: true`, key, migrations and first data OK |
| `import.meta` plugin | required: without it `hermesc` fails `'import.meta' is currently unsupported` (release and dev) |
| `@babel/plugin-transform-export-namespace-from` | not needed |
| Unpatched `effect/sql/Migrator` | Metro fails: `Invalid call at line 218: import(…)` |
| Hermes | `260318099.0.4`, bytecode 99, Static Hermes, JIT off |
| `typeof` on device | `TextDecoder` function (decodes correctly), `FinalizationRegistry` function, `WeakRef` function, `crypto.getRandomValues` function (polyfill), `Symbol.dispose` undefined, `structuredClone` undefined |
| SQLCipher flag in the Nix sandbox | yes: Gradle prints `[OP-SQLITE] using sqlcipher.` in every variant; `PRAGMA cipher_version` = 4.14.0 (op-sqlite 17.2.0), 4.19.0 (18.2.5) |
| DB unreadable without the key | `sqlite3`: `file is not a database (26)`; marker absent from raw bytes; `sqlcipher` with the key reads it; plain control DB readable |
| Key in Keystore | `react-native-keychain` 10.0.0 works under bridgeless: storage `KeystoreAESGCM_NoAuth`; first-run create ≈60–230 ms. `react-native-sensitive-info` not needed |
| op-sqlite 18.2.5 | passes commit, rollback, savepoint, `withAsyncQuery`, async transaction (same as 17.2.0) |
| Migrator workarounds | both run: `Migrator.fromRecord` (patched) applies `1_cases, 2_cases_created_at`, re-run applies nothing; local runner the same; local runner bundles with `effect` unpatched |
| Hermes bytecode in APK (arm64) | baseline 1,333,080 B; Effect + registry 2,959,020 B (+1.63 MB); local runner 2,939,668 B |
| `effect/Arbitrary` in the graph | +158,659 B bytecode (offline `hermesc -O`, `results/offline.txt`) |
| Minified JS by package | `effect` 852 KiB, `react-native` 735 KiB |
| APK (arm64, unsigned) | baseline 30.8 MB, Effect 32.5 MB; SQLCipher's `libcrypto.so` 5.0 MB + `libop-sqlite.so` 1.7 MB are in both |
| Cold start → first screen, median of 10 (emulator) | baseline 896 ms, Effect 952 ms (op18) / 980 ms (local) [`am` TotalTime 579 vs 586 / 575 ms] |
| 1,000 cases, query + Schema decode, median / p90 of 20 (emulator) | sync 153 / 170 ms (query 22, decode 131); `withAsyncQuery` 164 / 180 ms (query 24, decode 141) |
| JS frames dropped during the 20 runs | sync 173, async 159 (longest gap 188 vs 172 ms): decode blocks the JS thread either way |
| Backup | `allowBackup=false` (no `ALLOW_BACKUP` flag); `bmgr backupnow`: `Backup is not allowed`; `dataExtractionRules` excludes every domain |

The first variant measured after the emulator booted (`apk-x86_64`) ran 2–4× slower than the rest (warm-up), so
its timings are left out above.

Build fixes found:

- op-sqlite 17.2.0 sets no `ndkVersion`, and none of the native libraries set `buildToolsVersion`, so AGP falls back
  to NDK 28.2.13676358 and build-tools 36.0.0, which the SDK does not have. `android/build.gradle` pins both.
- AGP's `lintVital*` tasks run on release builds and read Google Maven's `master-index.xml` / `group-index.xml`.
  mitm-cache recorded 14 of them into `deps.json`, and one changed within hours (hash mismatch on rebuild).
  `package.nix` skips `lintVitalRelease`, `lintVitalAnalyzeRelease` and `lintVitalReportRelease`, and `deps.json`
  now has none. The lockfile is byte-identical for op-sqlite 17 and 18.
- RN's `URL` has no `hostname` or `searchParams` for a custom scheme, so parse deep links by hand. A link sent to the
  running app (`onNewIntent`) never reached JS's `Linking` `url` event on the emulator; links that launch the app
  (`getInitialURL`) work.
- The local host's network dropped mitm-cache and cache.nixos.org fetches (as in #32), so lockfiles are recorded in CI.
