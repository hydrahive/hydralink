"""HydraLink-Installer für macOS (Task f4a303a9, Plan hydrahive2 docs/plans/mac-agentlink.md).

Der Linux-Installer nutzt apt, systemd und useradd und läuft auf dem Mac nicht. Auf dem Mac:
Redis über Homebrew, Datenbank im vorhandenen postgresql@16 des HydraHive-Kerns, Dienste als
LaunchDaemons unter dem Dienstnutzer des Kerns (starten beim Hochfahren, ohne Anmeldung).

Die Skripte laufen hier wirklich, auf einem nachgebauten Mac (tests/mac_fake.py).
"""
from __future__ import annotations

import plistlib
import stat

import pytest

from mac_fake import INSTALL_MAC, MODULES, FakeMac


@pytest.fixture
def mac(tmp_path) -> FakeMac:
    return FakeMac(tmp_path)


def _plist(mac: FakeMac, label: str) -> dict:
    return plistlib.loads(mac.plist(label).read_bytes())


def _daemon_basics(p: dict, label: str) -> None:
    assert p["Label"] == label
    assert p["UserName"] == "tester"          # nie root
    assert p["RunAtLoad"] is True              # beim Hochfahren, ohne Anmeldung
    assert p["KeepAlive"] is True


# ---------------------------------------------------------------- 00-deps.sh (Redis)

def test_redis_installed_when_missing(mac):
    mac.uninstall("redis")
    r = mac.run("00-deps.sh")
    assert r.returncode == 0, r.stderr
    assert "brew install redis" in " ".join(mac.call_lines())


def test_redis_not_reinstalled(mac):
    r = mac.run("00-deps.sh")
    assert r.returncode == 0, r.stderr
    assert not any(c.startswith("brew install redis") for c in mac.call_lines())


def test_redis_runs_as_launchdaemon_on_localhost(mac):
    r = mac.run("00-deps.sh")
    assert r.returncode == 0, r.stderr
    p = _plist(mac, "io.hydrahive.redis")
    _daemon_basics(p, "io.hydrahive.redis")
    args = p["ProgramArguments"]
    assert args[0].endswith("/redis/bin/redis-server")
    joined = " ".join(args)
    assert "--bind 127.0.0.1" in joined          # nie im ganzen Netz
    assert "--protected-mode yes" in joined
    assert f"--dir {mac.data}/redis" in joined   # eigener Datenordner statt Homebrew-Standard
    assert f"launchctl load {mac.plist('io.hydrahive.redis')}" in mac.call_lines()


def test_redis_brew_services_agent_removed(mac):
    agent = mac.home / "Library" / "LaunchAgents" / "homebrew.mxcl.redis.plist"
    agent.write_text("x")
    r = mac.run("00-deps.sh")
    assert r.returncode == 0, r.stderr
    assert not agent.exists()                    # sonst zweiter Redis bei der Anmeldung
    assert "brew services stop redis" in mac.call_lines()


def test_redis_not_answering_fails(mac):
    r = mac.run("00-deps.sh", FAKE_REDIS_DOWN="1")
    assert r.returncode != 0


# ---------------------------------------------------------------- 10-postgres.sh

def test_db_password_created_private(mac):
    r = mac.run("10-postgres.sh")
    assert r.returncode == 0, r.stderr
    pwd = mac.config / "db.password"
    assert pwd.exists()
    assert stat.S_IMODE(pwd.stat().st_mode) == 0o600
    assert len(pwd.read_text().strip()) >= 24


def test_db_password_never_on_command_line(mac):
    r = mac.run("10-postgres.sh")
    assert r.returncode == 0, r.stderr
    pw = (mac.config / "db.password").read_text().strip()
    assert pw not in mac.calls.read_text()
    assert pw in mac.psql_stdin.read_text()
    assert "CREATE ROLE" in mac.psql_stdin.read_text()


def test_db_existing_role_gets_password_updated(mac):
    r = mac.run("10-postgres.sh", FAKE_ROLE_EXISTS="1")
    assert r.returncode == 0, r.stderr
    assert "ALTER ROLE" in mac.psql_stdin.read_text()


def test_db_created_only_once(mac):
    r = mac.run("10-postgres.sh")
    assert r.returncode == 0, r.stderr
    assert any(c.startswith("createdb") and "agentlink" in c for c in mac.call_lines())
    mac.calls.write_text("")
    r = mac.run("10-postgres.sh", FAKE_ROLE_EXISTS="1", FAKE_DB_EXISTS="1")
    assert r.returncode == 0, r.stderr
    assert not any(c.startswith("createdb") for c in mac.call_lines())


def test_db_uses_core_postgres_not_sudo_postgres(mac):
    r = mac.run("10-postgres.sh")
    assert r.returncode == 0, r.stderr
    calls = mac.call_lines()
    assert not any(c.startswith("sudo -u postgres") for c in calls)   # gibt es auf dem Mac nicht
    assert any(c.startswith("psql") and "-h 127.0.0.1" in c for c in calls)


def test_db_password_kept_on_rerun(mac):
    mac.run("10-postgres.sh")
    first = (mac.config / "db.password").read_text()
    mac.run("10-postgres.sh", FAKE_ROLE_EXISTS="1", FAKE_DB_EXISTS="1")
    assert (mac.config / "db.password").read_text() == first


