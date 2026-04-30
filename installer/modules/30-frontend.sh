#!/usr/bin/env bash
# AgentLink-Frontend (Vite/React) bauen + als statisches SPA via systemd ausliefern.
set -euo pipefail

HL_FRONTEND_PORT="${HL_FRONTEND_PORT:-9001}"
HL_FRONTEND_DIR="${HL_PREFIX}/frontend"

# Node aus apt — sicherer Default für Ubuntu 24.04 (Node 18). Wenn der Host
# eine neuere Version hat (nvm/fnm), wird die genutzt da PATH zuerst.
if ! command -v npm >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends nodejs npm
fi

mkdir -p "${HL_FRONTEND_DIR}"
rsync -a --delete "${REPO_ROOT}/agentlink/frontend/" "${HL_FRONTEND_DIR}/src/"
chown -R "${HL_USER}:${HL_USER}" "${HL_FRONTEND_DIR}"

# Build mit korrekter API-URL
VITE_API_URL="http://${HL_BIND_HOST}:${HL_BACKEND_PORT}"
sudo -u "${HL_USER}" -- bash -c "cd '${HL_FRONTEND_DIR}/src' && npm install --silent && VITE_API_URL='${VITE_API_URL}' npm run build"

# Symlink dist/ → /opt/hydralink/frontend/dist (stabiler Pfad für systemd)
ln -sfn "${HL_FRONTEND_DIR}/src/dist" "${HL_FRONTEND_DIR}/dist"

cat > /etc/systemd/system/agentlink-frontend.service <<EOF
[Unit]
Description=AgentLink Frontend (HydraLink, static SPA)
After=network.target

[Service]
Type=simple
User=${HL_USER}
Group=${HL_USER}
WorkingDirectory=${HL_FRONTEND_DIR}/dist
ExecStart=/usr/bin/python3 -m http.server ${HL_FRONTEND_PORT} --bind ${HL_BIND_HOST}
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable agentlink-frontend.service
systemctl restart agentlink-frontend.service

# Health-Wait
for i in $(seq 1 10); do
  if curl -fsS "http://${HL_BIND_HOST}:${HL_FRONTEND_PORT}/" >/dev/null 2>&1; then
    echo "AgentLink-Frontend up auf ${HL_BIND_HOST}:${HL_FRONTEND_PORT}"
    exit 0
  fi
  sleep 1
done
echo "Frontend antwortet nicht — siehe journalctl -u agentlink-frontend -n 50" >&2
exit 1
