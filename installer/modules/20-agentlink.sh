#!/usr/bin/env bash
# AgentLink-Backend in /opt/hydralink/agentlink, Python-venv, systemd-Service.
set -euo pipefail

# Service-User anlegen falls noch nicht da
if ! id "${HL_USER}" >/dev/null 2>&1; then
  useradd --system --shell /usr/sbin/nologin --home-dir "${HL_PREFIX}" --create-home "${HL_USER}"
fi

mkdir -p "${HL_PREFIX}/agentlink/backend"
# Backend-Code aus dem Repo kopieren (überschreibt bei Update)
rsync -a --delete "${REPO_ROOT}/agentlink/backend/" "${HL_PREFIX}/agentlink/backend/"
chown -R "${HL_USER}:${HL_USER}" "${HL_PREFIX}"

# venv + deps
sudo -u "${HL_USER}" python3 -m venv "${HL_PREFIX}/.venv"
sudo -u "${HL_USER}" "${HL_PREFIX}/.venv/bin/pip" install --upgrade pip wheel
sudo -u "${HL_USER}" "${HL_PREFIX}/.venv/bin/pip" install -r "${HL_PREFIX}/agentlink/backend/requirements.txt"

# Service-Unit installieren
DB_PWD="$(cat "$HL_DB_PWD_FILE")"
DATABASE_URL="postgresql://${HL_DB_USER}:${DB_PWD}@127.0.0.1:5432/${HL_DB_NAME}"

cat > /etc/systemd/system/agentlink.service <<EOF
[Unit]
Description=AgentLink Backend (HydraLink)
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=${HL_USER}
Group=${HL_USER}
WorkingDirectory=${HL_PREFIX}/agentlink/backend
Environment=DATABASE_URL=${DATABASE_URL}
Environment=REDIS_URL=redis://127.0.0.1:6379
ExecStart=${HL_PREFIX}/.venv/bin/uvicorn main:app --host ${HL_BIND_HOST} --port ${HL_BACKEND_PORT}
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${HL_PREFIX}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable agentlink.service
systemctl restart agentlink.service

# Health-Wait
for i in $(seq 1 20); do
  if curl -fsS "http://${HL_BIND_HOST}:${HL_BACKEND_PORT}/docs" >/dev/null 2>&1; then
    echo "AgentLink up auf ${HL_BIND_HOST}:${HL_BACKEND_PORT}"
    exit 0
  fi
  sleep 1
done
echo "AgentLink antwortet nicht — siehe journalctl -u agentlink -n 50" >&2
exit 1
