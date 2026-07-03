from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from orchestrator.improvement_council import ImprovementTrack, run_improvement_council
from research.bundle_promotion import write_stitch_catalog_candidate
from research.pattern_index import append_pattern_index, pattern_index_path
from research.stitch_manifests import persist_transplant_manifest
from research.stitch_models import TransplantManifest


def _healthy_repo(ws: Path) -> None:
    pkg = ws / "src"
    pkg.mkdir(parents=True)
    for name in ("app.py", "util.py", "routes.py"):
        (pkg / name).write_text("x = 1\n", encoding="utf-8")


def test_council_votes_research_transplant_for_pending_candidate(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    _healthy_repo(ws)
    run_id = uuid4()
    manifest = TransplantManifest(
        manifest_id="manifest-council-test",
        source_kind="stub",
        source_tree_hash="stub:council01",
        file_paths=("src/transplant.py",),
        license_paths=("LICENSE",),
        required_env_vars=(),
    )
    persist_transplant_manifest(ws, manifest)
    write_stitch_catalog_candidate(
        ws,
        run_id=run_id,
        manifest_id=manifest.manifest_id,
        files_added=["src/transplant.py"],
        bundle_hints={"title": "Council transplant"},
    )
    council = run_improvement_council(ws)
    tracks = {v.track for v in council.votes}
    assert ImprovementTrack.RESEARCH_TRANSPLANT in tracks
    assert council.selected == ImprovementTrack.RESEARCH_TRANSPLANT


def test_council_votes_research_transplant_for_pattern_index(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    _healthy_repo(ws)
    append_pattern_index(
        ws,
        pattern_id="pat-1",
        repo_url="https://github.com/example/auth-kit",
        paths=["lib/auth.py"],
        license_name="MIT",
        embedding_ref="emb-1",
    )
    assert pattern_index_path(ws).is_file()
    council = run_improvement_council(ws)
    tracks = {v.track for v in council.votes}
    assert ImprovementTrack.RESEARCH_TRANSPLANT in tracks


def test_run_research_transplant_skips_without_source(tmp_path: Path) -> None:
    from env import find_repo_root
    from orchestrator.slice_cycle_integration import run_research_transplant_track

    ws = tmp_path / "proj"
    _healthy_repo(ws)
    (ws / ".nimbusware" / "research").mkdir(parents=True)
    run_id = uuid4()

    class _Store:
        repo_root = ws
        _rows: list[dict] = []

        def list_run_events(self, _rid: str) -> list[dict]:
            return list(self._rows)

        def append(self, event) -> None:
            self._rows.append(
                {
                    "event_type": event.event_type.value,
                    "metadata": getattr(event, "metadata", None),
                    "payload": event.payload.model_dump(mode="json")
                    if hasattr(event.payload, "model_dump")
                    else {},
                },
            )

    store = _Store()
    store._rows.append(
        {
            "event_type": "run.created",
            "metadata": {"project": {"workspace_path": str(ws)}},
        },
    )
    applied = run_research_transplant_track(
        store,
        run_id,
        ws,
        repo_root=find_repo_root(),
    )
    assert applied is False
    skipped = [
        r
        for r in store._rows
        if (r.get("payload") or {}).get("stage_name") == "research.transplant.skipped"
    ]
    assert skipped
    assert not any(r["event_type"] == "research.brief.emitted" for r in store._rows)


def test_run_research_transplant_uses_catalog_url(tmp_path: Path) -> None:
    from env import find_repo_root
    from orchestrator.slice_cycle_integration import run_research_transplant_track

    ws = tmp_path / "proj"
    _healthy_repo(ws)
    (ws / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    run_id = uuid4()
    manifest = TransplantManifest(
        manifest_id="manifest-track-test",
        source_kind="stub",
        source_tree_hash="stub:track01",
        file_paths=("src/transplant.py",),
        license_paths=("LICENSE",),
        required_env_vars=(),
    )
    persist_transplant_manifest(ws, manifest)
    out = write_stitch_catalog_candidate(
        ws,
        run_id=run_id,
        manifest_id=manifest.manifest_id,
        files_added=["src/transplant.py"],
        bundle_hints={"title": "Track transplant"},
    )

    class _Store:
        repo_root = ws
        _rows: list[dict] = []

        def list_run_events(self, _rid: str) -> list[dict]:
            return list(self._rows)

        def append(self, event) -> None:
            self._rows.append(
                {
                    "event_type": event.event_type.value,
                    "metadata": getattr(event, "metadata", None),
                    "payload": event.payload.model_dump(mode="json")
                    if hasattr(event.payload, "model_dump")
                    else {},
                },
            )

    store = _Store()
    nimbus_root = find_repo_root()
    store._rows.append(
        {
            "event_type": "run.created",
            "metadata": {"project": {"workspace_path": str(ws)}},
        },
    )
    applied = run_research_transplant_track(
        store, run_id, ws, repo_root=nimbus_root
    )  # configs only
    assert applied is True
    brief_events = [r for r in store._rows if r["event_type"] == "research.brief.emitted"]
    assert brief_events
    sources = brief_events[0]["payload"].get("sources") or []
    assert sources
    assert str(sources[0]["url"]).startswith("catalog://")
    assert out["candidate_id"] in str(sources[0]["url"])
