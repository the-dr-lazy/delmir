#!/usr/bin/env bash
# THROWAWAY SPIKE (delmir#43): the build-time checks that need no phone. Bundles each entry with
# Metro (release and dev) and compiles it with RN 0.88's hermesc, with and without the import.meta
# plugin and the Migrator patch. Writes results/offline.txt. Needs `npm ci` first.
set -uo pipefail
cd "$(dirname "$0")"
OUT=results/offline.txt; T=$(mktemp -d); mkdir -p results; : > $OUT
H=node_modules/hermes-compiler/hermesc/linux64-bin/hermesc
M=node_modules/effect/dist/sql/Migrator.js
# Pristine Migrator.js from the npm tarball, so the script works whatever state node_modules is in.
npm pack effect@4.0.5 --pack-destination $T >/dev/null 2>&1 && tar -xzf $T/effect-4.0.5.tgz -C $T package/dist/sql/Migrator.js
b() { # name entry dev patched [env...]
  local name=$1 entry=$2 dev=$3 patched=$4; shift 4
  cp $T/package/dist/sql/Migrator.js $M; [ $patched = yes ] && sh patch-migrator.sh node_modules
  if env "$@" npx react-native bundle --platform android --dev $dev --minify false --entry-file $entry \
      --bundle-output $T/$name.js --reset-cache > $T/$name.metro.log 2>&1; then
    local O=-O; [ $dev = true ] && O=""
    if $H -emit-binary $O -out $T/$name.hbc $T/$name.js > $T/$name.hermesc.log 2>&1; then
      echo "$name: metro ok, hermesc ok, bytecode $(stat -c%s $T/$name.hbc) B" | tee -a $OUT
    else
      echo "$name: metro ok, hermesc FAILED: $(grep -m1 'error:' $T/$name.hermesc.log | sed 's|.*error: ||')" | tee -a $OUT
    fi
  else
    echo "$name: metro FAILED: $(grep -m1 -E 'Invalid call|Error' $T/$name.metro.log | sed 's|.*/node_modules/|node_modules/|')" | tee -a $OUT
  fi
}
b release-migrator-unpatched index.js false no
b release-migrator-patched index.js false yes
b dev-migrator-patched index.js true yes
b release-local-unpatched index.local.js false no
b release-local-no-import-meta-plugin index.local.js false no SPIKE_NO_IMPORT_META=1
b dev-local-no-import-meta-plugin index.local.js true no SPIKE_NO_IMPORT_META=1
b release-baseline index.baseline.js false no
b release-arbitrary index.arbitrary.js false yes
cp $T/package/dist/sql/Migrator.js $M && sh patch-migrator.sh node_modules
# Minified JS by package for the Effect entry.
npx react-native bundle --platform android --dev false --minify true --entry-file index.js \
  --bundle-output $T/min.js --sourcemap-output $T/min.js.map >/dev/null 2>&1
node -e '
const fs=require("fs"),[c,m]=[fs.readFileSync(process.argv[1],"utf8"),JSON.parse(fs.readFileSync(process.argv[2],"utf8"))];
const ls=[0];for(let i=0;i<c.length;i++)if(c[i]==="\n")ls.push(i+1);const off=s=>ls[s.offset.line]+s.offset.column,by={};
m.sections.forEach((s,i)=>{const e=i+1<m.sections.length?off(m.sections[i+1]):c.length,src=(s.map.sources||[])[0]||"?",mm=src.match(/node_modules\/((@[^/]+\/)?[^/]+)/),k=mm?mm[1]:"app";by[k]=(by[k]||0)+e-off(s)});
console.log("minified JS by package (index.js), KiB:");Object.entries(by).sort((a,b)=>b[1]-a[1]).slice(0,8).forEach(([k,v])=>console.log("  "+k+" "+(v/1024).toFixed(0)));
' $T/min.js $T/min.js.map | tee -a $OUT
rm -rf $T
