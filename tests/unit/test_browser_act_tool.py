from __future__ import annotations

from pathlib import Path

import pytest

from agent_tools.tools import tool_browser_act
from e2e.harness.playwright_skip import require_playwright_chromium


def test_browser_act_rejects_unknown_action() -> None:
    result = tool_browser_act(base_url="http://127.0.0.1:9", action="hover")
    assert result.ok is False
    assert "unsupported" in result.llm_output


@pytest.mark.parametrize("html", ['<html lang="en"><body><h1>Hi</h1></body>'])
def test_browser_act_goto_expect_text(tmp_path: Path, html: str) -> None:
    require_playwright_chromium()

    import socket
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(html, encoding="utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    handler = partial(SimpleHTTPRequestHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        goto = tool_browser_act(base_url=base, action="goto", url="/")
        assert goto.ok is True
        expect = tool_browser_act(
            base_url=base,
            action="expect_text",
            selector="h1",
            value="Hi",
        )
        assert expect.ok is True
    finally:
        server.shutdown()
