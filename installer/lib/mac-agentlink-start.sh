#!/bin/bash
# Start-Wrapper für AgentLink unter macOS (launchd).
#
# launchd kennt kein EnvironmentFile wie systemd. Zugangsdaten gehören aber nicht in die plist
# (/Library/LaunchDaemons/*.plist und `launchctl print` sind für jeden lokalen Nutzer lesbar).
# Darum liest dieser Wrapper KEY=WERT-Zeilen aus der 0600-Datei und startet dann das Programm.
#
# Aufruf (aus der plist): mac-agentlink-start.sh <env-datei> <programm> [argumente…]
set -euo pipefail

ENV_FILE="${1:?env-Datei fehlt}"
shift
if [ ! -r "$ENV_FILE" ]; then
  echo "mac-agentlink-start: $ENV_FILE fehlt oder ist nicht lesbar – AgentLink startet nicht" >&2
  exit 78  # EX_CONFIG
fi
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  key="${line%%=*}"
  case "$key" in *[!A-Za-z0-9_]*|'') continue ;; esac
  export "$key=${line#*=}"
done < "$ENV_FILE"

exec "$@"
