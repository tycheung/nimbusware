from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.model_binding_resolver import ModelBindingResolver

REPO = Path(__file__).resolve().parents[2]


def test_resolve_defaults_planner() -> None:
    resolver = ModelBindingResolver(REPO)
    binding = resolver.resolve("planner")
    assert binding.provider_id == "ollama"
    assert binding.model_id == "llama3.1:8b"
    assert binding.binding_source in ("user_defaults", "configs/model_bindings/defaults.yaml")


def test_run_snapshot_overrides_defaults() -> None:
    resolver = ModelBindingResolver(REPO)
    snapshot = {
        "roles": {
            "planner": {
                "provider_kind": "cloud",
                "provider_id": "openai",
                "model_id": "gpt-4o-mini",
                "api_key_ref": "OPENAI_API_KEY",
            },
        },
    }
    binding = resolver.resolve("planner", run_snapshot=snapshot)
    assert binding.provider_id == "openai"
    assert binding.binding_source == "run.model_bindings_snapshot"


def test_unknown_role_falls_back_to_primary() -> None:
    resolver = ModelBindingResolver(REPO)
    binding = resolver.resolve("custom_unknown_role_xyz")
    assert binding.binding_source == "model-routing.primary"
    assert binding.model_id


def test_hybrid_stage_providers_cloud_planner(tmp_path: Path) -> None:
    routing = tmp_path / "configs"
    routing.mkdir(parents=True)
    (routing / "model-routing.yaml").write_text(
        """
version: 1
cloud_runtime:
  enabled: true
  provider: openai_compatible
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
  model_id: gpt-4o-mini
stage_providers:
  plan: cloud
""",
        encoding="utf-8",
    )
    (routing / "model_bindings").mkdir(parents=True, exist_ok=True)
    (routing / "model_bindings" / "defaults.yaml").write_text(
        "version: 1\nroles: {}\n",
        encoding="utf-8",
    )
    resolver = ModelBindingResolver(tmp_path)
    binding = resolver.resolve(
        "planner",
        user_defaults={"version": 1, "roles": {}},
    )
    assert binding.binding_source == "hybrid_routing.stage_providers"
    assert binding.provider_kind == "cloud"
    assert binding.model_id == "gpt-4o-mini"
