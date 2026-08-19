from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "installer" / "modules" / "30-frontend.sh"


def test_frontend_build_uses_pinned_npm_toolchain_instead_of_npx_shim() -> None:
    text = SCRIPT.read_text()

    assert "npm exec -- vite build" in text
    assert "npx vite build" not in text
