from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from orchestrator.role_telemetry import merge_role_telemetry_metadata
from orchestrator.routing.cost_summary import summarize_run_role_cost
from orchestrator.routing.presets import (
    apply_routing_preset,
    list_routing_preset_summaries,
)
from orchestrator.stage_provider_routing import (
    probe_cloud_runtime,
    resolve_stage_provider,
    stage_chat_json,
)


def test_list_and_apply_routing_presets(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    canonical = yaml.safe_load(
        (repo / "configs" / "model-routing.yaml").read_text(encoding="utf-8")
    )
    routing_presets = canonical.get("routing_presets") or {"version": 1, "presets": {}}
    (tmp_path / "configs").mkdir(parents=True)
    (tmp_path / "configs" / "model-routing.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "models": {"primary": {"id": "llama3.1:8b"}},
                "routing_presets": routing_presets,
            },
        ),
        encoding="utf-8",
    )
    summaries = list_routing_preset_summaries(tmp_path)
    ids = {row["id"] for row in summaries}
    assert "local_only" in ids
    applied = apply_routing_preset(tmp_path, "local_cloud_critique")
    assert applied["preset_id"] == "local_cloud_critique"
    routing = yaml.safe_load((tmp_path / "configs" / "model-routing.yaml").read_text())
    assert routing["cloud_runtime"]["enabled"] is True
    assert routing["stage_providers"]["slice.critique"] == "cloud"


def test_resolve_stage_provider_requires_cloud_enabled() -> None:
    routing = {
        "cloud_runtime": {"enabled": False},
        "stage_providers": {"slice.critique": "cloud"},
    }
    assert resolve_stage_provider(routing, "slice.critique") == "local"
    routing["cloud_runtime"]["enabled"] = True
    assert resolve_stage_provider(routing, "slice.critique") == "cloud"


def test_probe_cloud_runtime_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    routing = {
        "cloud_runtime": {
            "enabled": True,
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
        },
    }
    probe = probe_cloud_runtime(routing)
    assert probe["reachable"] is False
    assert "OPENAI_API_KEY" in probe["message"]


def test_stage_chat_json_routes_cloud_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routing = {
        "cloud_runtime": {
            "enabled": True,
            "base_url": "https://api.example.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "model_id": "gpt-test",
        },
        "stage_providers": {"plan": "cloud"},
    }
    (tmp_path / "configs").mkdir(parents=True)
    (tmp_path / "configs" / "model-routing.yaml").write_text(
        yaml.dump(routing),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": '{"ok": true}'}}],
            }

    monkeypatch.setattr(
        "orchestrator.stage_provider_routing.httpx.post",
        lambda *a, **k: _Resp(),
    )
    out = stage_chat_json(
        repo_root=tmp_path,
        stage_name="plan",
        base_url="http://localhost:11434",
        model="llama",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == {"ok": True}


def test_summarize_run_role_cost_tokens() -> None:
    rows = [
        {
            "event_type": "stage.passed",
            "actor_role": "backend_writer",
            "metadata": merge_role_telemetry_metadata(
                {},
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=120,
            ),
        },
    ]
    summary = summarize_run_role_cost(rows)
    assert summary is not None
    assert summary["token_total"] == 150
    assert summary["inference_p95_ms"] == 120