def test_db_postgres_down_fails(mac):
    r = mac.run("10-postgres.sh", FAKE_PG_DOWN="1")
    assert r.returncode != 0
    assert "PostgreSQL" in r.stdout + r.stderr


# ---------------------------------------------------------------- 20-agentlink.sh

def _backend(mac, **extra):
    mac.run("10-postgres.sh")
    return mac.run("20-agentlink.sh", **extra)


def test_backend_code_copied_and_venv_built(mac):
    r = _backend(mac)
    assert r.returncode == 0, r.stderr
    assert (mac.hl_prefix / "agentlink" / "backend" / "main.py").exists()
    assert (mac.hl_prefix / ".venv" / "bin" / "uvicorn").exists()
    assert any(c.startswith("pip install -r") and "requirements.txt" in c for c in mac.call_lines())


def test_backend_env_file_private_with_psycopg2_url(mac):
    r = _backend(mac)
    assert r.returncode == 0, r.stderr
    env = mac.config / "agentlink.env"
    assert stat.S_IMODE(env.stat().st_mode) == 0o600
    text = env.read_text()
    pw = (mac.config / "db.password").read_text().strip()
    assert f"DATABASE_URL=postgresql+psycopg2://agentlink:{pw}@127.0.0.1:5432/agentlink" in text
    assert "REDIS_URL=redis://127.0.0.1:6379" in text


def test_backend_plist_without_secrets_and_via_wrapper(mac):
    r = _backend(mac)
    assert r.returncode == 0, r.stderr
    raw = mac.plist("io.hydrahive.agentlink").read_text()
    pw = (mac.config / "db.password").read_text().strip()
    assert pw not in raw                         # plists sind für alle lesbar
    assert "DATABASE_URL" not in raw
    p = _plist(mac, "io.hydrahive.agentlink")
    _daemon_basics(p, "io.hydrahive.agentlink")
    args = p["ProgramArguments"]
    assert args[1].endswith("installer/lib/mac-agentlink-start.sh")
    assert args[2] == str(mac.config / "agentlink.env")
    assert args[3] == str(mac.hl_prefix / ".venv" / "bin" / "uvicorn")
    assert args[4:] == ["main:app", "--host", "127.0.0.1", "--port", "9000"]
    assert p["WorkingDirectory"] == str(mac.hl_prefix / "agentlink" / "backend")


def test_backend_venv_rebuilt_when_python_changed(mac):
    _backend(mac)
    mac.calls.write_text("")
    r = mac.run("20-agentlink.sh", FAKE_VENV_VERSION="3.11")
    assert r.returncode == 0, r.stderr
    assert any("-m venv --clear" in c for c in mac.call_lines())


def test_backend_health_failure_reported(mac):
    r = _backend(mac, FAKE_CURL_FAIL="1")
    assert r.returncode != 0
    assert "agentlink" in (r.stdout + r.stderr).lower()


def test_backend_owned_by_service_user(mac):
    r = _backend(mac)
    assert r.returncode == 0, r.stderr
    assert any(c.startswith("chown -R tester") and str(mac.hl_prefix) in c for c in mac.call_lines())


# ---------------------------------------------------------------- 30-frontend.sh

def test_frontend_built_for_subpath(mac):
    r = mac.run("30-frontend.sh")
    assert r.returncode == 0, r.stderr
    builds = [c for c in mac.call_lines() if c.startswith("npm exec -- vite build")]
    assert builds, mac.call_lines()
    assert "--base=/agentlink/" in builds[0]
    assert "API=/agentlink/api" in builds[0] and "WS=/agentlink/ws" in builds[0]
    assert any(c.startswith("npm ci") for c in mac.call_lines())
    assert (mac.hl_prefix / "frontend" / "dist").is_symlink()


def test_frontend_plist_localhost(mac):
    r = mac.run("30-frontend.sh")
    assert r.returncode == 0, r.stderr
    p = _plist(mac, "io.hydrahive.agentlink-frontend")
    _daemon_basics(p, "io.hydrahive.agentlink-frontend")
    args = p["ProgramArguments"]
    assert args[1:] == ["-m", "http.server", "9001", "--bind", "127.0.0.1"]
    assert p["WorkingDirectory"] == str(mac.hl_prefix / "frontend" / "dist")


# ---------------------------------------------------------------- install-mac.sh

def test_install_mac_refuses_linux(mac):
    r = mac.run(INSTALL_MAC, FAKE_UNAME="Linux")
    assert r.returncode != 0
    assert "macOS" in r.stdout + r.stderr


def test_install_mac_refuses_root(mac):
    r = mac.run(INSTALL_MAC, FAKE_UID="0")
    assert r.returncode != 0


def test_install_mac_runs_all_modules_in_order(mac):
    r = mac.run(INSTALL_MAC)
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    order = [out.index(m) for m in ("00-deps.sh", "10-postgres.sh", "20-agentlink.sh", "30-frontend.sh")]
    assert order == sorted(order)
    for label in ("io.hydrahive.redis", "io.hydrahive.agentlink", "io.hydrahive.agentlink-frontend"):
        assert mac.plist(label).exists()


def test_mac_modules_have_no_linux_tools():
    for script in [*MODULES.glob("*.sh"), INSTALL_MAC]:
        text = script.read_text()
        for bad in ("apt-get", "systemctl", "useradd", "sudo -u postgres", "/etc/systemd"):
            assert bad not in text, f"{script.name}: {bad}"
