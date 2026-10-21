# THROWAWAY SPIKE for the-dr-lazy/delmir#43. Never merge.
# Build:            nix build ./spike-effect-rn#apk -L          (from the repo root)
# Regenerate lock:  nix build ./spike-effect-rn#apk.mitmCache.updateScript -o us && USE_BWRAP=0 ./us
{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/02c087f3fe673c9e317f206a627cb6b910336dbe";

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config = {
          android_sdk.accept_license = true;
          allowUnfree = true;
        };
      };
      apk = args: pkgs.callPackage ./package.nix args;
    in
    {
      packages.${system} = {
        # Effect + encrypted registry, Migrator.fromRecord with the Nix-patched Migrator.js, op-sqlite 17.2.0.
        apk = apk { };
        # Same, op-sqlite 18.2.5.
        apk-op18 = apk { opSqlite18 = true; };
        # Local migration runner, effect left unpatched (proves the runner needs no patch).
        apk-local = apk {
          entry = "index.local.js";
          patchMigrator = false;
        };
        # No Effect, no registry: size and cold-start baseline.
        apk-baseline = apk { entry = "index.baseline.js"; };
        # Debug build for the Metro + Hermes-from-source run.
        apk-debug = apk { buildType = "debug"; };
        default = self.packages.${system}.apk;
      };
    };
}
