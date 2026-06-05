"""LLM slice patch apply."""

from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.micro_slice import parse_slice_plan
from nimbusware_orchestrator.slice_patch_apply import apply_slice_file_edits


def test_apply_slice_file_edits_allowlist(tmp_path: Path) -> None:
    rel = "packages/demo_slice_target.py"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# old\n", encoding="utf-8")
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "target_paths": [rel],
        },
    )
    touched, errors = apply_slice_file_edits(
        tmp_path,
        plan,
        [{"path": rel, "content": "# new\nprint('ok')\n"}],
    )
    assert touched == [rel]
    assert not errors
    assert "new" in target.read_text(encoding="utf-8")


def test_apply_rejects_out_of_plan_path(tmp_path: Path) -> None:
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": ["a.py"]})
    touched, errors = apply_slice_file_edits(
        tmp_path,
        plan,
        [{"path": "other.py", "content": "x"}],
    )
    assert not touched
    assert errors
