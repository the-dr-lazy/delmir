# How does the Effect ecosystem fit a bare React Native app?

Research for ticket #17. Checked 2026-10-21 against primary sources: package tarballs, source repositories, maintainers' issues and official docs. Claims I could not verify are marked **Unverified**.

## Answer

**Verdict: Effect 4 fits bare React Native 0.88 on Hermes V1, with three known workarounds:**

- **(1)** A Babel plugin that replaces `import.meta`.
- **(2)** A `crypto.getRandomValues` polyfill.
- **(3)** Until effect 4.1: avoid or patch `effect/sql/Migrator`, whose dynamic `import()` Metro rejects.

Metro has no tree shaking, so expect about 0.8 MB of minified Effect JS (my estimate). Every public Effect-on-RN app found uses Expo, so DELMIR's bare setup needs a short spike before #26 settles it.

Recommended stack:

- **Runtime:** React Native 0.88 (Hermes `260318099.0.4`, the first line with `FinalizationRegistry`), React 19.3, `effect`/`@effect/*` 4.0.5 pinned, moving to 4.1 when it ships the Migrator fix.
- **Babel/Metro:** `@react-native/babel-preset` + `@react-native/metro-config` 0.88 defaults (package exports are on), plus a local `import.meta` → `{}` plugin. Import Effect only by subpath (`effect/Effect`, `effect/Schema`, `effect/sql/SqlClient`, `effect/reactivity/Atom`, `@effect/sql-sqlite-react-native/SqliteClient`), never `effect` or `effect/sql` barrels.
- **Polyfills:** `react-native-get-random-values` (UUIDs, encryption key), loaded first. Nothing for `AbortController`, `queueMicrotask`, `TextEncoder`, `WeakRef`, `performance` or `FinalizationRegistry`. Check `TextDecoder` on device.
- **State:** `@effect/atom-react` over `effect/reactivity` with one `Atom.runtime(layer)` for services. No hand-rolled `ManagedRuntime` hooks. Keep zoned `DateTime` for display only.
- **Navigation:** React Navigation 7 (`@react-navigation/native` 7.5.1, `native-stack` 7.21.0) with the static API. Route params carry case IDs only.
- **Schema:** interpreted decoding (no JIT). JSON Schema from `Schema.toJsonSchemaDocument` (Draft 2020-12, describes `Schema.toCodecJson`'s encoded side, brands dropped). Keep `arbitrary` out of the app's import graph.
- **Case registry:** `@effect/sql-sqlite-react-native` 4.0.5 on `@op-engineering/op-sqlite` 17.2.0 (peer `<18`) with `"op-sqlite": { "sqlcipher": true }`. The key lives in Android Keystore (library to pick in #26). Migrations via `Migrator.fromRecord`, patched or local runner until 4.1. Use `withAsyncQuery` for heavy queries. ECG images are files, not BLOBs. `allowBackup="false"` plus `dataExtractionRules` excluding the `database`, `file` and `sharedpref` domains for both cloud backup and device transfer.
- **Tests:** vitest 5 + `@effect/vitest` in Node for Effect code, contracts and SQL (via `@effect/sql-sqlite-node`). Jest 30 + `@react-native/jest-preset` + RNTL 14 for components.

## 1. Effect 4 on Hermes

**Verdict: Effect 4 core runs on the Hermes that ships with React Native 0.88. One build-time fix is required (`import.meta`). One polyfill is needed if DELMIR makes UUIDs or uses Effect's `Crypto` (`crypto.getRandomValues`). Everything else DELMIR plans to use is covered by Hermes V1 or by React Native's own globals.**

Engine baseline:

- React Native 0.88.0 is the current `latest` on npm. It depends on `hermes-compiler@260318099.0.4`, which is npm's `latest-v1` tag ([npm: react-native@0.88.0 dependencies](https://www.npmjs.com/package/react-native/v/0.88.0); [RN 0.88 release post, "Hermes moves to 260318099.0.4"](https://github.com/facebook/react-native-website/blob/main/website/blog/2026-10-19-react-native-0.88.mdx)).
- Hermes V1 has been the default engine since React Native 0.84. Opting out means pinning the legacy `hermes-compiler` ([RN 0.84 release post](https://github.com/facebook/react-native-website/blob/main/website/blog/2026-02-11-react-native-0.84.mdx)). Hermes V1 is built from the `static_h` branch ([Hermes blog, June 2026](https://github.com/facebook/hermes/tree/static_h/doc/blog)). Static Hermes's typed ahead-of-time compilation to native code is not part of React Native's default pipeline. **Unverified**: I found no RN doc that turns it on.
- React Native 0.84–0.87 shipped Hermes `250829098.0.x`. That line has no `FinalizationRegistry` ([Hermes `lib/VM/JSLib` at hermes-v250829098.0.19](https://github.com/facebook/hermes/tree/hermes-v250829098.0.19/lib/VM/JSLib)). 260318099 adds it ([same dir at hermes-v260318099.0.4](https://github.com/facebook/hermes/tree/hermes-v260318099.0.4/lib/VM/JSLib); [GlobalObject.cpp](https://github.com/facebook/hermes/blob/hermes-v260318099.0.4/lib/VM/JSLib/GlobalObject.cpp)). **So use RN ≥ 0.88.**

Code in `effect@4.0.5`'s `dist` that touches each API. I grepped code lines and skipped JSDoc, which is full of examples. Hermes/RN support is checked against the sources linked.

| API | Where Effect 4.0.5 uses it (code, not docs) | Hermes V1 / RN 0.88 | Needed for DELMIR? |
|---|---|---|---|
| `import.meta` | `ConfigProvider.fromEnv` default: `...import.meta?.env` (`dist/ConfigProvider.js`). It reaches any bundle that imports `effect/Config`, the root `effect` barrel, or `@effect/sql-sqlite-react-native/SqliteClient`, which imports `Config` for `layerConfig`. It is not in the `effect/Effect` or `effect/Schema` closures alone (my import-closure check). | **Compile error.** Hermes's resolver rejects it with "'import.meta' is currently unsupported" ([SemanticResolver.cpp](https://github.com/facebook/hermes/blob/hermes-v260318099.0.4/lib/Sema/SemanticResolver.cpp)). Metro 0.87.1 and `@react-native/babel-preset` 0.88 do not rewrite it (grep of both packages). | **Yes: a Babel plugin that replaces `import.meta` with `{}`**, as in the working RN 0.87 config posted on [effect#6252](https://github.com/Effect-TS/effect/issues/6252). The maintainers keep the token on purpose for Vite ([effect#6358](https://github.com/Effect-TS/effect/issues/6358), tim-smart's comment; guard PR [#6570](https://github.com/Effect-TS/effect/pull/6570) closed unmerged; [#7105](https://github.com/Effect-TS/effect/pull/7105) added `ConfigProvider.fromEnvRecord` but "the existing `import.meta` auto-detection token remains"). |
| `crypto.getRandomValues` / `randomUUID` | `internal/uuid.js` (used by `schema/Model` UUID fields and the event log), `Random.js` (unseeded ISAAC only), `Crypto` service implementations | Hermes has no `crypto` global (none in GlobalObject.cpp), and RN does not add one ([setUpXHR.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/Libraries/Core/setUpXHR.js), [setUpDefaultReactNativeEnvironment.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/src/private/setup/setUpDefaultReactNativeEnvironment.js)) | **Yes, if DELMIR makes case IDs as UUIDs on the phone.** Polyfill with `react-native-get-random-values` 2.0.0 (npm), or `react-native-quick-crypto` 1.1.8 if real `crypto.subtle` is also wanted. |
| `TextEncoder` / `TextDecoder` | Byte encodings (`encoding/Base64`, `Hex`), HTTP bodies, `Stream.decodeText`/`encodeText`, `KeyValueStore`, RPC | `TextEncoder` has been built in for a long time ([TextEncoder.cpp](https://github.com/facebook/hermes/tree/hermes-v250829098.0.19/lib/VM/JSLib)). `TextDecoder` is new in 260318099 as a *contrib* extension ([extensions/contrib](https://github.com/facebook/hermes/tree/hermes-v260318099.0.4/API/hermes/extensions/contrib); Hermes blog: "`TextDecoder` now ships with the engine"). It is built only with `HERMES_ENABLE_CONTRIB_EXTENSIONS` ([Extensions.cpp](https://github.com/facebook/hermes/blob/hermes-v260318099.0.4/API/hermes/extensions/Extensions.cpp)). | Probably fine. **Unverified on device**: check `typeof TextDecoder` in the spike. Fallback: a small polyfill. |
| `AbortController` / `AbortSignal` (`timeout`, `any`) | `Effect.promise`/`tryPromise` signal, `Effect.abortSignal`, `HttpClient` | RN installs its own `AbortController`/`AbortSignal`, including `timeout` and `any` ([setUpXHR.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/Libraries/Core/setUpXHR.js), [AbortSignal.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/src/private/webapis/dom/abort-api/AbortSignal.js)) | No polyfill. |
| `queueMicrotask`, `setImmediate` | The scheduler uses `setImmediate` when present, else `setTimeout(0)` (`Scheduler.js`). `queueMicrotask` appears only in docs. | Hermes defines `queueMicrotask` when the microtask queue is on ([GlobalObject.cpp](https://github.com/facebook/hermes/blob/hermes-v260318099.0.4/lib/VM/JSLib/GlobalObject.cpp)). RN sets timers up in `setUpTimers` | No polyfill. |
| `WeakRef` / `FinalizationRegistry` | `reactivity/Atom.family` (falls back to a strong map without them), `http/HttpClient` response registry | `WeakRef` is present. `FinalizationRegistry` arrives in 260318099 (RN 0.88). The leak on runtimes without `FinalizationRegistry` ([effect#8750](https://github.com/Effect-TS/effect/issues/8750)) is fixed in 4.0.5 with a `WeakMap` of timers (fix PR [#8830](https://github.com/Effect-TS/effect/pull/8830); verified in `dist/http/HttpClient.js`) | No polyfill. |
| `Intl.DateTimeFormat` | `DateTime` zones and formatting (`internal/dateTime.js`), CLI output | Hermes Intl covers only basic `DateTimeFormat`/`NumberFormat` ([Hermes Features.md](https://github.com/facebook/hermes/blob/static_h/doc/Features.md)). The Android Intl is Java-backed and omits `fractionalSecond`, which broke zoned `DateTime` ([effect#8689](https://github.com/Effect-TS/effect/issues/8689); fix [#8707](https://github.com/Effect-TS/effect/pull/8707); 4.0.5 has the fallback) | Keep case timestamps as UTC epoch millis. Use zoned `DateTime` only for display. |
| `Symbol.asyncIterator`, async generators | `Stream.toAsyncIterable`, `Channel` | Hermes V1 has them, but its blog marks them "not tested in production". The RN Babel preset lowers async generators anyway ([babel-preset main.js](https://www.npmjs.com/package/@react-native/babel-preset/v/0.88.0)) | Avoid `Stream.toAsyncIterable` on the phone. |
| `ReadableStream`, streaming `fetch` | `FetchHttpClient` response streams, `Stream.fromReadableStream`/`toReadableStream`, compression | RN's `fetch` is `whatwg-fetch` over XHR and has no streaming body ([Network/fetch.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/Libraries/Network/fetch.js)). Hermes has no `ReadableStream` | Not needed: reading and the case registry are offline. Buffered `json`/`text`/`arrayBuffer` responses work. |
| `structuredClone` | Only inside the bundled Swagger/Scalar UI page strings in `http-api/internal` (not executed on the phone) | Absent from Hermes | No. |
| `performance.now` | Clock nanos in `internal/effect.js`, with a `typeof` guard and a fallback | RN sets `global.performance` ([setUpPerformance.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/src/private/setup/setUpPerformance.js)) | No. |
| `Symbol.dispose`/`asyncDispose` | `Effect.acquireDisposable`, `ManagedRuntime[Symbol.asyncDispose]` (a computed key, harmless if undefined) | Not listed in Hermes Features.md. **Unverified** | No (do not use `await using`). |
| `new Function` | `schema/SchemaJITCompiler.js` only, opt-in (see section 4) | Works only if Hermes keeps its runtime compiler. **Unverified for release builds** | No (do not enable the JIT). |
| dynamic `import()` | `sql/Migrator.js` `fromFileSystem` | Metro rejects non-literal `import()` (section 2 and 5) | Avoid in 4.0.x (section 5). |

Earlier RN-specific breakages, now fixed:

- In v4 betas, exports named `Array` (and similar) shadowed globals once lowered to CommonJS, causing "Function is not a constructor" under Metro. Fixed in [effect-smol#1863](https://github.com/Effect-TS/effect-smol/pull/1863) for [effect-smol#1861](https://github.com/Effect-TS/effect-smol/issues/1861). The v3 analogue was [effect#2555](https://github.com/Effect-TS/effect/pull/2555).
- `Effect.fn` with transpiled generator bodies (babel-preset-expo) crashed in v3 ([effect#6254](https://github.com/Effect-TS/effect/pull/6254), still open, against v3). In 4.0.5, `Effect.fn` wraps any returned iterator with `fromIteratorUnsafe` and no longer sniffs `GeneratorFunction` (`dist/internal/effect.js`, `makeFn`). The bare RN preset uses regenerator only in dev builds ([babel-preset main.js](https://www.npmjs.com/package/@react-native/babel-preset/v/0.88.0), `enableRegenerator = isHermesProfile && dev`).
- [effect#6252](https://github.com/Effect-TS/effect/issues/6252) ("Can't use Effect with React Native", 4.0.0-beta.70, Expo, `useAtomSuspense` crash) was closed after a user reported the fix (shown as an image) and another user posted a working RN 0.87 Babel config. That config's essentials: `import.meta` replacement, `@babel/plugin-transform-export-namespace-from`, and `@babel/plugin-transform-object-rest-spread` applied to `effect`/`@effect/*` dist files.

**Required setup for bare RN 0.88:** (1) a Babel `import.meta` → `{}` plugin; (2) `react-native-get-random-values` imported first in `index.js`, if UUIDs are made on the phone; (3) possibly `@babel/plugin-transform-export-namespace-from`. Effect's barrels use `export * as X`. `@react-native/babel-preset` 0.88 does not include that plugin (its `passthrough-syntax-plugins` hold only nullish-coalescing and optional-chaining syntax), but [effect#9157](https://github.com/Effect-TS/effect/pull/9157) reports that the `effect/sql` barrel bundles with stock RN defaults. **Unverified**: add the plugin only if the spike fails without it. Settle all three in the spike.

## 2. Bundling with Metro

**Verdict: Metro resolves Effect 4's `exports` out of the box, but it does no tree shaking. A typical DELMIR Effect slice therefore costs about 0.8 MB of minified JS (≈0.22 MB gzipped) in the bundle, instead of about 0.17 MB with a tree-shaking bundler. That is acceptable for an app whose ONNX model is far larger. Import subpaths, never the root barrel.**

- **Package exports.** Metro 0.87.1 defaults `resolver.unstable_enablePackageExports: true` ([metro-config defaults](https://www.npmjs.com/package/metro-config/v/0.87.1), `src/defaults/index.js`). `@react-native/metro-config` 0.88.0 adds `unstable_conditionNames: ["react-native"]` ([dist/index.js](https://www.npmjs.com/package/@react-native/metro-config/v/0.88.0)). Effect 4's `exports` uses plain strings with no conditions: `".": "./dist/index.js"`, `"./*": "./dist/*.js"`, plus folder barrels such as `"./sql"` and `"./reactivity"`, and blocks `./internal/*` (`package.json` of effect@4.0.5). So `effect/Schema`, `effect/Effect`, `effect/sql/SqlClient` and `effect/reactivity/Atom` all resolve. PR [effect#9157](https://github.com/Effect-TS/effect/pull/9157) states it was bundle-tested with "Metro 0.87.1 (`@react-native/metro-config` defaults, package exports enabled)".
- **Module paths changed in 4.0.** Stable 4.0.x has no `effect/unstable/*`. The former unstable modules are top-level folders: `effect/http`, `effect/sql`, `effect/reactivity`, `effect/rpc`, `effect/persistence`, `effect/schema`, and so on (`exports` of effect@4.0.5; see also the `effect/http` import in [effect#8750](https://github.com/Effect-TS/effect/issues/8750)). Individual modules inside them may still carry `@stability unstable` in JSDoc.
- **ESM only.** `effect` is `"type": "module"` with ESM `dist`. Metro's Babel preset lowers it to CommonJS with `@babel/plugin-transform-modules-commonjs`, and `inlineRequires: true` is on by default ([babel-preset](https://www.npmjs.com/package/@react-native/babel-preset/v/0.88.0); [metro-config](https://www.npmjs.com/package/@react-native/metro-config/v/0.88.0)). `experimentalImportSupport` defaults to `false`.
- **Tree shaking.** Metro 0.87.1 has none: there is no tree-shaking or dead-export code in `metro`, `metro-transform-worker` or `metro-transform-plugins` 0.87.1 (grep of the packages). Every module reachable through an `import` ships whole. Expo's experimental tree shaking lives in `@expo/metro-config`, not in bare RN. [effect#4093](https://github.com/Effect-TS/effect/issues/4093) (v3, Metro) reports the same thing: bundles grow even for a few imports. Importing `import * as Array from "effect/Array"` helped there.
- **Dynamic `import()`.** Metro throws `InvalidRequireCallError` on any `import()` whose argument is not a literal, and `dynamicDepsInPackages` does not soften this, because `processImportCall` throws before that option is consulted ([metro 0.87.1 `collectDependencies.js`](https://www.npmjs.com/package/metro/v/0.87.1)). This is why `effect/sql/Migrator` broke ([effect#6347](https://github.com/Effect-TS/effect/issues/6347)). See section 5 for the 4.0.x status.
- **Bundle size (my estimate, not a measurement on a device).** I computed the static import closure of the `dist` files and minified each file with `bun build --no-bundle --minify`. That approximates Metro, which keeps every module whole. For comparison, a tree-shaking bundle of a sample app (`bun build --minify`):

| Entry points (effect 4.0.5) | Modules | Minified, summed (≈ Metro) | gzip of concat |
|---|---|---|---|
| `effect/Effect` | 65 | 223 KB | 64 KB |
| `effect/Schema` | 119 | 592 KB | 160 KB |
| `effect` (root barrel) | 221 | 1,022 KB | 275 KB |
| DELMIR-like slice: `Effect`, `Layer`, `Schema`, `ManagedRuntime`, `reactivity/Atom`, `@effect/atom-react`, `@effect/sql-sqlite-react-native`, `sql/Migrator` | 161 | 825 KB | 223 KB |
| Same slice, tree-shaken by bun (sample app using a struct schema, a SQL query, an atom and a runtime) | n/a | 173 KB | 57 KB |

  Hermes ships bytecode, not minified JS. Bytecode size differs and was not measured. Even so, Effect adds well under 1 MB to an APK that will carry an ONNX model. Startup parse cost is the more relevant number, and Hermes bytecode avoids parsing. **A measuring spike on a real release build is worthwhile** (see Risks).
- **Known Metro issues with Effect:** `Array`-named exports ([effect-smol#1861](https://github.com/Effect-TS/effect-smol/issues/1861), fixed), tree shaking ([effect#4093](https://github.com/Effect-TS/effect/issues/4093), inherent to Metro), the Migrator's dynamic `import()` ([effect#6347](https://github.com/Effect-TS/effect/issues/6347), fixed only on `v4/next-minor`), and `import.meta` (section 1, not fixed upstream by design).

## 3. State and UI integration with React

**Verdict: use `@effect/atom-react` 4.0.5 over `effect/reactivity` (`Atom`, `AtomRegistry`, `AsyncResult`), with one `Atom.runtime(layer)` holding the app's services: the case registry, the reading engine and the file store. Do not hand-roll a `ManagedRuntime` plus hooks. Use React Navigation 7 with its static API and `native-stack`. Keep navigation state out of Effect.**

- **What is current.** Atoms moved into core in v4. `effect/reactivity/Atom`, `AtomRegistry`, `AsyncResult`, `AtomRef`, `AtomRpc`, `AtomHttpApi`, `Hydration` and `Reactivity` are in `effect@4.0.5`'s `dist/reactivity`, and the React bindings are `@effect/atom-react@4.0.5` (npm `latest`, released in lockstep with `effect`; peer deps `react >=19 <20`, `scheduler >=0.25 <0.29`, `effect ^4.0.5`). RN 0.88 ships `scheduler@0.28.0` and requires `react ^19.3.0` ([npm: react-native@0.88.0](https://www.npmjs.com/package/react-native/v/0.88.0)), so the peers fit. The predecessors are for Effect 3 only: `@effect-atom/atom-react@0.7.0` peers on `effect ^3.22.1`, and `@effect-rx/rx-react@0.42.4` (last published 2025-08) peers on `effect ^3.17` (npm). Neither applies.
- **How it binds to React** (`@effect/atom-react` `dist/Hooks.js`, `RegistryContext.js`):
  - Values are read through `React.useSyncExternalStore`, so they are tear-free under concurrent rendering. Like any external store, an atom update renders synchronously, outside transitions.
  - `useAtomSuspense` throws a promise, the classic Suspense protocol (not React 19 `use()`), and suspends until an `AsyncResult` settles. That is the hook in the RN crash report [effect#6252](https://github.com/Effect-TS/effect/issues/6252), filed against beta.70 and since closed.
  - `RegistryProvider` builds an `AtomRegistry` whose scheduler is `scheduler.unstable_scheduleCallback(LowPriority, …)`, with a default idle TTL of 400 ms. It disposes the registry 500 ms after unmount, which survives StrictMode's double mount.
- **Runtime.** `Atom.runtime`/`Atom.context` builds a layer-backed runtime with a shared `memoMap` and `addGlobalLayer` (`dist/reactivity/Atom.js`). It plays the role of `ManagedRuntime`, but its lifetime is owned by the registry, and atoms built from it (`runtime.atom(effect)`, `runtime.fn(...)`) give loading/success/failure as `AsyncResult` with interruption on unmount. A hand-rolled `ManagedRuntime` plus `useEffect` would have to rebuild cancellation, Suspense and caching that the library already has. Keep `ManagedRuntime` only for non-React entry points, such as a headless task or tests.
- **Case registry reactivity.** `@effect/sql-sqlite-react-native`'s layer provides `Reactivity.layer` (`SqliteClient.js`). Queries wrapped in `Reactivity.query`/`mutation` keys can invalidate atoms when a case is saved. The exact wiring is for #26.
- **Navigation without Expo Router.**
  - React Navigation 7 is current: `@react-navigation/native@7.5.1` and `@react-navigation/native-stack@7.21.0` (npm `latest`). 8.0 is in alpha (`8.0.0-alpha.51`).
  - `native-stack` needs `react-native-screens >=4` (now 4.30.0) and `react-native-safe-area-context >=4` (now 5.10.1) (npm peers).
  - The static API (`createNativeStackNavigator({ screens: { … } })` + `createStaticNavigation`, `createNativeStackScreen`, `StaticScreenProps`, and the `RootNavigator` module augmentation for typed `useNavigation`) exists in 7.21 (checked in the package's `lib/module`) and is the documented default. Its one limit is that "the navigation structure must be static", while conditional screens through `if` are still allowed ([static vs dynamic](https://reactnavigation.org/docs/static-vs-dynamic); [native stack](https://reactnavigation.org/docs/native-stack-navigator)). DELMIR's screens are fixed (capture ECG image → reading → case → follow-up), so the static API fits.
  - **How Effect state relates:** route params carry only IDs (a case ID), never decoded objects. Screens read the case from a case-registry atom family keyed by ID. Navigation stays React Navigation's own state and is not mirrored into atoms.

## 4. Effect Schema at runtime on the phone

**Verdict: fine on Hermes. Decoding is interpreted by default: no `eval`, no `new Function`. Keep the opt-in JIT off. The JSON Schema that Nix emits for the pydantic models comes from `Schema.toJsonSchemaDocument` (Draft 2020-12), which describes the `Schema.toCodecJson` encoded form. Brands are dropped, as intended. `arbitrary` exports pull about 70 KB of generator code into the app bundle unless they are kept out of the phone's import graph.**

- **No dynamic code by default.**
  - `new Function` appears in exactly one runtime module, `schema/SchemaJITCompiler.js`, as `globalThis.Function(...)`. It is enabled only by importing the side-effect module `effect/schema/SchemaJITCompiler/enable` (listed in `sideEffects` in `package.json`). If dynamic function construction fails, it falls back to the interpreter.
  - The two other hits are the Swagger/Scalar HTML in `http-api/internal`, which ships as strings for browsers. There is no `eval(` anywhere in `dist` (grep).
  - `effect/schema/SchemaAOTCompiler` (and `SchemaAOTCompiler/Build`) generates static decoder modules at build time "for environments that disallow dynamic function construction". It is marked `@stability unstable` and must be regenerated on every schema or Effect change (`dist/schema/SchemaAOTCompiler.js` docs). That is a later optimisation for DELMIR, not a requirement.
- **Hermes and `eval`.** Hermes's `eval` is global-only ([Features.md](https://github.com/facebook/hermes/blob/static_h/doc/Features.md)). Hermes can compile source made at runtime ([compilation and runtime modes](https://github.com/facebook/hermes/blob/static_h/doc/blog/2025-11-02-hermes-compilation-runtime-modes.md)). **Unverified**: whether RN release builds keep that compiler, and how fast JIT-generated decoders run on Hermes. Since the JIT stays off, this does not matter.
- **Decoding cost on Hermes.** I found no published benchmark of Effect Schema on Hermes. Hermes V1 reports 2.7–3.4× faster `JSON.parse`/`stringify` and faster `Map`/`Set` ([Hermes blog, June 2026](https://github.com/facebook/hermes/blob/static_h/doc/blog/2026-06-05-new-hermes-stable-release.md)). A case is a small struct decoded a handful of times per screen, so cost is unlikely to matter. Decoding a long list of cases from the case registry is the one place to measure (Risks).
- **JSON Schema generation in v4** (`effect@4.0.5`):
  - `Schema.toJsonSchemaDocument(schema, options?)` "returns a JSON Schema document using draft 2020-12". The document "describes the encoded side of `Schema.toCodecJson(schema)`" (`dist/Schema.js` JSDoc). Transformations are therefore emitted as their JSON-encoded form, and `Schema.optional` fields accept `null` through the codec.
  - Lower-level entry points: `SchemaRepresentation.toRepresentation` → `SchemaRepresentation.toJsonSchemaDocument` / `toJsonSchemaMultiDocument`.
  - Dialect converters: `JsonSchema.toDocumentDraft07`, `toDocumentDraft04`, `toMultiDocumentOpenApi3_1` (`dist/JsonSchema.js`).
  - Generation is "best-effort". Regex flags, string length (code points vs UTF-16) and object checks can differ, and "the Effect decoder remains the final authority". Exact `oneOf` unions stay `oneOf`. Unions with approximations become `anyOf`. Identified schemas become definitions (references).
  - **Brands** "are not part of the schema AST and are therefore omitted" (`Schema.toRepresentation` JSDoc). This matches the project rule that brands are labels only. A branded ID in TypeScript is a plain string in pydantic.
- **`Schema.toCodecJson`** is stable (`@since 4.0.0`). Derivation runs no transformations. Declarations without a `toCodecJson`/`toCodec` annotation fall back to `Json` as the encoded schema. So any custom `Schema.declare` in `contracts/` needs a `toCodecJson` annotation, or its JSON Schema will be unconstrained.
- **Arbitrary.** In v4, `effect/Arbitrary` is Effect's own generator ("Derives, samples, and checks generated values from Effect Schema", `@stability unstable`) under `internal/arbitrary`. It has no `fast-check` dependency: `effect` has no runtime dependencies at all (`package.json`). The Schema closure without it is 592 KB minified. With `effect/Arbitrary` it is 663 KB (my per-file minify sum, section 2). Because DELMIR's data-type modules export `arbitrary` next to `schema`, Metro will ship that extra ~70 KB unless the app imports `schema`/`json` from a path that does not import `Arbitrary`. That can be a separate entry, or a lazy `arbitrary` getter that imports `effect/Arbitrary` only in tests. **Decision for #26.**

## 5. On-device storage for the case registry

**Verdict: `@effect/sql-sqlite-react-native` 4.0.5 over op-sqlite 17.x, with SQLCipher on and the key in Android Keystore. Two snags in 4.0.x: (1) `effect/sql/Migrator`, the `effect/sql` barrel and the package's own `SqliteMigrator`/root barrel do not bundle under Metro until effect 4.1. Import `@effect/sql-sqlite-react-native/SqliteClient` and `effect/sql/SqlClient` directly, and either patch `Migrator.js` (as a live app does) or run `fromRecord` migrations through a small local runner. (2) The peer range is op-sqlite `>=17.1.2 <18`, while op-sqlite `latest` is 18.2.5.**

- **Driver.**
  - `dist/SqliteClient.js` imports `@op-engineering/op-sqlite` and calls `open({ name, location?, encryptionKey? })`. `package.json` peers on `@op-engineering/op-sqlite >=17.1.2 <18.0.0` and `effect ^4.0.5`. Latest 17.x is 17.2.0. op-sqlite 18.0.0 (2026-08-14) removed cr-sqlite and reworked async/mutex behaviour ([release](https://github.com/OP-Engineering/op-sqlite/releases/tag/18.0.0)).
  - Two Effect 4.0.5 RN apps run op-sqlite 18.2.5 outside the peer range (prior art, section 7). That is **unverified** as safe. Pin 17.2.0 unless the spike shows 18 works.
- **How it runs** (`SqliteClient.js`):
  - One connection behind `Semaphore.make(1)`, with transactions through `SqlClient.makeSqliteAcquirers` and nested transactions as `SAVEPOINT`s.
  - By default each statement calls `db.executeSync` **on the JS thread**. `SqliteClient.withAsyncQuery(effect)` switches to `db.execute`, which returns a Promise. Use async for anything that touches many cases, so the UI does not stall.
  - `executeStream` is "not implemented". Use plain queries.
  - The race in which "a statement outside a transaction can run inside another fiber's transaction" ([effect#8920](https://github.com/Effect-TS/effect/issues/8920)) is fixed in 4.0.5 by [#8927](https://github.com/Effect-TS/effect/pull/8927) (merged to `main` 2026-10-08; the permit is now held through the statement in `dist/sql/SqlClient.js`).
  - Value queries were broken until [#7469](https://github.com/Effect-TS/effect/pull/7469) (fixed).
  - One gap remains: SQLite's own automatic rollback (`INSERT OR ROLLBACK`, `RAISE(ROLLBACK)`) still adds a cleanup defect on the RN client, because op-sqlite "can't report transaction state" ([#9599](https://github.com/Effect-TS/effect/pull/9599)). Avoid those SQL forms.
- **Migrations.**
  - The v4 `Migrator.make({ table = "effect_sql_migrations" })` runs all pending migrations in one `sql.withTransaction` (`dist/sql/Migrator.js`).
  - Loaders: `fromRecord({ "0001_init": effect })` (keys `<id>_<name>`), `fromGlob` (Vite `import.meta.glob`), `fromBabelGlob`, `fromFileSystem`. `fromRecord` needs no filesystem and is the one to use: each migration is an imported module, so it lives in the JS bundle.
  - **4.0.x blocker:** `Migrator.js` still contains `import(__rewriteRelativeImportExtension(url.href))` inside `fromFileSystem`. Metro refuses any non-literal `import()` at build time (section 2), even when only `fromRecord` is used ([effect#6347](https://github.com/Effect-TS/effect/issues/6347)).
  - The fix, [effect#9157](https://github.com/Effect-TS/effect/pull/9157), moves it to `effect/sql/MigratorFileSystem`. It was merged on 2026-10-14 to **`v4/next-minor`** with a *minor* changeset for `effect` and `@effect/sql-sqlite-react-native`, so it ships in 4.1.0, not in the pending 4.0.6 ([Version Packages #9197](https://github.com/Effect-TS/effect/pull/9197) is against `main`). The `effect/sql` barrel re-exports `Migrator`, and `@effect/sql-sqlite-react-native`'s root barrel re-exports `SqliteMigrator`, so both are affected.
  - Workaround in production: `vitalyiegorov/suuudokuuu` ships `patches/effect@4.0.5.patch`, which replaces that `import()` with `Effect.die(...)` and then uses `Migrator.fromRecord` ([patch](https://github.com/vitalyiegorov/suuudokuuu/blob/HEAD/patches/effect@4.0.5.patch); [runner](https://github.com/vitalyiegorov/suuudokuuu/blob/HEAD/packages/progress/src/migration/run-database-migrations.util.ts)). With npm + `importNpmLock` in Nix, the equivalent is a `postPatch`/`patch-package` step in the Nix build, or simply waiting for 4.1.
- **Encryption at rest (SQLCipher).** Turn it on with `"op-sqlite": { "sqlcipher": true }` in the app's root `package.json`. Some feature combinations are mutually exclusive and fail the build. Then `open({ name, encryptionKey })`, which `SqliteClient.make` already passes through as `encryptionKey` ([op-sqlite installation](https://github.com/op-engineering/op-sqlite/blob/main/docs/docs/installation.md); [API: SQLCipher open](https://github.com/op-engineering/op-sqlite/blob/main/docs/docs/api.md)). The docs stress "the single-connection-per-database rule", which the Effect client already follows. **Nix (unverified):** op-sqlite's native build reads this flag from the root `package.json`, so the Nix Android build must keep that file where Gradle finds it. Check this in the spike.
- **Key storage.** Generate a random key on first run (needs `crypto.getRandomValues`, section 1). Store it with the Android Keystore through a native module:
  - `react-native-keychain@10.0.0`: last npm release 2025-03, but the repo was pushed in 2026-04; 3.5k stars.
  - `react-native-sensitive-info@6.1.5`: 2026-06, a Nitro module, so it adds `react-native-nitro-modules`.
  - **Unverified:** whether either library declares RN 0.88 / New Architecture support, and which encrypted file it writes. Decide in #26.
  - The wrapped key blob is useless on another device, because the Keystore key is not backed up. That is one more reason to exclude the app's data from backup, below.
- **Excluding the case registry from Android backup.**
  - `android:allowBackup` defaults to `true`. On some manufacturers `allowBackup="false"` "doesn't disable device-to-device transfers" ([Android Auto Backup](https://developer.android.com/identity/data/autobackup)).
  - For API 31+, set `android:dataExtractionRules` with both `<cloud-backup>` and `<device-transfer>` sections that exclude `domain="database"` (op-sqlite's Android default location is the database directory, `ANDROID_DATABASE_PATH`, per [op-sqlite configuration](https://github.com/op-engineering/op-sqlite/blob/main/docs/docs/configuration.md)), `domain="file"` for ECG images, and `domain="sharedpref"` for the wrapped key. A missing section means "that mode is fully enabled".
  - For API ≤ 30, also set `android:fullBackupContent`.
  - The simplest safe setting is `allowBackup="false"` *plus* exclude-everything `dataExtractionRules`. Backup and export happen only through an explicit case export.
- **Alternatives, briefly.** `expo-sqlite@58` needs Expo modules. `react-native-nitro-sqlite@10.2.0` has no Effect driver. `@effect/sql-sqlite-wasm` is for web. Drizzle on op-sqlite is what `budgie-at/budgie` does for migrations (section 7). None beats the first-party Effect driver for DELMIR.
- **ECG images: files, not BLOBs.** Recommendation, not measured:
  - Store each ECG image as a file under app-private storage (`filesDir`), excluded from backup, and keep its relative path plus a content hash in the case.
  - BLOBs would bloat the SQLCipher pages, make every case query and `VACUUM` heavier, and push megabytes across JSI per read. Native image and ONNX code wants a file path anyway.
  - op-sqlite does support `ArrayBuffer`/`Uint8Array` BLOBs ([API: blobs](https://github.com/op-engineering/op-sqlite/blob/main/docs/docs/api.md)), which suits small derived data.
  - Trade-off: files are not covered by SQLCipher, so encrypt them separately or accept file-level protection. Decide in #28.

## 6. Testing

**Verdict: split. Use vitest 5 + `@effect/vitest` 4.0.5 in Node for everything that is Effect or contracts: schemas, round-trips, case-registry queries (with `@effect/sql-sqlite-node` in place of op-sqlite), reading post-processing, and atoms through `AtomRegistry` without React. Use Jest 30 + `@react-native/jest-preset` + `@testing-library/react-native` 14 for the few component tests. Treat running RN components under vitest as experimental.**

- `@effect/vitest@4.0.5` peers on `vitest >=5.0.0 <6.0.0` (vitest `latest` is 5.0.5). It exports `it.effect`, `it.live`, `layer`, `flakyTest`, `prop` ("Runs a synchronous property test using schemas or arbitraries") and `addEqualityTesters` (`dist/index.js`). This fits the project's vitest toolchain, and the per-module `arbitrary` exports feed `prop` directly.
- Atoms are testable without React: `AtomRegistry.make()` plus `registry.get`/`mount`/`set` (`effect/reactivity/AtomRegistry`).
- SQL logic runs the same `SqlClient` interface on `@effect/sql-sqlite-node@4.0.5`, which needs only `effect` as a peer. SQLCipher and op-sqlite specifics still need the device spike.
- `@testing-library/react-native@14.1.0` peers on **`jest >=29`**, `react >=19`, `react-native >=0.78` and `test-renderer ^1` (npm). It is built for Jest, and RN 0.88 ships `@react-native/jest-preset@0.88.0`.
- RN components under vitest: `vitest-native@0.13.0` ("Run real React Native tests under Vitest", peers `vitest >=4 <6`, `@testing-library/react-native >=12 <15`) exists. It was first published 2026-03-07, has one maintainer and is at 0.x (npm). The older `vitest-react-native@0.1.5` was last published 2024-01. Fine to try later. Do not build the test strategy on it.
- Keep components thin, with logic in atoms and Effect services, so most tests are Node vitest tests and the Jest suite stays small.

## 7. Real-world apps and prior art

**Verdict: real but young. Several public RN 0.86–0.88 apps use Effect 4, atoms and the Effect SQLite driver. Every one found uses Expo. I found no bare-RN Effect app, so DELMIR's Babel/Metro setup (section 1) is the untested part.**

From a GitHub code search for `@effect/atom-react` / `@effect/sql-sqlite-react-native` in `package.json` files; most hits are vendored copies of the Effect repo:

| Repo | Stack | Notes |
|---|---|---|
| [pingdotgg/t3code](https://github.com/pingdotgg/t3code) `apps/mobile` (29k★) | Expo 58, RN 0.88.0, `effect`/`@effect/atom-react` 4.0.5 (pnpm catalog), React Navigation 7.5.1, `@effect/vitest` | Babel: `babel-preset-expo` with `unstable_transformImportMeta: true`, Expo's answer to the `import.meta` problem |
| [budgie-at/budgie](https://github.com/budgie-at/budgie) `packages/app` | Expo 58, RN 0.88, effect 4.0.5, atom-react, sql-sqlite-react-native 4.0.5, op-sqlite 18.2.5, `@effect/vitest` + vitest 5 | Same `unstable_transformImportMeta`. Migrations via Drizzle SQL files, not the Effect Migrator |
| [vitalyiegorov/suuudokuuu](https://github.com/vitalyiegorov/suuudokuuu) | Expo 58, RN 0.88, effect 4.0.5, atom-react, sql-sqlite-react-native, op-sqlite 18.2.5, expo-router | Patches `effect@4.0.5` `Migrator.js` to drop the dynamic `import()`, then uses `Migrator.fromRecord` |
| [lucas-barake/effect-local](https://github.com/lucas-barake/effect-local) `examples/chat/mobile` | Expo 57, RN 0.86, effect 4.0.0 | Local-first example |
| [evelant/synchrotron](https://github.com/evelant/synchrotron) | Expo 54, RN 0.81, sql-sqlite-react-native, op-sqlite 15 | Sync engine with an RN SQLite example (Effect version via catalog, not checked) |
| [nikgraf/calendar](https://github.com/nikgraf/calendar) `apps/ios` | Expo 57, RN 0.86, op-sqlite 17.2.0 | Small |

- The RN 0.87 bare-ish config posted on [effect#6252](https://github.com/Effect-TS/effect/issues/6252) (react-native-macos 0.87, `@react-native/babel-preset`, `hermes-v250829098.0.15`) is the closest bare-RN evidence: "Effect v4 family works well" with an `import.meta` replacement plugin and two Babel transforms.
- Livestore (Effect-based, RN support) used `@effect-atom` on Effect 3. The Hermes schema error in [effect#5547](https://github.com/Effect-TS/effect/issues/5547) came from Livestore's own schema support, not from Effect.

## Risks and open questions

Needs a spike: one bare RN 0.88 Android release build with Effect, op-sqlite + SQLCipher, and atoms, built by Nix.

1. **`import.meta` plugin.** Confirm that the Babel replacement is enough, in both dev (Metro + Hermes compiling source) and release (`hermesc`). The evidence is the Hermes source plus a third-party config, not a DELMIR build.
2. **`TextDecoder`, `Symbol.dispose`, Hermes JIT/`Function` in release.** Probe `typeof` on device. Only `TextDecoder` matters for DELMIR.
3. **Bundle size and startup.** Measure the release APK's JS/bytecode size and time to first screen with and without Effect. My 825 KB figure is a per-file minify sum, not a Metro measurement.
4. **Schema decode cost on Hermes** for N cases (say 1,000) from the case registry, sync vs `withAsyncQuery`.
5. **op-sqlite 17 vs 18.** The peer says `<18`. Two live apps run 18.2.5. Decide on the pin, and check that the SQLCipher flag in `package.json` reaches Gradle inside the Nix build.
6. **Migrator in 4.0.x.** Choose between a Nix-applied patch of `dist/sql/Migrator.js`, a local `fromRecord` runner, or waiting for 4.1.0 (merged to `v4/next-minor`, date unknown).

For grilling ticket **#26** ("How is the app built on bare React Native and Effect?"):

- the exact Babel/Metro config and where it lives in the Nix build;
- subpath-import lint rule (oxlint `no-restricted-imports` on `effect`, `effect/sql`, `@effect/sql-sqlite-react-native`);
- the Keystore library (`react-native-keychain` vs `react-native-sensitive-info`, both **unverified** for RN 0.88);
- how `contracts/` modules expose `arbitrary` without bundling `effect/Arbitrary`;
- the Atom runtime and layer layout;
- the Jest/vitest split in CI.

For grilling ticket **#28** ("What does a case in the case registry hold?"):

- ECG image as a file (path + hash) vs BLOB;
- whether ECG image files are encrypted separately from the SQLCipher case registry;
- case ID format (UUIDv7 made on the phone needs the random polyfill);
- timestamps as UTC epoch millis (Hermes Android `Intl` quirks);
- what a case export contains, since backup is off and the case export is the only way out.

## Versions checked

Checked on npm/GitHub on 2026-10-21.

| Package / component | Version | Note |
|---|---|---|
| `react-native` | 0.88.0 (`latest`) | released 2026-10-19; React `^19.3.0`, `scheduler` 0.28.0 |
| `hermes-compiler` | 260318099.0.4 (`latest-v1`) | used by RN 0.88; RN 0.84–0.87 used 250829098.0.x |
| `metro` / `metro-config` | 0.87.1 | `unstable_enablePackageExports: true` by default |
| `@react-native/metro-config`, `@react-native/babel-preset`, `@react-native/jest-preset` | 0.88.0 | |
| `effect` | 4.0.5 (`latest`) | 4.0.6 pending in [#9197](https://github.com/Effect-TS/effect/pull/9197); Migrator fix targets 4.1 |
| `@effect/atom-react`, `@effect/vitest`, `@effect/sql-sqlite-react-native`, `@effect/sql-sqlite-node`, `@effect/platform-browser` | 4.0.5 | lockstep with `effect` |
| `@effect-atom/atom-react` | 0.7.0 | Effect 3 only |
| `@effect-rx/rx-react` | 0.42.4 | Effect 3 only, last published 2025-08 |
| `@op-engineering/op-sqlite` | 18.2.5 `latest`; 17.2.0 latest 17.x | Effect driver peers `>=17.1.2 <18` |
| `react` | 19.3.1 | |
| `@react-navigation/native` / `native-stack` | 7.5.1 / 7.21.0 | v8 in alpha |
| `react-native-screens` / `react-native-safe-area-context` | 4.30.0 / 5.10.1 | |
| `react-native-get-random-values` | 2.0.0 | |
| `react-native-quick-crypto` | 1.1.8 | |
| `react-native-keychain` / `react-native-sensitive-info` | 10.0.0 / 6.1.5 | |
| `vitest` | 5.0.5 | `@effect/vitest` needs `>=5 <6` |
| `jest` | 30.5.2 | |
| `@testing-library/react-native` | 14.1.0 | peers `jest >=29`, `test-renderer ^1` |
| `vitest-native` | 0.13.0 | experimental, first published 2026-03 |

## Sources

Effect issues and PRs:

- [effect#6252](https://github.com/Effect-TS/effect/issues/6252) Can't use Effect with React Native
- [effect#6358](https://github.com/Effect-TS/effect/issues/6358) `ConfigProvider.fromEnv` references `import.meta.env`
- [effect#6570](https://github.com/Effect-TS/effect/pull/6570) Guard `import.meta.env` (closed unmerged)
- [effect#7105](https://github.com/Effect-TS/effect/pull/7105) `ConfigProvider.fromEnvRecord`
- [effect#6347](https://github.com/Effect-TS/effect/issues/6347) Migrator dynamic imports break Metro
- [effect#9157](https://github.com/Effect-TS/effect/pull/9157) Move `fromFileSystem` to `MigratorFileSystem` (base `v4/next-minor`)
- [effect#9197](https://github.com/Effect-TS/effect/pull/9197) Version Packages 4.0.6
- [effect#8689](https://github.com/Effect-TS/effect/issues/8689) / [#8707](https://github.com/Effect-TS/effect/pull/8707) DateTime on Hermes Android Intl
- [effect#8750](https://github.com/Effect-TS/effect/issues/8750) / [#8830](https://github.com/Effect-TS/effect/pull/8830) HttpClient without `FinalizationRegistry`
- [effect#8920](https://github.com/Effect-TS/effect/issues/8920) / [#8927](https://github.com/Effect-TS/effect/pull/8927) SQLite statement/transaction race
- [effect#9599](https://github.com/Effect-TS/effect/pull/9599) SQLite automatic rollback
- [effect#7469](https://github.com/Effect-TS/effect/pull/7469) RN SQLite value queries
- [effect#5499](https://github.com/Effect-TS/effect/issues/5499) v3 RN SQLite silent failure
- [effect#4093](https://github.com/Effect-TS/effect/issues/4093) Metro tree shaking
- [effect#6254](https://github.com/Effect-TS/effect/pull/6254) `Effect.fn` with transpiled generators (v3)
- [effect#5547](https://github.com/Effect-TS/effect/issues/5547) RN + Livestore schema error
- [effect-smol#1861](https://github.com/Effect-TS/effect-smol/issues/1861) / [#1863](https://github.com/Effect-TS/effect-smol/pull/1863) v4 Metro import errors

Package sources, read from npm tarballs:

- `effect@4.0.5`: `dist/ConfigProvider.js`, `dist/internal/effect.js`, `dist/Scheduler.js`, `dist/Random.js`, `dist/internal/uuid.js`, `dist/internal/dateTime.js`, `dist/http/HttpClient.js`, `dist/reactivity/Atom.js`, `dist/schema/SchemaJITCompiler.js`, `dist/schema/SchemaAOTCompiler.js`, `dist/Schema.js`, `dist/JsonSchema.js`, `dist/SchemaRepresentation.js`, `dist/Arbitrary.js`, `dist/sql/Migrator.js`, `dist/sql/SqlClient.js`, `package.json`
- `@effect/sql-sqlite-react-native@4.0.5` (`dist/SqliteClient.js`, `dist/SqliteMigrator.js`, `dist/index.js`); `@effect/atom-react@4.0.5` (`dist/Hooks.js`, `dist/RegistryContext.js`); `@effect/vitest@4.0.5` (`dist/index.js`)
- `metro@0.87.1` (`src/ModuleGraph/worker/collectDependencies.js`), `metro-config@0.87.1` (`src/defaults/index.js`), `metro-transform-worker`/`metro-transform-plugins@0.87.1`, `@react-native/metro-config@0.88.0`, `@react-native/babel-preset@0.88.0` (`src/configs/main.js`, `src/passthrough-syntax-plugins.js`)
- `@react-navigation/native@7.5.1`, `@react-navigation/native-stack@7.21.0` (`lib/module`)

Hermes:

- [Features.md](https://github.com/facebook/hermes/blob/static_h/doc/Features.md)
- [New Hermes stable release (2026-06-05)](https://github.com/facebook/hermes/blob/static_h/doc/blog/2026-06-05-new-hermes-stable-release.md)
- [Compilation and runtime modes](https://github.com/facebook/hermes/blob/static_h/doc/blog/2025-11-02-hermes-compilation-runtime-modes.md)
- [GlobalObject.cpp @ hermes-v260318099.0.4](https://github.com/facebook/hermes/blob/hermes-v260318099.0.4/lib/VM/JSLib/GlobalObject.cpp)
- [SemanticResolver.cpp @ hermes-v260318099.0.4](https://github.com/facebook/hermes/blob/hermes-v260318099.0.4/lib/Sema/SemanticResolver.cpp)
- [extensions @ hermes-v260318099.0.4](https://github.com/facebook/hermes/tree/hermes-v260318099.0.4/API/hermes/extensions)
- [JSLib @ hermes-v250829098.0.19](https://github.com/facebook/hermes/tree/hermes-v250829098.0.19/lib/VM/JSLib)

React Native:

- [0.88 release post](https://github.com/facebook/react-native-website/blob/main/website/blog/2026-10-19-react-native-0.88.mdx), [0.87](https://github.com/facebook/react-native-website/blob/main/website/blog/2026-08-11-react-native-0.87.mdx), [0.84 (Hermes V1 default)](https://github.com/facebook/react-native-website/blob/main/website/blog/2026-02-11-react-native-0.84.mdx)
- [setUpDefaultReactNativeEnvironment.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/src/private/setup/setUpDefaultReactNativeEnvironment.js), [setUpXHR.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/Libraries/Core/setUpXHR.js), [AbortSignal.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/src/private/webapis/dom/abort-api/AbortSignal.js), [fetch.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/Libraries/Network/fetch.js), [setUpPerformance.js](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/src/private/setup/setUpPerformance.js)

op-sqlite:

- [installation (package.json config)](https://github.com/op-engineering/op-sqlite/blob/main/docs/docs/installation.md), [API (SQLCipher open, blobs)](https://github.com/op-engineering/op-sqlite/blob/main/docs/docs/api.md), [configuration (locations)](https://github.com/op-engineering/op-sqlite/blob/main/docs/docs/configuration.md), [18.0.0 release](https://github.com/OP-Engineering/op-sqlite/releases/tag/18.0.0)

Android:

- [Auto Backup / data extraction rules](https://developer.android.com/identity/data/autobackup)

React Navigation:

- [Static vs dynamic API](https://reactnavigation.org/docs/static-vs-dynamic), [Native stack](https://reactnavigation.org/docs/native-stack-navigator), [TypeScript (static)](https://reactnavigation.org/docs/typescript?config=static)

Prior art:

- [pingdotgg/t3code](https://github.com/pingdotgg/t3code), [budgie-at/budgie](https://github.com/budgie-at/budgie), [vitalyiegorov/suuudokuuu](https://github.com/vitalyiegorov/suuudokuuu), [lucas-barake/effect-local](https://github.com/lucas-barake/effect-local), [evelant/synchrotron](https://github.com/evelant/synchrotron), [nikgraf/calendar](https://github.com/nikgraf/calendar)

npm registry metadata (`npm view … dist-tags peerDependencies`) for every package in "Versions checked".
