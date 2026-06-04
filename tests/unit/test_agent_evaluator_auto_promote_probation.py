"""agent-evaluator probation→promoted auto path + timeline metadata."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from agent_core.models import EventType
from hermes_extensions.personas import PersonaShelf
from hermes_orchestrator.persona_catalog_audit import persona_catalog_run_id
from hermes_orchestrator.persona_shelf_auto_create import (
    auto_create_persona_correlation_id,
    try_auto_create_persona_if_missing,
)
from hermes_orchestrator.persona_shelf_promotion import (
    auto_promote_probation_correlation_id,
    try_auto_promote_probation_persona,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_agent_evaluator import (
    AgentEvaluatorAutoCreatePersonaBlock,
    parse_agent_evaluator_workflow_block,
)
from hermes_store.memory import InMemoryEventStore
from nimbusware_api.routes.runs import agent_evaluator_timeline_summary
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def _minimal_shelves(tmp: Path, *, commerce_on_probation: bool) -> None:
    cfg = tmp / "configs" / "personas"
    cfg.mkdir(parents=True, exist_ok=True)
    commerce: dict = {
        "id": "commerce",
        "display_name": "Commerce",
        "version": 3,
    }
    if commerce_on_probation:
        commerce["probation_status"] = "probation"
    payload = {
        "version": 1,
        "business_area": [commerce],
        "development_role": [{"id": "backend", "display_name": "Backend", "version": 1}],
    }
    (cfg / "shelves.yaml").write_text(
        yaml.dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def test_parse_agent_evaluator_auto_promote_probation(tmp_path: Path) -> None:
    wf = tmp_path / "configs" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / "ae.yaml").write_text(
        "version: 1\nagent_evaluator:\n  enabled: true\n"
        "  persona_id: commerce\n  auto_promote_probation: true\n",
        encoding="utf-8",
    )
    block = parse_agent_evaluator_workflow_block(tmp_path, "ae")
    assert block.auto_promote_probation is True


def test_parse_agent_evaluator_auto_create_persona_block(tmp_path: Path) -> None:
    wf = tmp_path / "configs" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / "ae_ac.yaml").write_text(
        "version: 1\nagent_evaluator:\n  enabled: true\n"
        "  persona_id: net_pid\n"
        "  auto_create_persona:\n"
        "    enabled: true\n"
        "    shelf: business_area\n"
        "    display_name: Net\n",
        encoding="utf-8",
    )
    block = parse_agent_evaluator_workflow_block(tmp_path, "ae_ac")
    assert block.auto_create_persona.enabled is True
    assert block.auto_create_persona.shelf == "business_area"
    assert block.auto_create_persona.display_name == "Net"


def test_try_auto_promote_applies_and_writes_disk(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=True)
    mem = InMemoryEventStore()
    run_id = uuid4()
    meta = try_auto_promote_probation_persona(
        tmp_path,
        mem,
        persona_id="commerce",
        run_id=run_id,
    )
    assert meta["auto_promote_probation_applied"] is True
    assert meta["shelf"] == "business_area"
    shelf = PersonaShelf(tmp_path / "configs" / "personas" / "shelves.yaml")
    shelf.validate_structure()
    row = shelf.find_entry("business_area", "commerce")
    assert row is not None
    assert row.get("probation_status") == "promoted"
    assert row.get("version") == 4


def test_try_auto_promote_skips_when_not_probation(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=False)
    mem = InMemoryEventStore()
    meta = try_auto_promote_probation_persona(
        tmp_path,
        mem,
        persona_id="commerce",
        run_id=uuid4(),
    )
    assert meta["auto_promote_probation_applied"] is False
    assert meta["reason"] == "not_on_probation"


def test_try_auto_promote_idempotent_on_store(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=True)
    mem = InMemoryEventStore()
    run_id = uuid4()
    m1 = try_auto_promote_probation_persona(tmp_path, mem, persona_id="commerce", run_id=run_id)
    assert m1["auto_promote_probation_applied"] is True
    m2 = try_auto_promote_probation_persona(tmp_path, mem, persona_id="commerce", run_id=run_id)
    assert m2["auto_promote_probation_applied"] is False
    assert m2["reason"] == "already_recorded"


def test_auto_promote_correlation_id_stable() -> None:
    rid = UUID("11111111-1111-4111-8111-111111111111")
    a = auto_promote_probation_correlation_id(rid, "commerce")
    b = auto_promote_probation_correlation_id(rid, "commerce")
    assert a == b
    assert a != auto_promote_probation_correlation_id(rid, "other")


def test_agent_evaluator_timeline_summary_surfaces_auto_promote() -> None:
    ev = {
        "event_type": EventType.STAGE_STARTED.value,
        "event_id": str(uuid4()),
        "occurred_at": "2026-01-01T00:00:00Z",
        "payload": {"stage_name": "agent_eval:commerce", "attempt": 1},
        "metadata": {
            "agent_evaluator": {
                "auto_promote_probation_applied": True,
                "shelf": "business_area",
            },
        },
    }
    got = agent_evaluator_timeline_summary([ev])
    assert got is not None
    assert got["persona_id"] == "commerce"
    assert got["auto_promote"]["auto_promote_probation_applied"] is True
    assert got.get("auto_promote_applied") is True


def test_agent_evaluator_timeline_summary_flattens_nested_auto_actions() -> None:
    ev = {
        "event_type": EventType.STAGE_STARTED.value,
        "event_id": str(uuid4()),
        "occurred_at": "2026-01-01T00:00:00Z",
        "payload": {"stage_name": "agent_eval:net", "attempt": 1},
        "metadata": {
            "agent_evaluator": {
                "auto_promote_probation": {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                },
                "auto_create_persona": {
                    "auto_create_persona_requested": True,
                    "auto_create_persona_applied": True,
                    "shelf": "business_area",
                    "display_name": "Net",
                },
            },
        },
    }
    got = agent_evaluator_timeline_summary([ev])
    assert got is not None
    assert got["auto_promote_requested"] is True
    assert got["auto_promote_applied"] is False
    assert got["auto_promote_reason"] == "env_kill_switch"
    assert got["auto_create_requested"] is True
    assert got["auto_create_applied"] is True
    assert got["auto_create_shelf"] == "business_area"
    assert got["auto_create_display_name"] == "Net"


def test_pipeline_env_suppresses_auto_promote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    shelves = tmp_path / "configs" / "personas" / "shelves.yaml"
    data = yaml.safe_load(shelves.read_text(encoding="utf-8"))
    for row in data.get("business_area", []):
        if isinstance(row, dict) and str(row.get("id", "")).strip() == "commerce":
            row["probation_status"] = "probation"
            row.setdefault("version", 1)
            break
    shelves.write_text(
        yaml.dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    wf_path = tmp_path / "configs" / "workflows" / "agent_evaluator_on.yaml"
    wtxt = wf_path.read_text(encoding="utf-8")
    if "auto_promote_probation:" not in wtxt:
        wf_path.write_text(
            wtxt.replace(
                "  persona_id: commerce\n",
                "  persona_id: commerce\n  auto_promote_probation: true\n",
            ),
            encoding="utf-8",
        )
    monkeypatch.delenv("HERMES_AGENT_EVALUATOR", raising=False)
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE", "0")

    orch, mem = make_dev_orchestrator(tmp_path)
    rid = orch.create_run("agent_evaluator_on")
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001

    prid = str(persona_catalog_run_id("business_area", "commerce"))
    assert not any(
        r.get("event_type") == "persona.shelf.updated" for r in mem.list_run_events(prid)
    )
    evs = mem.list_run_events(str(rid))
    stage = next(
        r
        for r in evs
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
    )
    meta = stage.get("metadata") or {}
    inner = meta.get("agent_evaluator") or {}
    promo = inner.get("auto_promote_probation") or {}
    assert promo.get("reason") == "env_kill_switch"
    disk = PersonaShelf(shelves)
    row = disk.find_entry("business_area", "commerce")
    assert row is not None
    assert row.get("probation_status") == "probation"


def test_pipeline_maybe_emit_promotes_commerce_on_probation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    shelves = tmp_path / "configs" / "personas" / "shelves.yaml"
    data = yaml.safe_load(shelves.read_text(encoding="utf-8"))
    patched = False
    for row in data.get("business_area", []):
        if isinstance(row, dict) and str(row.get("id", "")).strip() == "commerce":
            row["probation_status"] = "probation"
            row.setdefault("version", 1)
            patched = True
            break
    assert patched, "repo fixtures must include commerce on business_area shelf"
    shelves.write_text(
        yaml.dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    wf_path = tmp_path / "configs" / "workflows" / "agent_evaluator_on.yaml"
    wtxt = wf_path.read_text(encoding="utf-8")
    if "auto_promote_probation:" not in wtxt:
        wf_path.write_text(
            wtxt.replace(
                "  persona_id: commerce\n",
                "  persona_id: commerce\n  auto_promote_probation: true\n",
            ),
            encoding="utf-8",
        )
    monkeypatch.delenv("HERMES_AGENT_EVALUATOR", raising=False)
    monkeypatch.delenv("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE", raising=False)

    orch, mem = make_dev_orchestrator(tmp_path)
    rid = orch.create_run("agent_evaluator_on")
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001

    evs = mem.list_run_events(str(rid))
    assert any(
        r.get("event_type") == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
        for r in evs
    )
    prid = str(persona_catalog_run_id("business_area", "commerce"))
    assert any(r.get("event_type") == "persona.shelf.updated" for r in mem.list_run_events(prid))

    stage = next(
        r
        for r in evs
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
    )
    meta = stage.get("metadata") or {}
    inner = meta.get("agent_evaluator") or {}
    promo = inner.get("auto_promote_probation") or {}
    assert promo.get("auto_promote_probation_applied") is True

    disk = PersonaShelf(shelves)
    disk.validate_structure()
    row = disk.find_entry("business_area", "commerce")
    assert row is not None
    assert row.get("probation_status") == "promoted"


def test_auto_create_correlation_id_stable() -> None:
    rid = UUID("11111111-1111-4111-8111-111111111111")
    a = auto_create_persona_correlation_id(rid, "business_area", "new_pid")
    b = auto_create_persona_correlation_id(rid, "business_area", "new_pid")
    assert a == b
    assert a != auto_create_persona_correlation_id(rid, "development_role", "new_pid")


def test_try_auto_create_applies_when_missing(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=False)
    mem = InMemoryEventStore()
    run_id = uuid4()
    cfg = AgentEvaluatorAutoCreatePersonaBlock(
        enabled=True,
        shelf="business_area",
        display_name="Fresh AE",
    )
    meta = try_auto_create_persona_if_missing(
        tmp_path,
        mem,
        persona_id="fresh_ae_pid",
        run_id=run_id,
        cfg=cfg,
    )
    assert meta["auto_create_persona_applied"] is True
    assert meta["shelf"] == "business_area"
    shelf = PersonaShelf(tmp_path / "configs" / "personas" / "shelves.yaml")
    shelf.validate_structure()
    row = shelf.find_entry("business_area", "fresh_ae_pid")
    assert row is not None
    assert row.get("display_name") == "Fresh AE"


def test_try_auto_create_idempotent_on_store(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=False)
    mem = InMemoryEventStore()
    run_id = uuid4()
    cfg = AgentEvaluatorAutoCreatePersonaBlock(
        enabled=True,
        shelf="development_role",
        display_name="Twice",
    )
    m1 = try_auto_create_persona_if_missing(
        tmp_path,
        mem,
        persona_id="dup_ae",
        run_id=run_id,
        cfg=cfg,
    )
    assert m1["auto_create_persona_applied"] is True
    m2 = try_auto_create_persona_if_missing(
        tmp_path,
        mem,
        persona_id="dup_ae",
        run_id=run_id,
        cfg=cfg,
    )
    assert m2["auto_create_persona_applied"] is False
    assert m2["reason"] == "already_exists"


def test_try_auto_create_reserved_persona_id(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=False)
    mem = InMemoryEventStore()
    cfg = AgentEvaluatorAutoCreatePersonaBlock(
        enabled=True,
        shelf="business_area",
        display_name="X",
    )
    meta = try_auto_create_persona_if_missing(
        tmp_path,
        mem,
        persona_id="default",
        run_id=uuid4(),
        cfg=cfg,
    )
    assert meta["auto_create_persona_applied"] is False
    assert meta["reason"] == "reserved_or_empty_persona_id"


def test_try_auto_create_invalid_shelf(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=False)
    mem = InMemoryEventStore()
    cfg = AgentEvaluatorAutoCreatePersonaBlock(
        enabled=True,
        shelf="not_a_shelf",
        display_name="X",
    )
    meta = try_auto_create_persona_if_missing(
        tmp_path,
        mem,
        persona_id="x",
        run_id=uuid4(),
        cfg=cfg,
    )
    assert meta["auto_create_persona_applied"] is False
    assert meta["reason"] == "invalid_shelf"


def test_agent_evaluator_timeline_summary_nested_auto_promote_and_create() -> None:
    ev = {
        "event_type": EventType.STAGE_STARTED.value,
        "event_id": str(uuid4()),
        "occurred_at": "2026-01-01T00:00:00Z",
        "payload": {"stage_name": "agent_eval:net", "attempt": 1},
        "metadata": {
            "agent_evaluator": {
                "auto_promote_probation": {"auto_promote_probation_applied": False},
                "auto_create_persona": {
                    "auto_create_persona_applied": True,
                    "shelf": "business_area",
                },
            },
        },
    }
    got = agent_evaluator_timeline_summary([ev])
    assert got is not None
    assert got["auto_promote"]["auto_promote_probation_applied"] is False
    assert got["auto_create_persona"]["auto_create_persona_applied"] is True


def test_pipeline_env_suppresses_auto_create(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    wf_dir = tmp_path / "configs" / "workflows"
    (wf_dir / "ae_auto_create.yaml").write_text(
        "version: 1\nagent_evaluator:\n  enabled: true\n"
        "  persona_id: env_block_ae\n"
        "  auto_create_persona:\n"
        "    enabled: true\n"
        "    shelf: business_area\n"
        "    display_name: Env Block\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("HERMES_AGENT_EVALUATOR", raising=False)
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR_AUTO_CREATE", "0")

    orch, mem = make_dev_orchestrator(tmp_path)
    rid = orch.create_run("ae_auto_create")
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001

    prid = str(persona_catalog_run_id("business_area", "env_block_ae"))
    assert not any(
        r.get("event_type") == "persona.shelf.updated" for r in mem.list_run_events(prid)
    )
    evs = mem.list_run_events(str(rid))
    stage = next(
        r
        for r in evs
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
    )
    inner = (stage.get("metadata") or {}).get("agent_evaluator") or {}
    ac = inner.get("auto_create_persona") or {}
    assert ac.get("reason") == "env_kill_switch"


def test_pipeline_auto_create_net_new_persona(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    wf_dir = tmp_path / "configs" / "workflows"
    (wf_dir / "ae_auto_create_ok.yaml").write_text(
        "version: 1\nagent_evaluator:\n  enabled: true\n"
        "  persona_id: orch_net_new_ae\n"
        "  auto_create_persona:\n"
        "    enabled: true\n"
        "    shelf: business_area\n"
        "    display_name: Orch Net New\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("HERMES_AGENT_EVALUATOR", raising=False)
    monkeypatch.delenv("HERMES_AGENT_EVALUATOR_AUTO_CREATE", raising=False)

    orch, mem = make_dev_orchestrator(tmp_path)
    rid = orch.create_run("ae_auto_create_ok")
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001

    prid = str(persona_catalog_run_id("business_area", "orch_net_new_ae"))
    assert any(r.get("event_type") == "persona.shelf.updated" for r in mem.list_run_events(prid))

    disk = PersonaShelf(tmp_path / "configs" / "personas" / "shelves.yaml")
    disk.validate_structure()
    row = disk.find_entry("business_area", "orch_net_new_ae")
    assert row is not None
    assert row.get("display_name") == "Orch Net New"
