from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest

from orchestrator.browser_controller import close_persistent_browser_url, run_ui_flow
from orchestrator.factory.runtime import start_put_preview, stop_put_preview
from orchestrator.human_fidelity import run_human_fidelity_suite
from orchestrator.launch_flow_resolver import load_workspace_ui_flow
from orchestrator.launch_test_stage import (
    run_launch_test_critique,
    run_launch_test_plan,
    run_launch_test_write,
)

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]

_SPA_HTML = """<!DOCTYPE html>
<html lang="en"><body>
<div id="root">
  <h1>Launch preview</h1>
  <button type="button" data-testid="launch-go">Go</button>
</div>
</body></html>"""

_PUT_PREVIEW_PACKS: list[tuple[str, dict]] = [
    ("react_vite", {"react": "18", "vite": "5"}),
    ("vue_vite", {"vue": "3", "vite": "5"}),
    ("angular_cli", {"@angular/core": "17"}),
    ("svelte_vite", {"svelte": "4", "vite": "5"}),
    ("next_js", {"next": "14"}),
    ("nuxt", {"nuxt": "3"}),
    ("remix", {"@remix-run/react": "2"}),
]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _playwright_available() -> bool:
    from orchestrator.playwright_probe import playwright_chromium_launchable

    if playwright_chromium_launchable():
        return True
    if os.environ.get("NIMBUSWARE_FRAMEWORK_PACK_FIDELITY", "").strip() == "1":
        pytest.fail("playwright chromium required for framework pack fidelity gate")
    return False


def _seed_spa_workspace(tmp_path: Path, deps: dict) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": deps}), encoding="utf-8")
    (tmp_path / "index.html").write_text(_SPA_HTML, encoding="utf-8")


@pytest.mark.parametrize(("pack_id", "deps"), _PUT_PREVIEW_PACKS)
def test_framework_pack_put_preview_launch_cycle(
    tmp_path: Path,
    pack_id: str,
    deps: dict,
) -> None:
    _seed_spa_workspace(tmp_path, deps)
    port = _free_port()
    preview = start_put_preview(tmp_path, port, startup_timeout_seconds=8.0)
    assert preview.ok is True, preview.error
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"
    try:
        plan = run_launch_test_plan(tmp_path, preview_base_url=base_url)
        assert plan.passed is True
        assert plan.pack_id == pack_id

        write = run_launch_test_write(tmp_path, preview_base_url=base_url, flow_id="launch_draft")
        assert write.passed is True, write.findings

        critique = run_launch_test_critique(tmp_path, flow_id="launch_draft")
        assert critique.passed is True

        if not _playwright_available():
            return

        ui_flow = load_workspace_ui_flow(tmp_path, "launch_draft")
        if ui_flow is not None:
            ui = run_ui_flow(base_url, ui_flow)
            assert ui.passed is True, ui.detail

        close_persistent_browser_url(base_url)
        os.environ["NIMBUSWARE_MOUSE_FIDELITY"] = "1"
        fidelity = run_human_fidelity_suite(base_url)
        assert fidelity.passed is True, fidelity.detail
    finally:
        stop_put_preview(preview.handle)
