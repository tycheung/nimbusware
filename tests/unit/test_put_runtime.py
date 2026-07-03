from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.interaction_surface_map import (
    InteractionSurfaceMap,
    coverage_pct,
    discover_surfaces_from_html,
    discover_surfaces_from_openapi,
    discover_surfaces_static,
)
from orchestrator.put_runtime import (
    collect_put_artifacts,
    detect_put_stack,
    put_runtime_summary,
    start_put_preview,
    stop_put_preview,
)


def test_detect_put_stack_fastapi(tmp_path: Path) -> None:
    ws = tmp_path / "api"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi"]\n', encoding="utf-8")
    assert detect_put_stack(ws) == "fastapi"


def test_detect_put_stack_static(tmp_path: Path) -> None:
    ws = tmp_path / "site"
    ws.mkdir()
    (ws / "index.html").write_text("<html><body>Hello</body></html>", encoding="utf-8")
    assert detect_put_stack(ws) == "static"


def test_detect_put_stack_spa_package_json(tmp_path: Path) -> None:
    ws = tmp_path / "spa"
    ws.mkdir()
    (ws / "package.json").write_text('{"dependencies":{"react":"^18.0.0"}}', encoding="utf-8")
    assert detect_put_stack(ws) == "spa"


def test_detect_put_stack_spa_index_html(tmp_path: Path) -> None:
    ws = tmp_path / "vite"
    ws.mkdir()
    (ws / "index.html").write_text(
        '<div id="root"></div><script type="module" src="/src/main.tsx">', encoding="utf-8"
    )
    assert detect_put_stack(ws) == "spa"


def test_detect_put_stack_unknown(tmp_path: Path) -> None:
    ws = tmp_path / "empty"
    ws.mkdir()
    assert detect_put_stack(ws) == "unknown"


def test_start_put_preview_static_site(tmp_path: Path) -> None:
    ws = tmp_path / "preview"
    ws.mkdir()
    (ws / "index.html").write_text("<html><body>preview ok</body></html>", encoding="utf-8")
    port = 18765
    result = start_put_preview(ws, port, startup_timeout_seconds=10.0)
    try:
        assert result.ok is True
        assert result.handle is not None
        assert result.handle.stack == "static"
        assert result.probe.get("reachable") is True
        assert result.probe.get("ok") is True
    finally:
        stop_put_preview(result.handle)


def test_collect_put_artifacts_writes_manifest(tmp_path: Path) -> None:
    ws = tmp_path / "fail"
    ws.mkdir()
    artifacts = collect_put_artifacts(ws, None, reason="startup_timeout", stack="static")
    manifest_path = Path(artifacts["manifest_path"])
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["reason"] == "startup_timeout"
    assert manifest["stack"] == "static"


def test_put_runtime_summary(tmp_path: Path) -> None:
    ws = tmp_path / "summary"
    ws.mkdir()
    (ws / "index.html").write_text("<html></html>", encoding="utf-8")
    summary = put_runtime_summary(ws)
    assert summary["stack"] == "static"
    assert "preview_command" in summary


def test_discover_surfaces_from_openapi() -> None:
    spec = {
        "paths": {
            "/health": {"get": {"summary": "Health check"}},
            "/items": {
                "get": {"operationId": "listItems"},
                "post": {},
            },
        },
    }
    surfaces = discover_surfaces_from_openapi(spec)
    ids = {s.surface_id for s in surfaces}
    assert "openapi:GET:/health" in ids
    assert "openapi:POST:/items" in ids


def test_discover_surfaces_from_html_links() -> None:
    html = '<a href="/docs">Docs</a><a href="https://example.com/x">Ext</a><a href="#skip">Skip</a>'
    surfaces = discover_surfaces_from_html(html)
    paths = {s.path for s in surfaces}
    assert "/docs" in paths
    assert "https://example.com/x" in paths
    assert "#skip" not in paths


def test_discover_surfaces_static_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "ism"
    ws.mkdir()
    (ws / "openapi.json").write_text(
        json.dumps({"paths": {"/api/tags": {"get": {"summary": "Tags"}}}}),
        encoding="utf-8",
    )
    (ws / "index.html").write_text('<a href="/about">About</a>', encoding="utf-8")
    ism = discover_surfaces_static(ws)
    assert ism.source == "openapi+html"
    assert len(ism.surfaces) == 2


def test_coverage_pct_helper() -> None:
    ism = InteractionSurfaceMap.from_dict(
        {
            "version": "1",
            "surfaces": [
                {"surface_id": "a", "kind": "link", "path": "/a"},
                {"surface_id": "b", "kind": "link", "path": "/b"},
                {"surface_id": "c", "kind": "link", "path": "/c"},
            ],
        },
    )
    assert coverage_pct(ism, {"/a", "/c"}) == pytest.approx(66.67)
    assert coverage_pct(ism, set()) == 0.0
    assert coverage_pct(InteractionSurfaceMap(), set()) == 0.0


def test_campaign_driver_tick_includes_put_stack_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from env import find_repo_root
    from orchestrator.campaign import (
        campaign_policy_from_workflow,
        emit_campaign_created,
    )
    from orchestrator.campaign_driver import campaign_driver_tick
    from orchestrator.pipeline import make_dev_orchestrator

    monkeypatch.setenv("NIMBUSWARE_MICRO_SLICE_COUNT", "1")
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    policy = campaign_policy_from_workflow(repo, "campaign_micro_slice")
    emit_campaign_created(store, run_id, workflow_profile="campaign_micro_slice", policy=policy)

    ws = tmp_path / "campaign_ws"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi"]\n', encoding="utf-8")

    campaign_driver_tick(orch, run_id, workspace=ws)
    rows = store.list_run_events(str(run_id))
    tick_rows = [
        r
        for r in rows
        if isinstance(r.get("payload"), dict) and r["payload"].get("stage_name") == "campaign.tick"
    ]
    assert tick_rows
    meta = tick_rows[0].get("metadata") or {}
    assert "put_stack=fastapi" in str(meta.get("note", ""))
