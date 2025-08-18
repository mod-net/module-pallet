#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

has_nix() { command -v nix >/dev/null 2>&1; }
in_nix_shell() { [[ -n "${IN_NIX_SHELL:-}" ]]; }

# Load project .env for port configuration if present
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/.env"
  set +a
fi

# Defaults
IPFS_API_PORT="${IPFS_API_PORT:-5001}"
IPFS_GATEWAY_PORT="${IPFS_GATEWAY_PORT:-8080}"
IPFS_SWARM_PORT="${IPFS_SWARM_PORT:-4001}"

# Helper to run a command either inside nix dev shell or not
run_nix() {
  if has_nix && ! in_nix_shell; then
    env NIX_CONFIG='experimental-features = nix-command flakes' \
      nix develop "$PROJECT_ROOT/env-setup" -c "$@"
  else
    "$@"
  fi
}

# Use project-local IPFS repo by default to avoid conflicts with any system daemon
export IPFS_PATH="${IPFS_PATH:-$PROJECT_ROOT/.ipfs}"
mkdir -p "$IPFS_PATH"

# Serialize startup to avoid multiple PM2 starts racing on repo.lock
LAUNCH_LOCK="$IPFS_PATH/launcher.lock"
exec 9>"$LAUNCH_LOCK"
if ! flock -n 9; then
  echo "[run-ipfs] Another IPFS start is in progress; waiting for daemon to become ready..."
  # Wait up to 20s for API to respond
  for i in {1..20}; do
    if run_nix ipfs --api /ip4/127.0.0.1/tcp/${IPFS_API_PORT} id >/dev/null 2>&1; then
      echo "[run-ipfs] Existing daemon is up; exiting to avoid duplicate start."
      exit 0
    fi
    sleep 1
  done
  # API did not come up yet; try to acquire the lock with timeout
  if ! flock -w 20 9; then
    echo "[run-ipfs] Could not acquire launcher lock; exiting to avoid race."
    exit 0
  fi
fi

# Initialize repo if missing and configure API/Gateway
if [[ ! -f "$IPFS_PATH/config" ]]; then
  echo "[run-ipfs] Initializing IPFS repo at $IPFS_PATH"
  run_nix ipfs init
  run_nix ipfs config Addresses.API "/ip4/0.0.0.0/tcp/${IPFS_API_PORT}"
  run_nix ipfs config Addresses.Gateway "/ip4/0.0.0.0/tcp/${IPFS_GATEWAY_PORT}"
  # Only set swarm if provided (array value)
  if [[ -n "${IPFS_SWARM_PORT}" ]]; then
    run_nix ipfs config --json Addresses.Swarm "[\"/ip4/0.0.0.0/tcp/${IPFS_SWARM_PORT}\", \"/ip6/::/tcp/${IPFS_SWARM_PORT}\"]"
  fi
  run_nix ipfs config --json API.HTTPHeaders.Access-Control-Allow-Origin '["*"]'
  run_nix ipfs config --json API.HTTPHeaders.Access-Control-Allow-Methods '["GET", "POST"]'
fi

# Ensure existing repo respects env-configured ports
if [[ -f "$IPFS_PATH/config" ]]; then
  run_nix ipfs config Addresses.API "/ip4/0.0.0.0/tcp/${IPFS_API_PORT}" || true
  run_nix ipfs config Addresses.Gateway "/ip4/0.0.0.0/tcp/${IPFS_GATEWAY_PORT}" || true
  if [[ -n "${IPFS_SWARM_PORT}" ]]; then
    run_nix ipfs config --json Addresses.Swarm "[\"/ip4/0.0.0.0/tcp/${IPFS_SWARM_PORT}\", \"/ip6/::/tcp/${IPFS_SWARM_PORT}\"]" || true
  fi
fi

# Try graceful shutdown if a daemon is already up
if run_nix ipfs --api /ip4/127.0.0.1/tcp/${IPFS_API_PORT} id >/dev/null 2>&1; then
  run_nix ipfs --api /ip4/127.0.0.1/tcp/${IPFS_API_PORT} shutdown || true
fi

# Wait for repo.lock to clear (max ~15s)
LOCK_FILE="$IPFS_PATH/repo.lock"
for i in {1..30}; do
  if [[ ! -e "$LOCK_FILE" ]]; then
    break
  fi
  sleep 0.5
done

# If lock persists, check if any ipfs process holds it; if not, treat as stale and remove
if [[ -e "$LOCK_FILE" ]]; then
  # API not responding means no healthy daemon
  if ! run_nix ipfs --api /ip4/127.0.0.1/tcp/${IPFS_API_PORT} id >/dev/null 2>&1; then
    holder=""
    if command -v lsof >/dev/null 2>&1; then
      holder=$(lsof -t -- "$LOCK_FILE" 2>/dev/null || true)
    elif command -v fuser >/dev/null 2>&1; then
      holder=$(fuser -m "$LOCK_FILE" 2>/dev/null || true)
    fi
    if [[ -z "$holder" ]]; then
      echo "[run-ipfs] Detected stale IPFS repo.lock; removing"
      rm -f -- "$LOCK_FILE"
    else
      echo "[run-ipfs] repo.lock held by PID(s): $holder; attempting graceful termination"
      # Try SIGTERM then SIGKILL if needed
      kill $holder >/dev/null 2>&1 || true
      for i in {1..10}; do
        sleep 0.5
        if ! kill -0 $holder >/dev/null 2>&1; then
          break
        fi
      done
      if kill -0 $holder >/dev/null 2>&1; then
        echo "[run-ipfs] Forcing kill of PID(s): $holder"
        kill -9 $holder >/dev/null 2>&1 || true
        sleep 1
      fi
      rm -f -- "$LOCK_FILE" || true
    fi
  fi
fi

# Start daemon (exec so PM2 tracks the ipfs process)
if has_nix && ! in_nix_shell; then
  exec -a ipfs env NIX_CONFIG='experimental-features = nix-command flakes' \
    nix develop "$PROJECT_ROOT/env-setup" -c ipfs daemon
else
  exec -a ipfs ipfs daemon
fi
