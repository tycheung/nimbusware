"""Expanded self-evolution tests: API handlers, track executors, theater, prompt goldens."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from api.routes.runs.evolution import (
    EvolutionPromoteBody,
    get_run_evolution,
    post_run_evolution_promote,
)
from orchestrator.improvement.evolution_ledger import (
    EvolutionLayer,
    EvolutionPhase,
    emit_evolution_event,
    evolution_timeline_from_rows,
)
from orchestrator.improvement.evolution_loop import maybe_auto_promote_prompts
from orchestrator.improvement.improvement_council import ImprovementTrack
from orchestrator.improvement.prompt_evolution import (
    load_promoted_overlay_text,
    promote_or_reject_prompt,
    propose_overlay_from_learning,
    score_prompt_proposal,
)
from orchestrator.improvement.skill_evolution import (
    list_evolved_skill_briefs,
    propose_skill_from_fingerprint,
    record_skill_outcome,
)
from orchestrator.slice.cycle_improvement import execute_improvement_track
from projections.builders.run_theater import build_run_theater_messages


class _Store:
    def __init__(self, ws: Path | None = None) -> None:
        self.repo_root = ws
        self._rows: list[dict] = []

    def list_run_events(self, _rid: str) -> list[dict]:
        return list(self._rows)

    def append(self, event: object) -> None:
        if hasattr(event, "model_dump"):
            dumped = event.model_dump(mode="json")  # type: ignore[union-attr]
            self._rows.append(dumped)
            return
        payload = getattr(event, "payload", None)
        self._rows.append(
            {
                "event_type": getattr(event, "event_type", EventType.STAGE_PASSED).value
                if hasattr(getattr(event, "event_type", None), "value")
                else str(getattr(event, "event_type", "")),
                "event_id": str(getattr(event, "event_id", uuid4())),
                "run_id": str(getattr(event, "run_id", uuid4())),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "metadata": getattr(event, "metadata", None) or {},
                "payload": payload.model_dump(mode="json")
                if hasattr(payload, "model_dump")
                else (payload or {}),
            },
        )


def _seed_run(store: _Store, run_id, ws: Path, *, with_backlog: bool = False) -> None:
    meta: dict = {"project": {"workspace_path": str(ws), "id": str(uuid4()), "name": "t"}}
    store._rows.append(
        {
            "event_type": EventType.RUN_CREATED.value,
            "event_id": str(uuid4()),
            "run_id": str(run_id),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "metadata": meta,
            "payload": {},
        },
    )
    if with_backlog:
        from agent_core.models.backlog import BacklogEpic, BacklogFeature, DeliveryBacklog

        backlog = DeliveryBacklog(
            campaign_id=str(uuid4()),
            epics=(
                BacklogEpic(
                    epic_id="e1",
                    title="Epic",
                    features=(
                        BacklogFeature(feature_id="f1", title="Feat", slices=()),
                    ),
                ),
            ),
        )
        store._rows.append(
            {
                "event_type": EventType.DELIVERY_BACKLOG_GENERATED.value,
                "event_id": str(uuid4()),
                "run_id": str(run_id),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {},
                "payload": {"backlog": backlog.model_dump(mode="json")},
            },
        )


def _stage_names(store: _Store) -> list[str]:
    out: list[str] = []
    for row in store._rows:
        payload = row.get("payload") or {}
        sn = payload.get("stage_name")
        if sn:
            out.append(str(sn))
    return out


# --- API handlers ---


def test_evolution_api_get_404() -> None:
    store = _Store()
    with pytest.raises(HTTPException) as ei:
        get_run_evolution(uuid4(), store)  # type: ignore[arg-type]
    assert ei.value.status_code == 404


def test_evolution_api_get_and_promote(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    store = _Store(ws)
    run_id = uuid4()
    _seed_run(store, run_id, ws)
    draft = propose_overlay_from_learning(
        store,
        run_id,
        ws,
        excerpt="golden regression: NameError on helper",
    )
    assert draft is not None
    aid = draft["artifact_id"]
    body = get_run_evolution(run_id, store)  # type: ignore[arg-type]
    assert body["count"] >= 1
    assert body["pending"]
    assert any(p.get("artifact_id") == aid for p in body["pending"])

    out = post_run_evolution_promote(
        run_id,
        EvolutionPromoteBody(artifact_id=aid, promote=True),
        store,  # type: ignore[arg-type]
    )
    assert any(e.get("phase") == "promoted" for e in (out.get("timeline") or []))
    assert load_promoted_overlay_text(ws).strip()


def test_evolution_api_reject(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    store = _Store(ws)
    run_id = uuid4()
    _seed_run(store, run_id, ws)
    draft = propose_overlay_from_learning(store, run_id, ws, excerpt="reject me")
    assert draft is not None
    out = post_run_evolution_promote(
        run_id,
        EvolutionPromoteBody(artifact_id=draft["artifact_id"], promote=False),
        store,  # type: ignore[arg-type]
    )
    assert any(e.get("phase") == "rejected" for e in (out.get("timeline") or []))


# --- Prompt golden / soft-gate regression ---


def test_prompt_soft_gate_rejects_p0(tmp_path: Path) -> None:
    store = _Store()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    draft = propose_overlay_from_learning(store, run_id, ws, excerpt="security hole")
    assert draft is not None
    aid = draft["artifact_id"]
    score_prompt_proposal(
        store,
        run_id,
        artifact_id=aid,
        gate_pass_delta=1.0,
        has_p0_security=True,
    )
    timeline = evolution_timeline_from_rows(store.list_run_events(str(run_id)))
    scored = [e for e in timeline if e["phase"] == "scored"]
    assert scored
    assert scored[-1]["detail"].get("eligible") is False


def test_prompt_soft_gate_rejects_negative_delta(tmp_path: Path) -> None:
    store = _Store()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    draft = propose_overlay_from_learning(store, run_id, ws, excerpt="worse")
    assert draft is not None
    score_prompt_proposal(
        store,
        run_id,
        artifact_id=draft["artifact_id"],
        gate_pass_delta=-0.5,
        has_p0_security=False,
    )
    scored = [
        e
        for e in evolution_timeline_from_rows(store.list_run_events(str(run_id)))
        if e["phase"] == "scored"
    ]
    assert scored[-1]["detail"].get("eligible") is False


def test_maybe_auto_promote_respects_autopilot_and_enterprise(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    store = _Store(ws)
    run_id = uuid4()
    draft = propose_overlay_from_learning(store, run_id, ws, excerpt="auto")
    assert draft is not None
    aid = draft["artifact_id"]
    score_prompt_proposal(
        store,
        run_id,
        artifact_id=aid,
        gate_pass_delta=0.2,
        has_p0_security=False,
    )
    assert maybe_auto_promote_prompts(store, run_id, ws, autopilot_level=7) == []
    assert maybe_auto_promote_prompts(
        store,
        run_id,
        ws,
        autopilot_level=9,
        enterprise=True,
    ) == []
    promoted = maybe_auto_promote_prompts(store, run_id, ws, autopilot_level=8)
    assert aid in promoted


def test_skill_shelved_on_p0(tmp_path: Path) -> None:
    store = _Store()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    entry = propose_skill_from_fingerprint(
        store,
        run_id,
        ws,
        fingerprint="shelvefp001",
        excerpt="p0",
    )
    assert entry is not None
    sid = str(entry["id"])
    record_skill_outcome(store, run_id, ws, skill_ids=[sid], gate_passed=True)
    record_skill_outcome(
        store,
        run_id,
        ws,
        skill_ids=[sid],
        gate_passed=False,
        has_p0=True,
    )
    briefs = list_evolved_skill_briefs(ws)
    assert all(str(b.get("id")) != sid or str(b.get("status")) == "shelved" for b in briefs) or not any(
        str(b.get("id")) == sid for b in briefs
    )


# --- Track executors ---


@pytest.mark.parametrize(
    ("track", "stage_substr"),
    [
        (ImprovementTrack.IMPROVE_COVERAGE, "improve.coverage"),
        (ImprovementTrack.SECURITY_HARDEN, "council.security_harden"),
        (ImprovementTrack.PERFORMANCE_TUNE, "council.performance_tune"),
        (ImprovementTrack.DOCUMENT_CONTRACTS, "council.document_contracts"),
        (ImprovementTrack.DISTILL_ARTIFACTS, "distill.artifacts"),
        (ImprovementTrack.DISCOVER_FEATURES, "discover.features"),
    ],
)
def test_execute_improvement_track_emits_stage(
    tmp_path: Path,
    track: ImprovementTrack,
    stage_substr: str,
) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "mod.py").write_text("x = 1\n", encoding="utf-8")
    store = _Store(ws)
    run_id = uuid4()
    _seed_run(store, run_id, ws, with_backlog=True)
    execute_improvement_track(store, run_id, ws, track, repo_root=ws)
    names = _stage_names(store)
    assert any(stage_substr in n for n in names), names
    if track in {
        ImprovementTrack.IMPROVE_COVERAGE,
        ImprovementTrack.SECURITY_HARDEN,
        ImprovementTrack.PERFORMANCE_TUNE,
        ImprovementTrack.DOCUMENT_CONTRACTS,
        ImprovementTrack.DISCOVER_FEATURES,
    }:
        # Backlog queue should revise when seeded
        assert EventType.DELIVERY_BACKLOG_REVISED.value in [
            r.get("event_type") for r in store._rows
        ]


def test_variant_experiment_skips_when_l1_pending(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "a.py").write_text("x=1\n", encoding="utf-8")
    store = _Store(ws)
    run_id = uuid4()
    _seed_run(store, run_id, ws)
    propose_overlay_from_learning(store, run_id, ws, excerpt="pending overlay")
    execute_improvement_track(
        store,
        run_id,
        ws,
        ImprovementTrack.VARIANT_EXPERIMENT,
        repo_root=ws,
    )
    assert "variant.arena.skipped" in _stage_names(store)


def test_architecture_revise_emits_maintenance(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    store = _Store(ws)
    run_id = uuid4()
    _seed_run(store, run_id, ws, with_backlog=True)
    execute_improvement_track(
        store,
        run_id,
        ws,
        ImprovementTrack.ARCHITECTURE_REVISE,
        repo_root=ws,
    )
    types = [r.get("event_type") for r in store._rows]
    assert EventType.MAINTENANCE_ARCHITECTURE_STARTED.value in types
    assert EventType.MAINTENANCE_ARCHITECTURE_PASSED.value in types


# --- Theater ---


def test_theater_renders_evolution_promoted_and_rejected() -> None:
    run_id = uuid4()
    rows = []
    for phase, severity_hint in (
        (EvolutionPhase.PROPOSED, "info"),
        (EvolutionPhase.PROMOTED, "pass"),
        (EvolutionPhase.REJECTED, "warn"),
    ):
        ev = StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "evolution": {
                    "phase": phase.value,
                    "layer": EvolutionLayer.PROMPT.value,
                    "artifact_id": f"art-{phase.value}",
                    "detail": {},
                },
            },
            payload=StagePassedPayload(
                stage_name=f"evolution.{phase.value}",
                duration_ms=0,
            ),
        ).model_dump(mode="json")
        ev["store_seq"] = len(rows) + 1
        rows.append(ev)
    msgs = build_run_theater_messages(rows)
    testids = {m.get("data_testid") for m in msgs}
    assert "theater-evolution-proposed" in testids
    assert "theater-evolution-promoted" in testids
    assert "theater-evolution-rejected" in testids
    promoted = next(m for m in msgs if m.get("data_testid") == "theater-evolution-promoted")
    assert promoted.get("severity") == "pass"
    rejected = next(m for m in msgs if m.get("data_testid") == "theater-evolution-rejected")
    assert rejected.get("severity") == "warn"
    _ = severity_hint  # silence lint on loop unused in some checkers


def test_promote_missing_draft_emits_rejected(tmp_path: Path) -> None:
    store = _Store()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    ok = promote_or_reject_prompt(
        store,
        run_id,
        ws,
        artifact_id="prompt-missing-zzzz",
        promote=True,
    )
    assert ok is False
    assert any(
        e.get("phase") == "rejected"
        for e in evolution_timeline_from_rows(store.list_run_events(str(run_id)))
    )


def test_emit_scored_via_ledger_helper() -> None:
    store = _Store()
    run_id = uuid4()
    emit_evolution_event(
        store,
        run_id,
        phase=EvolutionPhase.SCORED,
        layer=EvolutionLayer.SKILL,
        artifact_id="skill-x",
        detail={"eligible": True},
    )
    assert store._rows[-1]["payload"]["stage_name"] == "evolution.scored"
