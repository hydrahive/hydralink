#!/bin/bash
# macOS: Redis über Homebrew als LaunchDaemon (nur 127.0.0.1).
# PostgreSQL bringt der HydraHive-Kern mit (postgresql@16, LaunchDaemon io.hydrahive.postgres).
set -euo pipefail
# shellcheck source=../lib/mac-common.sh
source "$(cd "$(dirname "$0")/../lib" && pwd)/mac-common.sh"

brew_ensure redis

REDIS_PREFIX="$(run_brew --prefix redis)"
REDIS_DIR="$HL_DATA_DIR/redis"
LABEL="io.hydrahive.redis"

# brew services würde Redis als LaunchAgent starten – der läuft erst nach der Anmeldung und
# stünde neben unserem Daemon. Abmelden, damit genau ein Redis läuft (wie bei PostgreSQL im Kern).
run_brew services stop redis >/dev/null 2>&1 || true
AGENT_HOME="$(dscl . -read "/Users/$HL_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}' || true)"
[ -n "$AGENT_HOME" ] || AGENT_HOME="/Users/$HL_USER"
priv rm -f "$AGENT_HOME/Library/LaunchAgents/homebrew.mxcl.redis.plist"

priv mkdir -p "$REDIS_DIR" "$HL_LOG_DIR"
priv chown -R "$HL_USER" "$HL_DATA_DIR"

# Einstellungen direkt als Argumente: keine eigene Konfigdatei, die bei brew-Updates überschrieben wird.
write_daemon "$LABEL" "$REDIS_DIR" "$HL_LOG_DIR/redis-hydralink.log" "$HL_LOG_DIR/redis-hydralink.log" \
  "$REDIS_PREFIX/bin/redis-server" \
  --bind 127.0.0.1 --port 6379 --protected-mode yes \
  --dir "$REDIS_DIR" --save 60 1000 --appendonly no

wait_for "Redis" "$REDIS_PREFIX/bin/redis-cli" -h 127.0.0.1 -p 6379 ping
