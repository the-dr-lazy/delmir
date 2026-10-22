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

## Results

See the resolution comment on #43 and `results/`.
