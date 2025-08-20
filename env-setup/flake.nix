{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    rust-overlay.url = "github:oxalica/rust-overlay";
    rust-overlay.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, rust-overlay, ... }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs {
        inherit system;
        overlays = [ rust-overlay.overlays.default ];
      };
      # Pin Rust toolchain so Nix builds use a Cargo new enough for lockfile v4
      # Include WASM targets directly in the toolchain (Nix builds do not use rustup)
      rustToolchain = (pkgs.rust-bin.stable."1.89.0".default.override {
        targets = [ "wasm32-unknown-unknown" "wasm32v1-none" ];
      });
      rustPlatform = pkgs.makeRustPlatform {
        rustc = rustToolchain;
        cargo = rustToolchain;
      };
      pythonTest = pkgs.python311.withPackages (ps: [ ps.pytest ps.pytest-cov ps.pytest-asyncio ps.pip ]);

      # Build the Rust node from the repository root (flake lives in env-setup/)
      nodeSrc = pkgs.lib.cleanSource ../.;
      nodePkg = rustPlatform.buildRustPackage {
        pname = "mod-net-node";
        version = "0.1.0";
        src = nodeSrc;
        # Use the lockfile from the cleaned repo source to keep evaluation pure
        cargoLock.lockFile = nodeSrc + "/Cargo.lock";
        # Build only the node crate within the workspace
        buildAndTestSubdir = "node";
        nativeBuildInputs = [ pkgs.pkg-config pkgs.protobuf pkgs.makeWrapper pkgs.clang pkgs.llvmPackages.lld ];
        buildInputs = [ pkgs.openssl pkgs.udev pkgs.llvm pkgs.libclang ];
        # Use clang as the linker and lld as the link backend
        CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER = "${pkgs.clang}/bin/clang";
        # Substrate builds can allocate a lot; ensure reproducible env
        RUSTFLAGS = "-C link-arg=-fuse-ld=lld";
        # Ensure bindgen can locate libclang shared library
        LIBCLANG_PATH = "${pkgs.libclang.lib}/lib";
        # Avoid git-based rebuild checks during Nix build
        MODNET_SKIP_GIT = "1";
        # Tests are heavy and unnecessary for package build here
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
        runtimeInputs = [
          pkgs.black
          pkgs.isort
          pkgs.rustup
          pkgs.fd
        ];
        text = ''
          set -euo pipefail
          export PROTOC="${pkgs.protobuf}/bin/protoc"
          ROOT="''${REPO_ROOT:-$PWD}"
          case "$ROOT" in
            /nix/store/*)
              echo "Error: running inside Nix store. Please pass REPO_ROOT or use provided aliases." >&2
              exit 1;;
          esac
          # Discover Python files reliably and pass the list to black/isort
          mapfile -t PY_FILES < <(fd -t f -e py . "$ROOT/mod_net_client" "$ROOT/modules/test_module")
          if [ "''${#PY_FILES[@]}" -eq 0 ]; then
            echo "No Python files found under mod_net_client or modules/test_module. Nothing to format."; exit 0
          fi
          black --config "$ROOT/pyproject.toml" "''${PY_FILES[@]}"
          isort --settings-path "$ROOT/pyproject.toml" --profile black "''${PY_FILES[@]}"
          rustup show >/dev/null 2>&1 || true
          rustup component add rustfmt >/dev/null 2>&1 || true
          cargo fmt --all
        '';
      };

      lintApp = pkgs.writeShellApplication {
        name = "lint";
        runtimeInputs = [ pkgs.ruff pkgs.rustup pkgs.protobuf pkgs.pkg-config ];
        text = ''
          set -euo pipefail
          export PROTOC="${pkgs.protobuf}/bin/protoc"
          ROOT="''${REPO_ROOT:-$PWD}"
          case "$ROOT" in
            /nix/store/*)
              echo "Error: running inside Nix store. Please pass REPO_ROOT or use provided aliases." >&2
              exit 1;;
          esac
          ruff check --config "$ROOT/pyproject.toml" "$ROOT/mod_net_client" "$ROOT/modules/test_module" "$ROOT/tests"
          rustup show >/dev/null 2>&1 || true
          rustup component add clippy >/dev/null 2>&1 || true
          rustup target add wasm32v1-none >/dev/null 2>&1 || true
          rustup target add wasm32-unknown-unknown >/dev/null 2>&1 || true
          # Lint only first-party pallets to avoid compiling unrelated external crates
          SKIP_WASM_BUILD=1 cargo clippy --manifest-path "$ROOT/pallets/module-registry/Cargo.toml" --all-targets --no-deps --quiet
          SKIP_WASM_BUILD=1 cargo clippy --manifest-path "$ROOT/pallets/template/Cargo.toml" --all-targets --no-deps --quiet
        '';
      };

      typecheckApp = pkgs.writeShellApplication {
        name = "typecheck";
        runtimeInputs = [
          pkgs.python311Packages.mypy
          pkgs.fd
        ];
        text = ''
          set -euo pipefail
          ROOT="''${REPO_ROOT:-$PWD}"
          case "$ROOT" in
            /nix/store/*)
              echo "Error: running inside Nix store. Please pass REPO_ROOT or use provided aliases." >&2
              exit 1;;
          esac
          # Find Python files explicitly to avoid mypy complaining about empty top-level dirs
          mapfile -t PY_FILES < <(fd -t f -e py . "$ROOT/mod_net_client" "$ROOT/modules/test_module")
          if [ "''${#PY_FILES[@]}" -eq 0 ]; then
            echo "No Python files found under mod_net_client or modules/test_module. Nothing to typecheck."; exit 0
          fi
          mypy --config-file "$ROOT/pyproject.toml" --ignore-missing-imports "''${PY_FILES[@]}"
        '';
      };

      testApp = pkgs.writeShellApplication {
        name = "test";
        runtimeInputs = [ pkgs.rustup pythonTest pkgs.protobuf pkgs.pkg-config ];
        text = ''
          set -euo pipefail
          export PROTOC="${pkgs.protobuf}/bin/protoc"
          ROOT="''${REPO_ROOT:-$PWD}"
          case "$ROOT" in
            /nix/store/*)
              echo "Error: running inside Nix store. Please pass REPO_ROOT or use provided aliases." >&2
              exit 1;;
          esac
          rustup show >/dev/null 2>&1 || true
          rustup target add wasm32v1-none >/dev/null 2>&1 || true
          rustup target add wasm32-unknown-unknown >/dev/null 2>&1 || true
          SKIP_WASM_BUILD=1 cargo test
          export PYTHONPATH="$ROOT:${PYTHONPATH:-}"
          # Ensure required Python runtime deps via an ephemeral virtualenv (no --user in Nix env)
          VENV_DIR="$(mktemp -d)/test-venv"
          python -m venv "$VENV_DIR"
          "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
          # Ensure pytest and related plugins are present inside the venv
          "$VENV_DIR/bin/pip" install -q pytest pytest-cov pytest-asyncio >/dev/null 2>&1 || true
          "$VENV_DIR/bin/python" - <<'PY'
import importlib, subprocess, sys
missing = []
for pkg in ("substrateinterface", "ipfshttpclient"):
    try:
        importlib.import_module(pkg)
    except Exception:
        missing.append(pkg)
if missing:
    print(f"Installing test-only Python deps into ephemeral venv: {missing}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
PY
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
          if command -v docker >/dev/null 2>&1; then
            ${dockerBuildApp}/bin/docker-build
            ${dockerSmokeApp}/bin/docker-smoke
          else
            echo "Docker not found; skipping Docker image build/smoke."
          fi
        '';
      };

      # Helper: build Nix-native Docker image (tarball in result/)
      dockerNodeBuildApp = pkgs.writeShellApplication {
        name = "docker-node";
        runtimeInputs = [ pkgs.nix pkgs.util-linux ];
        text = ''
          set -euo pipefail
          # Build the Docker image tarball from this flake explicitly
          OUT="$(nix build --print-out-paths path:./env-setup#dockerNodeImage)"
          echo "Built image tarball: $OUT"
        '';
      };

      # Helper: load the built image into local Docker daemon
      dockerNodeLoadApp = pkgs.writeShellApplication {
        name = "docker-load-node";
        runtimeInputs = [ pkgs.nix pkgs.docker ];
        text = ''
          set -euo pipefail
          OUT="$(nix build --print-out-paths path:./env-setup#dockerNodeImage)"
          echo "Loading image from: $OUT"
          docker load -i "$OUT"
          docker images | grep mod-net-node || true
        '';
      };
    in
    {
      packages = {
        mod-net-node = nodePkg;
        dockerNodeImage = dockerNodeImage;
      };

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
          pre-commit
          # Make helper apps available directly on PATH (not only via nix run)
          fmtApp
          lintApp
          typecheckApp
          testApp
          dockerBuildApp
          dockerSmokeApp
          ciApp
          dockerNodeBuildApp
          dockerNodeLoadApp
          # Provide a dedicated nix-test wrapper so `nix develop -c nix-test` works
          (pkgs.writeShellApplication {
            name = "nix-test";
            runtimeInputs = [ ];
            text = ''
              set -euo pipefail
              REPO_ROOT="''${REPO_ROOT:-$PWD}" exec ${testApp}/bin/test
            '';
          })
          # Provide a dedicated nix-typecheck wrapper so `nix develop -c nix-typecheck` works
          (pkgs.writeShellApplication {
            name = "nix-typecheck";
            runtimeInputs = [ ];
            text = ''
              set -euo pipefail
              REPO_ROOT="''${REPO_ROOT:-$PWD}" exec ${typecheckApp}/bin/typecheck
            '';
          })
        ];

        LIBCLANG_PATH = "${pkgs.libclang.lib}/lib";
        OPENSSL_DIR = pkgs.openssl.dev;
        PIP_DISABLE_PIP_VERSION_CHECK = 1;

        shellHook = ''
          # Allow alias expansion in non-interactive shells (for `nix develop -c <alias>`)
          if type bash >/dev/null 2>&1; then
            shopt -s expand_aliases || true
          fi
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

          # Handy aliases inside this dev shell (include flakes feature)
          export NIX_CONFIG="experimental-features = nix-command flakes"
          alias nix-fmt='REPO_ROOT="$PWD" nix run ./env-setup#fmt'
          alias nix-lint='REPO_ROOT="$PWD" nix run ./env-setup#lint'
          alias nix-typecheck='REPO_ROOT="$PWD" nix run ./env-setup#typecheck'
          alias nix-test='REPO_ROOT="$PWD" nix run ./env-setup#test'
          alias nix-ci='REPO_ROOT="$PWD" nix run ./env-setup#ci'
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
    });
}
