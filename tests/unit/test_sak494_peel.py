from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agent_core.slice_plan import SlicePlan, parse_slice_plan
from orchestrator.workflow.memory import (
    MemoryWorkflowBlock,
    retrieve_memory_excerpt_for_slice,
)

_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.sak494


def _stub_plan() -> SlicePlan:
    return parse_slice_plan(
        {
            "slice_id": "sak494-a",
            "rationale": "broker memory excerpt",
            "target_paths": ["packages/orchestrator/workflow/memory.py"],
            "acceptance_criteria": "uses try_broker_memory_search",
        },
    )


def test_sak494_a_slice_memory_wiring() -> None:
    """sak494-a: orchestrator slice/plan paths wire broker memory + refuse local."""
    memory = (_ROOT / "packages" / "orchestrator" / "workflow" / "memory.py").read_text(
        encoding="utf-8",
    )
    plan = (_ROOT / "packages" / "orchestrator" / "slice" / "plan.py").read_text(
        encoding="utf-8",
    )
    micro = (_ROOT / "packages" / "orchestrator" / "_pipeline" / "micro_slice.py").read_text(
        encoding="utf-8",
    )
    route = (_ROOT / "packages" / "memory" / "broker_route.py").read_text(encoding="utf-8")

    assert "sak494-a" in memory
    assert "try_broker_memory_search" in memory
    assert "_retrieve_slice_memory_via_broker" in memory
    assert "broker_memory_enabled" in plan
    assert "broker_memory_enabled" in micro
    assert "refuse_legacy" in route
    assert "sak494-a" in route


@pytest.mark.sak494_a
def test_retrieve_memory_uses_broker_under_memory_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-a: MEMORY=1 routes slice excerpt via broker."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    settings = MemoryWorkflowBlock(retrieval_k=3, excerpt_max_chars=500)
    broker_payload = {
        "hits": [
            {"chunk_id": "c1", "score": 0.9, "text": "prior sql injection fix"},
        ],
    }
    with patch(
        "agent_tools.memory_bridge.try_broker_memory_search",
        return_value=broker_payload,
    ) as broker_search:
        excerpt, hits, scope = retrieve_memory_excerpt_for_slice(
            None,
            _stub_plan(),
            repo_root=tmp_path,
            settings=settings,
        )
    broker_search.assert_called_once()
    assert "sql injection" in excerpt
    assert hits == []
    assert scope == ""


@pytest.mark.sak494_a
def test_retrieve_memory_refuses_local_under_memory_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-a / sak495-b: MEMORY=1 broker miss raises (no local search)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    settings = MemoryWorkflowBlock()
    with (
        patch("agent_tools.memory_bridge.try_broker_memory_search", return_value=None),
        patch("memory.peel_index.search.search_memory") as local_search,
        patch("memory.peel_index.search.search_user_memory") as user_search,
    ):
        with pytest.raises(RuntimeError, match="broker_miss: slice_memory"):
            retrieve_memory_excerpt_for_slice(
                object(),
                _stub_plan(),
                repo_root=tmp_path,
                settings=settings,
            )
    local_search.assert_not_called()
    user_search.assert_not_called()


@pytest.mark.sak494_a
def test_retrieve_memory_broker_only_reraises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-a: MEMORY=2 broker failure propagates (no local fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    settings = MemoryWorkflowBlock()
    with (
        patch(
            "agent_tools.memory_bridge.try_broker_memory_search",
            side_effect=RuntimeError("broker down"),
        ),
        patch("memory.peel_index.search.search_memory") as local_search,
    ):
        with pytest.raises(RuntimeError, match="broker down"):
            retrieve_memory_excerpt_for_slice(
                object(),
                _stub_plan(),
                repo_root=tmp_path,
                settings=settings,
            )
    local_search.assert_not_called()


# --- sak494-d: tool_run_shell / tool_memory_search peel miss ---

from unittest.mock import MagicMock

from agent_tools.shell_tools import tool_memory_search, tool_run_shell


@pytest.mark.sak494_d
def test_sak494_d_tool_run_shell_peel_raises_on_broker_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-d: SANDBOX=1 — broker None raises; no local sandbox fallback."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")
    local_called: list[object] = []

    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: local_called.append(True),
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        with pytest.raises(RuntimeError, match="broker_miss: shell"):
            tool_run_shell(tmp_path, "pytest", ["-q"])

    assert local_called == []


