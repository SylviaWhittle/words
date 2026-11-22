{ pkgs, ... }:

{
  # 1. Enable Python + uv integration
  languages.python = {
    enable = true;
    version = "3.13"; # Or "3.12"

    venv = {
      enable = true;
      # Installs your current directory in editable mode (-e .)
      requirements = ''
        -e .
      '';
    };

    uv = {
      enable = true;
      sync.enable = true; # Automatically runs `uv sync` when entering the environment
    };
  };

  # 2. System C-libraries for native C-extension pip packages
  packages = with pkgs; [
    stdenv.cc.cc.lib
    zlib
    openssl
    glib

    ruff
    ty
  ];

  # 3. Dynamic linker fix for pre-compiled binaries/C extensions on NixOS
  env.LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib";

  enterShell = ''
    echo "🐍 Python package development environment active!"
    echo "Installed package:"
    python -c "import my_package; print(my_package)" 2>/dev/null || echo "Package ready for installation."
  '';

 # expose scritps in the shell
 scripts.check.exec = ''
   ruff check .
   ruff format --check .
   ty check
  '';

}
