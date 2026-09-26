from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "installer" / "modules" / "20-agentlink.sh"


def test_dangling_venv_forces_clear_rebuild() -> None:
    text = SCRIPT.read_text()

    assert '[ -d "${HL_PREFIX}/.venv" ]' in text
    assert '[ ! -x "$VENV_PY" ]' in text
    assert 'VENV_ARGS="--clear"' in text


def test_agentlink_stops_before_clear_rebuild() -> None:
    text = SCRIPT.read_text()

    stop_pos = text.index("systemctl stop agentlink.service")
    create_pos = text.index('"${HL_PYTHON_BIN}" -m venv $VENV_ARGS')
    assert stop_pos < create_pos


def _unit_template(text: str) -> str:
    start = text.index("cat > /etc/systemd/system/agentlink.service <<EOF")
    return text[start:text.index("\nEOF", start)]


def test_db_password_not_in_world_readable_unit() -> None:
    # /etc/systemd/system/*.service ist für alle lesbar, ebenso `systemctl show`.
    unit = _unit_template(SCRIPT.read_text())

    assert "DB_PWD" not in unit
    assert "Environment=DATABASE_URL" not in unit
    assert "EnvironmentFile=${HL_ENV_FILE}" in unit


def test_env_file_written_private_and_atomic() -> None:
    text = SCRIPT.read_text()
    write_pos = text.index('> "${HL_ENV_FILE}.tmp"')

    assert "umask 077" in text[text.rindex("(", 0, write_pos):write_pos]
    assert 'chmod 600 "${HL_ENV_FILE}.tmp"' in text
    assert text.index('mv -f "${HL_ENV_FILE}.tmp" "${HL_ENV_FILE}"') < text.index("systemctl restart agentlink.service")


def test_healthy_venv_does_not_unconditionally_stop_service() -> None:
    text = SCRIPT.read_text()
    clear_guard = text.index('if [ "$VENV_ARGS" = "--clear" ]')
    stop_pos = text.index("systemctl stop agentlink.service")

    assert clear_guard < stop_pos
