from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from nimbusware_orchestrator.browser_controller import close_persistent_browser_url, run_ui_flow
from nimbusware_orchestrator.human_fidelity import run_human_fidelity_suite
from nimbusware_orchestrator.launch_flow_resolver import load_workspace_ui_flow
from nimbusware_orchestrator.launch_test_stage import (
    run_launch_test_critique,
    run_launch_test_plan,
    run_launch_test_write,
)
from nimbusware_orchestrator.put_runtime import start_put_preview, stop_put_preview

_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_web_app"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _playwright_required() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        if os.environ.get("NIMBUSWARE_FRAMEWORK_PACK_FIDELITY", "").strip() == "1":
            pytest.fail("playwright required for framework pack fidelity gate")
        return False
    from nimbusware_orchestrator.playwright_probe import playwright_chromium_launchable

    if not playwright_chromium_launchable():
        if os.environ.get("NIMBUSWARE_FRAMEWORK_PACK_FIDELITY", "").strip() == "1":
            pytest.fail("playwright chromium required for framework pack fidelity gate")
        return False
    return True


@pytest.mark.e2e
def test_static_html_launch_test_plan_write_critique_and_fidelity() -> None:
    if not _FIXTURE.is_dir():
        pytest.skip("fixture missing")
    port = _free_port()
    preview = start_put_preview(_FIXTURE, port, startup_timeout_seconds=8.0)
    assert preview.ok is True, preview.error
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"
    try:
        plan = run_launch_test_plan(_FIXTURE, preview_base_url=base_url)
        assert plan.passed is True
        assert plan.pack_id == "static_html"

        write = run_launch_test_write(_FIXTURE, preview_base_url=base_url, flow_id="launch_draft")
        assert write.passed is True, write.findings

        critique = run_launch_test_critique(_FIXTURE, flow_id="launch_draft")
        assert critique.passed is True

        if not _playwright_required():
            return

        ui_flow = load_workspace_ui_flow(_FIXTURE, "launch_draft")
        if ui_flow is not None:
            ui = run_ui_flow(base_url, ui_flow)
            assert ui.passed is True, ui.detail

        close_persistent_browser_url(base_url)
        os.environ["NIMBUSWARE_MOUSE_FIDELITY"] = "1"
        fidelity = run_human_fidelity_suite(base_url)
        assert fidelity.passed is True, fidelity.detail
    finally:
        stop_put_preview(preview.handle)
