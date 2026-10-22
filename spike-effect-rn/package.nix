# THROWAWAY SPIKE (delmir#43), grown from the delmir#32 spike on prototype/nix-apk.
{
  # Spike variants (see flake.nix).
  entry ? "index.js",
  opSqlite18 ? false,
  buildType ? "release",
  patchMigrator ? true,
  abi ? "arm64-v8a", # x86_64 only for the local KVM emulator

  lib,
  stdenv,
  writeText,
  androidenv,
  gradle-packages,
  jdk17_headless,
  nodejs_22,
  importNpmLock,
  procps,
  ninja,
  runCommand,
}:
let
  android = androidenv.composeAndroidPackages {
    platformVersions = [ "37" ];
    buildToolsVersions = [ "37.0.0" ];
    includeNDK = true;
    ndkVersions = [ "27.1.12297006" ];
    includeCmake = true;
    cmakeVersions = [ "3.31.6" ]; # 3.22.1's bundled ninja segfaults after autoPatchelf (glibc 2.44)
    includeEmulator = false;
    includeSystemImages = false;
    includeSources = false;
    toolsVersion = null;
  };
  sdk = "${android.androidsdk}/libexec/android-sdk";
  # androidenv autoPatchelfs Google's ninja into a binary that segfaults (seen with both
  # CMake 3.22.1 and 3.31.6), so keep the SDK's CMake but swap in nixpkgs' ninja.
  cmakeDir = runCommand "android-cmake-3.31.6-nixpkgs-ninja" { } ''
    mkdir -p $out
    cp -rs ${sdk}/cmake/3.31.6/. $out/
    chmod -R u+w $out/bin
    ln -sf ${ninja}/bin/ninja $out/bin/ninja
  '';
  jdk = jdk17_headless;
  # nixpkgs' gradle_9 (9.8.0) bundles Kotlin 2.4 metadata, which the RN Gradle plugin's
  # Kotlin 2.2 compiler rejects, so pin the RN template's wrapper version instead.
  gradle =
    (gradle-packages.mkGradle {
      version = "9.4.1";
      hash = "sha256-KrKVjyoeURIMMmytbzhRU7sR7pOzwhbF/M6/37t+xss=";
      defaultJava = jdk;
    }).wrapped;
  baseSrc = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./package.json
      ./package-lock.json
      ./index.js
      ./index.local.js
      ./index.baseline.js
      ./src
      ./app.json
      ./babel.config.js
      ./babel-plugin-import-meta.js
      ./metro.config.js
      ./tsconfig.json
      ./patch-migrator.sh
      ./android
    ];
  };
  # op-sqlite 18.2.5 is outside @effect/sql-sqlite-react-native's <18 peer range: swap in op18/'s
  # package.json (with an npm override) and lockfile.
  src =
    if opSqlite18 then
      runCommand "delmir-spike-src-op18" { } ''
        cp -r ${baseSrc} $out
        chmod -R u+w $out
        cp ${./op18/package.json} $out/package.json
        cp ${./op18/package-lock.json} $out/package-lock.json
      ''
    else
      baseSrc;
  variant = lib.concatStringsSep "-" (
    [ (lib.removeSuffix ".js" entry) ]
    ++ lib.optional opSqlite18 "op18"
    ++ lib.optional (!patchMigrator) "unpatched"
    ++ lib.optional (abi != "arm64-v8a") abi
    ++ [ buildType ]
  );
  gradleTask = if buildType == "debug" then ":app:assembleDebug" else ":app:assembleRelease";
in
stdenv.mkDerivation (finalAttrs: {
  pname = "delmir-spike-apk-${variant}";
  version = "0.0.1";

  inherit src;

  npmDeps = importNpmLock { npmRoot = if opSqlite18 then ./op18 else baseSrc; };

  nativeBuildInputs = [
    gradle
    jdk
    nodejs_22
    importNpmLock.npmConfigHook
    procps # spike instrumentation only
  ];

  mitmCache = gradle.fetchDeps {
    pkg = finalAttrs.finalPackage;
    # Recorded in CI for both op-sqlite 17 and 18: the two recordings were byte-identical.
    data = ./deps.json;
  };
  gradleBuildTask = gradleTask;
  # Record what both build types need, so one deps.json serves every variant.
  gradleUpdateTask = ":app:assembleRelease :app:assembleDebug";
  gradleInitScript = writeText "empty-init.gradle" "";

  gradleFlags = [
    "--project-dir"
    "android"
    "-Dorg.gradle.java.installations.auto-download=false"
    "-Dorg.gradle.java.installations.paths=${jdk.home}"
    "-Pandroid.aapt2FromMavenOverride=${sdk}/build-tools/37.0.0/aapt2"
    "-Pkotlin.compiler.execution.strategy=in-process"
    "-PreactNativeArchitectures=${abi}"
    "-PincludeJitpackRepository=false"
    "-PspikeEntry=${entry}"
    "-x"
    "lint"
  ];

  env = {
    ANDROID_HOME = sdk;
    ANDROID_SDK_ROOT = sdk;
    ANDROID_NDK_ROOT = "${sdk}/ndk/27.1.12297006";
    CI = "1";
  };

  # Spike instrumentation: sample the sandbox's disk use and the summed RSS of every
  # process in it (the sandbox has its own PID namespace) every 2 s; keep the peaks.
  preConfigure = ''
    (
      peak_disk=0; peak_rss=0
      while sleep 2; do
        d=$(du -sk "$NIX_BUILD_TOP" 2>/dev/null | cut -f1)
        r=$(ps -eo rss= | awk '{s+=$1} END {print s}')
        (( d > peak_disk )) && peak_disk=$d
        (( r > peak_rss )) && peak_rss=$r
        printf 'peak_build_dir_kib=%s\npeak_rss_kib=%s\n' $peak_disk $peak_rss > "$NIX_BUILD_TOP/.spike-peaks"
      done
    ) &
    echo "phase configure start $(date +%s)" >> "$NIX_BUILD_TOP/.spike-times"
  '';

  preBuild = ''
    echo "phase build start $(date +%s)" >> "$NIX_BUILD_TOP/.spike-times"
    export ANDROID_USER_HOME=$TMPDIR/android-user-home
    mkdir -p $ANDROID_USER_HOME
    printf 'sdk.dir=%s\ncmake.dir=%s\n' ${sdk} ${cmakeDir} > android/local.properties
  '' + lib.optionalString patchMigrator ''
    sh patch-migrator.sh node_modules
  '';

  installPhase = ''
    runHook preInstall
    apk=$(ls android/app/build/outputs/apk/${buildType}/*.apk)
    install -Dm644 $apk $out/delmir-spike-${variant}.apk
    echo "phase install start $(date +%s)" >> "$NIX_BUILD_TOP/.spike-times"
    cat "$NIX_BUILD_TOP/.spike-times" "$NIX_BUILD_TOP/.spike-peaks" > $out/spike-metrics.txt
    runHook postInstall
  '';

  allowedReferences = [ ];

  passthru = {
    androidsdk = android.androidsdk;
    inherit cmakeDir;
  };
})
