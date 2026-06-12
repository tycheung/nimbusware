from __future__ import annotations

import socket
from pathlib import Path
from uuid import uuid4

import pytest

from nimbusware_orchestrator.browser_controller import close_persistent_browser_url, run_ui_flow
from nimbusware_orchestrator.dev_env_supervisor import (
    frontend_base_url,
    start_dev_environment,
    stop_dev_environment,
)
from nimbusware_orchestrator.human_fidelity import run_human_fidelity_suite
from nimbusware_orchestrator.launch_flow_resolver import load_catalog_ui_flow
from nimbusware_orchestrator.put_e2e_runner import run_put_e2e_flow
from nimbusware_store.memory import InMemoryEventStore

_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_todo_fullstack"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.e2e
@pytest.mark.slow
def test_todo_fullstack_http_and_ui_launch() -> None:
    if not _FIXTURE.is_dir():
        pytest.skip("fixture missing")
    store = InMemoryEventStore()
    run_id = uuid4()
    port = _free_port()
    started = start_dev_environment(store, run_id, _FIXTURE, port=port)
    assert started.ok is True, started.error
    try:
        session = started.session
        assert session is not None
        api_url = session.api_base_url or session.base_url
        fe_url = frontend_base_url(_FIXTURE)
        assert api_url
        assert fe_url

        http = run_put_e2e_flow(api_url, "todo_api", workspace=_FIXTURE, require_playwright=False)
        assert http.verdict == "PASS"

        try:
            import playwright  # noqa: F401
        except ImportError:
            pytest.skip("playwright not installed")

        ui_flow = load_catalog_ui_flow("todo_api_ui")
        ui = run_ui_flow(fe_url, ui_flow)
        assert ui.passed is True, ui.detail

        close_persistent_browser_url(fe_url)
        fidelity = run_human_fidelity_suite(fe_url)
        assert fidelity.passed is True, fidelity.detail
    finally:
        stop_dev_environment(store, run_id, _FIXTURE)
