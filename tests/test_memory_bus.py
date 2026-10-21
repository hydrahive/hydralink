"""Nachrichtenkanal ohne Redis (REDIS_URL=memory://) – für macOS.

Befund 21.10.2026 auf dem Intel-Test-Mac: Homebrew hat für Redis keine fertigen Intel-Pakete mehr
und baut es samt LLVM und Rust aus dem Quellcode (Stunden). AgentLink nutzt Redis nur als
Pub/Sub innerhalb desselben (einzigen) uvicorn-Prozesses: publish → Listener → WebSocket-Broadcast.
Mit memory:// geht die Nachricht direkt an denselben Verteiler – gleiches Verhalten ohne Redis.
"""
from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "agentlink" / "backend"


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


def _load(monkeypatch, redis_url: str):
    monkeypatch.syspath_prepend(str(BACKEND))
    monkeypatch.setenv("DATABASE_URL", "postgresql://agentlink:x@127.0.0.1:5432/agentlink")
    monkeypatch.setenv("REDIS_URL", redis_url)
    for mod in ("main", "database"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("main")
    return main


@pytest.fixture
def memory_main(monkeypatch):
    main = _load(monkeypatch, "memory://")
    yield main
    for mod in ("main", "database"):
        sys.modules.pop(mod, None)


def _subscribe(main, channel: str) -> FakeWS:
    ws = FakeWS()
    main.manager.active_connections.setdefault(channel, set()).add(ws)
    return ws


def test_memory_mode_detected(memory_main):
    assert memory_main.MEMORY_BUS is True


def test_redis_mode_unchanged(monkeypatch):
    main = _load(monkeypatch, "redis://127.0.0.1:6379")
    try:
        assert main.MEMORY_BUS is False
    finally:
        for mod in ("main", "database"):
            sys.modules.pop(mod, None)


def test_publish_reaches_all_channel(memory_main):
    ws = _subscribe(memory_main, "all")
    asyncio.run(memory_main.publish_to_redis("agentlink:states", {"type": "state.created", "id": "s1"}))
    assert len(ws.sent) == 1
    assert '"state.created"' in ws.sent[0]


def test_handoff_reaches_target_agent(memory_main):
    """Kern: ask_agent wartet auf handoff_received im Kanal agent:<id>."""
    target = _subscribe(memory_main, "agent:hydrahive")
    other = _subscribe(memory_main, "agent:jemand")
    msg = {"type": "handoff_received", "to_agent": "hydrahive", "state_id": "s1"}
    asyncio.run(memory_main.publish_to_redis("agentlink:agent:hydrahive", msg))
    assert len(target.sent) == 1
    assert other.sent == []


def test_non_handoff_not_sent_to_agent_channel(memory_main):
    target = _subscribe(memory_main, "agent:hydrahive")
    asyncio.run(memory_main.publish_to_redis("agentlink:events", {"type": "state.claimed", "to_agent": "hydrahive"}))
    assert target.sent == []


def test_listener_does_not_connect_in_memory_mode(memory_main):
    # Ohne Redis darf der Listener nicht endlos Verbindungen versuchen (Log-Flut, Backoff-Schleife).
    asyncio.run(asyncio.wait_for(memory_main.redis_listener(), timeout=2))
    assert memory_main.redis_client is None


def test_health_reports_memory(memory_main):
    class _Q:
        def count(self):
            return 0

    class _DB:
        def query(self, *_):
            return _Q()

    res = asyncio.run(memory_main.health(db=_DB()))
    assert res["redis"] == "memory"
