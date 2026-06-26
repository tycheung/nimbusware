from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_api.routes.ollama import _routing_models
from nimbusware_api.schemas.ollama import (
    OllamaModelEntry,
    OllamaModelsResponse,
    OllamaPullRequest,
    OllamaUserPolicyBody,
)
from nimbusware_config.persist import load_model_routing_dict, persist_model_routing_dict
from nimbusware_orchestrator.ollama_manage import (
    OllamaModelRow,
    filter_models,
    runtime_base_url_from_routing,
)
from nimbusware_orchestrator.ollama_user_policy import policy_from_routing


def test_load_and_persist_model_routing_roundtrip(tmp_path: Path) -> None:
    (tmp_path / "configs").mkdir()
    path = tmp_path / "configs" / "model-routing.yaml"
    path.write_text(
        "runtime:\n  base_url: http://127.0.0.1:11434\n",
        encoding="utf-8",
    )
    loaded = load_model_routing_dict(tmp_path)
    assert loaded["runtime"]["base_url"] == "http://127.0.0.1:11434"
    loaded["ollama_user_policy"] = {"allow_pull": True}
    persist_model_routing_dict(tmp_path, loaded)
    again = load_model_routing_dict(tmp_path)
    assert again["ollama_user_policy"]["allow_pull"] is True


def test_ollama_models_response_schema() -> None:
    body = OllamaModelsResponse(
        reachable=True,
        base_url="http://127.0.0.1:11434",
        user_policy=OllamaUserPolicyBody(allow_pull=True),
        models=[OllamaModelEntry(name="llama3.1:8b", size_bytes=100)],
        primary_model_id="llama3.1:8b",
        fallback_model_ids=["qwen2.5:7b"],
        query="llama",
    )
    dumped = body.model_dump()
    assert dumped["models"][0]["name"] == "llama3.1:8b"
    assert policy_from_routing({"ollama_user_policy": dumped["user_policy"]}).allow_pull


def test_routing_models_primary_and_fallbacks() -> None:
    primary, fallbacks = _routing_models(
        {
            "models": {
                "primary": {"id": " llama "},
                "fallbacks": [{"id": "qwen"}, {"id": ""}, "skip"],
            },
        },
    )
    assert primary == "llama"
    assert fallbacks == ["qwen"]


def test_filter_models_and_runtime_url() -> None:
    rows = [OllamaModelRow(name="a"), OllamaModelRow(name="bb")]
    assert len(filter_models(rows, "a")) == 1
    assert runtime_base_url_from_routing({"runtime": {"base_url": "http://x/"}}) == "http://x"


def test_ollama_pull_request_validation() -> None:
    req = OllamaPullRequest(model="tiny")
    assert req.model == "tiny"


def test_openapi_access_ollama_routes() -> None:
    from nimbusware_api.openapi_access import (
        ACCESS_TAG_ADMIN,
        ACCESS_TAG_USER,
        access_tag_for_operation,
    )

    assert access_tag_for_operation("GET", "/v1/platform/ollama/models") == ACCESS_TAG_USER
    assert access_tag_for_operation("POST", "/v1/platform/ollama/pull") == ACCESS_TAG_USER
    assert access_tag_for_operation("PATCH", "/v1/admin/ollama/user-policy") == ACCESS_TAG_ADMIN


def test_config_flags_and_listener_status() -> None:
    from nimbusware_config import config_from_db_enabled, config_notify_enabled
    from nimbusware_config.listener import config_notify_listener_enabled, listener_status
    from nimbusware_config.notify import ConfigNotifyHub

    assert isinstance(config_from_db_enabled(), bool)
    assert isinstance(config_notify_enabled(), bool)
    assert isinstance(config_notify_listener_enabled(), bool)
    status = listener_status(ConfigNotifyHub())
    assert status["channel"] == "nimbusware_config_document"


def test_seed_preview_from_repo() -> None:
    from nimbusware_config.seed import preview_seed_from_repo
    from nimbusware_env import find_repo_root

    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    preview = preview_seed_from_repo(repo)
    assert len(preview) >= 5
    assert any(row.get("document_key") == "model-routing" for row in preview)


