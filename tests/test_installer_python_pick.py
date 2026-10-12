"""Interpreterwahl für das AgentLink-venv (HydraHive-Spec python-314-umstieg).

Regel wie im Kern: das System-Python (`python3`), aufgelöst auf die
versionierte Datei, sofern mindestens 3.12; nur wenn das zu alt ist, ein
nachinstalliertes 3.13/3.12.

Anlass: Prod (Ubuntu 26.04, python3 = 3.14) lief weiter auf einem 3.12 aus
alten 24.04-Paketen, weil pick_python 3.12 fest bevorzugte. Der damalige Grund
(pydantic==2.9.2 ohne cp314-Wheel) ist seit den Versionsbereichen in
requirements.txt erledigt; wks197 läuft seit dem 03.10. auf 3.14.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "installer" / "modules" / "20-agentlink.sh"


def _pick_python_function() -> str:
    text = SCRIPT.read_text()
    start = text.index("pick_python() {")
    end = text.index("\n}\n", start) + 3
    return text[start:end]


def _fake(bin_dir: Path, name: str, version: str) -> Path:
    path = bin_dir / name
    path.write_text(f'#!/bin/sh\nprintf "%s\\n" {version}\n')
    path.chmod(0o755)
    return path


def _pick(bin_dir: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    script = f'set -euo pipefail\n{_pick_python_function()}\npick_python\n'
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HL_PYTHON_BIN_DIR": str(bin_dir), **extra},
    )


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    d = tmp_path / "bin"
    d.mkdir()
    return d


def test_prod_case_system_python_wins_over_leftover_312(bin_dir: Path) -> None:
    _fake(bin_dir, "python3.14", "3.14")
    _fake(bin_dir, "python3.12", "3.12")
    (bin_dir / "python3").symlink_to("python3.14")

    result = _pick(bin_dir)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(bin_dir / "python3.14")


def test_ubuntu_2404_keeps_312(bin_dir: Path) -> None:
    _fake(bin_dir, "python3.12", "3.12")
    (bin_dir / "python3").symlink_to("python3.12")

    assert _pick(bin_dir).stdout.strip() == str(bin_dir / "python3.12")


def test_too_old_system_python_falls_back(bin_dir: Path) -> None:
    _fake(bin_dir, "python3.10", "3.10")
    _fake(bin_dir, "python3.12", "3.12")
    (bin_dir / "python3").symlink_to("python3.10")

    assert _pick(bin_dir).stdout.strip() == str(bin_dir / "python3.12")


def test_no_suitable_python_fails(bin_dir: Path) -> None:
    _fake(bin_dir, "python3.10", "3.10")
    (bin_dir / "python3").symlink_to("python3.10")

    result = _pick(bin_dir)

    assert result.returncode != 0
    assert "3.12" in result.stderr


def test_override_still_wins(bin_dir: Path) -> None:
    _fake(bin_dir, "python3.14", "3.14")
    (bin_dir / "python3").symlink_to("python3.14")
    pinned = _fake(bin_dir, "python3.12", "3.12")

    assert _pick(bin_dir, HL_PYTHON=str(pinned)).stdout.strip() == str(pinned)


def test_deps_install_python_dev_for_source_builds() -> None:
    deps = (SCRIPT.parent / "00-deps.sh").read_text()

    assert "python3-dev" in deps