@pytest.mark.sak494_d
def test_sak494_d_tool_run_shell_broker_only_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-d: SANDBOX=2 — broker failure propagates (no local fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "2")

    def _boom(*_a, **_k):
        raise RuntimeError("broker_miss: sandbox_exec: down")

    monkeypatch.setattr("agent_tools.sandbox_bridge.try_broker_sandbox_exec", _boom)
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("local sandbox")),
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            tool_run_shell(tmp_path, "pytest", ["-q"])


@pytest.mark.sak494_d
def test_sak494_d_tool_run_shell_peel_off_still_falls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-d: SANDBOX=0 — broker None still allows local/tools fallback."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.delenv("NIMBUSWARE_BROKER_TOOLS", raising=False)
    proc = MagicMock()
    proc.combined_output = "local ok"
    proc.returncode = 0
    proc.backend = "none"

    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "broker_client.stage_bind.tools.try_broker_shell_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: proc,
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        result = tool_run_shell(tmp_path, "pytest", ["-q"])

    assert result.ok is True
    assert "local ok" in result.llm_output


@pytest.mark.sak494_d
def test_sak494_d_tool_memory_search_peel_raises_on_broker_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-d: MEMORY=1 — broker None raises; no local search fallback."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    local_called: list[object] = []

    monkeypatch.setattr(
        "agent_tools.memory_bridge.try_broker_memory_search",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "memory.peel_index.search.search_memory",
        lambda *_a, **_k: local_called.append(True) or [],
    )

    with pytest.raises(RuntimeError, match="broker_miss: memory_search"):
        tool_memory_search("query", memory_store=MagicMock())

    assert local_called == []


@pytest.mark.sak494_d
def test_sak494_d_tool_memory_search_broker_only_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-d: MEMORY=2 — broker failure propagates (no local fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")

    def _boom(*_a, **_k):
        raise RuntimeError("broker_miss: memory_search: down")

    monkeypatch.setattr("agent_tools.memory_bridge.try_broker_memory_search", _boom)

    with pytest.raises(RuntimeError, match="broker_miss"):
        tool_memory_search("query", memory_store=MagicMock())


# --- sak494-e: research/egress peel miss + egress-audit export ---

from uuid import UUID

import httpx

from api.export_peel import early_egress_export_json_miss
from executor.fetch import egress_checked_httpx_get
from research.fetch import fetch_url


@pytest.mark.sak494_e
def test_sak494_e_fetch_url_peel_on_broker_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-e: RESEARCH=1 — broker None raises broker_miss (no local fetch)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    monkeypatch.setattr(
        "research.research_bridge.try_broker_research_fetch",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="broker_miss: research_fetch"):
        fetch_url("https://example.com/page")


@pytest.mark.sak494_e
def test_sak494_e_fetch_url_peel_off_broker_none_legacy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-e: RESEARCH=0 — broker None keeps sak416-h legacy error."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_RESEARCH", raising=False)
    monkeypatch.setattr(
        "research.research_bridge.try_broker_research_fetch",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="research local fetch removed"):
        fetch_url("https://example.com/page")


@pytest.mark.sak494_e
def test_sak494_e_fetch_url_broker_only_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-e: RESEARCH=2 — broker failure propagates (no local fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "2")

    def _boom(*_a, **_k):
        raise RuntimeError("broker_miss: research_fetch: down")

    monkeypatch.setattr("research.research_bridge.try_broker_research_fetch", _boom)
    with pytest.raises(RuntimeError, match="broker_miss"):
        fetch_url("https://example.com")


