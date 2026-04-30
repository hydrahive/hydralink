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

# User anlegen wenn nicht vorhanden, sonst Passwort updaten.
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${HL_DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE ROLE \"${HL_DB_USER}\" WITH LOGIN PASSWORD '${DB_PWD}';"
sudo -u postgres psql -c "ALTER ROLE \"${HL_DB_USER}\" WITH PASSWORD '${DB_PWD}';"

# DB anlegen wenn nicht vorhanden.
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${HL_DB_NAME}'" | grep -q 1 || \
  sudo -u postgres createdb -O "${HL_DB_USER}" "${HL_DB_NAME}"

echo "Postgres bereit: ${HL_DB_USER}@${HL_DB_NAME}"
