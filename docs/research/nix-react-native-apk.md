# Building DELMIR's React Native APK in the Nix sandbox

Research for [the-dr-lazy/delmir#31](https://github.com/the-dr-lazy/delmir/issues/31), carried out 2026-10-21. Versions are as of that date: React Native 0.88.0 (released 2026-10-15), nixpkgs `nixos-unstable` at `02c087f3fe673c9e317f206a627cb6b910336dbe`, onnxruntime-react-native 1.24.3. Nothing here has been built. Every claim links to its source, and estimates are marked as estimates.

## Answer

**Yes, with caveats. A Nix derivation can build a bare React Native Android APK with no network in the sandbox, and people do it today.** The method that works is nixpkgs' `gradle.fetchDeps`, which runs a recording proxy (mitm-cache) and writes a `deps.json` lockfile. Three public derivations build React Native or Expo apps this way: Joplin's mobile app, the `bb` Expo app (RN 0.86.2), and XMTP's React Native consumer apps ([Working examples](#working-examples)). gradle2nix is not a realistic option for RN 0.88: its v2 branch was last updated for Gradle 8.14.3 in August 2025, and RN 0.88 needs Gradle 9 and AGP 9.2.1.

**The caveats.** About ten well-understood workarounds are needed:

- point aapt2 at the SDK's patched copy;
- give Gradle JDK 17 and turn off toolchain auto-download;
- pin `cmake.dir` and give AGP a writable `ANDROID_USER_HOME`;
- make autolinking's `npx` call work offline;
- pin ONNX Runtime's Maven version, because `onnxruntime-react-native` asks for `latest.integration`;
- maybe more ([Known problems](#known-problems-and-their-fixes)).

**The maintenance cost.** Any change to Gradle-side dependencies (an RN bump, a native module, a Gradle or AGP change) means re-running `nix build .#apk.mitmCache.updateScript && ./result`. That is a full networked build, likely 10–30 minutes (my estimate). It rewrites a `deps.json` of a few hundred KB, which you commit. JS-only changes need no lockfile work, because `importNpmLock` reads `package-lock.json` directly. Every change under `app/` triggers a full, non-incremental APK rebuild in CI.

**The size cost** is about 2.6 GB of unpacked Android SDK, NDK and CMake that cache.nixos.org does not carry, plus an estimated 0.5–1 GB of Maven artifacts. The Android SDK licence forbids redistribution, so the SDK should not go into a public Cachix cache.

**Recommendation: a hybrid, gated on a measuring spike.** Build an **unsigned** (or committed-debug-key-signed) release APK as a flake package, one ABI (`arm64-v8a`), and run it under `nix flake check`. Sign it outside Nix with `apksigner`. Push Maven/npm fetches and the APK to Cachix but exclude the Android SDK. Keep the `app` devenv shell for day-to-day development (Metro, `installDebug`) either way; the Nix derivation adds a CI artifact and does not replace the incremental dev loop. If the spike shows cold builds that don't fit the CI runner (14 GB disk), or an update script that needs constant hand-patching, take the ADR's fallback: build the APK impurely in the devenv shell and keep everything else in Nix.

## What works today

### nixpkgs `gradle.fetchDeps` (mitm-cache): use this

`gradle.fetchDeps { pkg = finalAttrs.finalPackage; data = ./deps.json; }` sets `mitmCache` on a derivation ([gradle.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/gradle.section.md)). How it works:

- **Recording.** `mitmCache.updateScript` builds the source with `srcOnly` and enters a `nix-shell` for the derivation inside a `bwrap` sandbox that has network. It runs `unpackPhase`, `patchPhase`, `configurePhase`, then `preBuild`/`preGradleUpdate` and the `gradleUpdateTask`. All the while it records every HTTP(S) response through `mitm-cache record`. `.md5`/`.sha*` requests are rejected and redirects are forgotten ([update-deps.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/update-deps.nix), [README](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/README.md)). The result is compressed into `deps.json`: URLs plus SRI hashes, and for `maven-metadata.xml` only `groupId`/`release`/`latest`/`lastUpdated`. The XML itself is regenerated in Nix ([fetch-deps.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/fetch-deps.nix), [compress-deps-json.py](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/compress-deps-json.py)).
- **Fetching.** `mitm-cache.fetch` turns each URL into its own `fetchurl` fixed-output derivation and symlinks them into one tree ([fetch.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/by-name/mi/mitm-cache/fetch.nix)). There is no hand-maintained hash, which meets ADR 0004's lockfile rule.
- **Replaying.** In the real build, the mitm-cache setup hook generates a throwaway CA and starts `mitm-cache replay` on `127.0.0.1` ([setup-hook.sh](https://github.com/NixOS/nixpkgs/blob/master/pkgs/by-name/mi/mitm-cache/setup-hook.sh)). The Gradle hook then adds `--no-daemon`, the proxy host and port, and a truststore; without a `mitmCache` it adds `--offline` instead ([gradle setup-hook.sh](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/setup-hook.sh)). Only loopback networking is used; the sandbox stays closed.
- **What exists in nixpkgs.** nixpkgs unstable ships `gradle_9` = 9.8.0 (default JDK 25) and `gradle_8` = 8.14.4. The default `gradle` is `gradle_8`. `gradle-packages.mkGradle` builds any other version ([gradle default.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/default.nix)). mitm-cache is 0.1.2 and is on cache.nixos.org (checked: narinfo 200).

Two traps for Android builds:

- **Use a real build task for `gradleUpdateTask`, not the default `nixDownloadDeps`.** The default resolves every resolvable configuration ([init-deps.gradle](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/init-deps.gradle)), but AGP resolves things like aapt2 in detached configurations at execution time. Mic92's tincr says it directly: "AGP variant matching breaks the generic nixDownloadDeps task" ([tincr android-app.nix](https://github.com/Mic92/tincr/blob/HEAD/nix/android-app.nix)). Every Android example below sets `gradleUpdateTask = gradleBuildTask`.
- **The default init script can break AGP.** It turns on reproducible archives, which the nixpkgs manual warns can break some builds ([gradle.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/gradle.section.md)). The newpipe derivation replaces it with an empty script: "reproducible archives break some Android Gradle Plugin tasks" ([newpipe package.nix](https://github.com/mio-19/nurpkgs/blob/HEAD/by-name/ne/newpipe/package.nix)).

**Flake detail.** When `data` is a store path, as it is in a flake, the update script writes to the path relative to the flake root ([update-deps.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/update-deps.nix), the `outPath` logic). So run `nix build .#apk.mitmCache.updateScript && ./result` from the repo root. The script needs `nix-shell` and, on Linux by default, `bwrap`. Joplin and newpipe set `useBwrap = false`.

### gradle2nix v2: not for this project

gradle2nix records dependencies through a Gradle plugin into `gradle.lock` and builds with `buildGradlePackage` ([README](https://github.com/tadfisher/gradle2nix/blob/v2/README.org)). Its state:

- **Stale for Gradle 9.** The v2 branch's latest commit is "Update for Gradle 8.14.3" (2025-08-22), and master's latest is from 2023. It is not in nixpkgs. RN 0.88's template uses Gradle 9.4.1 and AGP 9.2.1 ([template gradle-wrapper.properties](https://github.com/react-native-community/template/blob/0.88-stable/template/android/gradle/wrapper/gradle-wrapper.properties), [libs.versions.toml](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml)).
- **Android support is partial.** [#13 "Make gradle2nix work for android projects"](https://github.com/tadfisher/gradle2nix/issues/13) is still open. [PR #67 "Add support for Android builds"](https://github.com/tadfisher/gradle2nix/issues/67) fixed `~/.android` writes. Its thread records that a patched aapt2 had to be injected through `overrides`, because overriding with an older SDK aapt2 failed with "unknown option '--source-path'". [#86](https://github.com/tadfisher/gradle2nix/issues/86) (Kotlin Android app, 2025–2026) needed workarounds to get debug builds working.
- **The author steers project builds elsewhere.** In #13, tadfisher says gradle2nix "isn't geared toward usage in a project, but more toward packaging third-party projects".

ADR 0004 lists gradle2nix as acceptable, but for RN 0.88 the only maintained option is `gradle.fetchDeps`.

### Plain Gradle lockfiles and verification metadata

Neither is enough alone. Gradle [dependency locking](https://docs.gradle.org/current/userguide/dependency_locking.html) pins versions but not URLs or hashes. [Dependency verification](https://docs.gradle.org/current/userguide/dependency_verification.html) (`verification-metadata.xml`) pins checksums but not URLs. XMTP uses `--dependency-verification=strict` *on top of* mitm-cache as a second check ([example-android-apk.nix](https://github.com/xmtp/libxmtp/blob/HEAD/nix/package/example-android-apk.nix)). That is optional for DELMIR.

### Android SDK, NDK and CMake: `androidenv` (or android-nixpkgs)

`androidenv.composeAndroidPackages` takes `platformVersions`, `buildToolsVersions`, `includeNDK` + `ndkVersions`, `includeCmake` + `cmakeVersions` and more ([android.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md)). The SDK root is `${androidsdk}/libexec/android-sdk`. Every version RN 0.88 needs is in nixpkgs' [repo.json](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/repo.json):

| Component | RN 0.88 wants | Available in androidenv |
|---|---|---|
| Platform | compileSdk 37 | `platforms` 37.0, 37.1 |
| Build-tools | 37.0.0 | 37.0.0 |
| NDK | 27.1.12297006 | 27.1.12297006 (r27b) |
| CMake | not pinned by RN | 3.22.1 … 4.1.2 |

The RN column comes from [libs.versions.toml](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml) and the [template build.gradle](https://github.com/react-native-community/template/blob/0.88-stable/template/android/build.gradle). I evaluated a composition with exactly these versions against nixpkgs `02c087f`.

androidenv patches its binaries for NixOS: build-tools (including `aapt2`), CMake and NDK prebuilts are `autoPatchelf`ed ([build-tools.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/build-tools.nix), [cmake.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/cmake.nix), [ndk-bundle/default.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/ndk-bundle/default.nix)).

An alternative SDK source is [tadfisher/android-nixpkgs](https://github.com/tadfisher/android-nixpkgs), which is regenerated daily from Google's repositories (last push 2026-10-20). Joplin uses it. devenv's `android` module uses androidenv by default and switches to android-nixpkgs when that input is present ([devenv android.nix](https://github.com/cachix/devenv/blob/main/src/modules/integrations/android.nix)). That matters for DELMIR: the devenv `app` shell and the Nix APK derivation can share the same SDK store paths if they use the same nixpkgs and the same composition.

`androidenv.buildApp` is Ant-based, kept "for historical purposes", and takes the keystore as a Nix input ([android.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md)). Don't use it.

### node_modules: `importNpmLock`

`importNpmLock { npmRoot = ./.; }` rewrites `package-lock.json` entries to store paths using the lock's own integrity hashes, so there is no `hash` to maintain ([javascript.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/javascript.section.md)). Its `npmConfigHook` does the following ([npm-config-hook.sh](https://github.com/NixOS/nixpkgs/blob/master/pkgs/build-support/node/import-npm-lock/hooks/npm-config-hook.sh)):

- sets `npm config set offline true`;
- runs `npm install --ignore-scripts`, then `npm rebuild`;
- runs `patchShebangs node_modules`;
- runs as a `postConfigureHook`.

So `node_modules` is a writable copy in the build directory. That matters: the RN Gradle plugin is an included build at `node_modules/@react-native/gradle-plugin` and Gradle writes `build/` and `.gradle/` inside it ([template settings.gradle](https://github.com/react-native-community/template/blob/0.88-stable/template/android/settings.gradle)). This is also why `importNpmLock.buildNodeModules` + `linkNodeModulesHook` (store symlinks, read-only) is meant for dev shells, not this build. That last point is my inference from the docs, not something they state for Gradle.

## Working examples

| Project | What | Gradle deps | node_modules | SDK | Signing | Hard parts they hit |
|---|---|---|---|---|---|---|
| [mio-19/repo `joplin`](https://github.com/mio-19/repo/blob/HEAD/app/apks/joplin/package.nix) | Joplin RN app, release APK | `gradle.fetchDeps`, `deps.json` ≈ 300 KB | yarn-berry `fetchYarnBerryDeps` | android-nixpkgs: NDK 27.1, CMake 3.31.6, build-tools 36 | patch to debug signing, separate `sign-joplin` script | `gradleUpdateTask` also compiles the RN/Expo included gradle plugins' Kotlin; a "bootstrap" build pre-resolves their deps; it [rewrites `google()`/`mavenCentral()`/`gradlePluginPortal()` to `file://` mitmCache paths](https://github.com/mio-19/repo/blob/HEAD/app/apks/joplin/rewrite-mitm-repos.sh) because "React Native / Expo included builds each declare their own repositories"; pins JDK installations and disables toolchain auto-download; `-x lintVital*` |
| [0xferrous/my-nix `bb`](https://github.com/0xferrous/my-nix/blob/HEAD/pkgs/bb/android.nix) | Expo SDK 57 / RN 0.86.2 release APK | `gradle.fetchDeps`, `gradleUpdateTask = … :app:assembleRelease` | `fetchPnpmDeps` (hashed) | androidenv: NDK 27.1.12297006, CMake 3.30.5, build-tools 35/36 | template default | `mkGradle` 9.3.1; `aapt2FromMavenOverride` via `GRADLE_OPTS`; `cmake.dir` in `local.properties`; `-PreactNativeArchitectures=x86_64`; `jcenter()` replaced in a dependency; serial build (`workers.max=1`) to limit disk/RAM |
| [xmtp/libxmtp `react-native-consumer.nix`](https://github.com/xmtp/libxmtp/blob/HEAD/nix/package/react-native-consumer.nix) | bare RN and Expo test consumers, Android in sandbox | `gradle.fetchDeps` per consumer (`android/gradle/dependencies.json`) | pnpm store tarball | own `rnShell` env, build-tools 37.0.0 | n/a | `--dependency-verification=strict`, `kotlin.compiler.execution.strategy=in-process`, R8 heap raised to 4 GiB |
| [xmtp/libxmtp `example-android-apk.nix`](https://github.com/xmtp/libxmtp/blob/HEAD/nix/package/example-android-apk.nix) | native Kotlin app, release APK | `gradle.fetchDeps` | n/a | androidenv | signed in-sandbox with AOSP's **public** test key via `android.injected.signing.*` | asserts the `mkGradle` version equals the wrapper's; `apksigner verify` + `aapt dump badging` in `installPhase` |
| [Mic92/tincr](https://github.com/Mic92/tincr/blob/HEAD/nix/android-app.nix) | Kotlin app, debug APK + Roborazzi screenshots | `gradle.fetchDeps` | n/a | androidenv (NDK 27.2 pinned "so the toolchain doesn't move on nixpkgs bumps") | debug | `nixDownloadDeps` breaks under AGP; `ANDROID_USER_HOME=$TMPDIR` |
| [mio-19/nurpkgs `newpipe`](https://github.com/mio-19/nurpkgs/blob/HEAD/by-name/ne/newpipe/package.nix) | AGP 9.2 app, release APK | `gradle.fetchDeps` | n/a | androidenv, build-tools 36+37 | n/a | `gradle_9.override { java = jdk21; }`, empty init script, configuration cache off ("flaky under the Gradle MITM proxy") |
| [status-im/status-mobile `nix/`](https://github.com/status-im/status-mobile/tree/develop/nix) | large RN app (RN 0.73.5) | own pipeline: `go-maven-resolver` → `deps.json` → `fetchurl` local Maven repo, `-Dmaven.repo.local`, `--offline` ([nix/deps/gradle](https://github.com/status-im/status-mobile/tree/develop/nix/deps/gradle)) | yarn2nix + a "patched" copy that rewrites every `build.gradle` in `node_modules` to the local repo ([nodejs-patched](https://github.com/status-im/status-mobile/blob/develop/nix/deps/nodejs-patched/default.nix)) | androidenv, NDK 25.2, CMake 3.22.1 | outside Nix; secrets via `extra-sandbox-paths` | custom patched `aapt2` overlay; a `deps_hack.sh` for deps the resolver misses; runs its own binary cache, whose NDK NAR downloads failed ([KNOWN_ISSUES](https://github.com/status-im/status-mobile/blob/develop/nix/KNOWN_ISSUES.md)) |

status-mobile predates mitm-cache. Its tooling (custom resolver, manual `add_package.sh` for misses) is the expensive version of this; the newer examples show `gradle.fetchDeps` removes most of it. None of the examples uses ONNX Runtime.

## Update cost

| Change | What you do | Lockfile/hash work |
|---|---|---|
| JS-only change, npm dep add/bump | `npm install` (updates `package-lock.json`) | none: `importNpmLock` reads the lock |
| Add a native module (e.g. camera, SQLite) | `npm install`; check its `android/build.gradle` for `jcenter()`, dynamic versions (`+`, `latest.*`), AGP `classpath` blocks, snapshot repos; patch if needed | re-run `mitmCache.updateScript`; commit `deps.json` |
| Change a Gradle/Maven dep or AGP | edit Gradle files | re-run update script |
| Bump React Native | follow the upgrade diff for `android/`; re-check `libs.versions.toml` and align `androidenv` platform/build-tools/NDK/CMake and the Gradle version; re-check the RN gradle plugin for new tasks or repos | re-run update script; expect a large `deps.json` diff |
| Bump nixpkgs | may move `gradle_9` (9.8.0 today), JDK and androidenv | re-run update script if Gradle changed; pin Gradle with `gradle-packages.mkGradle` and SDK versions explicitly to decouple |

For an RN bump, the `libs.versions.toml` to re-check is the one in [packages/react-native/gradle](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml).

The update script is a full build with network ([update-deps.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/update-deps.nix)), so each regeneration costs one cold Gradle build plus downloading the Maven set. That is roughly 10–30 minutes and 0.5–1 GB (estimates, see below).

The result is mechanical to review: URLs and hashes only. The format was designed so lockfiles "won't be human-reviewed" but stay "tampering-resistant" ([README, Security Considerations](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/README.md)). For scale, Joplin's `deps.json` is about 300 KB ([directory listing](https://github.com/mio-19/repo/tree/HEAD/app/apks/joplin)).

The real recurring cost is when the update script itself fails on a new kind of request. Joplin's bootstrap-resolve block and repository rewriting are what that looks like at the extreme, for a large Expo-flavoured app. A bare app with three native modules should sit much closer to `bb` or tincr.

## Known problems and their fixes

| Problem | Source | Fix |
|---|---|---|
| **aapt2 from Maven is an unpatched ELF.** AGP downloads `com.android.tools.build:aapt2:9.2.1-15009934:linux`; the binary inside is dynamically linked against `/lib64/ld-linux-x86-64.so.2` (checked with `readelf`), which does not exist in the sandbox. | nixpkgs [android.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md) | `-Pandroid.aapt2FromMavenOverride=${sdk}/build-tools/37.0.0/aapt2` (androidenv's autoPatchelfed copy). Keep build-tools ≥ AGP's aapt2: an older one fails with "unknown option '--source-path'" ([gradle2nix #67](https://github.com/tadfisher/gradle2nix/issues/67)). All the fetchDeps examples above do this. |
| **Gradle daemon.** | [setup hook](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/setup-hook.sh); [Gradle daemon docs](https://docs.gradle.org/current/userguide/gradle_daemon.html); [Kotlin execution strategy](https://kotlinlang.org/docs/compiler-execution-strategy.html) | The hook already passes `--no-daemon`. The template's `org.gradle.jvmargs=-Xmx2048m` still makes Gradle fork a single-use daemon JVM. Kotlin compiles in its own daemon by default; set `-Pkotlin.compiler.execution.strategy=in-process` as XMTP does. Raise the heap for R8 if it OOMs (XMTP: 4 GiB). |
| **RN Gradle plugin is an included build from `node_modules`**, with its own repositories and `plugins { id("org.gradle.toolchains.foojay-resolver-convention").version("1.0.0") }` and `kotlin { jvmToolchain(17) }`. | [packages/gradle-plugin/settings.gradle.kts](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/settings.gradle.kts) | `node_modules` must be writable (importNpmLock gives a copy). Run Gradle on JDK 17 (`gradle_9.override { java = jdk17; }` or `mkGradle … defaultJava = jdk17`). Add `-Dorg.gradle.java.installations.auto-download=false -Dorg.gradle.java.installations.paths=${jdk17.home}` so foojay never tries to download a JDK (Joplin does exactly this). Proxy replay should cover its repositories, but Joplin found it had to rewrite included-build repositories to `file://`. Treat that as the first thing to check if resolution fails. |
| **Autolinking runs `npx @react-native-community/cli config` during settings evaluation.** | [ReactSettingsExtension.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/settings-plugin/src/main/kotlin/com/facebook/react/ReactSettingsExtension.kt) | The CLI is a local devDependency and npm is configured offline, so `npx` should run the local bin. To make it explicit, call `autolinkLibrariesFromCommand(["node", "node_modules/@react-native-community/cli/build/bin.js", "config"])`, or generate the JSON once and use `autolinkLibrariesFromConfigFile(file)` (both in the same file). `node` must be in `nativeBuildInputs`. |
| **Codegen and bundling call `node`** (`nodeExecutableAndArgs` defaults to `["node"]`). | [ReactExtension.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/ReactExtension.kt) | `nodejs_22` in `nativeBuildInputs` (the template requires Node ≥ 22.11). Set `CI=1` so Metro doesn't watch, as status-mobile does. |
| **Hermes.** RN 0.88 uses the prebuilt `com.facebook.hermes:hermes-android:260318099.0.4` AAR from Maven ([version.properties](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/sdks/hermes-engine/version.properties)). `hermesc` comes from the `hermes-compiler` npm package, the third fallback in [PathUtils.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/utils/PathUtils.kt). | npm tarball `hermes-compiler@260318099.0.4` | Its `hermesc/linux64-bin/hermesc` is **statically linked**: `readelf` shows no `INTERP` and no dynamic section. It needs **no patchelf** and runs in the sandbox as is. Don't build Hermes from source; nothing requires it. |
| **NDK and CMake are always needed.** With New Architecture the RN plugin turns on prefab and points `externalNativeBuild.cmake.path` at `ReactAndroid/cmake-utils/default-app-setup/CMakeLists.txt` (min CMake 3.13), and `onnxruntime-react-native` has its own `CMakeLists.txt`. | [NdkConfiguratorUtils.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/utils/NdkConfiguratorUtils.kt); [ORT build.gradle](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/android/build.gradle) | Compose with `includeNDK = true; ndkVersions = ["27.1.12297006"]; cmakeVersions = [ "<pinned>" ]`. Write `sdk.dir` and `cmake.dir` to `android/local.properties`, which Google documents as taking precedence over `PATH` ([install-ndk](https://developer.android.com/studio/projects/install-ndk)). Pin `externalNativeBuild.cmake.version` if AGP asks for a different one. AGP's current default CMake version is not stated on that page (it still says 3.10.2), so let the spike choose. The SDK is read-only, so AGP's auto-install of a missing NDK/CMake fails ([android.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md), "SDK directory is not writable"). |
| **ONNX Runtime uses a dynamic version.** The module declares `extractLibs "com.microsoft.onnxruntime:onnxruntime-android:latest.integration@aar"`. Today that resolves to 1.31.0 (Maven Central metadata, `lastUpdated` 2026-10-09) while the npm package is 1.24.3. | [ORT build.gradle](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/android/build.gradle); [maven-metadata.xml](https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/maven-metadata.xml) | The mitm lockfile records `latest`/`release`, so sandbox builds are deterministic, but the native version jumps on every lockfile regeneration and drifts from the JS API. Pin it: `resolutionStrategy.force "com.microsoft.onnxruntime:onnxruntime-android:1.24.3"` in the root `build.gradle`, or patch the module in `preBuild` (`substituteInPlace … latest.integration 1.24.3`). Pinning is advisable outside Nix too. The module also has a `buildscript` `classpath` on AGP 7.4.2, which will likely add AGP 7.4.2's artifacts to the lockfile (unverified). |
| **AGP writes to `~/.android`** (prefs, debug keystore). | [gradle2nix PR #67](https://github.com/tadfisher/gradle2nix/issues/67) | `export ANDROID_USER_HOME=$TMPDIR/android` (tincr, newpipe, XMTP). |
| **SDK licence acceptance.** androidenv refuses to evaluate until accepted. | [license.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/license.nix), [compose-android-packages.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/compose-android-packages.nix) | In the flake: `import nixpkgs { config = { android_sdk.accept_license = true; allowUnfreePredicate = …; }; }`. The `NIXPKGS_ACCEPT_ANDROID_SDK_LICENSE=1` env var works only with `--impure`. The composition writes the licence hashes into `licenses/` itself. androidenv's `meta.license` is `unfree` ([default.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/default.nix)), so `allowUnfree` (or a predicate) is required. |
| **Extra repositories.** RN adds `repo.reactnative.dev/maven2` (for `com.facebook.react*`/`hermes*`) and JitPack. | [DependencyUtils.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/utils/DependencyUtils.kt), [PropertyUtils.kt](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/utils/PropertyUtils.kt) | Works through the proxy. Set `includeJitpackRepository=false` to cut lookups. There is also `exclusiveEnterpriseRepository`, which replaces *all* repos with one URL: a cleaner hook than Joplin's `sed` rewriting if proxy replay ever fails. |
| **Gradle version.** The RN template wraps Gradle 9.4.1; nixpkgs has 9.8.0. | [wrapper props](https://github.com/react-native-community/template/blob/0.88-stable/template/android/gradle/wrapper/gradle-wrapper.properties), [gradle default.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/build-managers/gradle/default.nix) | Use `gradle-packages.mkGradle { version = "9.4.1"; … }` (XMTP and `bb` build their own versions this way, XMTP asserting the version matches the wrapper), or test 9.8.0. Never run `./gradlew`, which downloads its distribution. |
| **Lint and configuration cache** misbehave in the sandbox. | Joplin (`-x :app:lintVital*`), `bb`, newpipe (`-x lint`, config cache off) | Skip lint in the Nix build (run it in devenv/CI separately if wanted), and leave configuration cache off. |
| **CI runner disk.** | [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners): 14 GB SSD (4 vCPU/16 GB RAM public, 2 vCPU/8 GB private) | SDK+NDK ≈ 2.6 GB, Maven ≈ 0.5–1 GB, JDK ≈ 0.5 GB, plus Gradle/CMake intermediates. Build one ABI only (`-PreactNativeArchitectures=arm64-v8a`, as `bb` does for x86_64). |

## Build time and cache size

**Cache coverage, checked.** I evaluated a composition matching RN 0.88 against nixpkgs `02c087f` and queried `cache.nixos.org/<hash>.narinfo` for each path:

| Path | narinfo |
|---|---|
| `android-sdk-build-tools-37.0.0` | 404 |
| `android-sdk-ndk-27.1.12297006` | 404 |
| `android-sdk-cmake-3.22.1` | 404 |
| `android-sdk-platforms-37.0` | 404 |
| `android-sdk-platform-tools-37.0.1` | 404 |
| `gradle-9.8.0` | 200 |
| `mitm-cache-0.1.2` | 200 |
| `openjdk-headless-17.0.20.1+1` | 200 (NarSize 494 MB) |

So every Nix machine and every cold CI run builds the SDK pieces locally: download the zips from `dl.google.com`, unpack, autoPatchelf. That follows from androidenv being unfree, so Hydra doesn't build it.

**SDK closure size, measured from Google's archives.** I read each zip's central directory over HTTP range requests; URLs and zip sizes come from [repo.json](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/repo.json).

| Package | Zip | Unpacked |
|---|---|---|
| NDK 27.1.12297006 (r27b) | 664 MB | 2,054 MB (9,277 files) |
| cmdline-tools 22.0 (included by default) | 182 MB | 182 MB |
| build-tools 37.0.0 | 66 MB | 158 MB |
| platform 37.0 | 67 MB | 125 MB |
| CMake 3.22.1 | 22 MB | 53 MB |
| platform-tools 37.0.1 | 9 MB | 22 MB |
| **Total** | **≈ 1.0 GB download** | **≈ 2.6 GB in the store** |

androidenv deletes the NDK's `docs`/`tests` ([ndk-bundle/default.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/mobile/androidenv/ndk-bundle/default.nix)), so the real figure is slightly lower. Setting `toolsVersion = null` drops the obsolete `tools` package.

**Maven set (estimate; the spike must measure it).** Sizes of the big artifacts, from Maven `Content-Length`:

| Artifact | Release | Debug |
|---|---|---|
| `react-android-0.88.0` AAR | 172 MB | 288 MB |
| `hermes-android-260318099.0.4` AAR | 85 MB | 118 MB |
| `onnxruntime-android-1.24.3` AAR | 41 MB | n/a |
| `kotlin-compiler-embeddable-2.2.0` | 56 MB | n/a |
| AGP 9.2.1 jar (13 MB) plus its dependency tree, R8, androidx, Kotlin Gradle plugin | probably 100–250 MB | n/a |

`onnxruntime-android` 1.31.0, which `latest.integration` picks today, is 55 MB. A release-only update task should record roughly **0.5–0.7 GB**; recording both debug and release adds ≈ 0.4 GB more. AARs are already zip-compressed, so Cachix's compression won't shrink them much.

**Cachix.** The free tier is 5 GB for open-source caches with least-recently-used eviction; paid plans start at 50 GiB ([pricing](https://www.cachix.org/pricing)). Cachix never stores paths that are already on cache.nixos.org (same page).

The Android SDK licence (shipped in repo.json) says "you may not copy (except for backup purposes), modify, adapt, redistribute … the SDK". Pushing the SDK to a **public** cache is redistribution, and androidenv's outputs are even modified (patchelf). So exclude SDK paths with cachix-action's `pushFilter` (e.g. `android-sdk-|androidsdk`). Note its warning: "paths may still be pushed if they are part of another path's closure" ([action.yml](https://github.com/cachix/cachix-action/blob/master/action.yml)). Give the APK derivation `allowedReferences = [ ]` so its output can never pull the SDK closure in. Without pushing the SDK, the cost per version is about 0.6–1 GB, comfortably inside 5 GB. CI then re-downloads about 1 GB of SDK zips from Google on each cold runner.

**Build time (unmeasured estimate).** No primary source publishes sandboxed RN build times. My estimate for a cold single-ABI release build on a 4-vCPU runner is **10–30 minutes**, excluding SDK download. Basis:

- SDK deploy: unzip and autoPatchelf about 2 GB, a few minutes;
- one cold Gradle configuration, including compiling the RN Gradle plugin's Kotlin;
- the Kotlin/Java compile;
- CMake/NDK compiles of the app's C++ and ORT's JNI layer for one ABI;
- the Metro bundle and `hermesc`;
- dex/R8 and packaging.

Nix gives no incremental Gradle builds: any change to `app/` sources reruns all of it. Input hashing does keep unrelated commits (training, contracts) from rebuilding the APK. The update script costs about the same, plus the downloads.

## Signing

- **Keys must not enter the store.** Store paths are world-readable, and `androidenv.buildApp`'s `keyStore = ./keystore` would copy the keystore into the store ([android.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md)). status-mobile instead injects secrets with `extra-sandbox-paths`, which needs a trusted user and is impure ([KNOWN_ISSUES](https://github.com/status-im/status-mobile/blob/develop/nix/KNOWN_ISSUES.md), [build.nix](https://github.com/status-im/status-mobile/blob/develop/nix/mobile/android/build.nix)).
- **The RN template signs debug *and* release with a committed `app/debug.keystore`** (password `android`) ([template app/build.gradle](https://github.com/react-native-community/template/blob/0.88-stable/template/android/app/build.gradle)). That is deterministic and fine for a CI artifact or sideloading, but it is a public key.
- **For real releases, build unsigned and sign outside Nix.** Remove the release `signingConfig` so AGP emits `app-release-unsigned.apk`, then sign with something like `apksigner sign --ks "$KS" --ks-key-alias delmir --ks-pass env:DELMIR_KS_PASS --out delmir.apk result/app-release-unsigned.apk` ([apksigner](https://developer.android.com/tools/apksigner); `--ks-pass` accepts `env:`, `file:`, `stdin`). Align before signing, never after ("If you use zipalign … use it before signing the APK", same page). AGP aligns its own output, but check it with `zipalign -c -P 16 4` in the spike. Then run `apksigner verify`.
- **The signing step fits as** a devenv script (`devenv` `app` shell) or a CI step that has the keystore secret, run on `nix build .#apk`'s output. RN's guide keeps credentials in `~/.gradle/gradle.properties` "to prevent them from being checked in to git" and notes Play needs App Signing for AABs ([signed-apk-android](https://reactnative.dev/docs/signed-apk-android)). An AAB (`bundleRelease`) can be built and signed the same way.
- **XMTP's alternative** signs in-sandbox with the AOSP *public* test key fetched by hash ([example-android-apk.nix](https://github.com/xmtp/libxmtp/blob/HEAD/nix/package/example-android-apk.nix)). That is equivalent to debug-signing.

## Sketch: `app/package.nix` (UNTESTED, illustrative only)

```nix
# UNTESTED SKETCH: shows the shape and the known workarounds, not a working build.
{
  lib, stdenv, writeText,
  androidenv, gradle_9, jdk17_headless, nodejs_22, importNpmLock,
}:
let
  android = androidenv.composeAndroidPackages {
    platformVersions = [ "37" ];
    buildToolsVersions = [ "37.0.0" ];
    includeNDK = true;
    ndkVersions = [ "27.1.12297006" ];   # = RN 0.88 libs.versions.toml
    includeCmake = true;
    cmakeVersions = [ "3.22.1" ];       # spike decides; pin it in build.gradle too
    includeEmulator = false;
    includeSystemImages = false;
    includeSources = false;
    toolsVersion = null;
  };
  sdk = "${android.androidsdk}/libexec/android-sdk";
  jdk = jdk17_headless;
  gradle = gradle_9.override { java = jdk; };  # or gradle-packages.mkGradle { version = "9.4.1"; ... }
in
stdenv.mkDerivation (finalAttrs: {
  pname = "delmir-apk";
  version = "0.1.0";
  src = lib.fileset.toSource { root = ./.; fileset = /* package.json, lock, src, android/, … */ ./.; };

  npmDeps = importNpmLock { npmRoot = ./.; };       # no hash: uses package-lock.json integrity
  nativeBuildInputs = [ gradle jdk nodejs_22 importNpmLock.npmConfigHook ];

  mitmCache = gradle.fetchDeps {
    pkg = finalAttrs.finalPackage;
    data = ./deps.json;                              # regenerate: nix build .#apk.mitmCache.updateScript && ./result
  };
  gradleUpdateTask = finalAttrs.gradleBuildTask;     # nixDownloadDeps misses AGP's execution-time deps
  gradleBuildTask = ":app:assembleRelease";
  gradleInitScript = writeText "empty-init.gradle" "";  # reproducible-archive init script can break AGP
  gradleFlags = [
    "--project-dir" "android"
    "-Dorg.gradle.java.installations.auto-download=false"
    "-Dorg.gradle.java.installations.paths=${jdk.home}"
    "-Pandroid.aapt2FromMavenOverride=${sdk}/build-tools/37.0.0/aapt2"
    "-Pkotlin.compiler.execution.strategy=in-process"
    "-PreactNativeArchitectures=arm64-v8a"
    "-PincludeJitpackRepository=false"
    "-x" "lint"
  ];

  env = { ANDROID_HOME = sdk; ANDROID_NDK_ROOT = "${sdk}/ndk/27.1.12297006"; CI = "1"; };

  # preBuild runs in both the real build and the update script (after npmConfigHook).
  preBuild = ''
    export ANDROID_USER_HOME=$TMPDIR/android; mkdir -p $ANDROID_USER_HOME
    printf 'sdk.dir=%s\ncmake.dir=%s\n' ${sdk} ${sdk}/cmake/3.22.1 > android/local.properties
    substituteInPlace node_modules/onnxruntime-react-native/android/build.gradle \
      --replace-fail 'onnxruntime-android:latest.integration' 'onnxruntime-android:1.24.3'
  '';

  installPhase = ''
    install -Dm644 android/app/build/outputs/apk/release/app-release-unsigned.apk $out/delmir-unsigned.apk
  '';
  allowedReferences = [ ];   # the APK must not drag the SDK/NDK closure along
})
```

Wiring: `packages.x86_64-linux.apk = pkgs.callPackage ./app/package.nix { };` and `checks.x86_64-linux.apk = self.packages.x86_64-linux.apk;`. `nix flake check` builds `checks` but only evaluates `packages`. nixpkgs must be imported with `config.android_sdk.accept_license = true` and an unfree predicate for androidenv.

## Open questions only a spike can settle

1. Does proxy replay cover the RN Gradle plugin's included build and foojay settings plugin, or do we need Joplin-style `file://` rewriting (or `exclusiveEnterpriseRepository`)?
2. Does autolinking's `npx @react-native-community/cli config` run offline in the sandbox unchanged?
3. Which CMake version does AGP 9.2.1 want with RN 0.88 and `onnxruntime-react-native`, and does build-tools 37.0.0's aapt2 satisfy AGP 9.2.1?
4. Does Gradle 9.8.0 (nixpkgs) work, or must we pin 9.4.1 with `mkGradle`?
5. Does `resolutionStrategy.force` reliably override ORT's `latest.integration@aar`, or is patching `node_modules` needed?
6. Actual numbers: cold build time on a GitHub runner, peak disk, `deps.json` size, Maven closure size (`nix path-info -S` on `mitmCache`), APK size for `arm64-v8a`.
7. Does the APK output reference any store path (does `allowedReferences = [ ]` hold, e.g. NDK paths embedded in uncompressed `.so` files)?
8. How stable is the lockfile: does re-running the update script on an unchanged tree give the same `deps.json`? Is the APK bit-for-bit reproducible (`nix build --rebuild`)? Nix does not require the latter.
9. Does AGP's unsigned output pass `zipalign -c -P 16 4` (16 KB page alignment for `.so`) so `apksigner` can be applied directly?

## Sources

nixpkgs (master unless noted):
- [doc/languages-frameworks/gradle.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/gradle.section.md)
- [doc/languages-frameworks/android.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md)
- [doc/languages-frameworks/javascript.section.md](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/javascript.section.md) (`importNpmLock`)
- [pkgs/development/tools/build-managers/gradle/](https://github.com/NixOS/nixpkgs/tree/master/pkgs/development/tools/build-managers/gradle): `fetch-deps.nix`, `update-deps.nix`, `setup-hook.sh`, `init-deps.gradle`, `init-build.gradle`, `compress-deps-json.py`, `README.md`, `default.nix`
- [pkgs/by-name/mi/mitm-cache/](https://github.com/NixOS/nixpkgs/tree/master/pkgs/by-name/mi/mitm-cache): `fetch.nix`, `setup-hook.sh`, `package.nix`
- [pkgs/development/mobile/androidenv/](https://github.com/NixOS/nixpkgs/tree/master/pkgs/development/mobile/androidenv): `compose-android-packages.nix`, `default.nix`, `license.nix`, `build-tools.nix`, `cmake.nix`, `ndk-bundle/default.nix`, `repo.json`
- [pkgs/build-support/node/import-npm-lock/hooks/npm-config-hook.sh](https://github.com/NixOS/nixpkgs/blob/master/pkgs/build-support/node/import-npm-lock/hooks/npm-config-hook.sh)

Tools:
- [chayleaf/mitm-cache README](https://github.com/chayleaf/mitm-cache)
- [tadfisher/gradle2nix v2 README](https://github.com/tadfisher/gradle2nix/blob/v2/README.org), issues [#13](https://github.com/tadfisher/gradle2nix/issues/13), [#67](https://github.com/tadfisher/gradle2nix/issues/67), [#86](https://github.com/tadfisher/gradle2nix/issues/86), and the [v2 commit history](https://github.com/tadfisher/gradle2nix/commits/v2)
- [tadfisher/android-nixpkgs README](https://github.com/tadfisher/android-nixpkgs)
- [cachix/devenv android module](https://github.com/cachix/devenv/blob/main/src/modules/integrations/android.nix)
- [cachix/cachix-action action.yml](https://github.com/cachix/cachix-action/blob/master/action.yml), [Cachix pricing](https://www.cachix.org/pricing)

React Native and ONNX Runtime:
- [libs.versions.toml @ v0.88.0](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml)
- [packages/gradle-plugin @ v0.88.0](https://github.com/facebook/react-native/tree/v0.88.0/packages/gradle-plugin): `settings.gradle.kts`, `ReactSettingsExtension.kt`, `PathUtils.kt`, `DependencyUtils.kt`, `PropertyUtils.kt`, `NdkConfiguratorUtils.kt`, `ReactExtension.kt`
- [hermes-engine/version.properties @ v0.88.0](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/sdks/hermes-engine/version.properties)
- [react-native-community/template 0.88-stable](https://github.com/react-native-community/template/tree/0.88-stable/template/android); npm `react-native@0.88.0`, `@react-native-community/template@0.88.0`, `hermes-compiler@260318099.0.4` (tarballs inspected locally)
- [reactnative.dev: Publishing to Google Play Store](https://reactnative.dev/docs/signed-apk-android), [Set up your environment](https://reactnative.dev/docs/set-up-your-environment) (both show the 0.87 docs)
- [microsoft/onnxruntime js/react_native/android/build.gradle @ v1.24.3](https://github.com/microsoft/onnxruntime/blob/v1.24.3/js/react_native/android/build.gradle); [onnxruntime-android maven-metadata.xml](https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/maven-metadata.xml)

Android, Gradle, Kotlin, GitHub docs:
- [apksigner](https://developer.android.com/tools/apksigner), [Install and configure the NDK and CMake](https://developer.android.com/studio/projects/install-ndk)
- [Gradle daemon](https://docs.gradle.org/current/userguide/gradle_daemon.html), [dependency locking](https://docs.gradle.org/current/userguide/dependency_locking.html), [dependency verification](https://docs.gradle.org/current/userguide/dependency_verification.html)
- [Kotlin compiler execution strategy](https://kotlinlang.org/docs/compiler-execution-strategy.html)
- [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

Working examples:
- [mio-19/repo joplin](https://github.com/mio-19/repo/tree/HEAD/app/apks/joplin)
- [0xferrous/my-nix bb android.nix](https://github.com/0xferrous/my-nix/blob/HEAD/pkgs/bb/android.nix)
- [xmtp/libxmtp react-native-consumer.nix](https://github.com/xmtp/libxmtp/blob/HEAD/nix/package/react-native-consumer.nix) and [example-android-apk.nix](https://github.com/xmtp/libxmtp/blob/HEAD/nix/package/example-android-apk.nix)
- [Mic92/tincr android-app.nix](https://github.com/Mic92/tincr/blob/HEAD/nix/android-app.nix), [android-env.nix](https://github.com/Mic92/tincr/blob/HEAD/nix/android-env.nix)
- [mio-19/nurpkgs newpipe](https://github.com/mio-19/nurpkgs/blob/HEAD/by-name/ne/newpipe/package.nix)
- [status-im/status-mobile nix/](https://github.com/status-im/status-mobile/tree/develop/nix)

Measurements made for this note (2026-10-21):
- `nix eval` of the androidenv composition at nixpkgs `02c087f`, plus `cache.nixos.org` narinfo lookups;
- unpacked sizes from the zip central directories of the `dl.google.com` archives;
- `readelf` on the `aapt2` jar from Google Maven and on `hermes-compiler`'s `hermesc`;
- `Content-Length` of the Maven AARs.
