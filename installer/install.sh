#!/usr/bin/env bash
# HydraLink Installer — native (kein Docker), für Ubuntu 24.04.
#
# Installiert:
#   - PostgreSQL (apt) + DB + User
#   - Redis (apt, default 127.0.0.1:6379)
#   - AgentLink-Backend als systemd-Service unter /opt/hydralink/agentlink
#
# Idempotent — mehrfaches Ausführen ist safe.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte als root ausführen (sudo bash install.sh)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export HL_PREFIX="${HL_PREFIX:-/opt/hydralink}"
export HL_USER="${HL_USER:-hydralink}"
export HL_DB_NAME="${HL_DB_NAME:-agentlink}"
export HL_DB_USER="${HL_DB_USER:-agentlink}"
# Passwort wird beim ersten Run erzeugt + persistiert — danach nicht mehr ändern!
export HL_DB_PWD_FILE="${HL_DB_PWD_FILE:-/etc/hydralink/db.password}"
export HL_BIND_HOST="${HL_BIND_HOST:-127.0.0.1}"
export HL_BACKEND_PORT="${HL_BACKEND_PORT:-8000}"
export HL_FRONTEND_PORT="${HL_FRONTEND_PORT:-9001}"

log() { echo -e "\033[1;36m[hydralink-install]\033[0m $*"; }

run_module() {
  local m="$SCRIPT_DIR/modules/$1"
  if [ ! -x "$m" ]; then
    echo "Modul fehlt oder nicht ausführbar: $m" >&2
    exit 1
  fi
  log "→ $1"
  "$m"
}

run_module 00-deps.sh
run_module 10-postgres.sh
run_module 20-agentlink.sh
run_module 30-frontend.sh

log "Fertig."
log "  Backend  http://${HL_BIND_HOST}:${HL_BACKEND_PORT}"
log "  Frontend http://${HL_BIND_HOST}:${HL_FRONTEND_PORT}"
log "Status: systemctl status agentlink agentlink-frontend"
log "Logs:   journalctl -u agentlink -f  (bzw. agentlink-frontend)"
