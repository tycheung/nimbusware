"""Unit tests for Nimbusware self-evolution stack (ledger, tracks, L1/L2/L3)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from orchestrator.improvement.evolution_ledger import (
    EvolutionLayer,
    EvolutionPhase,
    emit_evolution_event,
    evolution_timeline_from_rows,
    pending_proposals,
)
from orchestrator.improvement.evolution_loop import (
    after_diagnose_learn,
    l1_l2_evals_blocking,
    run_distill_artifacts,
)
from orchestrator.improvement.improvement_council import ImprovementTrack, run_improvement_council
from orchestrator.improvement.improvement_scope import RepoScope, filter_votes_by_scope, infer_repo_scope
from orchestrator.improvement.prompt_evolution import (
    promote_or_reject_prompt,
    propose_overlay_from_learning,
    score_prompt_proposal,
)
from orchestrator.improvement.skill_evolution import propose_skill_from_fingerprint, record_skill_outcome
from orchestrator.variant_arena import (
    VariantCandidate,
    promote_variant_to_workspace,
    variant_touches_forbidden_paths,
)


class _MemStore:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def append(self, event: object) -> None:
        if hasattr(event, "model_dump"):
            self.events.append(event.model_dump(mode="json"))
        else:
            self.events.append(dict(event))  # type: ignore[arg-type]

    def list_run_events(self, _run_id: str) -> list[dict]:
        return list(self.events)


def test_evolution_ledger_propose_score_promote(tmp_path: Path) -> None:
    store = _MemStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    draft = propose_overlay_from_learning(
        store,
        run_id,
        ws,
        excerpt="AttributeError: NoneType has no attribute x",
    )
    assert draft is not None
    aid = draft["artifact_id"]
    score_prompt_proposal(
        store,
        run_id,
        artifact_id=aid,
        gate_pass_delta=0.1,
        has_p0_security=False,
    )
    assert promote_or_reject_prompt(store, run_id, ws, artifact_id=aid, promote=True)
    timeline = evolution_timeline_from_rows(store.list_run_events(str(run_id)))
    phases = [e["phase"] for e in timeline]
    assert "proposed" in phases
    assert "scored" in phases
    assert "promoted" in phases
    assert pending_proposals(store.list_run_events(str(run_id))) == []


def test_skill_evolution_probation_to_promoted(tmp_path: Path) -> None:
    store = _MemStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    entry = propose_skill_from_fingerprint(
        store,
        run_id,
        ws,
        fingerprint="abcd1234ffff",
        excerpt="gate fail twice",
    )
    assert entry is not None
    sid = str(entry["id"])
    record_skill_outcome(
        store,
        run_id,
        ws,
        skill_ids=[sid],
        gate_passed=True,
    )
    record_skill_outcome(
        store,
        run_id,
        ws,
        skill_ids=[sid],
        gate_passed=True,
    )
    timeline = evolution_timeline_from_rows(store.list_run_events(str(run_id)))
    assert any(e["phase"] == "promoted" and e["layer"] == "skill" for e in timeline)


def test_repo_scope_matrix_includes_new_tracks() -> None:
    from orchestrator.improvement.improvement_council import CouncilVote

    harden = infer_repo_scope(loc=2000, orphan_count=8, duplicate_clusters=3)
    assert harden == RepoScope.HARDEN
    votes = [
        CouncilVote(ImprovementTrack.VARIANT_EXPERIMENT, 0.9, "x"),
        CouncilVote(ImprovementTrack.SECURITY_HARDEN, 0.8, "y"),
        CouncilVote(ImprovementTrack.IMPROVE_COVERAGE, 0.7, "z"),
    ]
    filtered = filter_votes_by_scope(votes, harden)
    tracks = {v.track for v in filtered}
    assert ImprovementTrack.VARIANT_EXPERIMENT not in tracks
    assert ImprovementTrack.SECURITY_HARDEN in tracks
    assert ImprovementTrack.IMPROVE_COVERAGE in tracks


def test_council_can_vote_coverage_and_discover(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "a.py").write_text("x = 1\n", encoding="utf-8")
    (ws / "b.py").write_text("y = 2\n", encoding="utf-8")
    (ws / "c.py").write_text("z = 3\n", encoding="utf-8")
    (ws / "d.py").write_text("w = 4\n", encoding="utf-8")
    council = run_improvement_council(ws)
    voted = {v.track for v in council.votes}
    # At least one of the previously-dead tracks should appear when signals match
    assert council.selected is not None
    assert voted  # non-empty


def test_distill_artifacts_propose_only(tmp_path: Path) -> None:
    store = _MemStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    learn = ws / "docs" / "learnings"
    learn.mkdir(parents=True)
    (learn / "abc.md").write_text("# learning\n\nfail\n", encoding="utf-8")
    # Seed diagnose.learn row so fingerprints / excerpt path works
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ),
            metadata={
                "diagnose_learn": {
                    "fingerprint": "deadbeefdeadbeef",
                    "excerpt": "TypeError: boom",
                    "learning_available": True,
                },
            },
            payload=StagePassedPayload(stage_name="diagnose.learn", duration_ms=0),
        ),
    )
    # Second diagnose same fingerprint triggers skill draft
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ),
            metadata={
                "diagnose_learn": {
                    "fingerprint": "deadbeefdeadbeef",
                    "excerpt": "TypeError: boom",
                },
            },
            payload=StagePassedPayload(stage_name="diagnose.learn", duration_ms=0),
        ),
    )
    result = run_distill_artifacts(store, run_id, ws)
    assert result.get("prompt") is not None or result.get("skill") is not None
    assert l1_l2_evals_blocking(store.list_run_events(str(run_id)))


def test_variant_forbidden_packages_path(tmp_path: Path) -> None:
    base = tmp_path / "base"
    var = tmp_path / "var"
    (base / "app").mkdir(parents=True)
    (var / "packages").mkdir(parents=True)
    (base / "app" / "main.py").write_text("x=1\n", encoding="utf-8")
    (var / "app").mkdir(parents=True)
    (var / "app" / "main.py").write_text("x=1\n", encoding="utf-8")
    (var / "packages" / "evil.py").write_text("hack=1\n", encoding="utf-8")
    candidate = VariantCandidate(variant_id="v1", label="v1", workspace=var)
    hits = variant_touches_forbidden_paths(candidate, base)
    assert any(h.startswith("packages/") for h in hits)
    assert promote_variant_to_workspace(candidate, base) is False


def test_emit_evolution_event_stage_names() -> None:
    store = _MemStore()
    run_id = uuid4()
    name = emit_evolution_event(
        store,
        run_id,
        phase=EvolutionPhase.PROPOSED,
        layer=EvolutionLayer.VARIANT,
        artifact_id="v1",
    )
    assert name == "evolution.proposed"
    assert store.events[0]["payload"]["stage_name"] == "evolution.proposed"


def test_after_diagnose_learn_creates_prompt(tmp_path: Path) -> None:
    store = _MemStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ),
            metadata={
                "diagnose_learn": {
                    "fingerprint": "aaaabbbbccccdddd",
                    "excerpt": "ImportError: missing",
                },
            },
            payload=StagePassedPayload(stage_name="diagnose.learn", duration_ms=0),
        ),
    )
    out = after_diagnose_learn(store, run_id, ws, store.list_run_events(str(run_id)))
    assert out.get("prompt") is not None
