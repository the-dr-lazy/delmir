# THROWAWAY SPIKE for the-dr-lazy/delmir#32. Never merge.
# Build:            nix build ./spike-nix-apk#apk -L          (from the repo root)
# Regenerate lock:  nix build ./spike-nix-apk#apk.mitmCache.updateScript && ./result
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
    in
    {
      packages.${system} = {
        apk = pkgs.callPackage ./package.nix { };
        default = self.packages.${system}.apk;
      };
      checks.${system}.apk = self.packages.${system}.apk;
    };
}
