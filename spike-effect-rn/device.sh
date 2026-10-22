#!/usr/bin/env bash
# THROWAWAY SPIKE (delmir#43): installs the Nix-built APKs on the USB phone and records every
# on-device measurement into results/. No taps needed: commands go in as delmirspike:// links.
# Usage (from spike-effect-rn/): nix shell nixpkgs#android-tools nixpkgs#sqlcipher nixpkgs#bc nixpkgs#jdk17_headless -c ./device.sh [variant...]
# APK_DIR=<dir> takes delmir-spike-<variant>.apk files from there (e.g. the CI artifact) instead of `nix build`.
set -euo pipefail
cd "$(dirname "$0")"
PKG=com.delmirspike
ACT=$PKG/com.helloworld.MainActivity
adb get-state >/dev/null
OUT=results/$(adb shell getprop ro.product.model | tr -d '\r' | tr ' ' '_')
mkdir -p "$OUT"
if [ $# -gt 0 ]; then VARIANTS=("$@"); else VARIANTS=(apk apk-op18 apk-local apk-baseline apk-debug); fi

SDK=$(nix build --no-link --print-out-paths .#apk.androidsdk)/libexec/android-sdk
APKSIGNER=$SDK/build-tools/37.0.0/apksigner

{
  echo "model=$(adb shell getprop ro.product.model) manufacturer=$(adb shell getprop ro.product.manufacturer)"
  echo "android=$(adb shell getprop ro.build.version.release) sdk=$(adb shell getprop ro.build.version.sdk) abi=$(adb shell getprop ro.product.cpu.abi)"
  echo "build=$(adb shell getprop ro.build.fingerprint)"
} | tee "$OUT/device.txt"

since() { adb shell date +%s.%N | tr -d '\r'; }
# Wait until a `SPIKE {"event":"<event>"...}` line appears in logcat after the given device time.
wait_event() {
  local event=$1 t0=$2 timeout=${3:-60} i
  for ((i = 0; i < timeout * 2; i++)); do
    line=$(adb logcat -d -v epoch -s ReactNativeJS:I | awk -v t0="$t0" '$1 > t0' | grep -F "SPIKE {\"event\":\"$event\"" | tail -1 || true)
    if [ -n "$line" ]; then echo "$line"; return 0; fi
    if adb logcat -d -v epoch -s ReactNativeJS:I | awk -v t0="$t0" '$1 > t0' | grep -q 'command-failed\|FATAL'; then
      adb logcat -d -v epoch | awk -v t0="$t0" '$1 > t0' | grep -E 'SPIKE|FATAL|AndroidRuntime|ReactNativeJS' | tail -20 >&2
      return 1
    fi
    sleep 0.5
  done
  echo "timeout waiting for $event" >&2; return 1
}
json() { sed 's/^.*SPIKE //'; }

cmd() { # variant url event
  local v=$1 url=$2 event=$3 t0
  t0=$(since)
  adb shell am start -a android.intent.action.VIEW -d "\"$url\"" $PKG >/dev/null
  wait_event "$event" "$t0" 300 | json | tee -a "$OUT/$v/events.jsonl"
  wait_event command-done "$t0" 300 >/dev/null
}

for v in "${VARIANTS[@]}"; do
  echo "=== $v"
  mkdir -p "$OUT/$v"; : > "$OUT/$v/events.jsonl"
  if [ -n "${APK_DIR:-}" ]; then
    name=$(nix eval --raw ".#$v.name"); name=${name#delmir-spike-apk-}; apk=$APK_DIR/delmir-spike-${name%-0.0.1}.apk
  else
    apk=$(ls "$(nix build --no-link --print-out-paths ".#$v")"/*.apk)
  fi
  echo "apk=$apk"
  "$APKSIGNER" sign --ks android/app/debug.keystore --ks-pass pass:android --key-pass pass:android \
    --out "$OUT/$v/signed.apk" "$apk"
  unzip -lv "$apk" | grep -E 'index.android.bundle|\.so$' | awk '{print $1, $3, $8}' > "$OUT/$v/apk-entries.txt"
  echo "apk_bytes=$(stat -c%s "$apk")" > "$OUT/$v/apk-size.txt"
  adb uninstall $PKG >/dev/null 2>&1 || true
  adb install "$OUT/$v/signed.apk" >/dev/null

  if [[ $v == apk-debug* ]]; then
    # Dev: Metro serves the bundle over adb reverse, and Hermes compiles it from source on the phone.
    adb reverse tcp:8081 tcp:8081
    npx react-native start --reset-cache > "$OUT/$v/metro.log" 2>&1 &
    metro=$!
    sleep 15
    adb logcat -c; t0=$(since)
    adb shell am start -W -n $ACT >/dev/null
    wait_event first-data "$t0" 180 >/dev/null || true
    adb logcat -d -v epoch | grep -E 'SPIKE|ReactNativeJS.*(Error|error)|FATAL' > "$OUT/$v/dev-run.txt" || true
    adb logcat -d -v epoch -s ReactNativeJS:I | grep -F 'SPIKE {"event":"' | json >> "$OUT/$v/events.jsonl" || true
    kill $metro || true
    continue
  fi

  # First run: creates the key and migrates; keep its events.
  adb logcat -c; t0=$(since)
  adb shell am start -W -n $ACT >/dev/null
  wait_event first-screen "$t0" 60 >/dev/null
  if [[ $v != apk-baseline* ]]; then
    wait_event first-data "$t0" 60 >/dev/null
    adb logcat -d -v epoch -s ReactNativeJS:I | grep -F 'SPIKE {"event":"' | json >> "$OUT/$v/events.jsonl"
  else
    wait_event probe "$t0" 5 | json >> "$OUT/$v/events.jsonl"
  fi
  sleep 2

  # Cold start x10: ActivityTaskManager START line -> JS first-screen log (device clock), and am's TotalTime.
  : > "$OUT/$v/cold-start.txt"
  for i in $(seq 1 10); do
    adb shell am force-stop $PKG; sleep 2; adb logcat -c; t0=$(since)
    total=$(adb shell am start -W -n $ACT | tr -d '\r' | awk -F': ' '/TotalTime/ {print $2}')
    fs=$(wait_event first-screen "$t0" 60 | awk '{print $1}')
    st=$(adb logcat -d -v epoch | grep -E 'START u0 .*'"$PKG" | head -1 | awk '{print $1}')
    echo "run=$i am_total_ms=$total start_to_first_screen_ms=$(echo "($fs - $st) * 1000" | bc)" | tee -a "$OUT/$v/cold-start.txt"
  done
  [[ $v == apk-baseline* ]] && continue

  cmd "$v" "delmirspike://checks" checks
  cmd "$v" "delmirspike://migrations" migrations
  cmd "$v" "delmirspike://seed?n=1000" seed
  for mode in sync async; do
    adb shell dumpsys gfxinfo $PKG reset >/dev/null
    cmd "$v" "delmirspike://bench?mode=$mode&runs=20" bench
    adb shell dumpsys gfxinfo $PKG | grep -E 'Total frames rendered|Janky frames|percentile' > "$OUT/$v/gfxinfo-$mode.txt"
  done

  if [ "$v" = apk ] || [ "$v" = apk-x86_64 ]; then
    # SQLCipher really on? Probe DBs live in the external files dir, the only place adb can read
    # on a non-debuggable release build.
    cmd "$v" "delmirspike://cipher" cipher-probe
    key=$(tail -1 "$OUT/$v/events.jsonl" | sed 's/.*"keyHex":"\([0-9a-f]*\)".*/\1/')
    adb pull /sdcard/Android/data/$PKG/files/cipher-probe.db "$OUT/$v/" >/dev/null
    adb pull /sdcard/Android/data/$PKG/files/plain-probe.db "$OUT/$v/" >/dev/null
    {
      echo "--- sqlite3 plain-probe.db (control)"; sqlite3 "$OUT/$v/plain-probe.db" 'SELECT v FROM probe' 2>&1 || true
      echo "--- sqlite3 cipher-probe.db"; sqlite3 "$OUT/$v/cipher-probe.db" 'SELECT v FROM probe' 2>&1 || true
      echo "--- grep marker in raw bytes"; grep -c DELMIR-SECRET-MARKER "$OUT/$v/plain-probe.db" "$OUT/$v/cipher-probe.db" || true
      echo "--- sqlcipher cipher-probe.db with the key"
      printf "PRAGMA key = \"x'%s'\";\nSELECT v FROM probe;\n" "$key" | sqlcipher "$OUT/$v/cipher-probe.db" 2>&1 || true
    } | tee "$OUT/$v/cipher-check.txt"

    # Backup exclusion.
    {
      echo "--- dumpsys package flags"; adb shell dumpsys package $PKG | grep -E 'flags=|privateFlags=' | head -4
      echo "--- bmgr enabled"; adb shell bmgr enabled
      echo "--- bmgr backupnow"; adb shell bmgr backupnow $PKG 2>&1 | tr -d '\r'
    } | tee "$OUT/$v/backup-check.txt"
  fi
done
echo "done: results in $OUT/"
