from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType
from env import find_repo_root
from maker.intent.classifier import WorkType, classify_intent
from maker.intent.domain_keywords import extract_domain_keywords
from orchestrator.improvement.improvement_council import ImprovementTrack
from orchestrator.improvement.self_evolve_curriculum import (
    is_self_evolve_run,
    load_diverse_repos,
    load_harness_catalog,
    maybe_run_self_evolve_curriculum_tick,
    pick_next_harness,
    pick_next_repo,
    resolve_domain_candidates,
    run_research_domain_track,
    run_research_harness_track,
    run_try_diverse_repo_track,
    select_curriculum_track,
)
from orchestrator.profiles.autopilot_profiles import default_autopilot_level_for_work_type
from orchestrator.workflow.profiles import workflow_profile_dict


def test_classify_self_evolve_intent() -> None:
    result = classify_intent(
        "Self evolve and get better: study other agentic harnesses and try diverse projects",
    )
    assert result.work_type == WorkType.SELF_EVOLVE
    assert result.suggested_profile == "campaign_self_evolve"
    assert "keyword_self_evolve" in result.signals


def test_self_evolve_autopilot_defaults_to_10() -> None:
    assert default_autopilot_level_for_work_type("self_evolve") == 10


def test_campaign_self_evolve_workflow_parses() -> None:
    root = find_repo_root()
    doc = workflow_profile_dict(root, "campaign_self_evolve")
    assert doc.get("campaign", {}).get("enabled") is True
    se = doc.get("self_evolve") or {}
    assert se.get("enabled") is True
    mix = se.get("mix") or {}
    assert float(mix.get("research_harness", 0)) > 0
    assert float(mix.get("try_diverse_repo", 0)) > 0
    assert float(mix.get("research_domain", 0)) > 0
    assert float(mix.get("distill_artifacts", 0)) > 0


def test_harness_and_repo_catalogs_load() -> None:
    root = find_repo_root()
    harnesses = load_harness_catalog(root)
    repos = load_diverse_repos(root)
    assert len(harnesses) >= 5
    assert len(repos) >= 5
    assert pick_next_harness(root, Path(".")) is not None
    assert pick_next_repo(root, Path(".")) is not None


def test_select_curriculum_track_returns_mix_member(tmp_path: Path) -> None:
    track = select_curriculum_track(tmp_path)
    assert track in {
        ImprovementTrack.RESEARCH_HARNESS,
        ImprovementTrack.TRY_DIVERSE_REPO,
        ImprovementTrack.DISTILL_ARTIFACTS,
    }
    track_d = select_curriculum_track(tmp_path, keywords=["accounting software"])
    assert track_d in {
        ImprovementTrack.RESEARCH_HARNESS,
        ImprovementTrack.TRY_DIVERSE_REPO,
        ImprovementTrack.RESEARCH_DOMAIN,
        ImprovementTrack.DISTILL_ARTIFACTS,
    }


def test_extract_and_research_domain(tmp_path: Path) -> None:
    from agent_core.models.backlog import BacklogEpic, BacklogFeature, DeliveryBacklog

    kws = extract_domain_keywords(
        "Self evolve on accounting software — build domain knowledge",
    )
    assert any("accounting" in k for k in kws)

    ws = tmp_path / "ws"
    ws.mkdir()
    root = find_repo_root()
    candidates = resolve_domain_candidates(root, keywords=kws)
    assert candidates
    assert candidates[0].get("domain_id") == "accounting"

    run_id = uuid4()

    class _Store:
        _rows: list[dict] = []

        def list_run_events(self, _rid: str) -> list[dict]:
            return list(self._rows)

        def append(self, event) -> None:
            payload = getattr(event, "payload", None)
            self._rows.append(
                {
                    "event_type": event.event_type.value
                    if hasattr(event.event_type, "value")
                    else str(event.event_type),
                    "metadata": getattr(event, "metadata", {}) or {},
                    "payload": payload.model_dump(mode="json")
                    if hasattr(payload, "model_dump")
                    else {},
                },
            )

    store = _Store()
    backlog = DeliveryBacklog(
        campaign_id=str(uuid4()),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="Epic",
                features=(BacklogFeature(feature_id="f1", title="Feat", slices=()),),
            ),
        ),
    )
    store._rows.append(
        {
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {
                "workflow_profile": "campaign_self_evolve",
                "work_type": "self_evolve",
                "requirements": {
                    "business_prompt": "Self evolve on accounting software",
                    "domain_keywords": kws,
                },
                "project": {"workspace_path": str(ws)},
            },
            "payload": {},
        },
    )
    store._rows.append(
        {
            "event_type": EventType.DELIVERY_BACKLOG_GENERATED.value,
            "metadata": {},
            "payload": {"backlog": backlog.model_dump(mode="json")},
        },
    )
    out = run_research_domain_track(store, run_id, ws, repo_root=root, keywords=kws)
    assert out.get("target_id")
    assert (ws / "docs" / "learnings" / "domain").is_dir()
    stages = [(r.get("payload") or {}).get("stage_name") for r in store._rows]
    assert "research.domain" in stages


