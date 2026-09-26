"""Das AgentLink-DB-Passwort darf nie in einer Befehlszeile stehen.

sudo protokolliert die komplette Befehlszeile (COMMAND=...) im systemd-Journal,
und jeder lokale Benutzer sieht laufende Befehlszeilen über `ps`. Das Passwort
muss deshalb über stdin an psql gehen.

Der Test führt 10-postgres.sh wirklich aus, mit einem Ersatz-`sudo` im PATH,
das Befehlszeilen und stdin getrennt mitschreibt.
"""
import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "installer" / "modules" / "10-postgres.sh"

FAKE_SUDO = """#!/usr/bin/env bash
# Ersatz für sudo: schreibt argv und stdin getrennt mit, beantwortet Abfragen.
printf '%s\\n' "$*" >> "$FAKE_LOG_DIR/argv.log"
case "$*" in
  *"FROM pg_roles"*)    [ "${FAKE_ROLE_EXISTS:-0}" = 1 ] && echo 1; exit 0 ;;
  *"FROM pg_database"*) [ "${FAKE_DB_EXISTS:-0}" = 1 ] && echo 1; exit 0 ;;
esac
if [ ! -t 0 ]; then cat >> "$FAKE_LOG_DIR/stdin.log"; fi
exit 0
"""


def _run(tmp_path: Path, *, role_exists: bool, password: str | None = None) -> tuple[str, str, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    sudo = bin_dir / "sudo"
    sudo.write_text(FAKE_SUDO)
    sudo.chmod(sudo.stat().st_mode | stat.S_IEXEC)

    pwd_file = tmp_path / "etc" / "db.password"
    if password is not None:
        pwd_file.parent.mkdir(parents=True, exist_ok=True)
        pwd_file.write_text(password + "\n")

    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_LOG_DIR": str(tmp_path),
        "FAKE_ROLE_EXISTS": "1" if role_exists else "0",
        "HL_DB_PWD_FILE": str(pwd_file),
        "HL_DB_USER": "agentlink",
        "HL_DB_NAME": "agentlink",
    }
    subprocess.run(["bash", str(SCRIPT)], env=env, check=True, stdin=subprocess.DEVNULL,
                   capture_output=True, text=True)
    argv_log = (tmp_path / "argv.log").read_text()
    stdin_log = (tmp_path / "stdin.log").read_text() if (tmp_path / "stdin.log").exists() else ""
    return argv_log, stdin_log, pwd_file


def test_existing_role_password_never_in_command_line(tmp_path: Path) -> None:
    secret = "Geheim-Test-Passwort-123"
    argv_log, stdin_log, _ = _run(tmp_path, role_exists=True, password=secret)

    assert secret not in argv_log, "Passwort steht in einer Befehlszeile (landet im sudo-Journal)"
    assert "ALTER ROLE" in stdin_log and secret in stdin_log, "Passwort muss per stdin gesetzt werden"


def test_new_role_password_never_in_command_line(tmp_path: Path) -> None:
    argv_log, stdin_log, pwd_file = _run(tmp_path, role_exists=False)
    generated = pwd_file.read_text().strip()

    assert len(generated) >= 24
    assert generated not in argv_log
    assert "CREATE ROLE" in stdin_log and generated in stdin_log


def test_generated_password_file_is_private(tmp_path: Path) -> None:
    _, _, pwd_file = _run(tmp_path, role_exists=False)
    assert stat.S_IMODE(pwd_file.stat().st_mode) == 0o600


def test_single_quote_in_password_is_escaped(tmp_path: Path) -> None:
    # token_urlsafe erzeugt keine Anführungszeichen, ein von Hand gesetztes Passwort schon.
    _, stdin_log, _ = _run(tmp_path, role_exists=True, password="a'b")
    assert "PASSWORD 'a''b'" in stdin_log
