#!/bin/bash
# HydraLink (AgentLink) Installer für macOS – Gegenstück zu install.sh (Ubuntu).
#
# Voraussetzungen: HydraHive-Kern ist mit installer/install-mac.sh installiert (Homebrew,
# postgresql@16 als LaunchDaemon). Der Kern ruft dieses Skript über
# installer/modules-mac/75-agentlink.sh auf, bei der Installation und bei jedem Update.
#
# Als Dienstnutzer des Kerns ausführen, nicht als root (sudo nur für die LaunchDaemons).
# Idempotent – mehrfaches Ausführen ist sicher.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
log() { printf "\033[1;36m[hydralink-mac]\033[0m %s\n" "$*"; }

if [ "$(uname)" != "Darwin" ]; then
  echo "install-mac.sh ist nur für macOS – unter Linux: sudo bash installer/install.sh" >&2
  exit 1
fi
if [ "$(id -u)" -eq 0 ]; then
  echo "Bitte als normaler Nutzer starten (Homebrew verweigert root); sudo wird bei Bedarf abgefragt." >&2
  exit 1
fi

export HL_USER="${HL_USER:-$(whoami)}"
export HL_REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

for m in 00-deps.sh 10-postgres.sh 20-agentlink.sh 30-frontend.sh; do
  log "→ $m"
  bash "$SCRIPT_DIR/modules-mac/$m"
done

log "Fertig. Backend http://127.0.0.1:${HL_BACKEND_PORT:-9000} · Dashboard über HydraHive unter /agentlink/"
log "Logs: ${HL_LOG_DIR:-/usr/local/var/log}/agentlink-error.log"
