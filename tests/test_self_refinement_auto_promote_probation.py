"""§14 #17: self-refinement probation→promoted auto path + timeline metadata."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from agent_core.models import EventType
from hermes_api.routes.runs import self_refinement_timeline_summary
from hermes_extensions.personas import PersonaShelf
from hermes_orchestrator.persona_catalog_audit import persona_catalog_run_id
from hermes_orchestrator.persona_shelf_promotion import try_auto_promote_probation_persona
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_self_refinement import parse_self_refinement_workflow_block

ROOT = Path(__file__).resolve().parents[1]


def _minimal_shelves(tmp: Path, *, commerce_on_probation: bool) -> None:
    cfg = tmp / "configs" / "personas"
    cfg.mkdir(parents=True, exist_ok=True)
    commerce: dict = {
        "id": "commerce",
        "display_name": "Commerce",
        "version": 3,
        "capability_profile": "Commerce expertise",
        "boundary_statement": "No payments",
    }
    if commerce_on_probation:
        commerce["probation_status"] = "probation"
    payload = {
        "version": 1,
        "business_area": [commerce],
        "development_role": [
            {
                "id": "backend",
                "display_name": "Backend",
                "version": 1,
                "capability_profile": "API design",
                "boundary_statement": "No infra",
            },
        ],
    }
    (cfg / "shelves.yaml").write_text(
        yaml.dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def test_parse_self_refinement_auto_promote_probation(tmp_path: Path) -> None:
    wf = tmp_path / "configs" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / "sr.yaml").write_text(
        "version: 1\nself_refinement:\n  enabled: true\n"
        "  auto_promote_probation: true\n  max_iterations: 5\n",
        encoding="utf-8",
    )
    block = parse_self_refinement_workflow_block(tmp_path, "sr")
    assert block.auto_promote_probation is True
    assert block.max_iterations == 5


def test_try_auto_promote_with_self_refinement_actor(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=True)
    mem = __import__("hermes_store.memory", fromlist=["InMemoryEventStore"]).InMemoryEventStore()
    run_id = uuid4()
    meta = try_auto_promote_probation_persona(
        tmp_path,
        mem,
        persona_id="commerce",
        run_id=run_id,
        actor="system:self_refinement",
    )
    assert meta["auto_promote_probation_applied"] is True
    prid = str(persona_catalog_run_id("business_area", "commerce"))
    ev = next(r for r in mem.list_run_events(prid) if r.get("event_type") == "persona.shelf.updated")
    assert (ev.get("payload") or {}).get("actor") == "system:self_refinement"


def test_pipeline_env_suppresses_sr_auto_promote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    shelves = tmp_path / "configs" / "personas" / "shelves.yaml"
    data = yaml.safe_load(shelves.read_text(encoding="utf-8"))
    for row in data.get("business_area", []):
        if isinstance(row, dict) and str(row.get("id", "")).strip() == "commerce":
            row["probation_status"] = "probation"
            row["capability_profile"] = "Commerce"
            row["boundary_statement"] = "Boundary"
            row.setdefault("version", 1)
            break
    for row in data.get("development_role", []):
        if isinstance(row, dict):
            row.setdefault("capability_profile", "Role skills")
            row.setdefault("boundary_statement", "Role limits")
    shelves.write_text(
        yaml.dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    wf_path = tmp_path / "configs" / "workflows" / "self_refinement_on.yaml"
    wtxt = wf_path.read_text(encoding="utf-8")
    wtxt = wtxt.replace(
        "auto_promote_probation: false",
        "auto_promote_probation: true",
    )
    if "auto_promote_probation:" not in wtxt:
        wtxt = wtxt.replace(
            "  enabled: true\n",
            "  enabled: true\n  auto_promote_probation: true\n",
        )
    wf_path.write_text(wtxt, encoding="utf-8")
    monkeypatch.delenv("HERMES_SELF_REFINEMENT_STAGE_MARKER", raising=False)
    monkeypatch.setenv("HERMES_SELF_REFINEMENT_AUTO_PROMOTE", "0")

    orch, mem = make_dev_orchestrator(tmp_path)
    rid = orch.create_run(
        "self_refinement_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001

    prid = str(persona_catalog_run_id("business_area", "commerce"))
    assert not any(
        r.get("event_type") == "persona.shelf.updated" for r in mem.list_run_events(prid)
    )
    stage = next(
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    )
    promo = ((stage.get("metadata") or {}).get("self_refinement") or {}).get(
        "auto_promote_probation",
    ) or {}
    assert promo.get("reason") == "env_kill_switch"


def test_pipeline_maybe_emit_sr_promotes_commerce_on_probation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    shelves = tmp_path / "configs" / "personas" / "shelves.yaml"
    data = yaml.safe_load(shelves.read_text(encoding="utf-8"))
    for row in data.get("business_area", []):
        if isinstance(row, dict) and str(row.get("id", "")).strip() == "commerce":
            row["probation_status"] = "probation"
            row["capability_profile"] = "Commerce"
            row["boundary_statement"] = "Boundary"
            row.setdefault("version", 1)
            break
    for row in data.get("development_role", []):
        if isinstance(row, dict):
            row.setdefault("capability_profile", "Role skills")
            row.setdefault("boundary_statement", "Role limits")
    shelves.write_text(
        yaml.dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    wf_path = tmp_path / "configs" / "workflows" / "self_refinement_on.yaml"
    wtxt = wf_path.read_text(encoding="utf-8")
    wtxt = wtxt.replace(
        "auto_promote_probation: false",
        "auto_promote_probation: true",
    )
    if "auto_promote_probation:" not in wtxt:
        wtxt = wtxt.replace(
            "  enabled: true\n",
            "  enabled: true\n  auto_promote_probation: true\n",
        )
    wf_path.write_text(wtxt, encoding="utf-8")
    monkeypatch.delenv("HERMES_SELF_REFINEMENT_STAGE_MARKER", raising=False)
    monkeypatch.delenv("HERMES_SELF_REFINEMENT_AUTO_PROMOTE", raising=False)

    orch, mem = make_dev_orchestrator(tmp_path)
    rid = orch.create_run(
        "self_refinement_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001

    prid = str(persona_catalog_run_id("business_area", "commerce"))
    assert any(r.get("event_type") == "persona.shelf.updated" for r in mem.list_run_events(prid))

    evs = mem.list_run_events(str(rid))
    stage = next(
        r
        for r in evs
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    )
    promo = ((stage.get("metadata") or {}).get("self_refinement") or {}).get(
        "auto_promote_probation",
    ) or {}
    assert promo.get("auto_promote_probation_applied") is True


def test_self_refinement_timeline_summary_surfaces_auto_promote() -> None:
    ev = {
        "event_type": EventType.STAGE_STARTED.value,
        "event_id": str(uuid4()),
        "occurred_at": "2026-01-01T00:00:00Z",
        "payload": {"stage_name": "self_refinement:policy", "attempt": 1},
        "metadata": {
            "self_refinement": {
                "max_iterations": 3,
                "auto_promote_probation": {
                    "auto_promote_probation_applied": True,
                    "shelf": "business_area",
                },
            },
        },
    }
    got = self_refinement_timeline_summary([ev])
    assert got is not None
    assert got.get("max_iterations") == 3
    assert got["auto_promote"]["auto_promote_probation_applied"] is True
    assert got.get("auto_promote_applied") is True
