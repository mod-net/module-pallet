{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };

      fmtApp = pkgs.writeShellApplication {
        name = "fmt";
        text = ''
          set -euo pipefail
          cd ..
          uv run black mod_net_client modules/test_module
          uv run isort mod_net_client modules/test_module --profile black
          cargo fmt --all
        '';
      };

      lintApp = pkgs.writeShellApplication {
        name = "lint";
        text = ''
          set -euo pipefail
          cd ..
          uv run ruff check mod_net_client modules/test_module tests
          SKIP_WASM_BUILD=1 cargo clippy --all-targets --locked --workspace --quiet
          SKIP_WASM_BUILD=1 cargo clippy --all-targets --all-features --locked --workspace --quiet
        '';
      };

      typecheckApp = pkgs.writeShellApplication {
        name = "typecheck";
        text = ''
          set -euo pipefail
          cd ..
          uv run mypy mod_net_client modules/test_module --ignore-missing-imports
        '';
      };

      testApp = pkgs.writeShellApplication {
        name = "test";
        text = ''
          set -euo pipefail
          cd ..
          SKIP_WASM_BUILD=1 cargo test
          uv run pytest tests/ -v --cov=mod_net_client --cov-report=xml
        '';
      };

      dockerBuildApp = pkgs.writeShellApplication {
        name = "docker-build";
        text = ''
          set -euo pipefail
          cd ..
          docker build --target blockchain-node -t mod-net-node:ci .
        '';
      };

      dockerSmokeApp = pkgs.writeShellApplication {
        name = "docker-smoke";
        text = ''
          set -euo pipefail
          docker run --rm mod-net-node:ci --version
        '';
      };

      ciApp = pkgs.writeShellApplication {
        name = "ci";
        text = ''
          set -euo pipefail
          ${fmtApp}/bin/fmt
          ${lintApp}/bin/lint
          ${typecheckApp}/bin/typecheck
          ${testApp}/bin/test
          ${dockerBuildApp}/bin/docker-build
          ${dockerSmokeApp}/bin/docker-smoke
        '';
      };
    in
    {
      devShells.default = pkgs.mkShell {
        packages = with pkgs; [
          rustup
          cargo
          clang
          llvm
          libclang
          protobuf
          openssl
          pkg-config
          cmake
          git
          curl
          jq
          python311
          uv
          pre-commit
        ];

        LIBCLANG_PATH = "${pkgs.libclang.lib}/lib";
        OPENSSL_DIR = pkgs.openssl.dev;
        PIP_DISABLE_PIP_VERSION_CHECK = 1;

        shellHook = ''
          # Ensure rustup toolchain and wasm target are available
          if ! rustup target list --installed | grep -q wasm32-unknown-unknown; then
            rustup target add wasm32-unknown-unknown >/dev/null
          fi

          echo "Dev shell ready. Common commands:"
          echo "  nix run .#fmt          # format"
          echo "  nix run .#lint         # lint"
          echo "  nix run .#typecheck    # mypy"
          echo "  nix run .#test         # tests"
          echo "  nix run .#docker-build # build node image"
          echo "  nix run .#docker-smoke # run --version"
        '';
      };

      apps = {
        fmt = { type = "app"; program = "${fmtApp}/bin/fmt"; };
        lint = { type = "app"; program = "${lintApp}/bin/lint"; };
        typecheck = { type = "app"; program = "${typecheckApp}/bin/typecheck"; };
        test = { type = "app"; program = "${testApp}/bin/test"; };
        docker-build = { type = "app"; program = "${dockerBuildApp}/bin/docker-build"; };
        docker-smoke = { type = "app"; program = "${dockerSmokeApp}/bin/docker-smoke"; };
        ci = { type = "app"; program = "${ciApp}/bin/ci"; };
      };
    });
}
