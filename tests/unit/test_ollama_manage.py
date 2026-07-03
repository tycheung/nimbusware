from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.ollama_manage import (
    OllamaManageError,
    OllamaModelRow,
    delete_model,
    filter_models,
    list_installed_models,
    ollama_reachable,
    pull_model,
    runtime_base_url_from_routing,
)


def test_filter_models_case_insensitive() -> None:
    rows = [
        OllamaModelRow(name="llama3.1:8b"),
        OllamaModelRow(name="qwen2.5:7b"),
    ]
    out = filter_models(rows, "LLAMA")
    assert [m.name for m in out] == ["llama3.1:8b"]


def test_runtime_base_url_from_routing() -> None:
    assert runtime_base_url_from_routing({}) == "http://127.0.0.1:11434"
    routing = {"runtime": {"base_url": "http://ollama:11434/"}}
    assert runtime_base_url_from_routing(routing) == "http://ollama:11434"


def test_list_installed_models_parses_tags() -> None:
    payload = {
        "models": [
            {"name": "a:latest", "size": 1000, "modified_at": "t1", "digest": "d1"},
            {"name": "b", "size": "bad"},
        ],
    }
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = json.dumps(payload).encode()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        rows = list_installed_models("http://127.0.0.1:11434")
    assert len(rows) == 2
    assert rows[0].name == "a:latest"
    assert rows[0].size_bytes == 1000


def test_ollama_reachable_false_on_error() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        assert ollama_reachable("http://127.0.0.1:11434") is False


def test_pull_model_requires_reachable() -> None:
    with patch("orchestrator.ollama_manage.ollama_reachable", return_value=False):
        with pytest.raises(OllamaManageError, match="not reachable"):
            pull_model("x")


def test_delete_model_http_error() -> None:
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://x/api/delete",
        code=404,
        msg="missing",
        hdrs=None,
        fp=MagicMock(read=MagicMock(return_value=b"nope")),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(OllamaManageError, match="delete failed"):
            delete_model("missing", host="http://127.0.0.1:11434")