def test_research_harness_and_diverse_repo_tracks(tmp_path: Path) -> None:
    from uuid import uuid4 as _uuid4

    from agent_core.models.backlog import BacklogEpic, BacklogFeature, DeliveryBacklog

    ws = tmp_path / "ws"
    ws.mkdir()
    root = find_repo_root()
    run_id = uuid4()

    class _Store:
        _rows: list[dict] = []

        def list_run_events(self, _rid: str) -> list[dict]:
            return list(self._rows)

        def append(self, event) -> None:
            payload = getattr(event, "payload", None)
            self._rows.append(
                {
                    "event_type": event.event_type.value
                    if hasattr(event.event_type, "value")
                    else str(event.event_type),
                    "metadata": getattr(event, "metadata", {}) or {},
                    "payload": payload.model_dump(mode="json")
                    if hasattr(payload, "model_dump")
                    else {},
                },
            )

    store = _Store()
    backlog = DeliveryBacklog(
        campaign_id=str(_uuid4()),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="Epic",
                features=(BacklogFeature(feature_id="f1", title="Feat", slices=()),),
            ),
        ),
    )
    store._rows.append(
        {
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {
                "workflow_profile": "campaign_self_evolve",
                "work_type": "self_evolve",
                "project": {"workspace_path": str(ws)},
            },
            "payload": {},
        },
    )
    store._rows.append(
        {
            "event_type": EventType.DELIVERY_BACKLOG_GENERATED.value,
            "metadata": {},
            "payload": {"backlog": backlog.model_dump(mode="json")},
        },
    )
    assert is_self_evolve_run(store.list_run_events(str(run_id)))
    out_h = run_research_harness_track(store, run_id, ws, repo_root=root)
    assert out_h.get("harness_id")
    assert (ws / "docs" / "learnings").is_dir()
    out_r = run_try_diverse_repo_track(store, run_id, ws, repo_root=root)
    assert out_r.get("repo_id")
    stages = [(r.get("payload") or {}).get("stage_name") for r in store._rows]
    assert "research.harness" in stages
    assert "try.diverse_repo" in stages


def test_curriculum_tick_runs_at_autopilot_8(tmp_path: Path) -> None:
    from agent_core.models.backlog import BacklogEpic, BacklogFeature, DeliveryBacklog

    ws = tmp_path / "ws"
    ws.mkdir()
    root = find_repo_root()
    run_id = uuid4()

    class _Store:
        _rows: list[dict] = []

        def list_run_events(self, _rid: str) -> list[dict]:
            return list(self._rows)

        def append(self, event) -> None:
            payload = getattr(event, "payload", None)
            self._rows.append(
                {
                    "event_type": event.event_type.value
                    if hasattr(event.event_type, "value")
                    else str(event.event_type),
                    "metadata": getattr(event, "metadata", {}) or {},
                    "payload": payload.model_dump(mode="json")
                    if hasattr(payload, "model_dump")
                    else {},
                },
            )

    store = _Store()
    backlog = DeliveryBacklog(
        campaign_id=str(uuid4()),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="Epic",
                features=(BacklogFeature(feature_id="f1", title="Feat", slices=()),),
            ),
        ),
    )
    store._rows.append(
        {
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {
                "workflow_profile": "campaign_self_evolve",
                "work_type": "self_evolve",
                "autopilot_effective": {"level": 10, "name": "Continuous improve"},
                "project": {"workspace_path": str(ws)},
            },
            "payload": {"workflow_profile": "campaign_self_evolve"},
        },
    )
    store._rows.append(
        {
            "event_type": EventType.DELIVERY_BACKLOG_GENERATED.value,
            "metadata": {},
            "payload": {"backlog": backlog.model_dump(mode="json")},
        },
    )
    ok = maybe_run_self_evolve_curriculum_tick(
        store,
        run_id,
        ws,
        store.list_run_events(str(run_id)),
        slices_completed=2,
        repo_root=root,
    )
    assert ok is True
