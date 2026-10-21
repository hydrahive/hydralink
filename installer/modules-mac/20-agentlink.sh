#!/bin/bash
# macOS: AgentLink-Backend nach $HL_PREFIX/agentlink/backend, Python-venv, LaunchDaemon.
set -euo pipefail
# shellcheck source=../lib/mac-common.sh
source "$(cd "$(dirname "$0")/../lib" && pwd)/mac-common.sh"

LABEL="io.hydrahive.agentlink"
BACKEND="$HL_PREFIX/agentlink/backend"
VENV="$HL_PREFIX/.venv"
ENV_FILE="$HL_CONFIG_DIR/agentlink.env"
START="$HL_PREFIX/installer/lib/mac-agentlink-start.sh"

priv mkdir -p "$BACKEND" "$HL_PREFIX/installer/lib" "$HL_LOG_DIR"
priv chown -R "$HL_USER" "$HL_PREFIX"
# Code + Start-Wrapper aus dem Repo (überschreibt bei Update). Der Wrapper liegt im Präfix,
# damit die plist nicht auf einen Arbeitsordner zeigt, der später verschwindet.
as_user rsync -a --delete --exclude __pycache__ "$HL_REPO_ROOT/agentlink/backend/" "$BACKEND/"
as_user cp "$HL_REPO_ROOT/installer/lib/mac-agentlink-start.sh" "$START"
as_user chmod 755 "$START"

PY="$(pick_python)"
WANT="$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
VENV_ARGS=""
if [ -d "$VENV" ]; then
  HAVE="$("$VENV/bin/python" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "?")"
  if [ "$HAVE" != "$WANT" ]; then
    log "venv ist Python $HAVE, erwartet $WANT – baue neu"
    VENV_ARGS="--clear"
    priv launchctl unload "$HL_PLIST_DIR/$LABEL.plist" >/dev/null 2>&1 || true
  fi
fi
log "venv mit $PY (Python $WANT)"
# shellcheck disable=SC2086  # VENV_ARGS ist leer oder genau ein Flag
as_user "$PY" -m venv $VENV_ARGS "$VENV"
as_user "$VENV/bin/pip" install --quiet --upgrade pip wheel
as_user "$VENV/bin/pip" install --quiet -r "$BACKEND/requirements.txt"

# Zugangsdaten: 0600, gehört dem Dienstnutzer, atomar ersetzt. Treiber psycopg2 ausdrücklich
# (SQLAlchemy 2.1 nähme bei „postgresql://“ psycopg 3, das nicht installiert ist).
DB_PWD="$(cat "$HL_CONFIG_DIR/db.password")"
( umask 077
  printf 'DATABASE_URL=postgresql+psycopg2://%s:%s@127.0.0.1:5432/%s\nREDIS_URL=redis://127.0.0.1:6379\n' \
    "$HL_DB_USER" "$DB_PWD" "$HL_DB_NAME" > "$ENV_FILE.tmp" )
chmod 600 "$ENV_FILE.tmp"
mv -f "$ENV_FILE.tmp" "$ENV_FILE"
priv chown "$HL_USER" "$ENV_FILE"

write_daemon "$LABEL" "$BACKEND" "$HL_LOG_DIR/agentlink.log" "$HL_LOG_DIR/agentlink-error.log" \
  /bin/bash "$START" "$ENV_FILE" "$VENV/bin/uvicorn" main:app \
  --host "$HL_BIND_HOST" --port "$HL_BACKEND_PORT"

if ! wait_for "AgentLink" curl -fsS "http://${HL_BIND_HOST}:${HL_BACKEND_PORT}/docs"; then
  echo "AgentLink startet nicht – siehe tail -50 $HL_LOG_DIR/agentlink-error.log" >&2
  exit 1
fi
