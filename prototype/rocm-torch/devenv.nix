# PROTOTYPE for #41, throwaway: does nixpkgs' torchWithRocm train on the RX 6600 XT?
{ pkgs, ... }:
{
  languages.python = {
    enable = true;
    package = pkgs.python313.withPackages (ps: [ ps.torchWithRocm ps.numpy ]);
  };
  packages = [ pkgs.rocmPackages.rocminfo ];
  # KFD node 1 is the RX 6600 XT (gfx1032), node 2 the Raphael iGPU (gfx1036).
  # Report only the dGPU as gfx1030, and hide the iGPU from ROCr.
  env.HSA_OVERRIDE_GFX_VERSION_1 = "10.3.0";
  env.ROCR_VISIBLE_DEVICES = "0";
}
