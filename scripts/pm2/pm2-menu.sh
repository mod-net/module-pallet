#!/usr/bin/env bash
set -euo pipefail

# PM2 Menu for mod-net services
# Runs services via wrapper scripts and ensures Nix dev shell environment.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

has_nix() { command -v nix >/dev/null 2>&1; }
in_nix_shell() { [[ -n "${IN_NIX_SHELL:-}" ]]; }
has_curl() { command -v curl >/dev/null 2>&1; }
has_ss() { command -v ss >/dev/null 2>&1; }

# Load environment overrides from project .env if present
load_env() {
  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$PROJECT_ROOT/.env"
    set +a
  fi
  # Defaults if not provided by env
  IPFS_API_PORT="${IPFS_API_PORT:-5001}"
  IPFS_WORKER_PORT="${IPFS_WORKER_PORT:-8003}"
  BLOCKCHAIN_EXPLORER_PORT="${BLOCKCHAIN_EXPLORER_PORT:-8081}"
  # Chain ports: allow CHAIN_WS_PORT override, else fall back to BLOCKCHAIN_RPC_PORT (repo uses 9944) and default HTTP 9933
  CHAIN_WS_PORT="${CHAIN_WS_PORT:-${BLOCKCHAIN_RPC_PORT:-9944}}"
  CHAIN_HTTP_PORT="${CHAIN_HTTP_PORT:-9933}"
}

reexec_in_nix_if_needed() {
  if has_nix && ! in_nix_shell; then
    exec env NIX_CONFIG='experimental-features = nix-command flakes' \
      nix develop "$PROJECT_ROOT/env-setup" -c bash -lc "\"$0\" $*"
  fi
}

# -------- Health checks --------
wait_for_port() {
  local host="$1" port="$2" timeout="${3:-60}"
  local start ts
  start=$(date +%s)
  while true; do
    if { bash -lc "</dev/tcp/$host/$port"; } >/dev/null 2>&1; then
      return 0
    fi
    ts=$(($(date +%s) - start))
    if (( ts >= timeout )); then
      return 1
    fi
    sleep 1
  done
}

wait_for_http_2xx() {
  local url="$1" timeout="${2:-60}" extra_curl_flags=("--max-time" "2" "-s" -o /dev/null -w "%{http_code}")
  local start ts code
  start=$(date +%s)
  while true; do
    if has_curl; then
      code=$(curl "${extra_curl_flags[@]}" "$url" 2>/dev/null || true)
      if [[ "$code" =~ ^2[0-9]{2}$ ]]; then
        return 0
      fi
    fi
    ts=$(($(date +%s) - start))
    if (( ts >= timeout )); then
      return 1
    fi
    sleep 1
  done
}

wait_healthy() {
  local name="$1" timeout="${2:-60}"
  # Ensure env is loaded so ports are available
  load_env
  case "$name" in
    ipfs)
      # Prefer HTTP API; fallback to port only
      if has_curl; then
        if wait_for_http_2xx "http://127.0.0.1:${IPFS_API_PORT}/api/v0/version" "$timeout"; then
          echo "✅ ipfs healthy (API)"
          return 0
        fi
      fi
      if wait_for_port 127.0.0.1 "$IPFS_API_PORT" "$timeout"; then
        echo "✅ ipfs port ${IPFS_API_PORT} open"
        return 0
      fi
      echo "⚠️ ipfs not healthy within ${timeout}s"
      return 1
      ;;
    chain)
      # Probe HTTP RPC only
      if wait_for_port 127.0.0.1 "$CHAIN_HTTP_PORT" "$timeout"; then
        echo "✅ chain RPC ${CHAIN_HTTP_PORT} open"
        return 0
      fi
      echo "⚠️ chain not healthy within ${timeout}s"
      return 1
      ;;
    ipfs-worker)
      # Default worker port
      if has_curl; then
        if wait_for_http_2xx "http://127.0.0.1:${IPFS_WORKER_PORT}/health" "$timeout"; then
          echo "✅ ipfs-worker healthy (/health)"
          return 0
        fi
      fi
      if wait_for_port 127.0.0.1 "$IPFS_WORKER_PORT" "$timeout"; then
        echo "✅ ipfs-worker port ${IPFS_WORKER_PORT} open"
        return 0
      fi
      echo "⚠️ ipfs-worker not healthy within ${timeout}s"
      return 1
      ;;
    blockchain-explorer)
      if has_curl; then
        if wait_for_http_2xx "http://127.0.0.1:${BLOCKCHAIN_EXPLORER_PORT}/" "$timeout"; then
          echo "✅ explorer healthy (HTTP)"
          return 0
        fi
      fi
      if wait_for_port 127.0.0.1 "$BLOCKCHAIN_EXPLORER_PORT" "$timeout"; then
        echo "✅ explorer port ${BLOCKCHAIN_EXPLORER_PORT} open"
        return 0
      fi
      echo "⚠️ explorer not healthy within ${timeout}s"
      return 1
      ;;
    *)
      echo "ℹ️ No health check defined for $name"
      return 0
      ;;
  esac
}