def test_workflow_read_profile_path(tmp_path: Path) -> None:
    from nimbusware_config import workflow_read

    workflows = tmp_path / "configs" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "default.yaml").write_text("workflow_profile: default\n", encoding="utf-8")
    data = workflow_read.workflow_profile_dict(tmp_path, "default")
    assert data.get("workflow_profile") == "default"
    assert workflow_read.workflow_profile_path(tmp_path, "default").is_file()


def test_workflow_read_escalation_policy_breadth(repo_root: Path) -> None:
    from nimbusware_config import workflow_read

    assert isinstance(workflow_read.escalation_policy_breadth(repo_root), dict)


@pytest.fixture
def repo_root() -> Path:
    from nimbusware_env import find_repo_root

    return find_repo_root(start=Path(__file__).resolve().parents[1])


def test_materializer_model_routing(repo_root: Path) -> None:
    from nimbusware_config.materializer import ConfigMaterializer

    mat = ConfigMaterializer(repo_root, use_db=False)
    routing = mat.get_model_routing_base()
    assert isinstance(routing, dict)
    assert "runtime" in routing or routing == {}


def test_materializer_workflow_bundle_and_agents(repo_root: Path) -> None:
    from nimbusware_config.materializer import ConfigMaterializer

    mat = ConfigMaterializer(repo_root, use_db=False)
    profile = mat.get_workflow_profile_dict("default")
    assert isinstance(profile, dict)
    catalog = mat.get_bundle_catalog()
    assert isinstance(catalog, dict)
    agents = mat.get_custom_agent_registry()
    assert agents is not None


def test_persist_model_routing_db_materializer(tmp_path: Path) -> None:
    from nimbusware_config.keys import KEY_MODEL_ROUTING, NS_POLICY
    from nimbusware_config.persist import load_model_routing_dict, persist_model_routing_dict

    class _Mat:
        use_db = True

        def __init__(self) -> None:
            self.rows: dict[tuple[str, str], dict] = {}

        def upsert_content(self, namespace: str, key: str, content: dict) -> None:
            self.rows[(namespace, key)] = content

        def get_model_routing_base(self) -> dict:
            return dict(self.rows.get((NS_POLICY, KEY_MODEL_ROUTING), {}))

    mat = _Mat()
    content = {"runtime": {"base_url": "http://127.0.0.1:11434"}}
    persist_model_routing_dict(tmp_path, content, materializer=mat)
    loaded = load_model_routing_dict(tmp_path, materializer=mat)
    assert loaded["runtime"]["base_url"] == "http://127.0.0.1:11434"


def test_export_config_to_repo_in_memory(tmp_path: Path) -> None:
    from nimbusware_config.export import export_config_to_repo
    from nimbusware_config.seed import seed_config_from_repo
    from nimbusware_config.store import InMemoryConfigStore
    from nimbusware_env import find_repo_root

    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(repo, store)
    out = tmp_path / "out"
    out.mkdir()
    counts = export_config_to_repo(store, out)
    assert sum(counts.values()) >= 1


def test_preview_seed_skips_duplicate_workflow_stem(tmp_path: Path) -> None:
    from nimbusware_config.seed import preview_seed_from_repo

    wf = tmp_path / "configs" / "workflows"
    wf.mkdir(parents=True)
    (wf / "dup.yaml").write_text("x: 1\n", encoding="utf-8")
    (wf / "dup.yml").write_text("y: 2\n", encoding="utf-8")
    rows = preview_seed_from_repo(tmp_path)
    assert sum(1 for row in rows if row.get("document_key") == "dup") == 1


def test_seed_policy_documents_from_repo_accepts_extra(tmp_path: Path) -> None:
    from nimbusware_config.seed import seed_policy_documents_from_repo
    from nimbusware_config.store import InMemoryConfigStore

    store = InMemoryConfigStore()
    counts = seed_policy_documents_from_repo(tmp_path, store, extra={})
    assert isinstance(counts, dict)
