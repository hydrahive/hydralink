"""Nachgebauter Mac für die macOS-Installer-Tests (läuft unter Linux).

brew, sudo, launchctl, curl, redis-cli, psql, pg_isready, npm, chown, uname, id und Python sind
Stubs im PATH bzw. im Schein-Homebrew-Präfix. Jeder Aufruf landet in calls.log, stdin von psql
getrennt in psql-stdin.log.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "installer" / "modules-mac"
INSTALL_MAC = ROOT / "installer" / "install-mac.sh"


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


class FakeMac:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.bin = tmp / "bin"
        self.prefix = tmp / "brew"
        self.calls = tmp / "calls.log"
        self.psql_stdin = tmp / "psql-stdin.log"
        self.plist_dir = tmp / "LaunchDaemons"
        self.config = tmp / "etc" / "hydralink"
        self.data = tmp / "var" / "hydralink"
        self.logs = tmp / "log"
        self.hl_prefix = tmp / "opt" / "hydralink"
        self.home = tmp / "home"
        for d in (self.bin, self.plist_dir, self.logs, self.home / "Library" / "LaunchAgents"):
            d.mkdir(parents=True, exist_ok=True)
        self.calls.touch()
        log = f'echo "$(basename "$0") $*" >> "{self.calls}"\n'

        # brew: Präfixe; list prüft Marker-Dateien, install legt sie an.
        _exe(self.bin / "brew", log + f'''
case "$1" in
  --prefix) if [ -n "${{2:-}}" ]; then echo "{self.prefix}/opt/$2"; else echo "{self.prefix}"; fi ;;
  list) [ -e "{self.prefix}/opt/$2/.installed" ] ;;
  install) mkdir -p "{self.prefix}/opt/$2/bin"; touch "{self.prefix}/opt/$2/.installed" ;;
esac
''')
        _exe(self.bin / "sudo", log + '''
while [ $# -gt 0 ]; do
  case "$1" in -u) shift 2 ;; -H|-n|-E) shift ;; *) break ;; esac
done
exec "$@"
''')
        _exe(self.bin / "launchctl", log)
        _exe(self.bin / "chown", log)
        _exe(self.bin / "dscl", f'echo "NFSHomeDirectory: {self.home}"\n')
        _exe(self.bin / "uname", 'echo "${FAKE_UNAME:-Darwin}"\n')
        _exe(self.bin / "id", 'if [ "$#" -eq 1 ] && [ "$1" = "-u" ]; then echo "${FAKE_UID:-501}"; '
                              'else exec /usr/bin/id "$@"; fi\n')
        _exe(self.bin / "curl", log + '[ "${FAKE_CURL_FAIL:-0}" = 1 ] && exit 7; exit 0\n')
        _exe(self.bin / "npm", f'echo "npm $* API=${{VITE_API_URL:-}} WS=${{VITE_WS_URL:-}} CWD=$PWD" >> "{self.calls}"\n'
                                 'mkdir -p dist; echo "<html>" > dist/index.html\n')

        redis = self.prefix / "opt" / "redis" / "bin"
        _exe(redis / "redis-cli", log + f'[ -f "{self.plist_dir}/io.hydrahive.redis.plist" ] || '
              'exit 1; [ "${FAKE_REDIS_DOWN:-0}" = 1 ] && exit 1; echo PONG\n')
        _exe(redis / "redis-server", log)

        pg = self.prefix / "opt" / "postgresql@16" / "bin"
        _exe(pg / "pg_isready", log + '[ "${FAKE_PG_DOWN:-0}" = 1 ] && exit 2; exit 0\n')
        _exe(pg / "psql", log + f'''
case "$*" in
  *"FROM pg_roles"*)    [ "${{FAKE_ROLE_EXISTS:-0}}" = 1 ] && echo 1; exit 0 ;;
  *"FROM pg_database"*) [ "${{FAKE_DB_EXISTS:-0}}" = 1 ] && echo 1; exit 0 ;;
esac
if [ ! -t 0 ]; then cat >> "{self.psql_stdin}"; fi
exit 0
''')
        _exe(pg / "createdb", log)
        (self.prefix / "opt" / "postgresql@16" / ".installed").touch()

        # Python: „-m venv [--clear] DIR“ legt ein Schein-venv an, „-c …“ meldet die Version.
        venv_python = (
            f'echo "venv-python $*" >> "{self.calls}"\n'
            'case "$1" in -c) echo "${FAKE_VENV_VERSION:-3.12}";; esac\n'
        )
        venv_pip = f'echo "pip $*" >> "{self.calls}"\n'
        _exe(self.prefix / "opt" / "python@3.12" / "bin" / "python3.12", log + f'''
case "$1" in
  -c) echo "3.12" ;;
  -m)
    for d in "$@"; do :; done
    mkdir -p "$d/bin"
    cat > "$d/bin/python" <<'PYEOF'
#!/usr/bin/env bash
{venv_python}PYEOF
    cat > "$d/bin/pip" <<'PIPEOF'
#!/usr/bin/env bash
{venv_pip}PIPEOF
    printf '#!/usr/bin/env bash\\n' > "$d/bin/uvicorn"
    chmod 755 "$d/bin/python" "$d/bin/pip" "$d/bin/uvicorn" ;;
esac
''')
        (self.prefix / "opt" / "python@3.12" / ".installed").touch()
        self.install("node")
        self.install("redis")

    def install(self, formula: str) -> None:
        d = self.prefix / "opt" / formula
        (d / "bin").mkdir(parents=True, exist_ok=True)
        (d / ".installed").touch()

    def uninstall(self, formula: str) -> None:
        (self.prefix / "opt" / formula / ".installed").unlink(missing_ok=True)

    def env(self, **extra: str) -> dict:
        return {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.home),
            "HL_USER": "tester",
            "HL_PREFIX": str(self.hl_prefix),
            "HL_CONFIG_DIR": str(self.config),
            "HL_DATA_DIR": str(self.data),
            "HL_LOG_DIR": str(self.logs),
            "HL_PLIST_DIR": str(self.plist_dir),
            "HL_WAIT": "2",
            **extra,
        }

    def run(self, script: str | Path, *args: str, **extra: str) -> subprocess.CompletedProcess:
        path = script if isinstance(script, Path) else MODULES / script
        return subprocess.run(["bash", str(path), *args], env=self.env(**extra), capture_output=True,
                              text=True, timeout=120, stdin=subprocess.DEVNULL)

    def call_lines(self) -> list[str]:
        return self.calls.read_text().splitlines()

    def plist(self, label: str) -> Path:
        return self.plist_dir / f"{label}.plist"
