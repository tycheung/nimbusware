from __future__ import annotations

import os

import pytest

from env.operator_presets import OPERATOR_PRESETS, apply_operator_preset


def test_operator_presets_known_names() -> None:
    assert set(OPERATOR_PRESETS) == {"offline", "local-llm", "production"}


def test_apply_operator_preset_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "NIMBUSWARE_QUICK_MODE",
        "NIMBUSWARE_SKIP_PREFLIGHT",
        "NIMBUSWARE_USE_LLM",
        "NIMBUSWARE_CONFIG_FROM_FILES",
        "NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE",
    ):
        monkeypatch.delenv(key, raising=False)
    trace = apply_operator_preset("offline")
    assert len(trace) == len(OPERATOR_PRESETS["offline"])
    assert os.environ["NIMBUSWARE_USE_LLM"] == "0"
    assert os.environ["NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE"] == "quick_local"
    assert all("=" in entry for entry in trace)


def test_apply_operator_preset_local_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_USE_LLM", raising=False)
    trace = apply_operator_preset("local-llm")
    assert os.environ["NIMBUSWARE_USE_LLM"] == "1"
    assert os.environ["NIMBUSWARE_OLLAMA_BASE_URL"] == "http://127.0.0.1:11434"
    assert len(trace) == len(OPERATOR_PRESETS["local-llm"])


def test_apply_operator_preset_unknown_raises() -> None:
    with pytest.raises(KeyError, match="unknown operator preset"):
        apply_operator_preset("does-not-exist")


def test_load_dotenv_applies_operator_preset(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("NIMBUSWARE_OPERATOR_PRESET=offline\n", encoding="utf-8")
    for key in OPERATOR_PRESETS["offline"]:
        monkeypatch.delenv(key, raising=False)
    from env.dotenv import load_dotenv

    load_dotenv(env_file, repo_root=tmp_path)
    assert os.environ["NIMBUSWARE_USE_LLM"] == "0"
    assert os.environ["NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE"] == "quick_local"
