#!/usr/bin/env bash
# Postgres-User + DB für AgentLink anlegen, idempotent.
set -euo pipefail

mkdir -p "$(dirname "$HL_DB_PWD_FILE")"
if [ ! -f "$HL_DB_PWD_FILE" ]; then
  umask 077
  python3 -c 'import secrets; print(secrets.token_urlsafe(24))' > "$HL_DB_PWD_FILE"
  chmod 600 "$HL_DB_PWD_FILE"
fi
DB_PWD="$(cat "$HL_DB_PWD_FILE")"
# Für das SQL-Literal: einfache Anführungszeichen verdoppeln.
DB_PWD_SQL="${DB_PWD//\'/\'\'}"

# Das Passwort geht ausschließlich über stdin an psql, nie über -c: sudo
# protokolliert die komplette Befehlszeile im Journal (COMMAND=...), und jeder
# lokale Benutzer sieht laufende Befehlszeilen über ps.
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${HL_DB_USER}'" | grep -q 1; then
  ROLE_SQL="ALTER ROLE \"${HL_DB_USER}\" WITH PASSWORD '${DB_PWD_SQL}';"
else
  ROLE_SQL="CREATE ROLE \"${HL_DB_USER}\" WITH LOGIN PASSWORD '${DB_PWD_SQL}';"
fi
# log_statement/log_min_duration_statement nur für diese Sitzung aus, damit das
# Statement auch bei geänderter Postgres-Logkonfiguration nicht im Serverlog landet.
sudo -u postgres psql -q -v ON_ERROR_STOP=1 >/dev/null <<SQL
SET log_statement = 'none';
SET log_min_duration_statement = -1;
${ROLE_SQL}
SQL

# DB anlegen wenn nicht vorhanden.
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${HL_DB_NAME}'" | grep -q 1 || \
  sudo -u postgres createdb -O "${HL_DB_USER}" "${HL_DB_NAME}"

echo "Postgres bereit: ${HL_DB_USER}@${HL_DB_NAME}"
