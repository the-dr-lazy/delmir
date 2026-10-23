# PROTOTYPE for #50, throwaway: the #19 training stack (nixpkgs torchWithRocm) plus what #42's spike imports.
{ pkgs, ... }:
{
  languages.python = {
    enable = true;
    package = pkgs.python313.withPackages (ps: [ ps.torchWithRocm ps.numpy ps.pandas ps.scipy ps.scikit-learn ]);
  };
  packages = [ pkgs.rocmPackages.rocminfo ];
  # KFD node 1 is the RX 6600 XT (gfx1032), node 2 the Raphael iGPU (gfx1036).
  env.HSA_OVERRIDE_GFX_VERSION_1 = "10.3.0";
  env.ROCR_VISIBLE_DEVICES = "0";
}
