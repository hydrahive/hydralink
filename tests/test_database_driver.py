"""Datenbanktreiber: AgentLink installiert nur psycopg2.

Seit SQLAlchemy 2.1 bedeutet ``postgresql://`` den Treiber psycopg (Version 3).
Ohne festen Treiber bricht das Backend nach jeder Neuinstallation mit
``No module named 'psycopg'`` ab (gefunden am 03.10.2026 auf tills-master-wks).
"""
import importlib
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "agentlink" / "backend"
INSTALLER = Path(__file__).resolve().parents[1] / "installer" / "modules" / "20-agentlink.sh"


@pytest.fixture
def database(monkeypatch):
    monkeypatch.syspath_prepend(str(BACKEND))
    monkeypatch.setenv("DATABASE_URL", "postgresql://agentlink:geheim@127.0.0.1:5432/agentlink")
    sys.modules.pop("database", None)
    mod = importlib.import_module("database")
    yield mod
    sys.modules.pop("database", None)


@pytest.mark.parametrize("raw, expected", [
    ("postgresql://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
    ("postgres://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
    ("postgresql+psycopg2://u@h/db", "postgresql+psycopg2://u@h/db"),
    ("postgresql+psycopg://u@h/db", "postgresql+psycopg://u@h/db"),   # bewusst gesetzt → so lassen
    ("sqlite:///tmp/x.db", "sqlite:///tmp/x.db"),
])
def test_engine_url_pins_psycopg2(database, raw, expected):
    assert database.engine_url(raw) == expected


def test_module_imports_with_plain_postgresql_url(database):
    """Der eigentliche Absturz: Import von database.py mit ``postgresql://`` aus der env-Datei."""
    assert database.engine.dialect.driver == "psycopg2"


def test_password_with_special_chars_survives(database):
    raw = "postgresql://agentlink:p%40ss%2Fw:rd@127.0.0.1:5432/agentlink"
    assert database.engine_url(raw) == raw.replace("postgresql://", "postgresql+psycopg2://", 1)


def test_installer_writes_explicit_driver():
    text = INSTALLER.read_text()
    assert "DATABASE_URL=postgresql+psycopg2://" in text
    assert "DATABASE_URL=postgresql://" not in text
