from __future__ import annotations

import socket
from pathlib import Path
from uuid import uuid4

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo
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

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]

PROMPT = "Build a todo app"


def _backlog_surface_ids(tree: dict) -> set[str]:
    surfaces: set[str] = set()
    for epic in tree.get("epics") or []:
        for feature in epic.get("features") or []:
            for sl in feature.get("slices") or []:
                raw = str(sl.get("surface_id") or "").strip()
                if raw:
                    surfaces.add(raw)
    return surfaces


def test_one_prompt_scope_to_fullstack_campaign_backlog(journey_client: JourneyClient, tmp_path) -> None:
    discover = journey_client.client.post(
        "/v1/chat/scope/discover",
        json={"business_prompt": PROMPT},
    )
    assert discover.status_code == 200, discover.text
    state = discover.json()["scope"]
    assert state["discovery_complete"] is False
    assert "web" in state.get("surfaces_likely", [])

    recommend = journey_client.client.post(
        "/v1/chat/scope/recommend",
        json={"business_prompt": PROMPT},
    )
    assert recommend.status_code == 200, recommend.text
    scope = recommend.json()["scope"]
    assert scope["discovery_complete"] is True
    manifest = scope["stack_manifest"]
    assert "api" in manifest["surfaces"]
    assert "web" in manifest["surfaces"]

    confirm = journey_client.client.post("/v1/chat/scope/confirm", json={"state": scope})
    assert confirm.status_code == 200, confirm.text
    confirmed = confirm.json()["scope"]
    assert confirmed.get("scope_confirmed") is True

    ws = copy_fixture_repo("tiny_python_app", tmp_path / "one-prompt-ws")
    journey_client.attach_project(ws)
    resp = journey_client.client.post(
        "/v1/campaigns",
        json={
            "project_id": journey_client.project_id,
            "requirements": {
                "business_prompt": PROMPT,
                "recommend_for_me": True,
                "stack_manifest": confirmed["stack_manifest"],
            },
            "autonomous": False,
            "workflow_profile": "campaign_fullstack",
        },
        headers=journey_client.admin_headers,
    )
    assert resp.status_code == 200, resp.text
    journey_client.run_id = str(resp.json()["run_id"])

    backlog = journey_client.client.get(f"/v1/campaigns/{journey_client.run_id}/backlog")
    assert backlog.status_code == 200, backlog.text
    surfaces = _backlog_surface_ids(backlog.json())
    assert "api" in surfaces
    assert "web" in surfaces

    progress = journey_client.client.get(
        f"/v1/runs/{journey_client.run_id}/maker-progress?simple=true",
    )
    assert progress.status_code == 200, progress.text
    body = progress.json()
    assert body.get("campaign_progress") is not None or body.get("status")


@pytest.mark.slow
def test_todo_fullstack_reference_api_and_ui_green() -> None:
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
        assert api_url and fe_url

        http = run_put_e2e_flow(api_url, "todo_api", workspace=_FIXTURE, require_playwright=False)
        assert http.verdict == "PASS"

        from e2e.harness.playwright_skip import require_playwright_chromium

        require_playwright_chromium()
        ui_flow = load_catalog_ui_flow("todo_api_ui")
        ui = run_ui_flow(fe_url, ui_flow)
        assert ui.passed is True, ui.detail
        close_persistent_browser_url(fe_url)
        fidelity = run_human_fidelity_suite(fe_url)
        assert fidelity.passed is True, fidelity.detail
    finally:
        stop_dev_environment(store, run_id, _FIXTURE)
