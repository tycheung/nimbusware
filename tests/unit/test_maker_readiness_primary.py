from __future__ import annotations

from pathlib import Path

import pytest

from maker.readiness import _check_ollama, _primary_model_id


def test_primary_model_id_from_dict() -> None:
    assert _primary_model_id({"primary": {"id": "llama3.1:8b"}}) == "llama3.1:8b"


def test_primary_model_id_legacy_string() -> None:
    assert _primary_model_id({"primary": "legacy:tag"}) == "legacy:tag"


def test_check_ollama_skip_uses_primary_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "model-routing.yaml").write_text(
        "models:\n  primary:\n    id: llama3.1:8b\n",
        encoding="utf-8",
    )
    out = _check_ollama(tmp_path)
    assert out["primary_model"] == "llama3.1:8b"
