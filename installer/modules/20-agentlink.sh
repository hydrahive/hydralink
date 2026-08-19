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

# Interpreter wählen. NICHT blind "python3": auf Ubuntu 26.04 ist das Python
# 3.14, und für die gepinnten Abhängigkeiten (pydantic==2.9.2) gibt es dafür
# keine fertigen Wheels. pip fällt dann auf den Rust-Build von pydantic-core
# zurück (maturin/pyo3) und die Installation bricht ab.
# Darum eine Version bevorzugen, für die Wheels existieren.
# HL_PYTHON übersteuert die Automatik.
pick_python() {
  if [ -n "${HL_PYTHON:-}" ]; then echo "$HL_PYTHON"; return; fi
  for candidate in python3.12 python3.13 python3.11 python3; do
    command -v "$candidate" >/dev/null 2>&1 && { echo "$candidate"; return; }
  done
  echo "python3"
}
HL_PYTHON_BIN="$(pick_python)"
echo "AgentLink-venv nutzt ${HL_PYTHON_BIN} ($(${HL_PYTHON_BIN} --version 2>&1))"

# venv anlegen. Bei einem BESTEHENDEN venv, dessen Standardinterpreter nicht
# zum gewaehlten passt, muss --clear gesetzt werden: "python3.X -m venv"
# aktualisiert zwar pyvenv.cfg und legt bin/python3.X an, ersetzt aber die
# vorhandenen Symlinks bin/python und bin/python3 NICHT. Ergebnis ist ein
# Zwitter:
#   pyvenv.cfg       -> version = 3.12
#   bin/python3      -> /usr/bin/python3   (3.14, leeres site-packages)
#   bin/uvicorn      -> #!.../bin/python3.12 (Pakete da)
# Der Dienst laeuft dann zufaellig, aber ".venv/bin/python -c 'import pydantic'"
# scheitert mit ModuleNotFoundError, obwohl pip das Paket meldet.
#
# Deshalb wird der TATSAECHLICHE Interpreter hinter bin/python geprueft, nicht
# nur die Angabe in pyvenv.cfg — die war im Fehlerfall bereits korrekt.
VENV_PY="${HL_PREFIX}/.venv/bin/python"
VENV_ARGS=""
if [ -d "${HL_PREFIX}/.venv" ]; then
  if [ ! -x "$VENV_PY" ]; then
    echo "AgentLink-venv: bin/python fehlt oder zeigt auf entfernten Interpreter — baue venv neu (--clear)"
    VENV_ARGS="--clear"
  else
    want="$("${HL_PYTHON_BIN}" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
    have="$("$VENV_PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "?")"
    if [ "$want" != "$have" ]; then
      echo "AgentLink-venv: bin/python ist ${have}, erwartet ${want} — baue venv neu (--clear)"
      VENV_ARGS="--clear"
    fi
  fi
fi

# Während --clear darf systemd den Dienst nicht fortlaufend neu starten: uvicorn
# kann sonst bereits auftauchen, während site-packages noch unvollständig sind.
if [ "$VENV_ARGS" = "--clear" ] && systemctl cat agentlink.service >/dev/null 2>&1; then
  echo "Stoppe agentlink.service vor dem Venv-Rebuild"
  systemctl stop agentlink.service || true
fi

# shellcheck disable=SC2086  # VENV_ARGS ist bewusst leer oder genau ein Flag
sudo -u "${HL_USER}" "${HL_PYTHON_BIN}" -m venv $VENV_ARGS "${HL_PREFIX}/.venv"
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