# Per-service health timeouts
health_timeout() {
  case "$1" in
    ipfs) echo 45 ;;
    chain) echo 30 ;;
    ipfs-worker) echo 20 ;;
    blockchain-explorer) echo 10 ;;
    *) echo 60 ;;
  esac
}

ensure_pm2() {
  if ! command -v pm2 >/dev/null 2>&1; then
    echo "❌ pm2 is not installed in this environment." >&2
    echo "   Inside Nix shell, pm2 should be available. Try: nix develop ./env-setup" >&2
    exit 1
  fi
}

# Map service -> script
service_script() {
  case "$1" in
    ipfs) echo "$PROJECT_ROOT/scripts/pm2/run-ipfs.sh" ;;
    chain) echo "$PROJECT_ROOT/scripts/pm2/run-chain.sh" ;;
    ipfs-worker) echo "$PROJECT_ROOT/scripts/pm2/run-ipfs-worker.sh" ;;
    blockchain-explorer) echo "$PROJECT_ROOT/scripts/pm2/run-explorer.sh" ;;
    *) return 1 ;;
  esac
}

start_service() {
  local name="$1"
  local script
  script=$(service_script "$name") || { echo "❌ Unknown service: $name"; return 1; }
  # Start script directly; rely on shebang and our internal exec -a to pin titles
  pm2 start "$script" --name "$name" --interpreter none
  local t
  t=$(health_timeout "$name")
  echo "⏳ Waiting up to ${t}s for $name to become healthy..."
  wait_healthy "$name" "$t" || true
}

restart_service() {
  local name="$1"
  pm2 restart "$name"
}

stop_service() {
  local name="$1"
  pm2 stop "$name"
}

delete_service() {
  local name="$1"
  pm2 delete "$name"
}

logs_service() {
  local name="$1"
  pm2 logs "$name"
}

tail_service() {
  local name="$1"; local lines="${2:-120}"
  tail -n "$lines" "$HOME/.pm2/logs/${name}-error.log" || true
  echo "---"
  tail -n "$lines" "$HOME/.pm2/logs/${name}-out.log" || true
}

status_all() {
  pm2 list
}

save_pm2() {
  pm2 save
}

flush_pm2() {
  pm2 flush
}

delete_all() {
  pm2 delete all || true
}

start_all() {
  for s in ipfs chain ipfs-worker blockchain-explorer; do
    start_service "$s" || true
  done
}

stop_all() {
  for s in ipfs chain ipfs-worker blockchain-explorer; do
    stop_service "$s" || true
  done
}

print_menu() {
  cat <<EOF
PM2 Service Menu (mod-net)
--------------------------
1) Start IPFS
2) Start Chain
3) Start IPFS Worker
4) Start Blockchain Explorer
5) Start ALL
6) Restart a service
7) Stop a service
8) Delete a service
9) Delete ALL
10) Status (pm2 list)
11) Logs (interactive pm2 logs)
12) Tail recent logs (non-interactive)
13) Flush PM2 logs
14) Save PM2 state
q) Quit
EOF
}

prompt_service_name() {
  local s
  echo "Enter service name [ipfs|chain|ipfs-worker|blockchain-explorer]: "
  read -r s
  echo "$s"
}

# Entry
reexec_in_nix_if_needed "$@"
ensure_pm2

while true; do
  print_menu
  printf "> "
  read -r choice || break
  case "$choice" in
    1) start_service ipfs ;;
    2) start_service chain ;;
    3) start_service ipfs-worker ;;
    4) start_service blockchain-explorer ;;
    5) start_all ;;
    6) svc=$(prompt_service_name); restart_service "$svc" ;;
    7) svc=$(prompt_service_name); stop_service "$svc" ;;
    8) svc=$(prompt_service_name); delete_service "$svc" ;;
    9) delete_all ;;
    10) status_all ;;
    11) svc=$(prompt_service_name); logs_service "$svc" ;;
    12) svc=$(prompt_service_name); echo -n "Lines [default 120]: "; read -r ln || ln=120; ln=${ln:-120}; tail_service "$svc" "$ln" ;;
    13) flush_pm2 ;;
    14) save_pm2 ;;
    q|Q) exit 0 ;;
    *) echo "Invalid choice" ;;
  esac
  echo
done
