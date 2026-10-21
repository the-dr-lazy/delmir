# Building and running DELMIR's React Native app from a devenv shell on NixOS

Research for [the-dr-lazy/delmir#9](https://github.com/the-dr-lazy/delmir/issues/9), carried out 2026-10-21. Versions are as of that date: devenv 2.4.0 (released 2026-09-24, tag commit `b904dcb`), React Native 0.88.0 (released 2026-10-15, still the latest stable), nixpkgs `nixos-unstable` at `02c087f3fe673c9e317f206a627cb6b910336dbe`, host NixOS 26.11pre with systemd 261.3. This note covers the impure, incremental dev loop (Metro, `run-android`, `installDebug`, adb). The sandboxed APK build is covered by [#31](https://github.com/the-dr-lazy/delmir/blob/research/nix-react-native-apk/docs/research/nix-react-native-apk.md) and the GO spike [#32](https://github.com/the-dr-lazy/delmir/issues/32) (branch `prototype/nix-apk`, dir `spike-nix-apk/`); I build on them and do not repeat them. Every claim links to its source. "Evaluated" means I ran a Nix evaluation or a shell on this host. Anything else not checked is marked unverified, and estimates are marked as estimates.

## Answer

**The most reliable setup is a plain devenv shell that does not use devenv's `android` module.** Instead, one Nix file (`nix/android.nix`) holds the Android composition and the #32 workarounds. Both the flake's APK derivation and the `app` devenv shell import it. The shell and the flake then use the same nixpkgs revision. I evaluated this on this host: a standalone `devenv shell` built from that file gave **exactly the same store paths as the spike's APK build**, `/nix/store/zcz6p97…-androidsdk` and `/nix/store/ly8cblp…-android-cmake-3.31.6-nixpkgs-ninja`. No new SDK build or download was needed.

Why not `android.enable`? devenv 2.4.0's module ([android.nix](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix)) works, but it fits DELMIR badly:

- It builds its own composition from its options, so it cannot carry the ninja-swapped CMake from #32.
- It always adds an `emulateApp` package, which pulls in a second composition with `platforms-35`, even when the emulator is off (evaluated).
- It writes `local.properties` to the devenv root, not to `android/` (or `app/android/`).
- Its defaults (platforms 32/34/36, build-tools 34.0.0, NDK 26.1, system images, Google APIs) are all wrong for RN 0.88.

The dev loop in that shell:

- **Toolchain.** JDK 17 is `JAVA_HOME`. Node 22 runs `npm ci` against the `package-lock.json` that #31 already relies on. Watchman is on `PATH`.
- **Gradle.** Use the project's `./gradlew`. It downloads Gradle 9.4.1, which runs on NixOS: its JNI libraries need only glibc (checked with `readelf`). Pin its checksum.
- **aapt2.** Point it at the SDK's patched copy through `GRADLE_OPTS`.
- **CMake.** Put the patched CMake in `android/local.properties` as `cmake.dir`. Without it the #32 ninja segfault applies here too.
- **Run.** `npx react-native run-android --active-arch-only` builds, installs and runs `adb reverse tcp:8081 tcp:8081` by itself.

**Phone over USB.** On this NixOS no `programs.adb` and no udev rules are needed. nixpkgs removed `programs.adb` and `android-udev-rules` because systemd 258+ tags adb and fastboot interfaces `uaccess` ([rename.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/nixos/modules/rename.nix#L66-L72), [systemd 70-uaccess.rules.in](https://github.com/systemd/systemd/blob/v258/rules.d/70-uaccess.rules.in#L80-L92)). The `adbusers` group is gone with it. Wireless debugging (`adb pair`, then `adb connect`) needs no inbound firewall port if Metro is reached with `adb reverse` over the wireless adb link.

**Emulator: practical on this machine, but not worth it now.** `/dev/kvm` is mode 0666 and `kvm_amd` is loaded. ONNX Runtime's AAR ships `x86_64` libraries. But it costs another 0.4–2.2 GB of unfree downloads on a flaky network, and on-device inference is DELMIR's point.

### Sketch (EVALUATED: shell entered, env checked; no Gradle build run)

```nix
# nix/android.nix — imported by app/package.nix (APK) AND the app devenv shell.
{ androidenv, gradle-packages, jdk17_headless, nodejs_22, ninja, runCommand }:
let
  ndkVersion = "27.1.12297006";        # RN 0.88 libs.versions.toml
  buildToolsVersion = "37.0.0";
  cmakeVersion = "3.31.6";             # #32: 3.22.1's ninja segfaults after autoPatchelf
  composition = androidenv.composeAndroidPackages {
    platformVersions = [ "37" ];
    buildToolsVersions = [ buildToolsVersion ];
    includeNDK = true; ndkVersions = [ ndkVersion ];
    includeCmake = true; cmakeVersions = [ cmakeVersion ];
    includeEmulator = false; includeSystemImages = false;
    includeSources = false; toolsVersion = null;
  };
  sdk = "${composition.androidsdk}/libexec/android-sdk";
in rec {
  inherit sdk ndkVersion;
  androidsdk = composition.androidsdk;
  platform-tools = composition.platform-tools;
  jdk = jdk17_headless;
  nodejs = nodejs_22;
  aapt2 = "${sdk}/build-tools/${buildToolsVersion}/aapt2";
  cmakeDir = runCommand "android-cmake-${cmakeVersion}-nixpkgs-ninja" { } ''
    mkdir -p $out; cp -rs ${sdk}/cmake/${cmakeVersion}/. $out/
    chmod -R u+w $out/bin; ln -sf ${ninja}/bin/ninja $out/bin/ninja
  '';
  gradle = (gradle-packages.mkGradle {         # sandbox only; the shell uses ./gradlew
    version = "9.4.1";
    hash = "sha256-KrKVjyoeURIMMmytbzhRU7sR7pOzwhbF/M6/37t+xss=";
    defaultJava = jdk;
  }).wrapped;
}
```

```nix
# nix/app-shell.nix — devenv module; devenv.nix: { imports = [ ./nix/app-shell.nix ]; }
{ pkgs, lib, ... }:
let android = pkgs.callPackage ./android.nix { };
in {
  packages = [ android.androidsdk android.platform-tools android.cmakeDir pkgs.watchman ];
  languages.java = { enable = true; jdk.package = android.jdk; lsp.enable = false; };
  languages.javascript = {
    enable = true; package = android.nodejs; directory = "app";
    npm.enable = true; npm.install.enable = true;    # runs `npm clean-install` when the lock changes
    lsp.enable = false;
  };
  env = {
    ANDROID_HOME = android.sdk;
    ANDROID_NDK_ROOT = "${android.sdk}/ndk/${android.ndkVersion}";
    GRADLE_OPTS = lib.concatStringsSep " " [
      "-Dorg.gradle.project.android.aapt2FromMavenOverride=${android.aapt2}"
      "-Dorg.gradle.java.installations.auto-download=false"
    ];
    DELMIR_ANDROID_CMAKE_DIR = "${android.cmakeDir}";   # also keeps it GC-rooted
  };
  enterShell = ''
    printf 'sdk.dir=%s\ncmake.dir=%s\n' "$ANDROID_HOME" "$DELMIR_ANDROID_CMAKE_DIR" \
      > app/android/local.properties
  '';
}
```

```yaml
# devenv.yaml — nixpkgs pinned to the SAME rev as flake.lock
inputs:
  nixpkgs:
    url: github:NixOS/nixpkgs/02c087f3fe673c9e317f206a627cb6b910336dbe
nixpkgs:
  allow_unfree: true
  android_sdk:
    accept_license: true
```

I evaluated two wirings of these files in a scratch directory under the scratchpad:

1. A standalone `devenv shell` with the `devenv.yaml` above (devenv 2.4.0 CLI, `devenv` input at `v2.4.0`). The shell reported:
   - `ANDROID_HOME=/nix/store/zcz6p97…-androidsdk/libexec/android-sdk`;
   - `JAVA_HOME` = openjdk-headless 17.0.20.1;
   - `node v22.23.3`;
   - `adb` 1.0.41 / 37.0.1 from the SDK;
   - the expected `local.properties`.
2. A flake `devenv.lib.mkShell` (`nix eval --no-pure-eval`). It gave the same `androidsdk` and `cmakeDir` store paths.

The evaluated copy also set `ANDROID_USER_HOME` to `$DEVENV_STATE/android`. I dropped that above; see [pitfalls](#pitfalls-in-the-dev-shell). Gradle, Metro and a device were not exercised. Add a flake check that fails when `devenv.lock`'s nixpkgs rev differs from `flake.lock`'s, so the two lockfiles cannot drift apart.

## devenv's Android support (devenv 2.4.0)

### The `android` module

Source: [src/modules/integrations/android.nix @ v2.4.0](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix); docs: [integrations/android.md @ v2.4.0](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/integrations/android.md).

| Option | Default | Note |
|---|---|---|
| `android.enable` | `false` | |
| `platforms.version` | `["32" "34" "36"]` | RN 0.88 needs 37 |
| `buildTools.version` | `["34.0.0"]` (`["35.0.0" "33.0.2" "30.0.3"]` with flutter) | Description says 30.0.3; the code says 34.0.0. RN 0.88 needs 37.0.0 |
| `ndk.enable` / `ndk.version` | `true` / `["26.1.10909125"]` | RN 0.88 needs 27.1.12297006 |
| `cmake.version` | `["3.22.1"]` | #32: 3.22.1's ninja segfaults |
| `cmdLineTools.version` | `"11.0"` (`"8.0"` with flutter) | |
| `tools.version` | `"26.1.1"` | obsolete `tools` package |
| `platformTools.version`, `emulator.version` | latest in nixpkgs' `repo.json` (string sort) | 37.0.1 / 37.2.4 today |
| `emulator.enable`, `systemImages.enable` | `true`, `true` | |
| `systemImageTypes`, `abis` | `["google_apis_playstore"]`, `["arm64-v8a" "x86_64"]` | |
| `sources.enable` | `false` | |
| `googleAPIs.enable`, `googleTVAddOns.enable` | `true`, `true` | |
| `extras` | `["extras;google;gcm"]` | |
| `extraLicenses` | 7 licence names | |
| `android-studio.enable` / `.package` | `false` / `pkgs.android-studio` | |
| `flutter.enable` / `.package` | `false` / `pkgs.flutter` | |
| `reactNative.enable` | `false` | |

What it does when enabled ([L303–L414](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L303-L414)):

- **SDK source.** It calls nixpkgs' `androidenv` with `licenseAccepted = true` hard-coded ([L19–L29](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L19-L29)), so no `android_sdk.accept_license` is needed. androidenv is still `unfree` ([default.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/mobile/androidenv/default.nix)), so `devenv.yaml` needs `nixpkgs.allow_unfree: true` or `permitted_unfree_packages` ([yaml-options](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/reference/yaml-options.mdx)). The same reference documents `nixpkgs.android_sdk.accept_license`, which matters when your own code calls `pkgs.androidenv`, as the sketch does.
- **android-nixpkgs.** If a `android-nixpkgs` input exists, the module uses that instead ([L6–L12](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L6-L12)). It then maps only platforms, build-tools, NDK and emulator; CMake, system images and extras are not mapped ([L63–L81](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L63-L81)). Every version RN 0.88 needs is already in nixpkgs' androidenv (#31), so DELMIR gains nothing from it.
- **Packages.** Adds the composed SDK, `platform-tools`, and **always** an `androidEnv.emulateApp` script ([L53–L56](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L53-L56), [L307–L309](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L307-L309)). `emulateApp` forces `cmdLineToolsVersion = "8.0"` and `platformVersions = [ "35" ]` on top of your arguments ([emulate-app.nix L36–L48](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/mobile/androidenv/emulate-app.nix#L36-L48)). Evaluated with `emulator.enable = false` and `systemImages.enable = false`: the module shell still depends on `android-sdk-platforms-35`. It also depends on `androidsdk-tools` and a second `androidsdk`.
- **Environment.** Sets `ANDROID_HOME`, and `ANDROID_NDK_ROOT = $ANDROID_HOME/ndk-bundle`. It does **not** set `ANDROID_SDK_ROOT`. It sets `GRADLE_OPTS=-Dorg.gradle.project.android.aapt2FromMavenOverride=…/build-tools/<first>/aapt2` ([L379–L388](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L379-L388)). So yes, devenv does the aapt2 override.
- **`enterShell`** ([L393–L413](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L393-L413)):
  - appends `vulkan-loader`, `libGL`, the build-tools `lib64` and the NDK's LLVM `lib` to `LD_LIBRARY_PATH`;
  - adds `tools`, `platform-tools`, `cmdline-tools/latest/bin` and `emulator` to `PATH`;
  - writes `./local.properties` with `sdk.dir` and `ndk.dir`, in the devenv root, not in the Gradle project; `ndk.dir` is deprecated ([install-ndk](https://developer.android.com/studio/projects/install-ndk));
  - sets `ANDROID_USER_HOME=$(pwd)/.android` and `ANDROID_AVD_HOME`;
  - runs under `set -e`.
- **`reactNative.enable`** only turns on `languages.javascript` with npm and sets the JDK to `pkgs.jdk17` ([L322–L327](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L322-L327)). There is no watchman, no Node version choice, and no Metro process. Evaluated: it gives `nodejs-slim-24.21.0`, `openjdk-17` (full, not headless), `jdt-language-server` and `typescript-language-server`.
- **AVDs.** The docs recommend creating them with `avdmanager` on the CLI, because Android Studio's GUI expects a mutable SDK ([android.md](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/integrations/android.md)).

**Store-path sharing through the module (evaluated).** I set the module to RN 0.88's versions (platform 37, build-tools 37.0.0, NDK 27.1, CMake 3.31.6, emulator, images, Google APIs and extras off). The NDK derivation (`p3qi08…-android-sdk-ndk-27.1.12297006.drv`) was identical to the spike's, so the 2 GB NDK is shared. Build-tools and the composed `androidsdk` were different paths, and CMake still carries the broken ninja.

### `languages.javascript` and `languages.java`

- **`languages.javascript`** ([javascript.nix @ v2.4.0](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/languages/javascript.nix)):
  - Options: `package` (default `pkgs.nodejs-slim`, Node 24.21.0 at our nixpkgs), `directory`, `nodejs.enable`, `corepack.enable`, and `npm|pnpm|yarn|bun.{enable,package,install.enable}`, plus `lsp`.
  - `npm.install.enable` runs `npm clean-install` when a `package-lock.json` exists. It reruns only when the hash of the lock plus the npm version changes ([L16–L49](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/languages/javascript.nix#L16-L49)).
  - It prepends `<directory>/node_modules/.bin` to `PATH`.
  - Evaluated quirk: with a package that has no dependencies, `npm ci` creates no `node_modules`, and the checksum write fails with a harmless error.
- **`languages.java`** ([java.nix @ v2.4.0](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/languages/java.nix)):
  - Options: `jdk.package` (default `pkgs.jdk`, 21.0.12 here), `maven.*`, `gradle.{enable,package}` (default `pkgs.gradle.override { java = jdk; }`, which is nixpkgs' Gradle 8), and `lsp.enable` (default **on**, which pulls `jdt-language-server`).
  - Sets `JAVA_HOME = jdk.package.home`.
  - Don't enable `gradle`: RN's CLI runs `./gradlew` ([buildAndroid/index.ts L84](https://github.com/react-native-community/cli/blob/v20.2.0/packages/cli-platform-android/src/commands/buildAndroid/index.ts#L84)), and nixpkgs' Gradle is the wrong major version.

### Standalone `devenv.yaml` vs the flake's `devenv.lib.mkShell`

devenv recommends its CLI over flakes. Flakes lose evaluation caching, GC protection and lazy trees, need `nix develop --no-pure-eval`, and cannot start processes in tests ([using-with-flakes.md](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/guides/using-with-flakes.md)). `devenv.lib.mkShell` returns the shell plus `.config` ([flake.nix L372–L381](https://github.com/cachix/devenv/blob/v2.4.0/flake.nix#L372-L381)). Both wirings evaluated to the same SDK store paths.

| | Standalone CLI + shared file | Flake `devenv.lib.mkShell` |
|---|---|---|
| Lockfiles | `devenv.lock` **and** `flake.lock`; the nixpkgs rev must match (needs a check) | one `flake.lock` |
| Entry | `devenv shell`, or `devenv hook` for auto-activation; the direnv integration is marked deprecated in favour of `devenv hook` ([direnv.mdx](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/integrations/direnv.mdx)) | `nix develop --no-pure-eval .#app` |
| Eval cache, GC root | yes | no (devenv docs) |
| `devenv up` processes (e.g. Metro) | yes | yes inside the shell; not in `devenv test` |

**Recommendation: the standalone CLI**, with the nixpkgs rev written literally in `devenv.yaml` and a `nix flake check` that compares it with `flake.lock`. It is the mode devenv supports best. The cost is one extra line to bump. #19 owns this decision.

## What React Native 0.88.0 requires

0.88.0 is the latest stable release; there is no 0.88.1 or 0.89 tag as of 2026-10-21 ([releases](https://github.com/facebook/react-native/releases)).

| Item | Value | Source |
|---|---|---|
| compileSdk / targetSdk / minSdk | 37 / 36 / 24 | [libs.versions.toml L3–L7](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml#L3-L7) |
| Build-tools | 37.0.0 | same |
| NDK | 27.1.12297006 | same |
| AGP | 9.2.1 | [L9](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml#L9) |
| Kotlin | 2.2.0 | [L33](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml#L33); [template build.gradle](https://github.com/react-native-community/template/blob/264d48336197f18218a69c5d0dc8f87e8acf04a4/template/android/build.gradle) |
| Gradle wrapper | 9.4.1 (sha256 `2ab2958f…7ec6cb` from [services.gradle.org](https://services.gradle.org/distributions/gradle-9.4.1-bin.zip.sha256), equal to the spike's `mkGradle` hash) | [gradle-wrapper.properties](https://github.com/react-native-community/template/blob/264d48336197f18218a69c5d0dc8f87e8acf04a4/template/android/gradle/wrapper/gradle-wrapper.properties) |
| CMake | not pinned by RN; #32 uses 3.31.6 | #31 |
| JDK | 17 ("You may encounter problems using higher JDK versions") | [_getting-started-linux-android.md L13](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/_getting-started-linux-android.md#L13) |
| Node | ≥ 22.11.0 | [template package.json](https://github.com/react-native-community/template/blob/264d48336197f18218a69c5d0dc8f87e8acf04a4/template/package.json) `engines`; docs [L9](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/_getting-started-linux-android.md#L9) |
| CLI | `@react-native-community/cli` 20.2.0 | template package.json |
| Metro | `metro-config`/`metro-runtime` ^0.87.1 | [@react-native/metro-config package.json](https://github.com/facebook/react-native/blob/v0.88.0/packages/metro-config/package.json) |

The website's Linux guide lags the release. It still asks for SDK Platform 35 and build-tools 36.0.0 ([L47–L50](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/_getting-started-linux-android.md#L47-L50)). Trust `libs.versions.toml`.

## Gradle, aapt2, CMake and the NDK in the shell

- **The wrapper's Gradle runs on NixOS.** It is Java, started with the shell's JDK. I unpacked `gradle-9.4.1-bin.zip`, the same file the wrapper downloads, and checked its native parts with `readelf`:
  - `libnative-platform.so` needs only `libc.so.6`;
  - `libgradle-fileevents.so` needs only glibc libraries (`libc`, `libm`, `libpthread`, `libdl`, `ld-linux`);
  - both are `dlopen`ed into a JVM that has already loaded nixpkgs' glibc;
  - only the curses console helper needs `libstdc++` and `ncurses`; I expect Gradle to fall back to a plain console without it (unverified).

  nixpkgs patches exactly these jars for its own Gradle ([gradle default.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/tools/build-managers/gradle/default.nix), `autoPatchelfInJar`). Add `distributionSha256Sum=2ab2958f2a1e51120c326cad6f385153bb11ee93b3c216c5fccebfdfbb7ec6cb` to `gradle-wrapper.properties`, so the download is checked.
- **aapt2.** AGP downloads `aapt2-<ver>-linux.jar` from Google Maven. Its binary asks for `/lib64/ld-linux-x86-64.so.2` (#31). Override it with the SDK's autoPatchelfed copy:
  - The nixpkgs manual recommends `GRADLE_OPTS=-Dorg.gradle.project.android.aapt2FromMavenOverride=…` ([android.section.md L254–L272](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/doc/languages-frameworks/android.section.md#L254-L272)).
  - `org.gradle.project.<name>` system properties become project properties ([build_environment.adoc L156](https://github.com/gradle/gradle/blob/v9.4.1/platforms/documentation/docs/src/docs/userguide/reference/runtime-configuration/build_environment.adoc#L156)).
  - Gradle's docs say `GRADLE_OPTS` "typically doesn't affect the daemon" ([L525–L531](https://github.com/gradle/gradle/blob/v9.4.1/platforms/documentation/docs/src/docs/userguide/reference/runtime-configuration/build_environment.adoc#L525-L531)). Still, the daemon applies the client's system properties for each build ([EstablishBuildEnvironment.java L52](https://github.com/gradle/gradle/blob/v9.4.1/platforms/core-runtime/launcher/src/main/java/org/gradle/launcher/daemon/server/exec/EstablishBuildEnvironment.java#L52)), so the override reaches AGP.
  - An equivalent, more explicit route is `android.aapt2FromMavenOverride=…` in `~/.gradle/gradle.properties`. It cannot go in the repo's `gradle.properties`, because the path is a store path.
  - **nix-ld is an alternative but not a fix.** This host already has `programs.nix-ld` enabled: `/lib64/ld-linux-x86-64.so.2` → `nix-ld-2.0.6`. So the Maven aapt2 might run unpatched. Whether its libraries resolve through nix-ld's default set is unverified. Keep the override, so the shell does not depend on host configuration and matches the sandbox.
- **JDK toolchain.** The RN Gradle plugin asks for `jvmToolchain(17)` and applies the foojay resolver (#31). Gradle auto-detects JDKs from `JAVA_HOME` ([toolchains.adoc L417–L431](https://github.com/gradle/gradle/blob/v9.4.1/platforms/documentation/docs/src/docs/userguide/reference/platforms/jvm/toolchains.adoc#L417-L431)), so JDK 17 in `JAVA_HOME` satisfies it with no download. `-Dorg.gradle.java.installations.auto-download=false` turns a mismatch into an error instead of a silent download of an unpatched JDK.
- **CMake and ninja.** The ninja segfault from #32 lives in the SDK's CMake store path, so it hits the shell exactly as it hit the sandbox. New Architecture always compiles C++ (#31). Write `cmake.dir=<cmakeDir>` into `android/local.properties`. Google: "If you set this property, Gradle no longer uses PATH to find CMake" ([install-ndk](https://developer.android.com/studio/projects/install-ndk)). Point it at the spike's ninja-swapped copy. Keep the path referenced from the shell's env, so the shell's GC root keeps it alive.
- **NDK.** AGP looks for `$ANDROID_HOME/ndk/<android.ndkVersion>`. androidenv links each NDK as `ndk/<version>` plus a default `ndk-bundle` ([compose-android-packages.nix L739–L748](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/mobile/androidenv/compose-android-packages.nix#L739-L748)). The NDK's prebuilt clang is autoPatchelfed (#31), and #32 compiled with it. Don't set `ndk.dir`; it is deprecated.
- **Versions must match exactly.** The SDK is read-only. If any Gradle module asks for a build-tools, NDK, CMake or platform version that is not in the composition, AGP tries to install it and fails ("SDK directory is not writable") ([android.section.md L307–L311](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/doc/languages-frameworks/android.section.md#L307-L311)). When a new native module pins its own `ndkVersion` or `compileSdk`, add it to `nix/android.nix`. Don't patch the module.
- **Hermes.** Debug builds skip JS bundling: `debuggableVariants` defaults to `["debug", "debugOptimized"]` ([ReactExtension.kt L99–L106](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/ReactExtension.kt#L99-L106)), so `hermesc` does not run in the dev loop. Release builds use the statically linked `hermesc` from npm, which needs no patching (#31).

## Node, package manager, Watchman

- **Node.** At our nixpkgs, `nodejs_22` = 22.23.3, `nodejs_24` = 24.21.0, and `nodejs`/`nodejs-slim` = 24.21.0 (evaluated). Use `nodejs_22`, as the spike does, so Metro in the shell and codegen in the sandbox run the same Node. Both satisfy ≥ 22.11.
- **Use npm.** #31's `importNpmLock` reads `package-lock.json`. Run `npm ci` in the shell, through `languages.javascript.npm.install.enable`. Don't use `importNpmLock.linkNodeModulesHook`, whose `node_modules` points into the read-only store, in the shell:
  - The RN Gradle plugin is an included build that writes inside `node_modules/@react-native/gradle-plugin` (#31).
  - Metro requires symlink targets to be inside `watchFolders` ([Metro Configuration.md L114–L128](https://github.com/facebook/metro/blob/v0.87.1/docs/Configuration.md#L114-L128)).

  pnpm (12.9.0 in nixpkgs) and yarn would mean a second lockfile format for Nix, and pnpm's symlinked layout runs into the same `watchFolders` rule. There is no reason to switch.
- **Watchman.** RN's guide calls it "highly recommended" ([L78–L81](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/_getting-started-linux-android.md#L78-L81)). Metro uses it when installed, unless `resolver.useWatchman = false` ([Configuration.md L357–L361](https://github.com/facebook/metro/blob/v0.87.1/docs/Configuration.md#L357-L361)). nixpkgs has `watchman` 2026.07.27.00, built to keep its state under `XDG_STATE_HOME` ([package.nix L76](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/by-name/wa/watchman/package.nix#L76)). Put it in the shell. Without it, Metro falls back to Node's own watcher; both use inotify on Linux (my understanding, not checked in Metro's source).
- **inotify limits.** NixOS sets `fs.inotify.max_user_watches` and `max_user_instances` to 524288 by default ([sysctl.nix L123–L124](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/nixos/modules/config/sysctl.nix#L123-L124)). This host shows both at 524288. Nothing to change.

## Metro

- **Port.** Default 8081 (`--port` defaults to `RCT_METRO_PORT || 8081`, [run-android index.ts L318–L321](https://github.com/react-native-community/cli/blob/v20.2.0/packages/cli-platform-android/src/commands/runAndroid/index.ts#L318-L321); [Metro `server.port`](https://github.com/facebook/metro/blob/v0.87.1/docs/Configuration.md#L674-L678)).
- **USB.** `run-android` runs `adb reverse tcp:<port> tcp:<port>` for each device ([tryRunAdbReverse.ts](https://github.com/react-native-community/cli/blob/v20.2.0/packages/cli-platform-android/src/commands/runAndroid/tryRunAdbReverse.ts), called from [runOnAllDevices.ts](https://github.com/react-native-community/cli/blob/v20.2.0/packages/cli-platform-android/src/commands/runAndroid/runOnAllDevices.ts)). After a phone reconnects, rerun `adb reverse tcp:8081 tcp:8081` by hand ([running-on-device.md, Method 1](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/running-on-device.md#L85-L101)). `--active-arch-only` builds native code only for the connected device's ABI ([buildAndroid/index.ts L110–L114](https://github.com/react-native-community/cli/blob/v20.2.0/packages/cli-platform-android/src/commands/buildAndroid/index.ts#L110-L114)), which cuts C++ build time.
- **Wi-Fi.** Use RN's Dev Menu → Dev Settings → "Debug server host & port for device" set to `<host IP>:8081` ([running-on-device.md, Method 2](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/running-on-device.md#L103-L114)). That needs inbound TCP 8081 open on the host. With wireless adb, `adb reverse` should also work over the adb TCP transport, which avoids the firewall port (expected, unverified on this phone).
- **Running Metro.** Run it in the shell as `npx react-native start`, or as a devenv process (`processes.metro.exec`, then `devenv up`).

## Physical phone over adb on NixOS

- **USB access.** In nixpkgs unstable:
  - `programs.adb` is a removed option: "no longer needed as systemd 258 handles uaccess rules automatically. Please add `pkgs.android-tools`…" ([rename.nix L66–L72](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/nixos/modules/rename.nix#L66-L72));
  - `android-udev-rules` throws, "superseded by built-in systemd uaccess rules", added 2025-10-21 ([aliases.nix L303](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/top-level/aliases.nix#L303));
  - `programs.adb.enable` still exists in NixOS 25.11 but not in 26.05 (NixOS option search).

  systemd 258 marks USB interfaces of class `dc0201`/`ff4201`/`ff4203` (ADB DbC, ADB, fastboot) as `ID_DEBUG_APPLIANCE="android"` and tags them `uaccess` ([70-uaccess.rules.in L80–L92, L128–L129](https://github.com/systemd/systemd/blob/v258/rules.d/70-uaccess.rules.in#L80-L92)). This host (systemd 261.3) ships that rule in `/run/current-system/sw/lib/udev/rules.d/70-uaccess.rules`. So no `adbusers` or `plugdev` group, and no custom rule. RN's docs still show a `51-android-usb.rules` plugdev rule ([running-on-device.md L271](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/running-on-device.md#L271)); it is not needed here. `uaccess` grants the ACL to the user of the active local seat session, so adb over SSH or from a non-seat session would not get access (my understanding of logind; not tested).
- **Which adb.** The RN CLI runs `$ANDROID_HOME/platform-tools/adb` whenever `ANDROID_HOME` is set ([getAdbPath.ts](https://github.com/react-native-community/cli/blob/v20.2.0/packages/cli-platform-android/src/commands/runAndroid/getAdbPath.ts)). In the shell that is the SDK's adb, 1.0.41 / 37.0.1-15733141 (evaluated). nixpkgs' `android-tools` is 37.0.0p1, also "Android Debug Bridge version 1.0.41" (checked). Both report protocol 1.0.41, so a system-wide `android-tools` and the shell's adb should share one server without the "server version doesn't match this client; killing…" restart loop (inference). Install `android-tools` in the NixOS config only if you want adb outside the shell.
- **Wireless debugging (Android 11+).** Developer options → Wireless debugging → "Pair using pairing code", then `adb pair <ip>:<pair-port>`, then `adb connect <ip>:<port>` with the port the device shows ([adb docs](https://developer.android.com/tools/adb)). Google's troubleshooting expects adb ≥ 37.0.0, `mdns_enabled: true` and backend `LIBADBMDNS` in `adb server-status`; `ADB_MDNS=1` and `ADB_MDNS_OPENSCREEN=0` fix the last two (same page).
- **Firewall.** `adb pair`/`adb connect` are outbound, so they need no inbound rule. mDNS auto-discovery receives multicast on UDP 5353, which the NixOS firewall may drop. Open it, or skip discovery and connect by IP (inference, unverified). Metro over Wi-Fi without `adb reverse` needs TCP 8081 inbound.

## Emulator on this AMD machine

- **KVM: ready.** The host has a Ryzen 9 7950X3D (`svm`), `kvm_amd` loaded with `nested=1`, and `/dev/kvm` mode `0666`. systemd's rule is `KERNEL=="kvm", GROUP="kvm", MODE="{{DEV_KVM_MODE}}"` ([50-udev-default.rules.in L113](https://github.com/systemd/systemd/blob/v258/rules.d/50-udev-default.rules.in#L113)), and the installed rule on this host has `MODE="0666"`. So no `kvm` group is needed. Google needs AMD-V plus RVI and checks with `emulator -accel-check` ([emulator-acceleration](https://developer.android.com/studio/run/emulator-acceleration)).
- **androidenv's emulator** (37.2.4 is the newest in `repo.json`) is autoPatchelfed. It is wrapped with `libGL`, `dbus` and `systemd` on `LD_LIBRARY_PATH`, and `VK_ADD_DRIVER_FILES=/run/opengl-driver/share/vulkan/icd.d` ([emulator.nix L75–L85](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/mobile/androidenv/emulator.nix#L75-L85)). This host has Mesa's `radeon_icd.x86_64.json`, so `-gpu host` (Vulkan on RADV) is plausible (unverified). If host mode misbehaves, use `-gpu swiftshader` or `-gpu lavapipe`. Google marks `swiftshader_indirect` deprecated since emulator 36.4.9 ([emulator-acceleration](https://developer.android.com/studio/run/emulator-acceleration)).
- **ABI.** `onnxruntime-android-1.24.3.aar` ships `jni/{arm64-v8a,armeabi-v7a,x86,x86_64}/libonnxruntime.so` (listed from the spike's Maven artifact). The spike's single `arm64-v8a` choice is only a release-APK flag (`-PreactNativeArchitectures=arm64-v8a`). For an emulator, build debug for `x86_64`; `--active-arch-only` does this automatically. An `arm64-v8a`-only release APK would not load its native libraries on an `x86_64` image. Whether ARM translation in recent x86_64 images could run it is unverified.
- **Cost.** Emulator zip 359 MB, plus an x86_64 image: 0.84 GB (`default` 36), 1.9 GB (`google_apis` 36) or 2.2 GB (`google_apis` 37.0) zipped ([repo.json](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/mobile/androidenv/repo.json)). None of it is on a public cache.
- **Verdict.** Practical, but not worth it now. A real phone measures what DELMIR cares about (ORT speed on ARM, camera). Revisit when you want camera-free UI tests or screenshots in CI. Then add the emulator as a **separate** composition or devenv profile, so the shared APK composition stays small.

## Pitfalls in the dev shell

| Problem | Source | Fix |
|---|---|---|
| AGP's aapt2 from Maven is an unpatched ELF | #31; [android.section.md](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/doc/languages-frameworks/android.section.md#L254-L272) | `GRADLE_OPTS=-Dorg.gradle.project.android.aapt2FromMavenOverride=$SDK/build-tools/37.0.0/aapt2` (devenv's module does this too) |
| SDK CMake's autoPatchelfed ninja segfaults | #32 | `cmake.dir=<ninja-swapped cmakeDir>` in `android/local.properties`, written by `enterShell` |
| SDK is read-only; AGP auto-install fails | [android.section.md L307–L311](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/doc/languages-frameworks/android.section.md#L307-L311) | keep `nix/android.nix` versions equal to every module's `compileSdk`/`buildToolsVersion`/`ndkVersion`; never run `sdkmanager` |
| Licence/unfree refusal | [license.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/mobile/androidenv/license.nix); [yaml-options](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/reference/yaml-options.mdx) | `devenv.yaml`: `nixpkgs.allow_unfree: true` and `nixpkgs.android_sdk.accept_license: true`; flake: the same two config keys (evaluated) |
| devenv `android` module drags in `emulateApp` (platform 35, second SDK) and writes `local.properties` in the wrong dir | [android.nix @ v2.4.0](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix#L304-L413) | don't use `android.enable`; use the shared file |
| foojay toolchain download of an unpatched JDK | #31; [toolchains.adoc](https://github.com/gradle/gradle/blob/v9.4.1/platforms/documentation/docs/src/docs/userguide/reference/platforms/jvm/toolchains.adoc#L417-L440) | `JAVA_HOME` = JDK 17; `-Dorg.gradle.java.installations.auto-download=false` |
| `./gradlew` fetches an unchecked distribution | [wrapper props](https://github.com/react-native-community/template/blob/264d48336197f18218a69c5d0dc8f87e8acf04a4/template/android/gradle/wrapper/gradle-wrapper.properties) | add `distributionSha256Sum=2ab2958f…7ec6cb` |
| Gradle daemon keeps old store paths after a nixpkgs bump | Gradle daemon behaviour (my understanding) | `./gradlew --stop` after changing the shell |
| `ANDROID_USER_HOME` per project (devenv module: `$(pwd)/.android`) may also move adb's key, so the phone asks to authorize again | devenv module L404–L411; adb key location unverified | leave `ANDROID_USER_HOME` unset in the shell; only the sandbox needs it |
| `local.properties` holds store paths | AGP reads it at configure time | regenerate in `enterShell`; keep it git-ignored (the template ignores it) |
| SDK (≈ 3.9 GiB NAR, #32) is on no public cache | NDK narinfo 404 on cache.nixos.org and devenv.cachix.org (checked) | build it once; the shared file keeps the shell from building a second SDK; don't push to a public Cachix (licence, #31) |
| Two adb servers of different versions fight | adb client/server version check (general adb behaviour) | use the shell's adb; `android-tools` 37.0.0p1 and SDK 37.0.1 both report 1.0.41 (checked) |
| `swiftshader_indirect` no longer works | [emulator-acceleration](https://developer.android.com/studio/run/emulator-acceleration) | `-gpu host`, `swiftshader` or `lavapipe` |
| devenv warns "2.4.0 is newer than devenv input (2.3.1)" with the input pinned to `v2.4.0` | the tag's `src/modules/latest-version` file says `2.3.1` (checked) | harmless |

## NixOS host configuration vs the repo

| Concern | Where | What |
|---|---|---|
| USB adb access | nothing needed on systemd ≥ 258 | don't set `programs.adb` (removed); no udev rule; no group |
| adb outside the shell | user's NixOS config (optional) | `environment.systemPackages = [ pkgs.android-tools ];` |
| Wireless Metro without `adb reverse` | user's NixOS config | `networking.firewall.allowedTCPPorts = [ 8081 ];` |
| mDNS discovery for wireless adb | user's NixOS config (optional, unverified need) | `networking.firewall.allowedUDPPorts = [ 5353 ];` |
| KVM for an emulator | already true here | `kvm-amd` loaded, `/dev/kvm` 0666; nothing to add |
| inotify | already true here | NixOS defaults are 524288 |
| nix-ld | already enabled here | not relied on; keep the aapt2 override |
| SDK, JDK, Node, Watchman, aapt2 override, `cmake.dir` | repo (`nix/android.nix`, `devenv.nix`, `devenv.yaml`) | as in the sketch |

So DELMIR needs **no host changes** for USB development. Wireless Metro needs one firewall line, or none if you use `adb reverse` over wireless adb.

## Open questions for #19 ("How do Nix and devenv build and provide DELMIR's environments?")

1. Standalone `devenv.yaml` (two lockfiles plus a rev-equality check) or the flake's `devenv.lib.mkShell` (one lock, `nix develop --no-pure-eval`, no eval cache or GC root)? This note recommends standalone.
2. How do the `app` and `training` shells coexist: one `devenv.yaml` with profiles, or per-directory `devenv.yaml` files with imports? Do both pin the same nixpkgs? `training` may need ROCm.
3. Where does `nix/android.nix` live, and does the repo flake expose it, e.g. `legacyPackages.androidToolchain`, so CI can build only the SDK?
4. Does `languages.javascript.npm.install.enable` (auto `npm ci` on shell entry) fit the flaky network, or should `npm ci` stay manual?
5. Should Metro be a devenv process (`devenv up`), or stay a manual `npx react-native start`?
6. Is an emulator profile wanted later (separate composition, x86_64 image, 1–2.5 GB unfree)?
7. Is a local, private binary cache for the SDK worth it (licence forbids public redistribution, #31)?

## Sources

devenv (v2.4.0, tag commit `b904dcb51fe48c30db250038241507f60752f222`):
- [src/modules/integrations/android.nix](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/integrations/android.nix), [src/modules/languages/javascript.nix](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/languages/javascript.nix), [src/modules/languages/java.nix](https://github.com/cachix/devenv/blob/v2.4.0/src/modules/languages/java.nix), [flake.nix](https://github.com/cachix/devenv/blob/v2.4.0/flake.nix)
- Docs: [integrations/android.md](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/integrations/android.md), [guides/using-with-flakes.md](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/guides/using-with-flakes.md), [guides/using-with-flake-parts.md](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/guides/using-with-flake-parts.md), [reference/yaml-options.mdx](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/reference/yaml-options.mdx), [integrations/direnv.mdx](https://github.com/cachix/devenv/blob/v2.4.0/docs/src/content/docs/integrations/direnv.mdx)
- [Releases](https://github.com/cachix/devenv/releases)

nixpkgs at `02c087f3fe673c9e317f206a627cb6b910336dbe`:
- [doc/languages-frameworks/android.section.md](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/doc/languages-frameworks/android.section.md)
- [androidenv/](https://github.com/NixOS/nixpkgs/tree/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/mobile/androidenv): `default.nix`, `compose-android-packages.nix`, `emulate-app.nix`, `emulator.nix`, `license.nix`, `repo.json`
- [gradle/default.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/development/tools/build-managers/gradle/default.nix), [watchman/package.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/by-name/wa/watchman/package.nix)
- [nixos/modules/rename.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/nixos/modules/rename.nix), [pkgs/top-level/aliases.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/pkgs/top-level/aliases.nix), [nixos/modules/config/sysctl.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/nixos/modules/config/sysctl.nix), [nixos/modules/programs/nix-ld.nix](https://github.com/NixOS/nixpkgs/blob/02c087f3fe673c9e317f206a627cb6b910336dbe/nixos/modules/programs/nix-ld.nix)
- Package versions from `nix eval` at this rev: `nodejs_22` 22.23.3, `nodejs_24`/`nodejs`/`nodejs-slim` 24.21.0, `jdk17` 17.0.20.1+1, `jdk` 21.0.12.1+1, `android-tools` 37.0.0p1, `watchman` 2026.07.27.00, `pnpm` 12.9.0, `ninja` 1.13.2, `nix-ld` 2.0.6
- NixOS option search (25.11 vs 26.05) for `programs.adb.enable`

systemd v258:
- [rules.d/70-uaccess.rules.in](https://github.com/systemd/systemd/blob/v258/rules.d/70-uaccess.rules.in), [rules.d/50-udev-default.rules.in](https://github.com/systemd/systemd/blob/v258/rules.d/50-udev-default.rules.in)

React Native:
- [libs.versions.toml @ v0.88.0](https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/gradle/libs.versions.toml), [ReactExtension.kt @ v0.88.0](https://github.com/facebook/react-native/blob/v0.88.0/packages/gradle-plugin/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/ReactExtension.kt), [packages/metro-config/package.json @ v0.88.0](https://github.com/facebook/react-native/blob/v0.88.0/packages/metro-config/package.json), [releases](https://github.com/facebook/react-native/releases)
- [react-native-community/template 0.88-stable @ 264d483](https://github.com/react-native-community/template/tree/264d48336197f18218a69c5d0dc8f87e8acf04a4/template): `android/build.gradle`, `android/gradle/wrapper/gradle-wrapper.properties`, `package.json`, `metro.config.js`
- react-native-website @ `d037e79`: [_getting-started-linux-android.md](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/_getting-started-linux-android.md), [running-on-device.md](https://github.com/facebook/react-native-website/blob/d037e79188a6ee3caee91949fa9480affc06cf7b/docs/running-on-device.md)
- [react-native-community/cli @ v20.2.0, cli-platform-android](https://github.com/react-native-community/cli/tree/v20.2.0/packages/cli-platform-android/src/commands): `runAndroid/index.ts`, `getAdbPath.ts`, `tryRunAdbReverse.ts`, `runOnAllDevices.ts`, `buildAndroid/index.ts`
- [Metro docs/Configuration.md @ v0.87.1](https://github.com/facebook/metro/blob/v0.87.1/docs/Configuration.md)

Gradle v9.4.1:
- [build_environment.adoc](https://github.com/gradle/gradle/blob/v9.4.1/platforms/documentation/docs/src/docs/userguide/reference/runtime-configuration/build_environment.adoc), [toolchains.adoc](https://github.com/gradle/gradle/blob/v9.4.1/platforms/documentation/docs/src/docs/userguide/reference/platforms/jvm/toolchains.adoc), [EstablishBuildEnvironment.java](https://github.com/gradle/gradle/blob/v9.4.1/platforms/core-runtime/launcher/src/main/java/org/gradle/launcher/daemon/server/exec/EstablishBuildEnvironment.java)
- [gradle-9.4.1-bin.zip.sha256](https://services.gradle.org/distributions/gradle-9.4.1-bin.zip.sha256)

Android developer docs (fetched 2026-10-21):
- [adb](https://developer.android.com/tools/adb), [Install and configure the NDK and CMake](https://developer.android.com/studio/projects/install-ndk), [Configure hardware acceleration](https://developer.android.com/studio/run/emulator-acceleration), [Emulator command-line options](https://developer.android.com/studio/run/emulator-commandline)

Prior DELMIR work:
- [#31 research note](https://github.com/the-dr-lazy/delmir/blob/research/nix-react-native-apk/docs/research/nix-react-native-apk.md); [#32 spike](https://github.com/the-dr-lazy/delmir/issues/32) (`prototype/nix-apk`, `spike-nix-apk/package.nix`, `flake.nix`, `README.md`)

Checks made on this host (2026-10-21):
- `nix eval` and `devenv shell` of the sketch, in standalone and flake form, plus the devenv `android` module for comparison; store-path comparison with the spike's existing outputs;
- `readelf` on the native libraries inside `gradle-9.4.1-bin.zip`;
- `unzip -l` on `onnxruntime-android-1.24.3.aar`;
- `adb version` of the SDK adb and of `android-tools`;
- narinfo lookups on cache.nixos.org and devenv.cachix.org;
- host state: `/dev/kvm`, `/sys/module/kvm_amd`, udev rules under `/run/current-system`, inotify sysctls, `/lib64/ld-linux-x86-64.so.2`.
