#!/bin/bash
# macOS: AgentLink-Dashboard (Vite/React) bauen und als statische Seite per LaunchDaemon ausliefern.
# nginx des Kerns leitet /agentlink/ dorthin (nur für angemeldete Admins).
set -euo pipefail
# shellcheck source=../lib/mac-common.sh
source "$(cd "$(dirname "$0")/../lib" && pwd)/mac-common.sh"

LABEL="io.hydrahive.agentlink-frontend"
FRONTEND="$HL_PREFIX/frontend"

brew_ensure node

priv mkdir -p "$FRONTEND/src" "$HL_LOG_DIR"
priv chown -R "$HL_USER" "$HL_PREFIX"
as_user rsync -a --delete --exclude node_modules --exclude dist \
  "$HL_REPO_ROOT/agentlink/frontend/" "$FRONTEND/src/"

# Relative Pfade: API und WebSocket laufen über denselben HTTPS-Origin wie HydraHive.
# npm ci: genau nach package-lock.json, ändert sie nie.
(
  cd "$FRONTEND/src"
  as_user npm ci --no-fund --no-audit
  as_user env VITE_API_URL=/agentlink/api VITE_WS_URL=/agentlink/ws \
    npm exec -- vite build --base=/agentlink/
)
as_user ln -sfn "$FRONTEND/src/dist" "$FRONTEND/dist"

PY="$(pick_python)"
write_daemon "$LABEL" "$FRONTEND/dist" \
  "$HL_LOG_DIR/agentlink-frontend.log" "$HL_LOG_DIR/agentlink-frontend.log" \
  "$PY" -m http.server "$HL_FRONTEND_PORT" --bind "$HL_BIND_HOST"

if ! wait_for "AgentLink-Dashboard" curl -fsS "http://${HL_BIND_HOST}:${HL_FRONTEND_PORT}/"; then
  echo "AgentLink-Dashboard startet nicht – siehe $HL_LOG_DIR/agentlink-frontend.log" >&2
  exit 1
fi
