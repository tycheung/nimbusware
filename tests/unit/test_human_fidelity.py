from __future__ import annotations

import socket
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from e2e.harness.playwright_skip import require_playwright_chromium
from orchestrator.factory.human_fidelity import (
    PERF_BUDGET_MS,
    run_axe_rules_check,
    run_axe_smoke,
    run_human_fidelity_suite,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _serve(tmp_path: Path, html: str, port: int) -> ThreadingHTTPServer:
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(html, encoding="utf-8")
    handler = partial(SimpleHTTPRequestHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@pytest.mark.parametrize(
    "html,expect_ok",
    [
        ('<html lang="en"><head><title>T</title></head><body><h1>Hi</h1></body>', True),
        ("<html><body></body>", False),
    ],
)
def test_axe_smoke_lang_and_heading(tmp_path: Path, html: str, expect_ok: bool) -> None:
    require_playwright_chromium()

    port = _free_port()
    server = _serve(tmp_path, html, port)
    try:
        result = run_axe_smoke(f"http://127.0.0.1:{port}")
        assert result.get("ok") is expect_ok
        if expect_ok:
            assert int(result.get("dcl_ms") or 0) <= PERF_BUDGET_MS + 500
    finally:
        server.shutdown()


def test_human_fidelity_static_site(tmp_path: Path) -> None:
    require_playwright_chromium()

    port = _free_port()
    html = '<html lang="en"><head><title>Welcome</title></head><body><h1>Welcome</h1></body>'
    server = _serve(tmp_path, html, port)
    try:
        suite = run_human_fidelity_suite(f"http://127.0.0.1:{port}")
        assert suite.passed is True
        kinds = {c.get("kind") for c in suite.checks}
        assert "keyboard_nav" in kinds
        assert "axe_rules" in kinds
    finally:
        server.shutdown()


def test_axe_rules_disabled_by_default(tmp_path: Path) -> None:
    require_playwright_chromium()

    port = _free_port()
    html = '<html lang="en"><head><title>T</title></head><body><h1>Hi</h1></body>'
    server = _serve(tmp_path, html, port)
    try:
        result = run_axe_rules_check(f"http://127.0.0.1:{port}")
        assert result.get("ok") is True
        assert result.get("detail") == "axe_disabled"
    finally:
        server.shutdown()