@pytest.mark.sak494_e
def test_sak494_e_egress_checked_peel_on_broker_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-e: EGRESS=1 — broker None raises broker_miss (no local httpx)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    role = UUID("11111111-1111-4111-8111-111111111101")
    client = MagicMock(spec=httpx.Client)
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="broker_miss: egress"):
        egress_checked_httpx_get(
            "https://example.com/path",
            actor_role_id=role,
            scraper_role_allowlist=[role],
            domain_allowlist=["example.com"],
            client=client,
        )
    client.get.assert_not_called()


@pytest.mark.sak494_e
def test_sak494_e_egress_checked_peel_off_broker_none_legacy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-e: EGRESS=0 — broker None keeps sak416-i legacy error."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_EGRESS", raising=False)
    role = UUID("11111111-1111-4111-8111-111111111101")
    client = MagicMock(spec=httpx.Client)
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="local egress removed"):
        egress_checked_httpx_get(
            "https://example.com/path",
            actor_role_id=role,
            scraper_role_allowlist=[role],
            domain_allowlist=["example.com"],
            client=client,
        )
    client.get.assert_not_called()


@pytest.mark.sak494_e
def test_sak494_e_egress_audit_export_peel_on_returns_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-e: EGRESS=1 — egress-audit JSON export returns broker_miss envelope."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    miss = early_egress_export_json_miss(feature="egress_audit")
    assert miss is not None
    body = miss.body.decode("utf-8")
    assert "broker_miss" in body
    assert "egress_audit" in body
    assert "degraded" in body


@pytest.mark.sak494_e
def test_sak494_e_egress_audit_export_peel_off_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak494-e: EGRESS=0 — egress-audit export guard does not block local read."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_EGRESS", raising=False)
    assert early_egress_export_json_miss(feature="egress_audit") is None


@pytest.mark.sak494_e
def test_sak494_e_source_markers() -> None:
    """sak494-e: research/egress peel wired in production modules."""
    research = (_ROOT / "packages" / "research" / "fetch.py").read_text(encoding="utf-8")
    egress = (_ROOT / "packages" / "executor" / "fetch.py").read_text(encoding="utf-8")
    outbound = (_ROOT / "packages" / "orchestrator" / "outbound_http.py").read_text(
        encoding="utf-8",
    )
    scraper = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "pipeline_scraper.py"
    ).read_text(encoding="utf-8")
    research_ops = (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "research_ops.py"
    ).read_text(encoding="utf-8")
    assert "broker_miss: research_fetch" in research
    assert "broker_miss: egress" in egress
    assert "sak494-e" in outbound
    assert "broker_miss" in scraper
    assert "early_egress_export_json_miss" in research_ops


# --- sak494-f: launch_evaluator / launch_test_llm peel residuals ---

import httpx
from pydantic import ValidationError

from orchestrator.launch.launch_evaluator import (
    _llm_panel_extras,
    evaluate_workspace_rubric,
    fetch_llm_rubric_panel,
)
from orchestrator.launch.launch_test_llm import generate_llm_ui_flow_dict


