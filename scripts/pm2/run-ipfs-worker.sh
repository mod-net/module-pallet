#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$PROJECT_ROOT/scripts"

has_nix() { command -v nix >/dev/null 2>&1; }
in_nix_shell() { [[ -n "${IN_NIX_SHELL:-}" ]]; }

# Load .env and defaults
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/.env"
  set +a
fi
IPFS_WORKER_PORT="${IPFS_WORKER_PORT:-8003}"
export PORT="$IPFS_WORKER_PORT"
# Import module path and pip spec are configurable to handle repo layout changes
IPFS_SERVICE_MODULE="${IPFS_SERVICE_MODULE:-ipfs_service}"
IPFS_SERVICE_PIP_SPEC="${IPFS_SERVICE_PIP_SPEC:-git+https://github.com/mod-net/ipfs-service}"

# Ensure the IPFS service module is importable; install if missing
ensure_ipfs_service() {
  local candidates=("${IPFS_SERVICE_MODULE}" ipfs_service ipfs_service_app commune_ipfs app)
  local found=0
  for m in "${candidates[@]}"; do
    if python - <<PY >/dev/null 2>&1
import importlib.util, sys
m = sys.argv[1]
sys.exit(0 if importlib.util.find_spec(m) else 1)
PY
      "$m"; then
      found=1
      break
    fi
  done
  if [[ $found -eq 0 ]]; then
    echo "[ipfs-worker] Installing: ${IPFS_SERVICE_PIP_SPEC}"
    uv pip install -U "${IPFS_SERVICE_PIP_SPEC}"
  fi
}

# Determine the import path that exposes FastAPI `app` as `${module}.main:app`.
# Tries user-provided module first, then common fallbacks.
resolve_app_import() {
  local candidates=("${IPFS_SERVICE_MODULE}" ipfs_service ipfs_service_app commune_ipfs app)
  local found=""
  for m in "${candidates[@]}"; do
    if python - <<PY >/dev/null 2>&1
import importlib, sys
m = sys.argv[1]
try:
    mod = importlib.import_module(f"{m}.main")
    getattr(mod, 'app')
except Exception:
    sys.exit(1)
sys.exit(0)
PY
    "$m"; then
      found="$m"
      break
    fi
  done
  if [[ -z "$found" ]]; then
    echo "[ipfs-worker] ERROR: Could not locate a module exposing 'main:app'. Tried: ${candidates[*]}" >&2
    echo "[ipfs-worker] Installed dists:" >&2
    uv pip list >&2 || true
    exit 1
  fi
  echo "$found"
}

# Prefer running via Nix dev shell
if has_nix && ! in_nix_shell; then
  exec -a ipfs-worker env NIX_CONFIG='experimental-features = nix-command flakes' \
    nix develop "$PROJECT_ROOT/env-setup" -c bash -lc "cd '$APP_DIR' && (python -c \"import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('${IPFS_SERVICE_MODULE}') else 1)\" || uv pip install -U '${IPFS_SERVICE_PIP_SPEC}') && MOD=\"$(python - <<'PY'
import importlib, sys
candidates = [\"${IPFS_SERVICE_MODULE}\", \"ipfs_service\", \"ipfs_service_app\", \"commune_ipfs\", \"app\"]
for m in candidates:
    try:
        mod = importlib.import_module(f\"{m}.main\")
        if hasattr(mod, 'app'):
            print(m)
            sys.exit(0)
    except Exception:
        pass
print(\"\", end=\"\")
sys.exit(2)
PY
)\"; if [[ -z \"$MOD\" ]]; then echo \"[ipfs-worker] ERROR: Could not locate module exposing main:app\" >&2; uv pip list >&2 || true; exit 1; fi; echo \"[ipfs-worker] Using module: $MOD\"; uv run uvicorn \"$MOD.main:app\" --host 0.0.0.0 --port ${IPFS_WORKER_PORT}"
else
  cd "$APP_DIR"
  ensure_ipfs_service
  MOD="$(resolve_app_import)"
  echo "[ipfs-worker] Using module: $MOD"
  exec -a ipfs-worker uv run uvicorn "$MOD.main:app" --host 0.0.0.0 --port "${IPFS_WORKER_PORT}"
fi
