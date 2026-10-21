#!/bin/bash
# Gemeinsame Helfer der macOS-Module (installer/modules-mac/*.sh).
# Läuft unter /bin/bash 3.2 (macOS): keine leeren Arrays unter set -u, kein ${x,,}, kein readarray.
#
# Erwartet (gesetzt von install-mac.sh, in Tests von außen):
#   HL_USER        Dienstnutzer (wie der HydraHive-Kern auf dem Mac, nie root)
#   HL_PREFIX      Code + venv, Standard /opt/hydralink
#   HL_CONFIG_DIR  Zugangsdaten (0600), Standard /usr/local/etc/hydralink
#   HL_LOG_DIR     Logs, Standard /usr/local/var/log
#   HL_PLIST_DIR   LaunchDaemons, Standard /Library/LaunchDaemons

log() { printf "  · %s\n" "$*"; }

HL_USER="${HL_USER:?HL_USER fehlt}"
HL_PREFIX="${HL_PREFIX:-/opt/hydralink}"
HL_CONFIG_DIR="${HL_CONFIG_DIR:-/usr/local/etc/hydralink}"
HL_LOG_DIR="${HL_LOG_DIR:-/usr/local/var/log}"
HL_PLIST_DIR="${HL_PLIST_DIR:-/Library/LaunchDaemons}"
HL_DB_NAME="${HL_DB_NAME:-agentlink}"
HL_DB_USER="${HL_DB_USER:-agentlink}"
HL_BIND_HOST="${HL_BIND_HOST:-127.0.0.1}"
HL_BACKEND_PORT="${HL_BACKEND_PORT:-9000}"
HL_FRONTEND_PORT="${HL_FRONTEND_PORT:-9001}"
HL_WAIT="${HL_WAIT:-30}"
HL_REPO_ROOT="${HL_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# Homebrew über den vollen Pfad: /opt/homebrew (Apple Silicon) oder /usr/local (Intel). Nicht über PATH –
# als root (Kern-Update per LaunchDaemon) verweigert `brew shellenv` den Dienst und sudo setzt einen eigenen
# PATH ohne Homebrew („sudo: brew: command not found“, Befund 21.10.2026 auf dem Test-Mac).
HL_BREW="${HL_BREW:-}"
if [ -z "$HL_BREW" ]; then
  for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    if [ -x "$candidate" ]; then HL_BREW="$candidate"; break; fi
  done
fi
[ -n "$HL_BREW" ] || HL_BREW="$(command -v brew || true)"
if [ -z "$HL_BREW" ]; then
  echo "Homebrew nicht gefunden (/opt/homebrew/bin/brew oder /usr/local/bin/brew)" >&2
  exit 1
fi
export PATH="$(dirname "$HL_BREW"):$PATH"

as_root() { [ "$(id -u)" -eq 0 ]; }
# Homebrew verweigert root – als root deshalb über den Dienstnutzer aufrufen.
run_brew() { if as_root; then sudo -u "$HL_USER" "$HL_BREW" "$@"; else "$HL_BREW" "$@"; fi; }
# Befehl als Dienstnutzer (für git/pip/npm in dessen Ordnern).
# sudo setzt einen eigenen PATH (secure_path) – npm/node aus Homebrew wären sonst unauffindbar.
as_user() { if as_root; then sudo -u "$HL_USER" env "PATH=$PATH" HOME="$(_user_home)" "$@"; else "$@"; fi; }
_user_home() {
  local h
  h="$(dscl . -read "/Users/$HL_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}' || true)"
  echo "${h:-/Users/$HL_USER}"
}
priv() { if as_root; then "$@"; else sudo "$@"; fi; }

brew_ensure() {
  if run_brew list "$1" >/dev/null 2>&1; then
    log "$1 bereits installiert"
  else
    log "brew install $1"
    run_brew install "$1" --quiet
  fi
}

# Python ab 3.12 aus Homebrew (gleiche Linie wie der Kern: python@3.12 zuerst, dann neuere).
pick_python() {
  if [ -n "${HL_PYTHON:-}" ]; then echo "$HL_PYTHON"; return 0; fi
  local v bin
  for v in 3.12 3.13 3.14; do
    bin="$(run_brew --prefix "python@$v" 2>/dev/null)/bin/python$v"
    if [ -x "$bin" ]; then echo "$bin"; return 0; fi
  done
  echo "Kein Homebrew-Python ab 3.12 gefunden (brew install python@3.12)" >&2
  return 1
}

# write_daemon LABEL WORKDIR STDOUT STDERR ARG... — LaunchDaemon unter HL_USER, startet beim
# Hochfahren (RunAtLoad), wird neu gestartet (KeepAlive). Keine Geheimnisse hier hinein:
# plists in /Library/LaunchDaemons sind für jeden lokalen Nutzer lesbar.
write_daemon() {
  local label="$1" workdir="$2" out="$3" err="$4"
  shift 4
  local plist="$HL_PLIST_DIR/$label.plist" args="" a
  for a in "$@"; do
    a="${a//&/&amp;}"; a="${a//</&lt;}"; a="${a//>/&gt;}"
    args="$args        <string>$a</string>
"
  done
  log "Schreibe $plist"
  priv tee "$plist" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${label}</string>
    <key>ProgramArguments</key>
    <array>
${args}    </array>
    <key>WorkingDirectory</key>
    <string>${workdir}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$(run_brew --prefix)/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>LC_ALL</key>
        <string>en_US.UTF-8</string>
    </dict>
    <key>UserName</key>
    <string>${HL_USER}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${out}</string>
    <key>StandardErrorPath</key>
    <string>${err}</string>
</dict>
</plist>
EOF
  priv chmod 644 "$plist"
  priv launchctl unload "$plist" >/dev/null 2>&1 || true
  priv launchctl load "$plist"
}

# wait_for BESCHREIBUNG BEFEHL... — wartet bis HL_WAIT Sekunden, bis BEFEHL gelingt.
wait_for() {
  local what="$1" i=0
  shift
  while [ "$i" -lt "$HL_WAIT" ]; do
    if "$@" >/dev/null 2>&1; then
      log "$what antwortet"
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  echo "$what antwortet nach ${HL_WAIT} s nicht" >&2
  return 1
}
