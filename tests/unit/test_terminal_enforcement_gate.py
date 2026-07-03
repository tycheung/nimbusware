from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from orchestrator.enforcement_pipeline import (
    emit_terminal_enforcement_gate,
    terminal_enforcement_emitted,
)
from orchestrator.profiles.enforcement_profiles import (
    persist_run_enforcement,
    resolve_enforcement_profile,
)
from store.memory import InMemoryEventStore


def test_terminal_enforcement_emitted_detects_stage() -> None:
    rows = [
        {
            "payload": {"stage_name": "enforcement.gate"},
            "metadata": {"enforcement_gate": True},
        },
    ]
    assert terminal_enforcement_emitted(rows) is True


def test_emit_terminal_enforcement_gate_skips_without_profile(tmp_path: Path) -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    meta = emit_terminal_enforcement_gate(store, run_id, ws, [])
    assert meta is None


def test_emit_terminal_enforcement_gate_emits_stage(tmp_path: Path) -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    (ws / "src" / "app").mkdir(parents=True)
    (ws / "src" / "app" / "calc.py").write_text("def add(a,b): return a+b\n", encoding="utf-8")
    (ws / "tests").mkdir()
    (ws / "tests" / "test_calc.py").write_text(
        "from app.calc import add\n\ndef test_add():\n    assert add(1,2)==3\n",
        encoding="utf-8",
    )
    (ws / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\ntestpaths = ["tests"]\n',
        encoding="utf-8",
    )
    profile = resolve_enforcement_profile(level=10)
    persist_run_enforcement(store, run_id, profile)
    rows = store.list_run_events(str(run_id))
    meta = emit_terminal_enforcement_gate(store, run_id, ws, rows, timeout_seconds=180.0)
    assert meta is not None
    assert meta.get("enforcement_gate") is True
    rows = store.list_run_events(str(run_id))
    assert terminal_enforcement_emitted(rows) is True
    stages = [
        r.get("payload", {}).get("stage_name")
        for r in rows
        if r.get("event_type", "").endswith("stage")
    ]
    assert "enforcement.gate" in stages or any(
        (r.get("payload") or {}).get("stage_name") == "enforcement.gate" for r in rows
    )
