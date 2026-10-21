#!/bin/sh
# SPIKE (delmir#43), workaround A until effect 4.1: replace the non-literal `import()` in
# effect 4.0.5's Migrator.fromFileSystem (which Metro rejects at build time) with Effect.die.
# Usage: sh patch-migrator.sh <node_modules dir>. Run by package.nix in the Nix build.
set -eu
f="$1/effect/dist/sql/Migrator.js"
grep -q 'Effect.promise(() => import(__rewriteRelativeImportExtension(' "$f"
sed -i 's|Effect.promise(() => import(__rewriteRelativeImportExtension(|Effect.die(new Error("Migrator.fromFileSystem is unsupported on React Native: " + (|' "$f"
! grep -q 'import(' "$f"
