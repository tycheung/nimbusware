from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from nimbusware_orchestrator.micro_slice import parse_slice_plan
from nimbusware_orchestrator.slice_implement import execute_slice_implement


def test_slice_implement_llm_applies_mocked_edits(tmp_path: Path) -> None:
    rel = "pkg.py"
    fp = tmp_path / rel
    fp.write_text("x = 1\n", encoding="utf-8")
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": [rel]})
    edits = [{"path": rel, "content": "x = 2\n"}]

    with patch.dict(
        os.environ,
        {"NIMBUSWARE_SLICE_IMPLEMENT": "llm", "NIMBUSWARE_USE_LLM": "1"},
        clear=False,
    ):
        with patch(
            "nimbusware_orchestrator.llm_slice.execute_slice_implement_llm",
            return_value=edits,
        ):
            with patch(
                "nimbusware_orchestrator.slice_implement._run_ruff_format",
                return_value=(0, "ok\n"),
            ):
                result = execute_slice_implement(
                    tmp_path,
                    plan,
                    llm_base_url="http://localhost:11434",
                    llm_model_id="m",
                )
    assert result.mode == "llm"
    assert rel in result.paths_touched
    assert "2" in fp.read_text(encoding="utf-8")
