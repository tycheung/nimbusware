from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from nimbusware_orchestrator.test_writer_stage import run_test_writer_stage


def test_llm_body_uses_stub_when_env_enabled() -> None:
    with patch.dict(
        os.environ,
        {"NIMBUSWARE_USE_LLM": "1", "NIMBUSWARE_TEST_WRITER_LLM_STUB": "1"},
        clear=False,
    ):
        code, log, mode = run_test_writer_stage(
            Path("."),
            llm_body_enabled=True,
            llm_stub_fallback=False,
            llm_model_id="model-x",
        )
    assert code == 0
    assert "stub" in log
    assert mode == "stub"


def test_llm_body_falls_back_to_stub_without_model() -> None:
    with patch.dict(os.environ, {"NIMBUSWARE_USE_LLM": "1"}, clear=False):
        code, _log, mode = run_test_writer_stage(
            Path("."),
            llm_body_enabled=True,
            llm_stub_fallback=True,
            llm_model_id=None,
        )
    assert code == 0
    assert mode == "stub"
