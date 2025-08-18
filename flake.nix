{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
      pythonTest = pkgs.python311.withPackages (ps: [ ps.pytest ps.pytest-cov ps.pytest-asyncio ps.pip ]);

      # Build the Rust node from the repository root
      nodeSrc = pkgs.lib.cleanSource ./.;
      nodePkg = pkgs.rustPlatform.buildRustPackage {
        pname = "mod-net-node";
        version = "0.1.0";
        src = nodeSrc;
        # Use the lockfile via the cleaned repo source to keep evaluation pure
        cargoLock.lockFile = nodeSrc + "/Cargo.lock";
        # Build only the node crate within the workspace
        buildAndTestSubdir = "node";
        nativeBuildInputs = [ pkgs.pkg-config pkgs.protobuf pkgs.makeWrapper ];
        buildInputs = [ pkgs.openssl pkgs.udev pkgs.clang pkgs.llvm ];
        RUSTFLAGS = "-C link-arg=-fuse-ld=lld";
        MODNET_SKIP_GIT = "1";
        doCheck = false;
      };

      # Nix-native Docker image with the compiled node binary
      dockerNodeImage = pkgs.dockerTools.buildLayeredImage {
        name = "mod-net-node";
        tag = "nix";
        contents = [ nodePkg pkgs.bash pkgs.coreutils pkgs.glibc ];
        config = {
          Entrypoint = [ "/bin/mod-net-node" ];
          ExposedPorts = {
            "30333/tcp" = {};
            "9933/tcp" = {};
            "9615/tcp" = {};
          };
        };
      };

      fmtApp = pkgs.writeShellApplication {
        name = "fmt";
        runtimeInputs = [ pkgs.black pkgs.isort pkgs.rustup pkgs.fd ];
        text = ''
          set -euo pipefail
          ROOT="''${REPO_ROOT:-$PWD}"
          mapfile -t PY_FILES < <(fd -t f -e py . "$ROOT/mod_net_client" "$ROOT/modules/test_module")
          if [ "''${#PY_FILES[@]}" -gt 0 ]; then
            black --config "$ROOT/pyproject.toml" "''${PY_FILES[@]}"
            isort --settings-path "$ROOT/pyproject.toml" --profile black "''${PY_FILES[@]}"
          fi
          rustup show >/dev/null 2>&1 || true
          rustup component add rustfmt >/dev/null 2>&1 || true
          cargo fmt --all
        '';
      };

      lintApp = pkgs.writeShellApplication {
        name = "lint";
        runtimeInputs = [ pkgs.ruff pkgs.rustup ];
        text = ''
          set -euo pipefail
          ROOT="''${REPO_ROOT:-$PWD}"
          ruff check --config "$ROOT/pyproject.toml" "$ROOT/mod_net_client" "$ROOT/modules/test_module" "$ROOT/tests"
          rustup show >/dev/null 2>&1 || true
          rustup component add clippy >/dev/null 2>&1 || true
          rustup target add wasm32-unknown-unknown >/dev/null 2>&1 || true
          SKIP_WASM_BUILD=1 cargo clippy --manifest-path "$ROOT/pallets/module-registry/Cargo.toml" --all-targets --no-deps --quiet
          SKIP_WASM_BUILD=1 cargo clippy --manifest-path "$ROOT/pallets/template/Cargo.toml" --all-targets --no-deps --quiet
        '';
      };

      typecheckApp = pkgs.writeShellApplication {
        name = "typecheck";
        runtimeInputs = [ pkgs.python311Packages.mypy pkgs.fd ];
        text = ''
          set -euo pipefail
          ROOT="''${REPO_ROOT:-$PWD}"
          mapfile -t PY_FILES < <(fd -t f -e py . "$ROOT/mod_net_client" "$ROOT/modules/test_module")
          if [ "''${#PY_FILES[@]}" -gt 0 ]; then
            mypy --config-file "$ROOT/pyproject.toml" --ignore-missing-imports "''${PY_FILES[@]}"
          fi
        '';
      };

      testApp = pkgs.writeShellApplication {
        name = "test";
        runtimeInputs = [ pkgs.rustup pythonTest ];
        text = ''
          set -euo pipefail
          ROOT="''${REPO_ROOT:-$PWD}"
          rustup show >/dev/null 2>&1 || true
          rustup target add wasm32-unknown-unknown >/dev/null 2>&1 || true
          SKIP_WASM_BUILD=1 cargo test
          export PYTHONPATH="$ROOT:${PYTHONPATH:-}"
          VENV_DIR="$(mktemp -d)/test-venv"
          python -m venv "$VENV_DIR"
          "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
          "$VENV_DIR/bin/pip" install -q pytest pytest-cov pytest-asyncio >/dev/null 2>&1 || true
          "$VENV_DIR/bin/pytest" --cov=mod_net_client --cov-report=xml "$ROOT/tests/" -v
        '';
      };

      dockerBuildApp = pkgs.writeShellApplication {
        name = "docker-build";
        text = ''
          set -euo pipefail
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

      dockerNodeBuildApp = pkgs.writeShellApplication {
        name = "docker-node";
        runtimeInputs = [ pkgs.nix pkgs.util-linux ];
        text = ''
          set -euo pipefail
          OUT="$(nix build --print-out-paths .#dockerNodeImage)"
          echo "Built image tarball: $OUT"
        '';
      };

      dockerNodeLoadApp = pkgs.writeShellApplication {
        name = "docker-load-node";
        runtimeInputs = [ pkgs.nix pkgs.docker ];
        text = ''
          set -euo pipefail
          OUT="$(nix build --print-out-paths .#dockerNodeImage)"
          echo "Loading image from: $OUT"
          docker load -i "$OUT"
          docker images | grep mod-net-node || true
        '';
      };

    in {
      packages = {
        mod-net-node = nodePkg;
        dockerNodeImage = dockerNodeImage;
      };

      devShells.default = pkgs.mkShell {
        packages = with pkgs; [
          rustup cargo clang llvm libclang protobuf openssl pkg-config cmake git curl jq python311 pre-commit
          fmtApp lintApp typecheckApp testApp dockerBuildApp dockerSmokeApp ciApp dockerNodeBuildApp dockerNodeLoadApp
        ];
        LIBCLANG_PATH = "${pkgs.libclang.lib}/lib";
        OPENSSL_DIR = pkgs.openssl.dev;
        PIP_DISABLE_PIP_VERSION_CHECK = 1;
        shellHook = ''
          if type bash >/dev/null 2>&1; then shopt -s expand_aliases || true; fi
          if ! rustup target list --installed | grep -q wasm32-unknown-unknown; then
            rustup target add wasm32-unknown-unknown >/dev/null
          fi
          export NIX_CONFIG="experimental-features = nix-command flakes"
          alias nix-fmt='REPO_ROOT="$PWD" nix run .#fmt'
          alias nix-lint='REPO_ROOT="$PWD" nix run .#lint'
          alias nix-typecheck='REPO_ROOT="$PWD" nix run .#typecheck'
          alias nix-test='REPO_ROOT="$PWD" nix run .#test'
          alias nix-docker='REPO_ROOT="$PWD" nix run .#docker-node'
          alias nix-docker-load='REPO_ROOT="$PWD" nix run .#docker-load-node'
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
        docker-node = { type = "app"; program = "${dockerNodeBuildApp}/bin/docker-node"; };
        docker-load-node = { type = "app"; program = "${dockerNodeLoadApp}/bin/docker-load-node"; };
      };
    }
  );
}
