# THROWAWAY SPIKE (delmir#32), grown from the untested sketch in
# docs/research/nix-react-native-apk.md on research/nix-react-native-apk.
{
  lib,
  stdenv,
  writeText,
  androidenv,
  gradle-packages,
  jdk17_headless,
  nodejs_22,
  importNpmLock,
  procps,
}:
let
  android = androidenv.composeAndroidPackages {
    platformVersions = [ "37" ];
    buildToolsVersions = [ "37.0.0" ];
    includeNDK = true;
    ndkVersions = [ "27.1.12297006" ];
    includeCmake = true;
    cmakeVersions = [ "3.22.1" ];
    includeEmulator = false;
    includeSystemImages = false;
    includeSources = false;
    toolsVersion = null;
  };
  sdk = "${android.androidsdk}/libexec/android-sdk";
  jdk = jdk17_headless;
  # nixpkgs' gradle_9 (9.8.0) bundles Kotlin 2.4 metadata, which the RN Gradle plugin's
  # Kotlin 2.2 compiler rejects, so pin the RN template's wrapper version instead.
  gradle =
    (gradle-packages.mkGradle {
      version = "9.4.1";
      hash = "sha256-KrKVjyoeURIMMmytbzhRU7sR7pOzwhbF/M6/37t+xss=";
      defaultJava = jdk;
    }).wrapped;
in
stdenv.mkDerivation (finalAttrs: {
  pname = "delmir-spike-apk";
  version = "0.0.1";

  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./package.json
      ./package-lock.json
      ./index.js
      ./App.tsx
      ./app.json
      ./babel.config.js
      ./metro.config.js
      ./tsconfig.json
      ./android
    ];
  };

  npmDeps = importNpmLock { npmRoot = finalAttrs.src; };

  nativeBuildInputs = [
    gradle
    jdk
    nodejs_22
    importNpmLock.npmConfigHook
    procps # spike instrumentation only
  ];

  mitmCache = gradle.fetchDeps {
    pkg = finalAttrs.finalPackage;
    data = ./deps.json;
  };
  gradleBuildTask = ":app:assembleRelease";
  gradleUpdateTask = finalAttrs.gradleBuildTask;
  gradleInitScript = writeText "empty-init.gradle" "";

  gradleFlags = [
    "--project-dir"
    "android"
    "-Dorg.gradle.java.installations.auto-download=false"
    "-Dorg.gradle.java.installations.paths=${jdk.home}"
    "-Pandroid.aapt2FromMavenOverride=${sdk}/build-tools/37.0.0/aapt2"
    "-Pkotlin.compiler.execution.strategy=in-process"
    "-PreactNativeArchitectures=arm64-v8a"
    "-PincludeJitpackRepository=false"
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
    printf 'sdk.dir=%s\ncmake.dir=%s\n' ${sdk} ${sdk}/cmake/3.22.1 > android/local.properties
  '';

  installPhase = ''
    runHook preInstall
    install -Dm644 android/app/build/outputs/apk/release/app-release-unsigned.apk $out/delmir-spike-unsigned.apk
    echo "phase install start $(date +%s)" >> "$NIX_BUILD_TOP/.spike-times"
    cat "$NIX_BUILD_TOP/.spike-times" "$NIX_BUILD_TOP/.spike-peaks" > $out/spike-metrics.txt
    runHook postInstall
  '';

  allowedReferences = [ ];

  passthru.androidsdk = android.androidsdk;
})
