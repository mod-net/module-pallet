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
BLOCKCHAIN_EXPLORER_PORT="${BLOCKCHAIN_EXPLORER_PORT:-8081}"

cd "$PROJECT_ROOT/webui"
if has_nix && ! in_nix_shell; then
  exec -a blockchain-explorer env NIX_CONFIG='experimental-features = nix-command flakes' \
    nix develop "$PROJECT_ROOT/env-setup" -c python3 -m http.server "$BLOCKCHAIN_EXPLORER_PORT"
else
  exec -a blockchain-explorer python3 -m http.server "$BLOCKCHAIN_EXPLORER_PORT"
fi
