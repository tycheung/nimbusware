from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

from nimbusware_orchestrator.ollama_chat import OllamaLlmJson, extract_ollama_usage, ollama_chat_json
from nimbusware_orchestrator.security_semgrep import run_semgrep_scan
from nimbusware_config.listener import (
    config_notify_listener_enabled,
    listener_status,
    start_config_notify_listener,
)
from nimbusware_config.notify import ConfigNotifyHub, encode_notify_payload


def test_extract_ollama_usage_counts() -> None:
    usage = extract_ollama_usage(
        {
            "prompt_eval_count": 10,
            "eval_count": 20,
            "eval_duration": 2_000_000,
        },
    )
    assert usage["prompt_tokens"] == 10
    assert usage["completion_tokens"] == 20
    assert usage["latency_ms"] >= 1


def test_ollama_chat_json_parses_message(monkeypatch) -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "message": {"content": '{"ok": true}'},
    }

    class _Client:
        def post(self, *args, **kwargs):
            return response

    monkeypatch.setattr("nimbusware_orchestrator.ollama_chat.httpx.post", _Client().post)
    out = ollama_chat_json(
        base_url="http://127.0.0.1:11434",
        model="tiny",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == {"ok": True}

    llm = OllamaLlmJson("http://127.0.0.1:11434")
    assert llm.complete_json(model="tiny", system="s", user="u") == {"ok": True}


def test_semgrep_scan_branches(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("nimbusware_orchestrator.security_semgrep.semgrep_enabled", lambda: False)
    code, out = run_semgrep_scan(tmp_path)
    assert code == 0
    assert "skipped" in out

    monkeypatch.setattr("nimbusware_orchestrator.security_semgrep.semgrep_enabled", lambda: True)
    monkeypatch.setattr("nimbusware_orchestrator.security_semgrep.shutil.which", lambda _: None)
    code, out = run_semgrep_scan(tmp_path)
    assert "not on PATH" in out

    (tmp_path / "packages").mkdir()
    monkeypatch.setattr("nimbusware_orchestrator.security_semgrep.shutil.which", lambda _: "semgrep")
    proc = MagicMock(returncode=0, stdout="{}", stderr="")
    monkeypatch.setattr("nimbusware_orchestrator.security_semgrep.subprocess.run", lambda *a, **k: proc)
    code, out = run_semgrep_scan(tmp_path)
    assert code == 0
    assert "semgrep" in out


def test_config_listener_status_and_enabled(monkeypatch) -> None:
    monkeypatch.setattr("nimbusware_config.flags.config_from_db_enabled", lambda: True)
    monkeypatch.setattr("nimbusware_config.flags.config_notify_enabled", lambda: True)
    assert config_notify_listener_enabled() is True
    hub = ConfigNotifyHub()
    hub.handle_payload(
        encode_notify_payload(
            namespace="policy",
            document_key="model-routing",
            version=2,
        ),
    )
    status = listener_status(hub)
    assert status["delivery_count"] == 1
    assert status["last_event"]["document_key"] == "model-routing"


def test_start_config_notify_listener_stops_cleanly(monkeypatch) -> None:
    stop = threading.Event()
    stop.set()

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *args, **kwargs):
            return None

        @property
        def notifies(self):
            return []

    monkeypatch.setattr("nimbusware_config.listener.psycopg.connect", lambda *a, **k: _Conn())
    hub = ConfigNotifyHub()
    thread = start_config_notify_listener("postgresql://local/test", hub, stop)
    thread.join(timeout=2.0)
    assert not thread.is_alive()
