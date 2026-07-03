from __future__ import annotations

import socket
from pathlib import Path
from uuid import uuid4

import pytest

from e2e.harness.playwright_skip import require_playwright_chromium
from orchestrator.dev_env.supervisor import start_dev_environment, stop_dev_environment
from orchestrator.human_fidelity import run_human_fidelity_suite
from store.memory import InMemoryEventStore


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.e2e
def test_dev_env_session_start_status_stop(tmp_path: Path) -> None:
    ws = tmp_path / "tiny"
    ws.mkdir()
    (ws / "index.html").write_text(
        '<html lang="en"><head><title>Welcome</title></head>'
        "<body><h1>Welcome</h1><a href='contact.html'>Contact</a></body></html>",
        encoding="utf-8",
    )
    (ws / "contact.html").write_text(
        '<html lang="en"><head><title>Contact</title></head><body><form></form></body></html>',
        encoding="utf-8",
    )
    store = InMemoryEventStore()
    run_id = uuid4()
    port = _free_port()
    started = start_dev_environment(store, run_id, ws, port=port)
    assert started.ok is True, started.error
    try:
        require_playwright_chromium()
        fidelity = run_human_fidelity_suite(started.session.base_url if started.session else "")
        assert fidelity.passed is True
    finally:
        stop_dev_environment(store, run_id, ws)
