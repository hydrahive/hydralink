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


def test_healthy_venv_does_not_unconditionally_stop_service() -> None:
    text = SCRIPT.read_text()
    clear_guard = text.index('if [ "$VENV_ARGS" = "--clear" ]')
    stop_pos = text.index("systemctl stop agentlink.service")

    assert clear_guard < stop_pos
