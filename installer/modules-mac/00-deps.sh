#!/bin/bash
# macOS: Voraussetzungen prüfen bzw. über Homebrew nachinstallieren.
#
# Kein Redis: Homebrew hat für Intel-Macs keine fertigen Redis-Pakete mehr und baut es samt LLVM
# und Rust aus dem Quellcode (Befund 21.10.2026, Test-Mac). AgentLink nutzt auf dem Mac den
# Nachrichtenkanal im Speicher (REDIS_URL=memory://, siehe agentlink/backend/main.py).
# PostgreSQL bringt der HydraHive-Kern mit (postgresql@16, LaunchDaemon io.hydrahive.postgres).
set -euo pipefail
# shellcheck source=../lib/mac-common.sh
source "$(cd "$(dirname "$0")/../lib" && pwd)/mac-common.sh"

brew_ensure python@3.12
brew_ensure node

PG_BIN="$(run_brew --prefix postgresql@16)/bin"
if [ ! -x "$PG_BIN/pg_isready" ] || ! "$PG_BIN/pg_isready" -h 127.0.0.1 -q 2>/dev/null; then
  echo "PostgreSQL (postgresql@16) läuft nicht auf 127.0.0.1 – erst den HydraHive-Kern installieren" >&2
  exit 1
fi
log "PostgreSQL des Kerns läuft"
