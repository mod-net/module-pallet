#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

has_nix() { command -v nix >/dev/null 2>&1; }
in_nix_shell() { [[ -n "${IN_NIX_SHELL:-}" ]]; }

# Load .env for port config
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/.env"
  set +a
fi

# Defaults if not provided by env (RPC only)
CHAIN_HTTP_PORT="${CHAIN_HTTP_PORT:-9933}"

# Ensure wasm32 target and build runtime first so the embedded wasm is available
build_node_with_runtime() {
  cd "$PROJECT_ROOT"
  # Ensure wasm toolchain target is available
  if command -v rustup >/dev/null 2>&1; then
    if ! rustup target list --installed | grep -q '^wasm32-unknown-unknown$'; then
      rustup target add wasm32-unknown-unknown
    fi
  fi
  # Clean to avoid stale OUT_DIR producing WASM_BINARY=None
  cargo clean || true
  # Build runtime (triggers wasm builder) then node
  cargo build --release -p mod-net-runtime
  # Sanity check: ensure embedded WASM is present
  if ! grep -R --fixed-strings "WASM_BINARY: Option<&[u8]> = Some(" target/release/build/mod-net-runtime-*/out/wasm_binary.rs >/dev/null 2>&1; then
    echo "[chain] ERROR: Runtime WASM not embedded (WASM_BINARY=None). Dumping candidates:" >&2
    grep -R --line-number "WASM_BINARY" target/release/build/mod-net-runtime-*/out/wasm_binary.rs 2>/dev/null >&2 || true
    echo "[chain] Retrying a fresh build of runtime..." >&2
    cargo clean || true
    cargo build --release -p mod-net-runtime
    if ! grep -R --fixed-strings "WASM_BINARY: Option<&[u8]> = Some(" target/release/build/mod-net-runtime-*/out/wasm_binary.rs >/dev/null 2>&1; then
      echo "[chain] WARN: Still no embedded runtime WASM. Node will attempt to load from wbuild files." >&2
    fi
  fi
  cargo build --release -p mod-net-node
}

# Always rebuild to ensure runtime wasm is generated and embedded
echo "[chain] Building runtime and node (release)..."
if has_nix && ! in_nix_shell; then
  env NIX_CONFIG='experimental-features = nix-command flakes' \
    nix develop "$PROJECT_ROOT/env-setup" -c bash -lc "$(typeset -f build_node_with_runtime); build_node_with_runtime"
else
  build_node_with_runtime
fi

cd "$PROJECT_ROOT"
if has_nix && ! in_nix_shell; then
  exec -a chain env NIX_CONFIG='experimental-features = nix-command flakes' \
    nix develop "$PROJECT_ROOT/env-setup" -c "$PROJECT_ROOT/target/release/mod-net-node" --dev --rpc-external --rpc-cors all --rpc-port "$CHAIN_HTTP_PORT"
else
  exec -a chain "$PROJECT_ROOT/target/release/mod-net-node" --dev --rpc-external --rpc-cors all --rpc-port "$CHAIN_HTTP_PORT"
fi