@pytest.mark.sak494_f
def test_sak494_f_launch_eval_peel_on_empty_panel_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-f: LLM=1 — empty panel propagates broker_miss (no advisory fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_LAUNCH_EVAL_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "src").mkdir()
    (ws / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

    with patch(
        "orchestrator.launch.launch_evaluator.fetch_llm_rubric_panel",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            evaluate_workspace_rubric(ws, min_aggregate=0.0)


@pytest.mark.sak494_f
def test_sak494_f_launch_eval_peel_off_empty_panel_advisory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-f: LLM=0 — empty panel keeps advisory file-count fallback."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_LAUNCH_EVAL_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "src").mkdir()
    (ws / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

    with patch(
        "orchestrator.launch.launch_evaluator.fetch_llm_rubric_panel",
        return_value=None,
    ):
        scorecard = evaluate_workspace_rubric(ws, min_aggregate=0.0)
    assert scorecard.llm_findings
    assert "advisory" in scorecard.llm_findings[0]


@pytest.mark.sak494_f
def test_sak494_f_launch_eval_peel_on_http_error_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-f: LLM=1 — fetch HTTP failure propagates (no None/advisory path)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "README.md").write_text("demo", encoding="utf-8")

    with (
        patch(
            "orchestrator.launch.launch_evaluator.ollama_base_url",
            return_value="http://ollama",
        ),
        patch(
            "orchestrator.llm.chat_facade.ollama_chat_json_via_plan_patch",
            side_effect=httpx.ConnectError("down"),
        ),
    ):
        with pytest.raises(httpx.ConnectError):
            fetch_llm_rubric_panel(ws)


@pytest.mark.sak494_f
def test_sak494_f_launch_eval_panel_extras_peel_on_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-f: LLM=2 — _llm_panel_extras refuses advisory when panel empty."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    monkeypatch.setenv("NIMBUSWARE_LAUNCH_EVAL_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()

    with patch(
        "orchestrator.launch.launch_evaluator.fetch_llm_rubric_panel",
        return_value={"findings": [], "dimensions": {}},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            _llm_panel_extras(ws)


@pytest.mark.sak494_f
def test_sak494_f_launch_test_llm_peel_on_validation_error_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-f: LLM=1 — invalid flow payload propagates (no None → ISM fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_DEFAULT_MODEL", "m")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "README.md").write_text("demo", encoding="utf-8")

    with patch(
        "orchestrator.launch.launch_test_llm.ollama_chat_json_via_plan_patch",
        return_value={"flow": {"id": "launch_draft", "steps": []}},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            generate_llm_ui_flow_dict(ws)


@pytest.mark.sak494_f
def test_sak494_f_launch_test_llm_peel_off_validation_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-f: LLM=0 — invalid flow still soft-returns None for ISM fallback."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_DEFAULT_MODEL", "m")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "README.md").write_text("demo", encoding="utf-8")

    with patch(
        "orchestrator.launch.launch_test_llm.ollama_chat_json_via_plan_patch",
        return_value={"flow": {"id": "launch_draft", "steps": []}},
    ):
        assert generate_llm_ui_flow_dict(ws) is None


@pytest.mark.sak494_f
def test_sak494_f_launch_test_llm_peel_on_parse_error_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak494-f: LLM=2 — pydantic validation failure propagates under peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_DEFAULT_MODEL", "m")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "README.md").write_text("demo", encoding="utf-8")

    with patch(
        "orchestrator.launch.launch_test_llm.ollama_chat_json_via_plan_patch",
        return_value={"flow": "not-a-dict"},
    ):
        with pytest.raises(ValidationError):
            generate_llm_ui_flow_dict(ws)


@pytest.mark.sak494_f
def test_sak494_f_source_markers() -> None:
    """sak494-f: launch peel residuals wired in production modules."""
    eval_src = (_ROOT / "packages" / "orchestrator" / "launch" / "launch_evaluator.py").read_text(
        encoding="utf-8"
    )
    test_src = (_ROOT / "packages" / "orchestrator" / "launch" / "launch_test_llm.py").read_text(
        encoding="utf-8"
    )
    assert "broker_llm_enabled()" in eval_src
    assert "broker_miss: launch_evaluator" in eval_src
    assert "sak494-f" in test_src
    assert "broker_llm_enabled()" in test_src


# --- sak494-c: enterprise peel OpenAPI helpers + checked-in artifact ---

import json

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    egress_json_openapi_responses,
    enterprise_peel_json_openapi_responses,
    memory_json_openapi_responses,
    research_json_openapi_responses,
)

SAK494_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/fleet-memory/rebuild", "post"),
    ("/v1/enterprise/fleet-memory/sync", "post"),
    ("/v1/enterprise/research-index", "get"),
    ("/v1/enterprise/egress-audit", "get"),
)


def _openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


@pytest.mark.sak494_c
def test_sak494_c_openapi_artifact_documents_peel_503() -> None:
    """sak494-c: openapi.json lists 503 problem+json on memory/research/egress peel paths."""
    spec = json.loads(_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK494_C_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, (
            f"missing 503 problem+json on {method.upper()} {path}"
        )
        schema = content["application/problem+json"].get("schema", {})
        assert schema.get("type") == "object"
        assert "code" in schema.get("properties", {})


@pytest.mark.sak494_c
def test_sak494_c_peel_routes_source_wire_openapi_helpers() -> None:
    """sak494-c: route sources wire memory/research/egress peel OpenAPI helpers."""
    root = _ROOT / "packages" / "api"
    fleet = (root / "routes" / "enterprise" / "fleet_memory.py").read_text(encoding="utf-8")
    research = (root / "routes" / "enterprise" / "research_ops.py").read_text(encoding="utf-8")
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")

    assert "sak494-c" in peel
    assert enterprise_peel_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert research_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert egress_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert memory_json_openapi_responses()[503] is PROBLEM_RESPONSE_503

    assert "/rebuild" in fleet and "responses=memory_json_openapi_responses" in fleet
    assert "/sync" in fleet and "responses=memory_json_openapi_responses" in fleet
    assert "/research-index" in research and "responses=research_json_openapi_responses" in research
    assert "/egress-audit" in research and "egress_json_openapi_responses" in research


# --- sak494-g: admin BFF peel OpenAPI + sub-fetch aggregation ---

from console.services import enterprise as enterprise_svc

SAK494_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/admin/ui/enterprise/fleet-dashboard", "get"),
    ("/v1/admin/ui/enterprise/fleet-compare", "get"),
    ("/v1/admin/ui/operator-chat/message", "post"),
    ("/v1/platform/workspace-readiness", "get"),
)


@pytest.mark.sak494_g
def test_sak494_g_openapi_artifact_documents_bff_peel_503() -> None:
    """sak494-g: openapi.json lists 503 problem+json on admin BFF + workspace-readiness."""
    spec = json.loads(_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK494_G_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, (
            f"missing 503 problem+json on {method.upper()} {path}"
        )


@pytest.mark.sak494_g
def test_sak494_g_bff_routes_wire_admin_openapi_helpers() -> None:
    """sak494-g: admin BFF routes wire admin_bff_json_openapi_responses."""
    from api.schemas.peel_responses import admin_bff_json_openapi_responses

    bff = (_ROOT / "packages" / "api" / "routes" / "admin_ui_bff.py").read_text(
        encoding="utf-8"
    )
    platform = (_ROOT / "packages" / "api" / "routes" / "platform.py").read_text(
        encoding="utf-8"
    )
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8"
    )

    assert "sak494-g" in peel
    assert admin_bff_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert "admin_bff_json_openapi_responses" in bff
    assert "/enterprise/fleet-dashboard" in bff
    assert "/enterprise/fleet-compare" in bff
    assert "/operator-chat/message" in bff
    assert "first_peel_from_fetches" in bff
    assert "/platform/workspace-readiness" in platform
    assert "capacity_json_openapi_responses" in platform


@pytest.mark.sak494_g
def test_sak494_g_first_peel_from_fetches_propagates_capacity_miss() -> None:
    """sak494-g: enterprise helper surfaces first sub-fetch peel miss."""
    memory = {"tenant_id": "t1", "local_chunk_count": 0}
    hardware = {
        "via": "broker_miss",
        "capacity_source": "broker_miss",
        "status": "degraded",
        "error": "down",
        "feature": "platform_hardware_fleet",
    }
    peel = enterprise_svc.first_peel_from_fetches(memory, hardware)
    assert peel.get("via") == "broker_miss"
    assert peel.get("capacity_source") == "broker_miss"
    assert peel.get("feature") == "platform_hardware_fleet"


@pytest.mark.sak494_g
def test_sak494_g_first_peel_from_fetches_memory_before_worker() -> None:
    """sak494-g: first miss wins among sub-fetch bodies."""
    memory = {
        "via": "broker_miss",
        "status": "degraded",
        "error": "memory down",
        "feature": "fleet_memory_status",
    }
    worker = {
        "via": "broker_miss",
        "status": "degraded",
        "error": "compute down",
        "feature": "fleet_worker_health",
    }
    peel = enterprise_svc.first_peel_from_fetches(memory, worker)
    assert peel.get("feature") == "fleet_memory_status"


# --- sak494-b: fleet-memory rebuild/sync refuse local ---


@pytest.mark.sak494_b
def test_sak494_b_fleet_memory_source_markers() -> None:
    """sak494-b: fleet-memory routes refuse local peel_index under MEMORY=1|2."""
    fleet = (_ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_memory.py").read_text(
        encoding="utf-8",
    )
    route = (_ROOT / "packages" / "memory" / "broker_route.py").read_text(encoding="utf-8")
    assert "sak494-b" in fleet
    assert "map_broker_memory_local_refuse" in route
    assert "sak494-b" in route


# --- sak494-h: admin UI memory peel miss on fleet dashboard ---


@pytest.mark.sak494_h
def test_sak494_h_admin_fleet_memory_peel_markers() -> None:
    """sak494-h: formatReadCatchMessage + FleetDashboardPanel memoryPeelMiss wired."""
    peel = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.ts").read_text(
        encoding="utf-8",
    )
    fleet_page = (_ROOT / "packages" / "admin_ui" / "src" / "pages" / "FleetPage.tsx").read_text(
        encoding="utf-8",
    )
    panel = (
        _ROOT / "packages" / "admin_ui" / "src" / "pages" / "fleet" / "FleetDashboardPanel.tsx"
    ).read_text(encoding="utf-8")
    assert "sak494-h" in peel or "formatReadCatchMessage" in peel
    assert "formatReadCatchMessage" in peel
    assert "memoryPeelMiss" in fleet_page
    assert "sak494-h" in fleet_page
    assert "memoryPeelMiss" in panel


