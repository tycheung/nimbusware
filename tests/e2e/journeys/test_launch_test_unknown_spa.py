from __future__ import annotations

import socket
from pathlib import Path

import pytest

from nimbusware_orchestrator.browser_controller import close_persistent_browser_url, run_ui_flow
from nimbusware_orchestrator.human_fidelity import run_human_fidelity_suite
from nimbusware_orchestrator.js_framework_detect import detect_js_framework
from nimbusware_orchestrator.launch_flow_resolver import load_workspace_ui_flow
from nimbusware_orchestrator.launch_test_stage import (
    build_launch_test_writer_prompt,
    run_launch_test_critique,
    run_launch_test_plan,
    run_launch_test_write,
)
from nimbusware_orchestrator.put_runtime import start_put_preview, stop_put_preview

_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_spa_unknown"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.e2e
def test_unknown_spa_launch_test_synthesis_critique_and_ui() -> None:
    if not _FIXTURE.is_dir():
        pytest.skip("fixture missing")
    assert detect_js_framework(_FIXTURE) == "spa_generic"
    prompt = build_launch_test_writer_prompt(_FIXTURE)
    assert "spa_generic" in prompt
    assert "Unknown SPA" in prompt

    port = _free_port()
    preview = start_put_preview(_FIXTURE, port, startup_timeout_seconds=8.0)
    assert preview.ok is True, preview.error
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"
    try:
        plan = run_launch_test_plan(_FIXTURE, preview_base_url=base_url)
        assert plan.passed is True
        write = run_launch_test_write(_FIXTURE, preview_base_url=base_url, flow_id="launch_draft")
        assert write.passed is True
        critique = run_launch_test_critique(_FIXTURE, flow_id="launch_draft")
        assert critique.passed is True, critique.findings

        try:
            import playwright  # noqa: F401
        except ImportError:
            pytest.skip("playwright not installed")

        ui_flow = load_workspace_ui_flow(_FIXTURE, "launch_draft")
        assert ui_flow is not None
        ui = run_ui_flow(base_url, ui_flow)
        assert ui.passed is True, ui.detail

        close_persistent_browser_url(base_url)
        fidelity = run_human_fidelity_suite(base_url)
        assert fidelity.passed is True, fidelity.detail
    finally:
        stop_put_preview(preview.handle)
