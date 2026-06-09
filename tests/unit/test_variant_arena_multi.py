from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.variant_arena import run_variant_arena


def test_run_variant_arena_caps_at_four_candidates(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "app.py").write_text("x = 1\n", encoding="utf-8")
    tests = base / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    arena = run_variant_arena(base, tmp_path / "variants", max_candidates=6)
    assert len(arena.candidates) == 4
    assert arena.winner is not None