# --- sak494-i: SDK session queue degraded miss ---


@pytest.mark.sak494_i
def test_sak494_i_sdk_session_queue_degraded_markers() -> None:
    """sak494-i: Python SDK nodes-ok + queue-fail → broker_miss/degraded."""
    root = Path(__file__).resolve().parents[3] / "SwissArmyNoife"
    py = (root / "sdks" / "python" / "src" / "swissarmynoife" / "client.py").read_text(
        encoding="utf-8",
    )
    assert "sak494-i" in py
    assert "_broker_session_queue_miss" in py
    assert '"status": "degraded"' in py or "'status': 'degraded'" in py


# --- sak494-j: shared domain peel miss builder refactor ---


@pytest.mark.sak494_j
def test_sak494_j_domain_peel_miss_refactor() -> None:
    """sak494-j: build_domain_peel_miss shared by memory/capacity routes."""
    from broker_client.dual_run_route import build_domain_peel_miss, map_broker_http_miss
    from broker_client.peel_assert import build_http_miss
    from hw import capacity_route
    from memory import broker_route as memory_route

    body = build_domain_peel_miss("down", feature="memory")
    assert body["via"] == "broker_miss"
    assert body["status"] == "degraded"
    assert body["feature"] == "memory"
    assert callable(map_broker_http_miss)
    assert callable(build_http_miss)
    assert callable(memory_route.map_broker_memory_http_miss)
    assert callable(capacity_route.map_broker_capacity_http_miss)

    mem_src = (_ROOT / "packages" / "memory" / "broker_route.py").read_text(encoding="utf-8")
    cap_src = (_ROOT / "packages" / "hw" / "capacity_route.py").read_text(encoding="utf-8")
    dual_src = (_ROOT / "packages" / "broker_client" / "dual_run_route.py").read_text(
        encoding="utf-8",
    )
    assert "map_domain_broker_http_miss" in cap_src  # sak500-a
    assert "sak500-a" in cap_src
    assert "map_domain_broker_http_miss" in mem_src  # sak499-f
    assert "sak499-f" in mem_src
    assert "build_domain_peel_miss" in dual_src
    assert "sak494-j" in dual_src
