#!/bin/bash
# macOS: Rolle + Datenbank für AgentLink im vorhandenen postgresql@16 des HydraHive-Kerns.
# Kein zweites PostgreSQL. Homebrew-PostgreSQL gehört dem Dienstnutzer (Superuser = dieser Nutzer),
# einen Systemnutzer „postgres“ gibt es auf dem Mac nicht.
set -euo pipefail
# shellcheck source=../lib/mac-common.sh
source "$(cd "$(dirname "$0")/../lib" && pwd)/mac-common.sh"

PG_BIN="$(run_brew --prefix postgresql@16)/bin"
if ! "$PG_BIN/pg_isready" -h 127.0.0.1 -q 2>/dev/null; then
  echo "PostgreSQL (postgresql@16) läuft nicht auf 127.0.0.1 – erst den HydraHive-Kern installieren" >&2
  exit 1
fi

PWD_FILE="$HL_CONFIG_DIR/db.password"
priv mkdir -p "$HL_CONFIG_DIR"
priv chown "$HL_USER" "$HL_CONFIG_DIR"
priv chmod 700 "$HL_CONFIG_DIR"
if [ ! -s "$PWD_FILE" ]; then
  # Hex: steht später unverändert in einer URL (DATABASE_URL). Nicht „tr < /dev/urandom | head“:
  # unter pipefail endet das mit SIGPIPE (141) und bricht das Skript ab.
  ( umask 077; openssl rand -hex 24 > "$PWD_FILE" )
fi
chmod 600 "$PWD_FILE"
priv chown "$HL_USER" "$PWD_FILE"   # auch wenn das Kern-Update als root läuft
DB_PWD="$(cat "$PWD_FILE")"
DB_PWD_SQL="${DB_PWD//\'/\'\'}"

psql_admin() { as_user "$PG_BIN/psql" -h 127.0.0.1 -d postgres -v ON_ERROR_STOP=1 "$@"; }

# Passwort nur über stdin an psql, nie in eine Befehlszeile (ps zeigt sie jedem Nutzer).
if psql_admin -tAc "SELECT 1 FROM pg_roles WHERE rolname='${HL_DB_USER}'" | grep -q 1; then
  ROLE_SQL="ALTER ROLE \"${HL_DB_USER}\" WITH LOGIN PASSWORD '${DB_PWD_SQL}';"
else
  ROLE_SQL="CREATE ROLE \"${HL_DB_USER}\" WITH LOGIN PASSWORD '${DB_PWD_SQL}';"
fi
psql_admin -q >/dev/null <<SQL
SET log_statement = 'none';
SET log_min_duration_statement = -1;
${ROLE_SQL}
SQL

if ! psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname='${HL_DB_NAME}'" | grep -q 1; then
  log "Lege Datenbank ${HL_DB_NAME} an"
  as_user "$PG_BIN/createdb" -h 127.0.0.1 -O "$HL_DB_USER" "$HL_DB_NAME"
fi

log "PostgreSQL bereit: ${HL_DB_USER}@${HL_DB_NAME}"
