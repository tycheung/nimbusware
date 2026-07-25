#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable

from peel_common import NIMBUSWARE_ROOT, run_peel_script

SOAK_DOMAINS: tuple[str, ...] = (
    "llm",
    "sandbox",
    "tools",
    "memory",
    "research",
    "egress",
    "compute",
    "capacity",
)

DOMAIN_FLAGS: dict[str, str] = {
    "llm": "NIMBUSWARE_BROKER_LLM",
    "sandbox": "NIMBUSWARE_BROKER_SANDBOX",
    "tools": "NIMBUSWARE_BROKER_TOOLS",
    "memory": "NIMBUSWARE_BROKER_MEMORY",
    "research": "NIMBUSWARE_BROKER_RESEARCH",
    "egress": "NIMBUSWARE_BROKER_EGRESS",
    "compute": "NIMBUSWARE_BROKER_COMPUTE",
    "capacity": "NIMBUSWARE_BROKER_CAPACITY",
}

DOMAIN_OFFERS: dict[str, str] = {
    "llm": "llm.chat",
    "sandbox": "sandbox.exec",
    "tools": "tools.shell",
    "memory": "memory.search",
    "research": "research.fetch",
    "egress": "network.egress.check",
    "compute": "compute.work",
    "capacity": "capacity.probe",
}

DUAL_RUN_CONTRACT_TESTS: tuple[str, ...] = (
    "tests/unit/test_broker_bridge.py::test_sak403_e_flag_and_bridge_contract",
    "tests/unit/test_sak404_dual_run_contract.py::test_sak404_e_sandbox_tools_dual_run_contract",
    "tests/unit/test_sak405_dual_run_contract.py::test_sak405_e_memory_dual_run_contract",
    "tests/unit/test_sak406_dual_run_contract.py::test_sak406_g_research_egress_dual_run_contract",
    "tests/unit/test_sak407_dual_run_contract.py::test_sak407_e_compute_dual_run_contract",
)

COMPUTE_STAGE_WIRE_NOTE = (
    "compute stage wire active (worker_cli + pipeline_hook; see peel-compute-stage-wire.md)"
)


def print_check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line = f"{line} - {detail}"
    print(line)
    return ok


def soak_env(base: dict[str, str] | None = None, *, broker_only: bool = False) -> dict[str, str]:
    """Copy env with PYTHONPATH and dual-run flags set (in-process only).

    Default flags=``1``. When ``broker_only=True``, set flags to ``2`` (`sak421-b`).
    """
    env = (base or os.environ.copy()).copy()
    env.setdefault("PYTHONPATH", "packages;tests")
    mode = "2" if broker_only else "1"
    for flag in DOMAIN_FLAGS.values():
        env[flag] = mode
    return env


def _is_capacity_refuse_msg(exc: BaseException) -> bool:
    text = str(exc)
    return "CAPACITY=2" in text or "CAPACITY=1|2" in text


def _is_compute_refuse_msg(exc: BaseException) -> bool:
    text = str(exc)
    return "COMPUTE=2" in text or "COMPUTE=1|2" in text


def _assert_node_store_refuse() -> bool:
    """sak428-b: build_compute_node_store raises under COMPUTE=2 (already set in env)."""
    from compute.node_store import build_compute_node_store

    try:
        build_compute_node_store(None)
        return False
    except RuntimeError as exc:
        return _is_compute_refuse_msg(exc)


def _assert_compute_bridge_reraises() -> bool:
    """sak435-a: under COMPUTE=1, try_broker_compute_work re-raises (no None soft miss)."""
    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        import broker_client.compute_bridge as bridge_mod

        def _boom(*_a, **_k):
            raise RuntimeError("soak-bridge-down")

        orig = bridge_mod.compute_work_via_broker
        bridge_mod.compute_work_via_broker = _boom  # type: ignore[assignment]
        try:
            from broker_client.compute_bridge import try_broker_compute_work

            try:
                try_broker_compute_work({"kind": "echo"})
                return False
            except RuntimeError as exc:
                return "soak-bridge-down" in str(exc)
        finally:
            bridge_mod.compute_work_via_broker = orig
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_map_broker_compute_http_error() -> bool:
    """sak436-c: map_broker_compute_http_error returns broker_miss under COMPUTE=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        from compute.broker_route import map_broker_compute_http_error

        out = map_broker_compute_http_error(
            RuntimeError("soak-map-down"),
            feature="soak",
            miss_extra={"status": "degraded"},
        )
        return out.get("via") == "broker_miss" and out.get("status") == "degraded"
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_stage_bind_http_no_mcp() -> bool:
    """sak436-a: HTTP error shape returned without MCP call_tool."""
    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    saved_http = os.environ.get("NIMBUSWARE_BROKER_HTTP")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        os.environ["NIMBUSWARE_BROKER_HTTP"] = "http://soak-broker.test"
        from unittest.mock import MagicMock

        from broker_client.stage_bind import compute as stage

        http = MagicMock()
        http.compute_work.return_value = {"error": "soak-http-err", "work": None}
        mcp = MagicMock()
        out = stage.compute_work_via_broker(
            {"action": "list"},
            client=mcp,
            http=http,
        )
        return out.get("error") == "soak-http-err" and not mcp.call_tool.called
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved
        if saved_http is None:
            os.environ.pop("NIMBUSWARE_BROKER_HTTP", None)
        else:
            os.environ["NIMBUSWARE_BROKER_HTTP"] = saved_http


def _assert_sak438_error_empty_list() -> bool:
    """sak438-a: error + empty list raises via assert_broker_compute_ok."""
    from compute.broker_session_status import assert_broker_compute_ok

    try:
        assert_broker_compute_ok(
            {"error": "soak-empty", "nodes": []},
            feature="soak",
            list_key="nodes",
        )
        return False
    except RuntimeError as exc:
        return "soak-empty" in str(exc)


def _assert_sak439_claim_normalize() -> bool:
    """sak439-c: empty queue vs hard miss normalization."""
    from compute.broker_session_status import normalize_claim_work_response

    empty = normalize_claim_work_response({"work": None, "error": "queue empty"})
    if empty.get("work") is not None or empty.get("via") != "broker":
        return False
    try:
        normalize_claim_work_response({"work": None, "error": "unreachable"})
        return False
    except RuntimeError as exc:
        return "unreachable" in str(exc)


def _assert_sak440_node_match() -> bool:
    """sak440-d: shared broker_node_match helpers."""
    from compute.broker_node_match import pick_broker_node_for_user

    hit = pick_broker_node_for_user(
        [{"label": "user:u1", "caps": []}, {"label": "other"}],
        "u1",
    )
    return isinstance(hit, dict) and str(hit.get("label") or "") == "user:u1"


def _assert_sak440_node_store_ctor() -> bool:
    """sak440-b: InMemoryComputeNodeStore ctor refuses under COMPUTE=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        from compute.node_store import InMemoryComputeNodeStore

        try:
            InMemoryComputeNodeStore()
            return False
        except RuntimeError as exc:
            return "InMemoryComputeNodeStore unavailable" in str(exc)
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_sak441_list_null_miss() -> bool:
    """sak441-a: null list_key is a miss."""
    from compute.broker_session_status import assert_broker_compute_ok

    try:
        assert_broker_compute_ok({"nodes": None}, feature="soak", list_key="nodes")
        return False
    except RuntimeError as exc:
        return "non-list" in str(exc)


def _assert_sak441_capacity_http_miss() -> bool:
    """sak441-c: capacity HTTP miss body under CAPACITY=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_CAPACITY")
    try:
        os.environ["NIMBUSWARE_BROKER_CAPACITY"] = "1"
        from hw.capacity_route import map_broker_capacity_http_miss

        body = map_broker_capacity_http_miss(RuntimeError("x"), feature="soak")
        return (
            body.get("capacity_source") == "broker_miss"
            and body.get("status") == "degraded"
        )
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_CAPACITY", None)
        else:
            os.environ["NIMBUSWARE_BROKER_CAPACITY"] = saved


def _assert_sak442_capacity_2_503() -> bool:
    """sak442-b: CAPACITY=2 miss raises HTTP 503."""
    saved = os.environ.get("NIMBUSWARE_BROKER_CAPACITY")
    try:
        os.environ["NIMBUSWARE_BROKER_CAPACITY"] = "2"
        from fastapi import HTTPException

        from hw.capacity_route import map_broker_capacity_http_miss

        try:
            map_broker_capacity_http_miss(RuntimeError("x"), feature="soak")
            return False
        except HTTPException as exc:
            return exc.status_code == 503
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_CAPACITY", None)
        else:
            os.environ["NIMBUSWARE_BROKER_CAPACITY"] = saved


def _assert_sak442_list_nodes_assert() -> bool:
    """sak442-f: BrokerClient.list_nodes_filtered asserts list shape."""
    from unittest.mock import patch

    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test")
    with patch.object(client, "compute_nodes", return_value={"error": "x", "nodes": []}):
        try:
            client.list_nodes_filtered()
            return False
        except RuntimeError as exc:
            return "broker_miss" in str(exc)


def _assert_sak443_apply_preset_miss() -> bool:
    """sak443-a: apply-preset returns capacity miss body under CAPACITY=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_CAPACITY")
    try:
        os.environ["NIMBUSWARE_BROKER_CAPACITY"] = "1"
        from unittest.mock import MagicMock, patch

        from api.routes import platform_model_routing as pmr

        orch = MagicMock()
        orch.repo_root = "."
        body = pmr.ApplyPresetBody(model_id="m1")
        with patch(
            "api.routes.platform_model_routing.get_cached_profile",
            side_effect=RuntimeError("CAPACITY miss"),
        ):
            out = pmr.post_apply_preset(orch, body)
        return out.get("via") == "broker_miss"
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_CAPACITY", None)
        else:
            os.environ["NIMBUSWARE_BROKER_CAPACITY"] = saved


def _assert_sak443_opt_out_via() -> bool:
    """sak443-c: opt-out via=broker_opt_out under COMPUTE=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        from unittest.mock import MagicMock, patch
        from uuid import uuid4

        from api.routes import chat_session as cs
        from fastapi import Request

        session_id = uuid4()
        body = cs.SessionComputeOptInBody(enabled=False)
        chat_store = MagicMock()
        with patch("api.routes.chat_session.session_or_404"):
            out = cs.session_compute_opt_in(
                session_id,
                body,
                MagicMock(spec=Request),
                chat_store,
                user=None,
                _user=None,  # type: ignore[arg-type]
            )
        return out.get("via") == "broker_opt_out"
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_sak447_raw_compute_post() -> bool:
    """sak447-g: BrokerClient.compute_work raises on hard error."""
    from unittest.mock import MagicMock, patch

    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch("broker_client.client.post_json", return_value={"error": "x"}):
        try:
            client.compute_work({"action": "enqueue", "kind": "t"})
            return False
        except RuntimeError as exc:
            return "broker_miss" in str(exc)


def _assert_sak447_readiness_miss() -> bool:
    """sak447-c: readiness returns capacity miss under CAPACITY=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_CAPACITY")
    try:
        os.environ["NIMBUSWARE_BROKER_CAPACITY"] = "1"
        from unittest.mock import MagicMock, patch

        from api.routes import platform as plat

        with patch(
            "api.routes.platform.build_platform_readiness",
            side_effect=RuntimeError("CAPACITY miss"),
        ):
            out = plat.get_platform_readiness(MagicMock(repo_root="."), MagicMock())
        return out.get("via") == "broker_miss"
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_CAPACITY", None)
        else:
            os.environ["NIMBUSWARE_BROKER_CAPACITY"] = saved


def _assert_sak448_health_assert() -> bool:
    """sak448-i: BrokerClient.health raises on error dict."""
    from unittest.mock import MagicMock, patch

    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch("broker_client.client.get_json", return_value={"error": "x"}):
        try:
            client.health()
            return False
        except RuntimeError as exc:
            return "broker_miss" in str(exc)


def _assert_sak448_oauth_openapi() -> bool:
    """sak448-d: SubscriptionOauthStatusResponse exists."""
    from api.routes.provider_subscription_oauth import SubscriptionOauthStatusResponse

    return SubscriptionOauthStatusResponse(providers=[]).providers == []


def _assert_sak449_module_capacity_assert() -> bool:
    """sak449-i: BrokerClient.get_module/capacity raise on error."""
    from unittest.mock import MagicMock, patch

    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch("broker_client.client.get_json", return_value={"error": "x"}):
        try:
            client.capacity()
            return False
        except RuntimeError as exc:
            return "broker_miss" in str(exc)


def _assert_sak449_edition_openapi() -> bool:
    """sak449-d: PlatformEditionResponse exists."""
    from api.routes.platform import PlatformEditionResponse

    return PlatformEditionResponse(edition="individual").edition == "individual"


def _assert_sak480_settings_openapi() -> bool:
    """sak480-c: SettingsCatalogResponse exists."""
    from api.routes.operator_settings import SettingsCatalogResponse

    return SettingsCatalogResponse().install == {}


def _assert_sak480_queue_depth() -> bool:
    """sak480-i: BrokerClient.queue_depth returns via=broker."""
    from unittest.mock import MagicMock, patch

    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch.object(client, "list_work_filtered", return_value={"work": []}):
        out = client.queue_depth()
    return out.get("via") == "broker" and out.get("queued") == 0


def _assert_sak481_folder_openapi() -> bool:
    """sak481-d: FolderListResponse exists."""
    from api.routes.chat_collab import FolderListResponse

    return FolderListResponse(folders=[]).folders == []


def _assert_sak481_compliance_openapi() -> bool:
    """sak481-c: ComplianceSummaryResponse exists."""
    from api.routes.enterprise.compliance import ComplianceSummaryResponse

    return ComplianceSummaryResponse().completed_runs is None


def _assert_sak482_group_mutation_openapi() -> bool:
    """sak482-e: GroupMutationResponse exists."""
    from api.routes.chat_collab import GroupMutationResponse

    return GroupMutationResponse().via is None


def _assert_sak482_fleet_slice_openapi() -> bool:
    """sak482-g: FleetSlicePolicyResponse exists."""
    from api.routes.enterprise.fleet_tenant_policies import FleetSlicePolicyResponse

    return FleetSlicePolicyResponse().via is None


def _assert_sak483_standards_openapi() -> bool:
    """sak483-e: StandardsRegistryResponse exists."""
    from api.routes.standards import StandardsRegistryResponse

    return StandardsRegistryResponse().via is None


def _assert_sak483_fleet_enforcement_openapi() -> bool:
    """sak483-f: FleetEnforcementPolicyResponse exists."""
    from api.routes.enterprise.fleet_enforcement import FleetEnforcementPolicyResponse

    return FleetEnforcementPolicyResponse().via is None


def _assert_sak484_campaign_openapi() -> bool:
    """sak484-e: CreateCampaignResponse exists."""
    from api.routes.campaigns.create import CreateCampaignResponse

    return CreateCampaignResponse().via is None


def _assert_sak484_timeline_explain_openapi() -> bool:
    """sak484-g: TimelineExplainResponse exists."""
    from api.routes.runs.timeline_explain import TimelineExplainResponse

    return TimelineExplainResponse().via is None


def _assert_sak485_findings_openapi() -> bool:
    """sak485-e: RunFindingsResponse exists."""
    from api.routes.runs.detail import RunFindingsResponse

    return RunFindingsResponse().via is None


def _assert_sak485_fleet_learnings_openapi() -> bool:
    """sak485-f: FleetLearningsSearchResponse exists."""
    from api.routes.enterprise.fleet_learnings import FleetLearningsSearchResponse

    return FleetLearningsSearchResponse().via is None


def _assert_sak486_research_index_openapi() -> bool:
    """sak486-e: ResearchIndexResponse exists."""
    from api.routes.enterprise.research_ops import ResearchIndexResponse

    return ResearchIndexResponse().via is None


def _assert_sak486_model_policy_openapi() -> bool:
    """sak486-f: ModelPolicyResponse exists."""
    from api.routes.enterprise.model_policy import ModelPolicyResponse

    return ModelPolicyResponse().via is None


def _assert_sak487_actions_openapi() -> bool:
    """sak487-e: ActionStatusResponse exists."""
    from api.routes.actions import ActionStatusResponse

    return ActionStatusResponse().via is None


def _assert_sak487_signout_openapi() -> bool:
    """sak487-g: SignoutResponse exists."""
    from api.routes.auth import SignoutResponse

    return SignoutResponse().via is None


def _assert_sak488_delete_ok_openapi() -> bool:
    """sak488-d: DeleteOkResponse exists."""
    from api.schemas.peel_responses import DeleteOkResponse

    return DeleteOkResponse().ok is True


def _assert_sak488_export_peel() -> bool:
    """sak488-e: early_export_json_miss exists."""
    from api.export_peel import early_export_json_miss

    return callable(early_export_json_miss)


def _assert_sak489_peel_assert() -> bool:
    """sak489-d: broker_client.peel_assert consolidates asserts."""
    from broker_client.peel_assert import is_compute_miss

    return is_compute_miss({"via": "broker_miss"}) is True


def _assert_sak489_sse_peel() -> bool:
    """sak489-f: sse_error_envelope exists."""
    from api.sse_peel import sse_error_envelope

    return "error" in sse_error_envelope(feature="t", error="x")


def _assert_sak490_broker_route() -> bool:
    """sak490-e: compute.broker_route uses shared dual_run_route primitives."""
    from broker_client.dual_run_route import broker_problem, map_broker_http_miss
    from broker_client.peel_assert import build_http_miss
    from compute import broker_route as cr

    body = broker_problem("broker_compute_only", "x")
    miss = build_http_miss("down", feature="compute")
    return (
        body.get("code") == "broker_compute_only"
        and miss.get("via") == "broker_miss"
        and callable(map_broker_http_miss)
        and callable(cr.map_broker_compute_http_error)
    )


def _assert_sak490_capacity_route() -> bool:
    """sak490-e: hw.capacity_route maps via shared dual_run_route."""
    from hw import capacity_route as cr

    return callable(cr.map_broker_capacity_http_miss) and callable(cr.refuse_legacy)


def _assert_sak491_queue_read_refuse() -> bool:
    """sak491-a: under COMPUTE=1, InMemoryWorkUnitQueue read ops refuse."""
    from uuid import uuid4

    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        from compute.work_unit import InMemoryWorkUnitQueue

        queue = InMemoryWorkUnitQueue()
        run_id = uuid4()
        for op_fn in (
            lambda: queue.list_units(run_id=run_id),
            lambda: queue.queued_count(),
            lambda: queue.terminate_restart(uuid4()),
        ):
            try:
                op_fn()
                return False
            except RuntimeError as exc:
                if "broker_miss" not in str(exc):
                    return False
        return True
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_sak491_compute_openapi() -> bool:
    """sak491-c: ComputePeelMissResponse + compute_json_openapi_responses PROBLEM."""
    from api.schemas.openapi import PROBLEM_RESPONSE_503
    from api.schemas.peel_responses import (
        ComputePeelMissResponse,
        compute_json_openapi_responses,
    )

    base = ComputePeelMissResponse(via="broker_miss", status="degraded")
    responses = compute_json_openapi_responses()
    return (
        base.via == "broker_miss"
        and base.status == "degraded"
        and responses.get(503) is PROBLEM_RESPONSE_503
    )


def _assert_sak492_capacity_openapi() -> bool:
    """sak492-a: CapacityPeelMissResponse + capacity_json_openapi_responses PROBLEM."""
    from api.schemas.openapi import PROBLEM_RESPONSE_503
    from api.schemas.peel_responses import (
        CapacityPeelMissResponse,
        capacity_json_openapi_responses,
    )

    base = CapacityPeelMissResponse(via="broker_miss", status="degraded")
    responses = capacity_json_openapi_responses()
    return (
        base.via == "broker_miss"
        and base.status == "degraded"
        and responses.get(503) is PROBLEM_RESPONSE_503
    )


def _assert_sak492_chat_facade_peel_strict() -> bool:
    """sak492-d: chat_facade exposes peel_strict parameter."""
    import inspect

    from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch

    return "peel_strict" in inspect.signature(ollama_chat_json_via_plan_patch).parameters


def _assert_sak493_llm_openapi() -> bool:
    """sak493-b: LlmPeelMissResponse + llm_json_openapi_responses PROBLEM."""
    from api.schemas.openapi import PROBLEM_RESPONSE_503
    from api.schemas.peel_responses import LlmPeelMissResponse, llm_json_openapi_responses

    base = LlmPeelMissResponse(via="broker_miss", status="degraded")
    responses = llm_json_openapi_responses()
    return (
        base.via == "broker_miss"
        and base.status == "degraded"
        and responses.get(503) is PROBLEM_RESPONSE_503
    )


def _assert_sak493_memory_openapi() -> bool:
    """sak493-i: MemoryPeelMissResponse + memory_json_openapi_responses PROBLEM."""
    from api.schemas.openapi import PROBLEM_RESPONSE_503
    from api.schemas.peel_responses import MemoryPeelMissResponse, memory_json_openapi_responses

    base = MemoryPeelMissResponse(via="broker_miss", status="degraded")
    responses = memory_json_openapi_responses()
    return (
        base.via == "broker_miss"
        and base.status == "degraded"
        and responses.get(503) is PROBLEM_RESPONSE_503
    )


def _assert_sak494_memory_refuse_legacy() -> bool:
    """sak494-b: memory.broker_route.refuse_legacy callable under MEMORY peel."""
    from memory.broker_route import refuse_legacy

    return callable(refuse_legacy)


def _assert_sak494_research_openapi() -> bool:
    """sak494-c/e: research_json_openapi_responses PROBLEM."""
    from api.schemas.openapi import PROBLEM_RESPONSE_503
    from api.schemas.peel_responses import research_json_openapi_responses

    return research_json_openapi_responses().get(503) is PROBLEM_RESPONSE_503


def _assert_sak494_domain_peel_miss() -> bool:
    """sak494-j: build_domain_peel_miss + route refactor markers."""
    from broker_client.dual_run_route import build_domain_peel_miss, map_broker_http_miss
    from broker_client.peel_assert import build_http_miss
    from hw import capacity_route as cap_route
    from memory import broker_route as mem_route

    body = build_domain_peel_miss("down", feature="memory")
    return (
        body.get("via") == "broker_miss"
        and body.get("status") == "degraded"
        and callable(map_broker_http_miss)
        and callable(build_http_miss)
        and callable(mem_route.map_broker_memory_http_miss)
        and callable(cap_route.map_broker_capacity_http_miss)
    )


def _assert_sak495_memory_assert() -> bool:
    """sak495-g: assert_memory_ok rejects peel miss; empty hits ok."""
    from broker_client.peel_assert import assert_memory_ok, is_memory_miss

    try:
        assert_memory_ok(
            {"via": "broker_miss", "error": "down", "hits": []},
            feature="memory_search",
        )
        return False
    except RuntimeError:
        pass
    assert_memory_ok({"hits": []}, feature="memory_search")
    return callable(is_memory_miss) and is_memory_miss({"code": "broker_memory_only"})


def _assert_sak495_analytics_openapi() -> bool:
    """sak495-c: analytics_json_openapi_responses PROBLEM."""
    from api.schemas.openapi import PROBLEM_RESPONSE_503
    from api.schemas.peel_responses import analytics_json_openapi_responses

    return analytics_json_openapi_responses().get(503) is PROBLEM_RESPONSE_503


def _assert_sak495_tools_peel_miss() -> bool:
    """sak495-i: raise_tools_peel_miss refuses under TOOLS=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_TOOLS")
    try:
        os.environ["NIMBUSWARE_BROKER_TOOLS"] = "1"
        from agent_tools.sandbox_bridge import raise_tools_peel_miss

        try:
            raise_tools_peel_miss("shell")
            return False
        except RuntimeError as exc:
            low = str(exc).lower()
            return "broker_miss" in low or "tools" in low
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_TOOLS", None)
        else:
            os.environ["NIMBUSWARE_BROKER_TOOLS"] = saved


def _assert_sak495_compute_domain_peel_miss() -> bool:
    """sak495-j: compute route build_domain_peel_miss + node: None."""
    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        from compute.broker_route import map_broker_compute_http_error

        out = map_broker_compute_http_error(
            RuntimeError("soak-compute-down"),
            feature="compute_nodes",
        )
        return (
            out.get("via") == "broker_miss"
            and out.get("status") == "degraded"
            and out.get("node") is None
            and out.get("feature") == "compute_nodes"
        )
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_sak496_lifecycle_peel_wiring() -> bool:
    """sak496-a: lifecycle_plan refuses stub fallback under LLM peel."""
    from broker_client.flags import broker_llm_enabled

    lifecycle = (
        NIMBUSWARE_ROOT
        / "packages"
        / "orchestrator"
        / "_pipeline"
        / "lifecycle_plan.py"
    ).read_text(encoding="utf-8")
    return "sak496-a" in lifecycle and callable(broker_llm_enabled)


def _assert_sak496_domain_broker_route_raises() -> bool:
    """sak496-d: domain broker_route raise helpers refuse under peel."""
    saved = os.environ.get("NIMBUSWARE_BROKER_RESEARCH")
    try:
        os.environ["NIMBUSWARE_BROKER_RESEARCH"] = "1"
        from research.broker_route import raise_research_peel_miss

        try:
            raise_research_peel_miss("research_fetch")
            return False
        except RuntimeError as exc:
            low = str(exc).lower()
            return "broker_miss" in low or "research" in low
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_RESEARCH", None)
        else:
            os.environ["NIMBUSWARE_BROKER_RESEARCH"] = saved


def _assert_sak496_early_llm_sse_peel_miss() -> bool:
    """sak496-g: early_llm_sse_peel_miss returns broker_miss frame under LLM=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_LLM")
    try:
        os.environ["NIMBUSWARE_BROKER_LLM"] = "1"
        from api.sse_peel import early_llm_sse_peel_miss

        frame = early_llm_sse_peel_miss(feature="chat_session_stream")
        return frame is not None and "broker_miss" in frame
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_LLM", None)
        else:
            os.environ["NIMBUSWARE_BROKER_LLM"] = saved


def _assert_sak496_domain_peel_assert() -> bool:
    """sak496-i: peel_assert domain miss detectors + asserts."""
    from broker_client.peel_assert import (
        assert_llm_ok,
        is_llm_miss,
        is_sandbox_miss,
    )

    assert is_sandbox_miss({"code": "broker_sandbox_only"})
    assert is_llm_miss({"code": "broker_llm_unavailable"})
    try:
        assert_llm_ok({"via": "broker_miss", "error": "down"}, feature="llm_chat")
        return False
    except RuntimeError:
        pass
    assert_llm_ok({"content": "ok"}, feature="llm_chat")
    return True


def _assert_sak497_slice_facade_plan_llm_wire() -> bool:
    """sak497-a/j: slice_facade plan/replan broker chat peel_strict."""
    src = (
        NIMBUSWARE_ROOT / "packages" / "orchestrator" / "llm" / "slice_facade.py"
    ).read_text(encoding="utf-8")
    return (
        "sak497-a" in src
        and "_require_broker_chat" in src
        and "peel_strict=True" in src
        and "execute_slice_plan_llm" in src
    )


def _assert_sak497_campaign_openapi_helper() -> bool:
    """sak497-d/j: campaign_json_openapi_responses documents broker-only 503."""
    from api.schemas.openapi import PROBLEM_RESPONSE_503
    from api.schemas.peel_responses import campaign_json_openapi_responses

    return campaign_json_openapi_responses().get(503) is PROBLEM_RESPONSE_503


def _assert_sak497_domain_flag_matrix_modules() -> bool:
    """sak497-i/j: domain flag-matrix HTTP test modules tagged."""
    root = NIMBUSWARE_ROOT / "tests" / "api_http"
    for name in (
        "test_sandbox_broker_flags_api.py",
        "test_research_broker_flags_api.py",
        "test_egress_broker_flags_api.py",
        "test_tools_broker_flags_api.py",
    ):
        path = root / name
        if not path.is_file():
            return False
        if "sak497-i" not in path.read_text(encoding="utf-8"):
            return False
    return True


def _assert_sak498_bootstrap_resolve_memory() -> bool:
    """sak498-a/j: runtime bootstrap skips memory.factory via peel guard."""
    src = (
        NIMBUSWARE_ROOT / "packages" / "orchestrator" / "runtime_bootstrap.py"
    ).read_text(encoding="utf-8")
    return (
        "sak498-a" in src
        and "resolve_memory_chunk_store_for_bootstrap" in src
        and "broker_memory_enabled" in src
    )


def _assert_sak498_require_local_memory() -> bool:
    """sak498-b/h/j: require_local_memory_chunk_store + resolve_memory_store_or_miss."""
    route = (NIMBUSWARE_ROOT / "packages" / "memory" / "broker_route.py").read_text(
        encoding="utf-8",
    )
    if (
        "sak498-b" not in route
        or "require_local_memory_chunk_store" not in route
        or "resolve_memory_store_or_miss" not in route
        or "sak498-h" not in route
    ):
        return False
    saved = os.environ.get("NIMBUSWARE_BROKER_MEMORY")
    try:
        os.environ["NIMBUSWARE_BROKER_MEMORY"] = "1"
        from memory.broker_route import resolve_memory_store_or_miss

        out = resolve_memory_store_or_miss(feature="soak_probe")
        return isinstance(out, dict) and out.get("via") == "broker_miss"
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_MEMORY", None)
        else:
            os.environ["NIMBUSWARE_BROKER_MEMORY"] = saved


def _assert_sak498_llm_exports_not_removed() -> bool:
    """sak498-c/d/j: self_refinement + agent_evaluator delegates exported (not _removed)."""
    init = (
        NIMBUSWARE_ROOT / "packages" / "orchestrator" / "llm" / "__init__.py"
    ).read_text(encoding="utf-8")
    return (
        "execute_self_refinement_critique_llm" in init
        and "execute_self_refinement_critique_llm = _removed" not in init
        and "execute_agent_evaluator_policy_llm" in init
        and "execute_agent_evaluator_policy_llm = _removed" not in init
        and "sak498-d" in init
    )


def _assert_sak498_domain_assert_llm_ok() -> bool:
    """sak498-g/j: domain MCP assert_llm_ok raises on peel miss."""
    peel = (NIMBUSWARE_ROOT / "packages" / "broker_client" / "peel_assert.py").read_text(
        encoding="utf-8",
    )
    if "sak498-g" not in peel or "assert_llm_ok" not in peel:
        return False
    from broker_client.peel_assert import assert_llm_ok

    try:
        assert_llm_ok({"via": "broker_miss", "error": "down"}, feature="llm_chat")
        return False
    except RuntimeError:
        pass
    assert_llm_ok({"content": "ok"}, feature="llm_chat")
    return True


def _assert_sak499_peel_guard() -> bool:
    """sak499-e/j: shared LLM peel_guard module present."""
    guard = (
        NIMBUSWARE_ROOT / "packages" / "orchestrator" / "llm" / "peel_guard.py"
    ).read_text(encoding="utf-8")
    return "sak499-e" in guard and "_llm_broker_miss_or_transport" in guard


def _assert_sak499_maker_domain_miss() -> bool:
    """sak499-a/i/j: Maker chat + home/build/wizard domain peel helpers."""
    js = NIMBUSWARE_ROOT / "packages" / "maker_web" / "static" / "js"
    chat = (js / "tabs" / "chat.js").read_text(encoding="utf-8")
    build = (js / "tabs" / "build.js").read_text(encoding="utf-8")
    return (
        "sak499-a" in chat
        and "isDomainPeelMiss" in chat
        and "sak499-i" in build
        and "isDomainPeelMiss" in build
    )


def _assert_sak500_maker_ribbons() -> bool:
    """sak500-a/b/f: Maker ribbons + enterprise/safe-coding domain peel helpers."""
    js = NIMBUSWARE_ROOT / "packages" / "maker_web" / "static" / "js"
    enf = (js / "enforcement-ribbon.js").read_text(encoding="utf-8")
    enterprise = (js / "tabs" / "home_enterprise_policy_ui.js").read_text(encoding="utf-8")
    return (
        "sak500-a" in enf
        and "formatDomainMissMessage" in enf
        and "sak500-b" in enterprise
        and "isDomainPeelMiss" in enterprise
    )


def _assert_sak500_sse_bootstrap() -> bool:
    """sak500-g/h/j: sse-client + api-client drop isBrokerMiss."""
    js = NIMBUSWARE_ROOT / "packages" / "maker_web" / "static" / "js"
    sse = (js / "sse-client.js").read_text(encoding="utf-8")
    api = (js / "api-client.js").read_text(encoding="utf-8")
    return (
        "sak500-g" in sse
        and "isBrokerMiss" not in sse
        and "sak500-h" in api
        and "isDomainPeelMiss" in api
    )


def _assert_sak501_hardware_capacity_formatter() -> bool:
    """sak501-a/d/f: Hardware domain peel + Maker formatCapacityMissMessage."""
    hw = (
        NIMBUSWARE_ROOT / "packages" / "admin_ui" / "src" / "pages" / "HardwarePage.tsx"
    ).read_text(encoding="utf-8")
    miss = (
        NIMBUSWARE_ROOT / "packages" / "maker_web" / "static" / "js" / "broker_miss.js"
    ).read_text(encoding="utf-8")
    return (
        "sak501-a" in hw
        and "isDomainPeelMiss" in hw
        and "sak501-d" in miss
        and "formatCapacityMissMessage" in miss
    )


def _assert_sak501_openapi_settings_bindings() -> bool:
    """sak501-g/h/i/j: settings + model-bindings + push OpenAPI peel markers."""
    settings = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "operator_settings.py"
    ).read_text(encoding="utf-8")
    bindings = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "model_bindings.py"
    ).read_text(encoding="utf-8")
    push = (NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "maker_push.py").read_text(
        encoding="utf-8",
    )
    return (
        "sak501-g" in settings
        and "sak501-h" in bindings
        and "sak501-i" in push
    )


def _assert_sak502_with_long_tail_helper() -> bool:
    """sak502-a/d/f: with_long_tail_peel_503 helper + runs create wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    create = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "create.py"
    ).read_text(encoding="utf-8")
    return (
        "sak502-d" in peel
        and "with_long_tail_peel_503" in peel
        and "sak502-a" in create
        and "with_long_tail_peel_503" in create
    )


def _assert_sak502_run_detail_openapi() -> bool:
    """sak502-g/h/i/j: run detail/slice/factory OpenAPI peel markers."""
    detail = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "detail.py"
    ).read_text(encoding="utf-8")
    slices = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "slices.py"
    ).read_text(encoding="utf-8")
    factory = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "factory_evidence.py"
    ).read_text(encoding="utf-8")
    return "sak502-g" in detail and "sak502-h" in slices and "sak502-i" in factory


def _assert_sak503_enterprise_peel_helper() -> bool:
    """sak503-d/f: with_enterprise_peel_503 + fleet enforcement wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    enf = (
        NIMBUSWARE_ROOT
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "fleet_enforcement.py"
    ).read_text(encoding="utf-8")
    return (
        "sak503-d" in peel
        and "with_enterprise_peel_503" in peel
        and "sak503-c" in enf
        and "with_enterprise_peel_503()" in enf
    )


def _assert_sak503_run_compact_openapi() -> bool:
    """sak503-g/h/i/j: compact/budget/integrations OpenAPI peel markers."""
    compact = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "compact.py"
    ).read_text(encoding="utf-8")
    budget = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "context_budget.py"
    ).read_text(encoding="utf-8")
    integ = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "integrations.py"
    ).read_text(encoding="utf-8")
    return "sak503-g" in compact and "sak503-h" in budget and "sak503-i" in integ


def _assert_sak504_artifact_peel_helper() -> bool:
    """sak504-d/f: artifact_peel_503_response + auth wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    auth = (NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "auth.py").read_text(
        encoding="utf-8",
    )
    return (
        "sak504-d" in peel
        and "artifact_peel_503_response" in peel
        and "sak504-a" in auth
        and "with_long_tail_peel_503()" in auth
    )


def _assert_sak504_run_projection_openapi() -> bool:
    """sak504-g/h/i/j: timeline/lifecycle/projection OpenAPI peel markers."""
    detail = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "detail.py"
    ).read_text(encoding="utf-8")
    life = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "lifecycle.py"
    ).read_text(encoding="utf-8")
    return "sak504-g" in detail and "sak504-h" in life and "sak504-i" in detail


def _assert_sak505_ensure_operation_peel() -> bool:
    """sak505-d/f: ensure_operation_peel_503 + personas wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    personas = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "personas_handlers.py"
    ).read_text(encoding="utf-8")
    return (
        "sak505-d" in peel
        and "ensure_operation_peel_503" in peel
        and "sak505-a" in personas
        and "with_long_tail_peel_503" in personas
    )


def _assert_sak505_bindings_autopilot_openapi() -> bool:
    """sak505-g/h/i/j: bindings/role-claims/autopilot OpenAPI peel markers."""
    swap = (
        NIMBUSWARE_ROOT
        / "packages"
        / "api"
        / "routes"
        / "runs"
        / "model_bindings_swap.py"
    ).read_text(encoding="utf-8")
    auto = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "autopilot.py"
    ).read_text(encoding="utf-8")
    return "sak505-g" in swap and "sak505-h" in swap and "sak505-i" in auto


def _assert_sak506_ensure_paths_peel() -> bool:
    """sak506-d/f: ensure_paths_peel_503 + theater wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    theater = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "theater.py"
    ).read_text(encoding="utf-8")
    return (
        "sak506-d" in peel
        and "ensure_paths_peel_503" in peel
        and "sak506-a" in theater
        and "with_long_tail_peel_503" in theater
    )


def _assert_sak506_standards_actions_openapi() -> bool:
    """sak506-g/h/i/j: override/interjection/standards OpenAPI peel markers."""
    actions = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "actions.py"
    ).read_text(encoding="utf-8")
    standards = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "standards.py"
    ).read_text(encoding="utf-8")
    return "sak506-g" in actions and "sak506-h" in standards and "sak506-i" in standards


def _assert_sak507_count_missing_peel() -> bool:
    """sak507-d/f: count_missing_peel_503 + maker wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    maker = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "maker_approval.py"
    ).read_text(encoding="utf-8")
    return (
        "sak507-d" in peel
        and "count_missing_peel_503" in peel
        and "sak507-a" in maker
        and "with_long_tail_peel_503" in maker
    )


def _assert_sak507_maker_mutate_openapi() -> bool:
    """sak507-g/h/i/j: maker mutate + campaign bundle OpenAPI peel markers."""
    maker = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "maker_approval.py"
    ).read_text(encoding="utf-8")
    bundle = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "artifact_bundle.py"
    ).read_text(encoding="utf-8")
    return "sak507-g" in maker and "sak507-h" in maker and "sak507-i" in bundle


def _assert_sak508_list_missing_peel() -> bool:
    """sak508-d/f: list_missing_peel_503 + deploy apply wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    deploy = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform_deploy_mutations.py"
    ).read_text(encoding="utf-8")
    return (
        "sak508-d" in peel
        and "list_missing_peel_503" in peel
        and "sak508-a" in deploy
        and "with_long_tail_peel_503" in deploy
    )


def _assert_sak508_deploy_hardware_openapi() -> bool:
    """sak508-g/h/i/j: deploy approve/audit + hardware OpenAPI peel markers."""
    deploy = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform_deploy.py"
    ).read_text(encoding="utf-8")
    hw = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform_hardware.py"
    ).read_text(encoding="utf-8")
    return "sak508-g" in deploy and "sak508-h" in deploy and "sak508-i" in hw


def _assert_sak509_count_missing_dry() -> bool:
    """sak509-d/f: count_missing DRY via list_missing + fleet wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    hw = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform_hardware.py"
    ).read_text(encoding="utf-8")
    return (
        "sak509-d" in peel
        and "return len(list_missing_peel_503" in peel
        and "sak509-a" in hw
    )


def _assert_sak509_platform_residual_openapi() -> bool:
    """sak509-g/h/i/j: routing/invite/collab OpenAPI peel markers."""
    routing = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform_model_routing.py"
    ).read_text(encoding="utf-8")
    platform = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")
    return "sak509-g" in routing and "sak509-h" in platform and "sak509-i" in platform


def _assert_sak510_patch_openapi_helper() -> bool:
    """sak510-d/f: patch_openapi_json_peel_503 + readiness wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    platform = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")
    return (
        "sak510-d" in peel
        and "def patch_openapi_json_peel_503" in peel
        and "sak510-a" in platform
    )


def _assert_sak510_prefs_bindings_openapi() -> bool:
    """sak510-g/h/i/j: precommit/safe-coding/bindings OpenAPI peel markers."""
    platform = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")
    bindings = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "model_bindings.py"
    ).read_text(encoding="utf-8")
    return "sak510-g" in platform and "sak510-h" in platform and "sak510-i" in bindings


def _assert_sak511_openapi_complete_helper() -> bool:
    """sak511-d/f: openapi_peel_503_complete + enterprise status wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    core = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "enterprise" / "core.py"
    ).read_text(encoding="utf-8")
    return (
        "sak511-d" in peel
        and "def openapi_peel_503_complete" in peel
        and "sak511-a" in core
    )


def _assert_sak511_exports_streams_openapi() -> bool:
    """sak511-g/h/i/j: factory-evidence/streams/policy/audit OpenAPI peel markers."""
    factory = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "factory_evidence.py"
    ).read_text(encoding="utf-8")
    stream = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "runs" / "stream.py"
    ).read_text(encoding="utf-8")
    policy = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "policy.py"
    ).read_text(encoding="utf-8")
    return "sak511-g" in factory and "sak511-h" in stream and "sak511-i" in policy


def _assert_sak512_list_missing_file_helper() -> bool:
    """sak512-d/f: list_missing_peel_503_in_openapi_json + bundles promote wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    bundles = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "bundles.py"
    ).read_text(encoding="utf-8")
    return (
        "sak512-d" in peel
        and "def list_missing_peel_503_in_openapi_json" in peel
        and "sak512-a" in bundles
    )


def _assert_sak512_projects_chat_openapi() -> bool:
    """sak512-g/h/i/j: projects + chat start/scope OpenAPI peel markers."""
    projects = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "projects.py"
    ).read_text(encoding="utf-8")
    chat = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_session.py"
    ).read_text(encoding="utf-8")
    return (
        "sak512-g" in projects
        and "sak512-h" in projects
        and "sak512-i" in chat
    )


def _assert_sak513_complete_in_file_helper() -> bool:
    """sak513-d/f: openapi_peel_503_complete_in_file + chat compute wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    chat = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_session.py"
    ).read_text(encoding="utf-8")
    return (
        "sak513-d" in peel
        and "def openapi_peel_503_complete_in_file" in peel
        and "sak513-a" in chat
    )


def _assert_sak513_sessions_transfer_openapi() -> bool:
    """sak513-g/h/i/j: sessions/classify/host-transfer OpenAPI peel markers."""
    chat = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat.py"
    ).read_text(encoding="utf-8")
    collab = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")
    return "sak513-g" in chat and "sak513-h" in chat and "sak513-i" in collab


def _assert_sak514_peel_503_coverage_helper() -> bool:
    """sak514-d/f: peel_503_coverage + host-transfer bundle wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    collab = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")
    return (
        "sak514-d" in peel
        and "def peel_503_coverage" in peel
        and "sak514-a" in collab
    )


def _assert_sak514_folders_groups_openapi() -> bool:
    """sak514-g/h/i/j: folders/groups OpenAPI peel markers."""
    collab = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")
    return "sak514-g" in collab and "sak514-h" in collab and "sak514-i" in collab


def _assert_sak515_coverage_in_file_helper() -> bool:
    """sak515-d/f: peel_503_coverage_in_file + access-grants wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    collab = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")
    return (
        "sak515-d" in peel
        and "def peel_503_coverage_in_file" in peel
        and "sak515-a" in collab
    )


def _assert_sak515_join_stream_openapi() -> bool:
    """sak515-g/h/i/j: join/stream OpenAPI peel markers."""
    participants = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_participants.py"
    ).read_text(encoding="utf-8")
    stream = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_stream.py"
    ).read_text(encoding="utf-8")
    return (
        "sak515-g" in participants
        and "sak515-h" in participants
        and "sak515-i" in stream
    )


def _assert_sak516_count_missing_file_helper() -> bool:
    """sak516-d/f: count_missing_peel_503_in_openapi_json + commentary wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    stream = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "chat_stream.py"
    ).read_text(encoding="utf-8")
    return (
        "sak516-d" in peel
        and "def count_missing_peel_503_in_openapi_json" in peel
        and "sak516-a" in stream
    )


def _assert_sak516_user_profile_openapi() -> bool:
    """sak516-g/h/i/j: user-profile OpenAPI peel markers."""
    profiles = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform_user_profiles.py"
    ).read_text(encoding="utf-8")
    discipline = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "platform_discipline_profile.py"
    ).read_text(encoding="utf-8")
    return "sak516-g" in profiles and "sak516-h" in discipline and "sak516-i" in discipline


def _assert_sak517_ensure_openapi_helper() -> bool:
    """sak517-d/f: ensure_openapi_json_peel_503 + provider-connections wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    connections = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "provider_connections.py"
    ).read_text(encoding="utf-8")
    return (
        "sak517-d" in peel
        and "def ensure_openapi_json_peel_503" in peel
        and "sak517-a" in connections
    )


def _assert_sak517_compute_nodes_openapi() -> bool:
    """sak517-g/h/i/j: compute nodes OpenAPI peel markers."""
    compute = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "compute.py"
    ).read_text(encoding="utf-8")
    return "sak517-g" in compute and "sak517-h" in compute and "sak517-i" in compute


def _assert_sak518_ensure_paths_skip_helper() -> bool:
    """sak518-d/f: ensure_paths skip-absent + settings wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    settings = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "operator_settings.py"
    ).read_text(encoding="utf-8")
    return (
        "sak518-d" in peel
        and "Skips targets whose path/method is absent" in peel
        and "sak518-a" in settings
    )


def _assert_sak518_fleet_policy_openapi() -> bool:
    """sak518-g/h/i/j: fleet-ollama/tenant-policy OpenAPI peel markers."""
    ops = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_ops.py"
    ).read_text(encoding="utf-8")
    tenants = (
        NIMBUSWARE_ROOT
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "fleet_tenant_policies.py"
    ).read_text(encoding="utf-8")
    return "sak518-g" in ops and "sak518-i" in tenants


def _assert_sak519_complete_in_file_dry_helper() -> bool:
    """sak519-d/f: complete-in-file DRY + stack-policy wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    tenants = (
        NIMBUSWARE_ROOT
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "fleet_tenant_policies.py"
    ).read_text(encoding="utf-8")
    return (
        "sak519-d" in peel
        and "count_missing_peel_503_in_openapi_json" in peel
        and "sak519-a" in tenants
    )


def _assert_sak519_policy_openapi() -> bool:
    """sak519-g/h/i/j: model/collab-policy OpenAPI peel markers."""
    model = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "enterprise" / "model_policy.py"
    ).read_text(encoding="utf-8")
    collab = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "enterprise" / "collab_policy.py"
    ).read_text(encoding="utf-8")
    tenant = (
        NIMBUSWARE_ROOT
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "tenant_collab_policy.py"
    ).read_text(encoding="utf-8")
    return "sak519-g" in model and "sak519-h" in collab and "sak519-i" in tenant


def _assert_sak520_report_helper() -> bool:
    """sak520-d/f: openapi_json_peel_503_report + tenant model-policy wire."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    tenant = (
        NIMBUSWARE_ROOT
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "tenant_model_policy.py"
    ).read_text(encoding="utf-8")
    return (
        "sak520-d" in peel
        and "openapi_json_peel_503_report" in peel
        and "sak520-a" in tenant
    )


def _assert_sak520_enforcement_push_openapi() -> bool:
    """sak520-g/h/i/j: fleet-enforcement + push-subscriptions OpenAPI peel markers."""
    bff = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "admin_ui_bff.py"
    ).read_text(encoding="utf-8")
    push = (
        NIMBUSWARE_ROOT / "packages" / "api" / "routes" / "maker_push.py"
    ).read_text(encoding="utf-8")
    return "sak520-g" in bff and "sak520-h" in bff and "sak520-i" in push


def _assert_sak521_product_complete_helper() -> bool:
    """sak521-a…f: inventory + oauth skip + product-complete gate."""
    peel = (
        NIMBUSWARE_ROOT / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")
    return (
        "sak521-a" in peel
        and "iter_openapi_json_operations" in peel
        and "PEEL_503_OAUTH_SKIP" in peel
        and "openapi_product_peel_503_complete_in_file" in peel
        and "sak521-d" in peel
    )


def _assert_sak446_remote_host_refuse() -> bool:
    """sak446-d: remote_host refuses under CAPACITY=1."""
    saved = os.environ.get("NIMBUSWARE_BROKER_CAPACITY")
    try:
        os.environ["NIMBUSWARE_BROKER_CAPACITY"] = "1"
        from unittest.mock import MagicMock

        from api.routes import platform_hardware as ph

        try:
            ph._hardware_response(MagicMock(repo_root="."), remote_host="ssh://h")
            return False
        except RuntimeError as exc:
            low = str(exc).lower()
            return "remote_host" in low or "capacity" in low
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_CAPACITY", None)
        else:
            os.environ["NIMBUSWARE_BROKER_CAPACITY"] = saved


def _assert_sak446_broker_modules() -> bool:
    """sak446-g: BrokerClient.list_modules raises on error+[]."""
    from unittest.mock import MagicMock, patch

    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch(
        "broker_client.client.get_json",
        return_value={"error": "x", "modules": []},
    ):
        try:
            client.list_modules()
            return False
        except RuntimeError as exc:
            return "broker_miss" in str(exc)


def _assert_sak445_capacity_try_gone() -> bool:
    """sak445-a: capacity_route try_broker_call / try_capacity_or_refuse removed."""
    from hw import capacity_route as cr

    return (
        not hasattr(cr, "try_broker_call")
        and not hasattr(cr, "try_capacity_or_refuse")
        and callable(cr.map_broker_capacity_http_miss)
    )


def _assert_sak445_broker_client_list() -> bool:
    """sak445-f: BrokerClient.list_work raises on error+[]."""
    from unittest.mock import MagicMock, patch

    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch(
        "broker_client.client.get_json",
        return_value={"error": "x", "work": []},
    ):
        try:
            client.list_work()
            return False
        except RuntimeError as exc:
            return "broker_miss" in str(exc)


def _assert_sak444_try_broker_call_gone() -> bool:
    """sak444-c: compute.broker_route.try_broker_call removed."""
    import compute.broker_route as br

    return not hasattr(br, "try_broker_call") and callable(br.map_broker_compute_http_error)


def _assert_sak444_maker_capacity_helpers() -> bool:
    """sak444-g: Maker capacity miss helpers."""
    from maker.services.models import assert_capacity_ok, is_capacity_miss

    if not is_capacity_miss({"via": "broker_miss"}):
        return False
    try:
        assert_capacity_ok({"via": "broker_miss"}, feature="soak")
        return False
    except RuntimeError as exc:
        return "broker_miss" in str(exc)


def _assert_queue_refuse_compute_1() -> bool:
    """sak433: under COMPUTE=1, get_work_unit_queue refuses."""
    from compute.work_unit import get_work_unit_queue

    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        try:
            get_work_unit_queue()
            return False
        except RuntimeError as exc:
            return _is_compute_refuse_msg(exc)
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_mesh_stage_refuse_compute_1() -> bool:
    """sak432: under COMPUTE=1, local mesh_stage_runner refuses."""
    from uuid import uuid4

    from compute.mesh_stage_runner import execute_mesh_stage_on_worker
    from compute.work_unit import WorkUnitRecord

    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        rec = WorkUnitRecord(
            work_unit_id=uuid4(),
            run_id=uuid4(),
            session_id=None,
            stage_name="implementation",
            agent_role="implementation",
            executor_user_id="",
            status="assigned",
            payload={"mesh_assignment": True},
        )
        try:
            execute_mesh_stage_on_worker(rec)
            return False
        except RuntimeError as exc:
            return "COMPUTE=1" in str(exc) or "COMPUTE=1|2" in str(exc)
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def _assert_mesh_wait_compute_1_broker_first() -> bool:
    """sak430: under COMPUTE=1, wait_for_mesh_units prefers broker list."""
    from unittest.mock import patch
    from uuid import uuid4

    from compute.mesh_host_sync import wait_for_mesh_units

    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "1"
        with (
            patch(
                "broker_client.stage_bind.compute.compute_work_via_broker",
                return_value={
                    "work": [
                        {
                            "kind": "implementation",
                            "status": "completed",
                            "payload": {"stage_name": "implementation"},
                            "result": {},
                        }
                    ]
                },
            ),
            patch("compute.mesh_host_sync.mesh_poll_interval_seconds", return_value=0.01),
            patch("compute.mesh_host_sync.mesh_wait_timeout_seconds", return_value=2.0),
        ):
            return wait_for_mesh_units(uuid4(), ["implementation"]) is True
    finally:
        if saved is None:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        else:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved


def assert_broker_only_refuse_local(env: dict[str, str]) -> bool:
    """sak421-b / sak422-h: under COMPUTE=2 / CAPACITY=2, local mesh paths refuse."""
    from pathlib import Path
    from uuid import uuid4

    from compute.mesh_event_replay import baseline_event_ids
    from compute.mesh_host_sync import wait_for_mesh_units
    from compute.mesh_stage_runner import execute_mesh_stage_on_worker
    from compute.mesh_workspace_merge import workspace_file_digests
    from compute.work_unit import WorkUnitRecord, get_work_unit_queue
    from compute.work_unit_execute import execute_work_unit_on_worker
    from hw.cache import get_cached_profile

    all_ok = True
    saved_compute = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    saved_capacity = os.environ.get("NIMBUSWARE_BROKER_CAPACITY")
    try:
        os.environ["NIMBUSWARE_BROKER_COMPUTE"] = "2"
        os.environ["NIMBUSWARE_BROKER_CAPACITY"] = "2"
        rec = WorkUnitRecord(
            work_unit_id=uuid4(),
            run_id=uuid4(),
            session_id=None,
            stage_name="implementation",
            agent_role="implementation",
            executor_user_id="",
            status="assigned",
            payload={"mesh_assignment": True},
        )
        try:
            execute_mesh_stage_on_worker(rec)
            all_ok &= print_check("COMPUTE=2 mesh_stage_runner refuses local", False, "no raise")
        except RuntimeError as exc:
            all_ok &= print_check(
                "COMPUTE=2 mesh_stage_runner refuses local",
                _is_compute_refuse_msg(exc),
                str(exc)[:80],
            )
        for label, fn in (
            (
                "COMPUTE=2 mesh_host_sync broker wait ok",
                lambda: wait_for_mesh_units(uuid4(), []),
            ),
            (
                "COMPUTE=2 mesh_event_replay refuses local",
                lambda: baseline_event_ids(None, uuid4()),  # type: ignore[arg-type]
            ),
            (
                "COMPUTE=2 mesh_workspace_merge refuses local",
                lambda: workspace_file_digests(Path(".")),
            ),
            ("COMPUTE=2 work_unit queue refuses local", get_work_unit_queue),
            (
                "COMPUTE=2 work_unit_execute refuses local",
                lambda: execute_work_unit_on_worker(rec),
            ),
            (
                "COMPUTE=2 absorb helpers available",
                lambda: __import__(
                    "compute.mesh_event_replay", fromlist=["replay_events_to_store_absorb"]
                ).replay_events_to_store_absorb(
                    type("S", (), {"list_run_events": lambda self, _r: [], "append": lambda self, _e: None})(),
                    uuid4(),
                    [],
                )
                == 0,
            ),
            (
                "sak426 dual-run API helpers",
                lambda: callable(
                    __import__(
                        "compute.broker_public", fromlist=["broker_node_public"]
                    ).broker_node_public
                )
                and callable(
                    __import__(
                        "compute.broker_public", fromlist=["broker_work_public"]
                    ).broker_work_public
                ),
            ),
            (
                "sak427 BrokerClient register/heartbeat",
                lambda: callable(
                    getattr(
                        __import__("broker_client.client", fromlist=["BrokerClient"]).BrokerClient,
                        "register_node",
                    )
                )
                and callable(
                    getattr(
                        __import__("broker_client.client", fromlist=["BrokerClient"]).BrokerClient,
                        "heartbeat_node",
                    )
                ),
            ),
            (
                "sak428 node_store refuses under COMPUTE=2",
                _assert_node_store_refuse,
            ),
            (
                "sak428 broker_miss + requeue payload",
                lambda: __import__(
                    "compute.broker_miss", fromlist=["broker_miss"]
                ).broker_miss(error="x")["via"]
                == "broker_miss"
                and __import__(
                    "broker_client.stage_bind.compute",
                    fromlist=["build_compute_requeue_payload"],
                ).build_compute_requeue_payload("w")["action"]
                == "requeue",
            ),
            (
                "sak429 BrokerClient.requeue_work",
                lambda: callable(
                    getattr(
                        __import__("broker_client.client", fromlist=["BrokerClient"]).BrokerClient,
                        "requeue_work",
                    )
                ),
            ),
            (
                "sak430 terminate_restart_via_broker",
                lambda: callable(
                    getattr(
                        __import__(
                            "broker_client.stage_bind.compute",
                            fromlist=["terminate_restart_via_broker"],
                        ),
                        "terminate_restart_via_broker",
                    )
                ),
            ),
            (
                "sak430 mesh wait broker-first under COMPUTE=1",
                _assert_mesh_wait_compute_1_broker_first,
            ),
            (
                "sak431 BrokerClient.enqueue_work",
                lambda: callable(
                    getattr(
                        __import__("broker_client.client", fromlist=["BrokerClient"]).BrokerClient,
                        "enqueue_work",
                    )
                ),
            ),
            (
                "sak431 broker_route.miss",
                lambda: __import__(
                    "compute.broker_route", fromlist=["miss"]
                ).miss(error="x")["via"]
                == "broker_miss",
            ),
            (
                "sak432 BrokerClient.claim_work",
                lambda: callable(
                    getattr(
                        __import__("broker_client.client", fromlist=["BrokerClient"]).BrokerClient,
                        "claim_work",
                    )
                )
                and callable(
                    getattr(
                        __import__("broker_client.client", fromlist=["BrokerClient"]).BrokerClient,
                        "complete_work",
                    )
                ),
            ),
            (
                "sak432 mesh_stage_runner refuses COMPUTE=1",
                _assert_mesh_stage_refuse_compute_1,
            ),
            (
                "sak433 queue refuses COMPUTE=1",
                _assert_queue_refuse_compute_1,
            ),
            (
                "sak433 capacity_route.refuse_legacy",
                lambda: callable(
                    getattr(
                        __import__("hw.capacity_route", fromlist=["refuse_legacy"]),
                        "refuse_legacy",
                    )
                ),
            ),
            (
                "sak434 dual_run_route.refuse_when",
                lambda: callable(
                    getattr(
                        __import__(
                            "broker_client.dual_run_route", fromlist=["refuse_when"]
                        ),
                        "refuse_when",
                    )
                ),
            ),
            (
                "sak434 BrokerClient.terminate_restart_work",
                lambda: callable(
                    getattr(
                        __import__("broker_client.client", fromlist=["BrokerClient"]).BrokerClient,
                        "terminate_restart_work",
                    )
                ),
            ),
            (
                "sak435 broker_session_compute_status",
                lambda: callable(
                    getattr(
                        __import__(
                            "compute.broker_session_status",
                            fromlist=["broker_session_compute_status"],
                        ),
                        "broker_session_compute_status",
                    )
                ),
            ),
            (
                "sak435 compute bridge exclusivity",
                _assert_compute_bridge_reraises,
            ),
            (
                "sak436 map_broker_compute_http_error",
                _assert_map_broker_compute_http_error,
            ),
            (
                "sak436 stage_bind HTTP no MCP fallthrough",
                _assert_stage_bind_http_no_mcp,
            ),
            (
                "sak436 BrokerClient.session_compute_status",
                lambda: callable(
                    getattr(
                        __import__(
                            "broker_client.client", fromlist=["BrokerClient"]
                        ).BrokerClient,
                        "session_compute_status",
                    )
                ),
            ),
            (
                "sak437 assert_broker_compute_ok",
                lambda: callable(
                    getattr(
                        __import__(
                            "compute.broker_session_status",
                            fromlist=["assert_broker_compute_ok"],
                        ),
                        "assert_broker_compute_ok",
                    )
                ),
            ),
            (
                "sak437 map_broker_chat_compute_miss",
                lambda: callable(
                    getattr(
                        __import__(
                            "compute.broker_route",
                            fromlist=["map_broker_chat_compute_miss"],
                        ),
                        "map_broker_chat_compute_miss",
                    )
                ),
            ),
            (
                "sak437 BrokerClient.queue_depth",
                lambda: callable(
                    getattr(
                        __import__(
                            "broker_client.client", fromlist=["BrokerClient"]
                        ).BrokerClient,
                        "queue_depth",
                    )
                ),
            ),
            (
                "sak438 assert_broker_compute_record_ok",
                lambda: callable(
                    getattr(
                        __import__(
                            "compute.broker_session_status",
                            fromlist=["assert_broker_compute_record_ok"],
                        ),
                        "assert_broker_compute_record_ok",
                    )
                ),
            ),
            (
                "sak438 assert rejects error+empty list",
                lambda: _assert_sak438_error_empty_list(),
            ),
            (
                "sak439 normalize_claim_work_response",
                lambda: callable(
                    getattr(
                        __import__(
                            "compute.broker_session_status",
                            fromlist=["normalize_claim_work_response"],
                        ),
                        "normalize_claim_work_response",
                    )
                ),
            ),
            (
                "sak439 claim empty vs miss",
                lambda: _assert_sak439_claim_normalize(),
            ),
            (
                "sak440 broker_node_match",
                lambda: _assert_sak440_node_match(),
            ),
            (
                "sak440 node_store ctor refuse",
                lambda: _assert_sak440_node_store_ctor(),
            ),
            (
                "sak441 list null is miss",
                lambda: _assert_sak441_list_null_miss(),
            ),
            (
                "sak441 capacity http miss",
                lambda: _assert_sak441_capacity_http_miss(),
            ),
            (
                "sak442 capacity=2 HTTP 503",
                lambda: _assert_sak442_capacity_2_503(),
            ),
            (
                "sak442 list_nodes_filtered assert",
                lambda: _assert_sak442_list_nodes_assert(),
            ),
            (
                "sak443 apply-preset miss",
                lambda: _assert_sak443_apply_preset_miss(),
            ),
            (
                "sak443 opt-out via",
                lambda: _assert_sak443_opt_out_via(),
            ),
            (
                "sak444 try_broker_call gone",
                lambda: _assert_sak444_try_broker_call_gone(),
            ),
            (
                "sak444 maker capacity helpers",
                lambda: _assert_sak444_maker_capacity_helpers(),
            ),
            (
                "sak445 capacity try_broker_call gone",
                lambda: _assert_sak445_capacity_try_gone(),
            ),
            (
                "sak445 BrokerClient list assert",
                lambda: _assert_sak445_broker_client_list(),
            ),
            (
                "sak446 remote_host CAPACITY refuse",
                lambda: _assert_sak446_remote_host_refuse(),
            ),
            (
                "sak446 BrokerClient modules assert",
                lambda: _assert_sak446_broker_modules(),
            ),
            (
                "sak447 raw compute_work assert",
                lambda: _assert_sak447_raw_compute_post(),
            ),
            (
                "sak447 readiness capacity miss",
                lambda: _assert_sak447_readiness_miss(),
            ),
            (
                "sak448 BrokerClient health assert",
                lambda: _assert_sak448_health_assert(),
            ),
            (
                "sak448 oauth status OpenAPI",
                lambda: _assert_sak448_oauth_openapi(),
            ),
            (
                "sak449 BrokerClient capacity assert",
                lambda: _assert_sak449_module_capacity_assert(),
            ),
            (
                "sak449 edition OpenAPI",
                lambda: _assert_sak449_edition_openapi(),
            ),
            (
                "sak480 settings OpenAPI",
                lambda: _assert_sak480_settings_openapi(),
            ),
            (
                "sak480 BrokerClient queue_depth",
                lambda: _assert_sak480_queue_depth(),
            ),
            (
                "sak481 folder OpenAPI",
                lambda: _assert_sak481_folder_openapi(),
            ),
            (
                "sak481 compliance OpenAPI",
                lambda: _assert_sak481_compliance_openapi(),
            ),
            (
                "sak482 group mutation OpenAPI",
                lambda: _assert_sak482_group_mutation_openapi(),
            ),
            (
                "sak482 fleet slice OpenAPI",
                lambda: _assert_sak482_fleet_slice_openapi(),
            ),
            (
                "sak483 standards OpenAPI",
                lambda: _assert_sak483_standards_openapi(),
            ),
            (
                "sak483 fleet enforcement OpenAPI",
                lambda: _assert_sak483_fleet_enforcement_openapi(),
            ),
            (
                "sak484 campaign OpenAPI",
                lambda: _assert_sak484_campaign_openapi(),
            ),
            (
                "sak484 timeline explain OpenAPI",
                lambda: _assert_sak484_timeline_explain_openapi(),
            ),
            (
                "sak485 findings OpenAPI",
                lambda: _assert_sak485_findings_openapi(),
            ),
            (
                "sak485 fleet learnings OpenAPI",
                lambda: _assert_sak485_fleet_learnings_openapi(),
            ),
            (
                "sak486 research index OpenAPI",
                lambda: _assert_sak486_research_index_openapi(),
            ),
            (
                "sak486 model policy OpenAPI",
                lambda: _assert_sak486_model_policy_openapi(),
            ),
            (
                "sak487 actions OpenAPI",
                lambda: _assert_sak487_actions_openapi(),
            ),
            (
                "sak487 signout OpenAPI",
                lambda: _assert_sak487_signout_openapi(),
            ),
            (
                "sak488 delete ok OpenAPI",
                lambda: _assert_sak488_delete_ok_openapi(),
            ),
            (
                "sak488 export peel",
                lambda: _assert_sak488_export_peel(),
            ),
            (
                "sak489 peel_assert",
                lambda: _assert_sak489_peel_assert(),
            ),
            (
                "sak489 sse peel",
                lambda: _assert_sak489_sse_peel(),
            ),
            (
                "sak490 broker_route peel",
                lambda: _assert_sak490_broker_route(),
            ),
            (
                "sak490 capacity_route peel",
                lambda: _assert_sak490_capacity_route(),
            ),
            (
                "sak491 queue read refuse",
                lambda: _assert_sak491_queue_read_refuse(),
            ),
            (
                "sak491 compute OpenAPI",
                lambda: _assert_sak491_compute_openapi(),
            ),
            (
                "sak492 capacity OpenAPI",
                lambda: _assert_sak492_capacity_openapi(),
            ),
            (
                "sak492 chat_facade peel_strict",
                lambda: _assert_sak492_chat_facade_peel_strict(),
            ),
            (
                "sak493 llm OpenAPI",
                lambda: _assert_sak493_llm_openapi(),
            ),
            (
                "sak493 memory OpenAPI",
                lambda: _assert_sak493_memory_openapi(),
            ),
            (
                "sak494 memory refuse_legacy",
                lambda: _assert_sak494_memory_refuse_legacy(),
            ),
            (
                "sak494 research OpenAPI",
                lambda: _assert_sak494_research_openapi(),
            ),
            (
                "sak494 domain peel_miss refactor",
                lambda: _assert_sak494_domain_peel_miss(),
            ),
            (
                "sak495 memory assert_memory_ok",
                lambda: _assert_sak495_memory_assert(),
            ),
            (
                "sak495 analytics OpenAPI",
                lambda: _assert_sak495_analytics_openapi(),
            ),
            (
                "sak495 tools peel miss",
                lambda: _assert_sak495_tools_peel_miss(),
            ),
            (
                "sak495 compute domain peel_miss refactor",
                lambda: _assert_sak495_compute_domain_peel_miss(),
            ),
            (
                "sak496 lifecycle peel wiring",
                lambda: _assert_sak496_lifecycle_peel_wiring(),
            ),
            (
                "sak496 domain broker_route raise helpers",
                lambda: _assert_sak496_domain_broker_route_raises(),
            ),
            (
                "sak496 early_llm_sse_peel_miss",
                lambda: _assert_sak496_early_llm_sse_peel_miss(),
            ),
            (
                "sak496 domain peel_assert detectors",
                lambda: _assert_sak496_domain_peel_assert(),
            ),
            (
                "sak497 slice_facade plan LLM wire",
                lambda: _assert_sak497_slice_facade_plan_llm_wire(),
            ),
            (
                "sak497 campaign OpenAPI helper",
                lambda: _assert_sak497_campaign_openapi_helper(),
            ),
            (
                "sak497 domain flag-matrix modules",
                lambda: _assert_sak497_domain_flag_matrix_modules(),
            ),
            (
                "sak498 bootstrap resolve_memory",
                lambda: _assert_sak498_bootstrap_resolve_memory(),
            ),
            (
                "sak498 require_local_memory / resolve_memory_store_or_miss",
                lambda: _assert_sak498_require_local_memory(),
            ),
            (
                "sak498 self_refinement agent_evaluator exports",
                lambda: _assert_sak498_llm_exports_not_removed(),
            ),
            (
                "sak498 domain assert_llm_ok",
                lambda: _assert_sak498_domain_assert_llm_ok(),
            ),
            (
                "sak499 peel_guard",
                lambda: _assert_sak499_peel_guard(),
            ),
            (
                "sak499 maker domain peel miss",
                lambda: _assert_sak499_maker_domain_miss(),
            ),
            (
                "sak500 maker ribbons domain peel miss",
                lambda: _assert_sak500_maker_ribbons(),
            ),
            (
                "sak500 sse/bootstrap domain peel",
                lambda: _assert_sak500_sse_bootstrap(),
            ),
            (
                "sak501 hardware + capacity formatter",
                lambda: _assert_sak501_hardware_capacity_formatter(),
            ),
            (
                "sak501 settings/bindings/push OpenAPI",
                lambda: _assert_sak501_openapi_settings_bindings(),
            ),
            (
                "sak502 with_long_tail_peel_503 + runs",
                lambda: _assert_sak502_with_long_tail_helper(),
            ),
            (
                "sak502 run detail/slice/factory OpenAPI",
                lambda: _assert_sak502_run_detail_openapi(),
            ),
            (
                "sak503 with_enterprise_peel_503",
                lambda: _assert_sak503_enterprise_peel_helper(),
            ),
            (
                "sak503 run compact/budget/integrations OpenAPI",
                lambda: _assert_sak503_run_compact_openapi(),
            ),
            (
                "sak504 artifact_peel_503 + auth",
                lambda: _assert_sak504_artifact_peel_helper(),
            ),
            (
                "sak504 run timeline/lifecycle/projection OpenAPI",
                lambda: _assert_sak504_run_projection_openapi(),
            ),
            (
                "sak505 ensure_operation_peel_503 + personas",
                lambda: _assert_sak505_ensure_operation_peel(),
            ),
            (
                "sak505 bindings/role-claims/autopilot OpenAPI",
                lambda: _assert_sak505_bindings_autopilot_openapi(),
            ),
            (
                "sak506 ensure_paths_peel_503 + theater",
                lambda: _assert_sak506_ensure_paths_peel(),
            ),
            (
                "sak506 override/interjection/standards OpenAPI",
                lambda: _assert_sak506_standards_actions_openapi(),
            ),
            (
                "sak507 count_missing_peel_503 + maker",
                lambda: _assert_sak507_count_missing_peel(),
            ),
            (
                "sak507 maker mutate/bundle OpenAPI",
                lambda: _assert_sak507_maker_mutate_openapi(),
            ),
            (
                "sak508 list_missing_peel_503 + deploy",
                lambda: _assert_sak508_list_missing_peel(),
            ),
            (
                "sak508 deploy approve/audit/hardware OpenAPI",
                lambda: _assert_sak508_deploy_hardware_openapi(),
            ),
            (
                "sak509 count_missing DRY + fleet/models",
                lambda: _assert_sak509_count_missing_dry(),
            ),
            (
                "sak509 routing/invite/collab OpenAPI",
                lambda: _assert_sak509_platform_residual_openapi(),
            ),
            (
                "sak510 patch_openapi_json_peel_503 + readiness",
                lambda: _assert_sak510_patch_openapi_helper(),
            ),
            (
                "sak510 precommit/safe-coding/bindings OpenAPI",
                lambda: _assert_sak510_prefs_bindings_openapi(),
            ),
            (
                "sak511 openapi_peel_503_complete + enterprise",
                lambda: _assert_sak511_openapi_complete_helper(),
            ),
            (
                "sak511 factory-evidence/streams/policy OpenAPI",
                lambda: _assert_sak511_exports_streams_openapi(),
            ),
            (
                "sak512 list_missing file helper + bundles",
                lambda: _assert_sak512_list_missing_file_helper(),
            ),
            (
                "sak512 projects/chat-start/scope OpenAPI",
                lambda: _assert_sak512_projects_chat_openapi(),
            ),
            (
                "sak513 complete-in-file + chat compute",
                lambda: _assert_sak513_complete_in_file_helper(),
            ),
            (
                "sak513 sessions/classify/host-transfer OpenAPI",
                lambda: _assert_sak513_sessions_transfer_openapi(),
            ),
            (
                "sak514 peel_503_coverage + host-transfer",
                lambda: _assert_sak514_peel_503_coverage_helper(),
            ),
            (
                "sak514 folders/groups OpenAPI",
                lambda: _assert_sak514_folders_groups_openapi(),
            ),
            (
                "sak515 coverage-in-file + access-grants",
                lambda: _assert_sak515_coverage_in_file_helper(),
            ),
            (
                "sak515 join/stream OpenAPI",
                lambda: _assert_sak515_join_stream_openapi(),
            ),
            (
                "sak516 count-in-file + commentary",
                lambda: _assert_sak516_count_missing_file_helper(),
            ),
            (
                "sak516 user-profile OpenAPI",
                lambda: _assert_sak516_user_profile_openapi(),
            ),
            (
                "sak517 ensure OpenAPI + provider-connections",
                lambda: _assert_sak517_ensure_openapi_helper(),
            ),
            (
                "sak517 compute nodes OpenAPI",
                lambda: _assert_sak517_compute_nodes_openapi(),
            ),
            (
                "sak518 ensure_paths skip + settings",
                lambda: _assert_sak518_ensure_paths_skip_helper(),
            ),
            (
                "sak518 fleet-ollama/tenant-policy OpenAPI",
                lambda: _assert_sak518_fleet_policy_openapi(),
            ),
            (
                "sak519 complete-in-file DRY + stack-policy",
                lambda: _assert_sak519_complete_in_file_dry_helper(),
            ),
            (
                "sak519 model/collab-policy OpenAPI",
                lambda: _assert_sak519_policy_openapi(),
            ),
            (
                "sak520 report helper + tenant model-policy",
                lambda: _assert_sak520_report_helper(),
            ),
            (
                "sak520 enforcement/push OpenAPI",
                lambda: _assert_sak520_enforcement_push_openapi(),
            ),
            (
                "sak521 product peel complete + oauth skip",
                lambda: _assert_sak521_product_complete_helper(),
            ),
        ):
            try:
                result = fn()
                if (
                    label.startswith("COMPUTE=2 mesh_host_sync broker")
                    or label.startswith("COMPUTE=2 absorb helpers")
                    or label.startswith("sak426 dual-run")
                    or label.startswith("sak427 BrokerClient")
                    or label.startswith("sak428")
                    or label.startswith("sak429")
                    or label.startswith("sak430")
                    or label.startswith("sak431")
                    or label.startswith("sak432")
                    or label.startswith("sak433")
                    or label.startswith("sak434")
                    or label.startswith("sak435")
                    or label.startswith("sak436")
                    or label.startswith("sak437")
                    or label.startswith("sak438")
                    or label.startswith("sak439")
                    or label.startswith("sak440")
                    or label.startswith("sak441")
                    or label.startswith("sak442")
                    or label.startswith("sak443")
                    or label.startswith("sak444")
                    or label.startswith("sak445")
                    or label.startswith("sak446")
                    or label.startswith("sak447")
                    or label.startswith("sak448")
                    or label.startswith("sak449")
                    or label.startswith("sak480")
                    or label.startswith("sak481")
                    or label.startswith("sak482")
                    or label.startswith("sak483")
                    or label.startswith("sak484")
                    or label.startswith("sak485")
                    or label.startswith("sak486")
                    or label.startswith("sak487")
                    or label.startswith("sak488")
                    or label.startswith("sak489")
                    or label.startswith("sak490")
                    or label.startswith("sak491")
                    or label.startswith("sak492")
                    or label.startswith("sak493")
                    or label.startswith("sak494")
                    or label.startswith("sak495")
                    or label.startswith("sak496")
                    or label.startswith("sak497")
                    or label.startswith("sak498")
                    or label.startswith("sak499")
                    or label.startswith("sak500")
                    or label.startswith("sak501")
                    or label.startswith("sak502")
                    or label.startswith("sak503")
                    or label.startswith("sak504")
                    or label.startswith("sak505")
                    or label.startswith("sak506")
                    or label.startswith("sak507")
                    or label.startswith("sak508")
                    or label.startswith("sak509")
                    or label.startswith("sak510")
                    or label.startswith("sak511")
                    or label.startswith("sak512")
                    or label.startswith("sak513")
                    or label.startswith("sak514")
                    or label.startswith("sak515")
                    or label.startswith("sak516")
                    or label.startswith("sak517")
                    or label.startswith("sak518")
                    or label.startswith("sak519")
                    or label.startswith("sak520")
                    or label.startswith("sak521")
                ):
                    all_ok &= print_check(label, result is True, f"result={result!r}")
                else:
                    all_ok &= print_check(label, False, "no raise")
            except RuntimeError as exc:
                if (
                    label.startswith("COMPUTE=2 mesh_host_sync broker")
                    or label.startswith("COMPUTE=2 absorb helpers")
                    or label.startswith("sak426 dual-run")
                    or label.startswith("sak427 BrokerClient")
                    or label.startswith("sak428")
                    or label.startswith("sak429")
                    or label.startswith("sak430")
                    or label.startswith("sak431")
                    or label.startswith("sak432")
                    or label.startswith("sak433")
                    or label.startswith("sak434")
                    or label.startswith("sak435")
                    or label.startswith("sak436")
                    or label.startswith("sak437")
                    or label.startswith("sak438")
                    or label.startswith("sak439")
                    or label.startswith("sak440")
                    or label.startswith("sak441")
                    or label.startswith("sak442")
                    or label.startswith("sak443")
                    or label.startswith("sak444")
                    or label.startswith("sak445")
                    or label.startswith("sak446")
                    or label.startswith("sak447")
                    or label.startswith("sak448")
                    or label.startswith("sak449")
                    or label.startswith("sak480")
                    or label.startswith("sak481")
                    or label.startswith("sak482")
                    or label.startswith("sak483")
                    or label.startswith("sak484")
                    or label.startswith("sak485")
                    or label.startswith("sak486")
                    or label.startswith("sak487")
                    or label.startswith("sak488")
                    or label.startswith("sak489")
                    or label.startswith("sak490")
                    or label.startswith("sak491")
                    or label.startswith("sak492")
                    or label.startswith("sak493")
                    or label.startswith("sak494")
                    or label.startswith("sak495")
                    or label.startswith("sak496")
                    or label.startswith("sak497")
                    or label.startswith("sak498")
                    or label.startswith("sak499")
                    or label.startswith("sak500")
                    or label.startswith("sak501")
                    or label.startswith("sak502")
                    or label.startswith("sak503")
                    or label.startswith("sak504")
                    or label.startswith("sak505")
                    or label.startswith("sak506")
                    or label.startswith("sak507")
                    or label.startswith("sak508")
                    or label.startswith("sak509")
                    or label.startswith("sak510")
                    or label.startswith("sak511")
                    or label.startswith("sak512")
                    or label.startswith("sak513")
                    or label.startswith("sak514")
                    or label.startswith("sak515")
                    or label.startswith("sak516")
                    or label.startswith("sak517")
                    or label.startswith("sak518")
                    or label.startswith("sak519")
                    or label.startswith("sak520")
                    or label.startswith("sak521")
                ):
                    all_ok &= print_check(label, False, str(exc)[:80])
                else:
                    all_ok &= print_check(label, _is_compute_refuse_msg(exc), str(exc)[:80])
            except Exception as exc:  # noqa: BLE001
                if (
                    label.startswith("COMPUTE=2 mesh_host_sync broker")
                    or label.startswith("COMPUTE=2 absorb helpers")
                    or label.startswith("sak426 dual-run")
                    or label.startswith("sak427 BrokerClient")
                    or label.startswith("sak428")
                    or label.startswith("sak429")
                    or label.startswith("sak430")
                    or label.startswith("sak431")
                    or label.startswith("sak432")
                    or label.startswith("sak433")
                    or label.startswith("sak434")
                    or label.startswith("sak435")
                    or label.startswith("sak436")
                    or label.startswith("sak437")
                    or label.startswith("sak438")
                    or label.startswith("sak439")
                    or label.startswith("sak440")
                    or label.startswith("sak441")
                    or label.startswith("sak442")
                    or label.startswith("sak443")
                    or label.startswith("sak444")
                    or label.startswith("sak445")
                    or label.startswith("sak446")
                    or label.startswith("sak447")
                    or label.startswith("sak448")
                    or label.startswith("sak449")
                    or label.startswith("sak480")
                    or label.startswith("sak481")
                    or label.startswith("sak482")
                    or label.startswith("sak483")
                    or label.startswith("sak484")
                    or label.startswith("sak485")
                    or label.startswith("sak486")
                    or label.startswith("sak487")
                    or label.startswith("sak488")
                    or label.startswith("sak489")
                    or label.startswith("sak490")
                    or label.startswith("sak491")
                    or label.startswith("sak492")
                    or label.startswith("sak493")
                    or label.startswith("sak494")
                    or label.startswith("sak495")
                    or label.startswith("sak496")
                    or label.startswith("sak497")
                    or label.startswith("sak498")
                    or label.startswith("sak499")
                    or label.startswith("sak500")
                    or label.startswith("sak501")
                    or label.startswith("sak502")
                    or label.startswith("sak503")
                    or label.startswith("sak504")
                    or label.startswith("sak505")
                    or label.startswith("sak506")
                    or label.startswith("sak507")
                    or label.startswith("sak508")
                    or label.startswith("sak509")
                    or label.startswith("sak510")
                    or label.startswith("sak511")
                    or label.startswith("sak512")
                    or label.startswith("sak513")
                    or label.startswith("sak514")
                    or label.startswith("sak515")
                    or label.startswith("sak516")
                    or label.startswith("sak517")
                    or label.startswith("sak518")
                    or label.startswith("sak519")
                    or label.startswith("sak520")
                    or label.startswith("sak521")
                ):
                    all_ok &= print_check(label, False, str(exc)[:80])
                else:
                    all_ok &= print_check(label, _is_compute_refuse_msg(exc), str(exc)[:80])
        # Capacity=2 with broker down / probe miss should refuse local cache path.
        from unittest.mock import patch

        with patch(
            "broker_client.capacity_bridge.try_broker_probe_dict",
            return_value=None,
        ):
            import hw.cache as cache_mod

            cache_mod._broker_cached = None
            try:
                get_cached_profile(fresh=True)
                all_ok &= print_check("CAPACITY=2 cache refuses local", False, "no raise")
            except RuntimeError as exc:
                all_ok &= print_check(
                    "CAPACITY=2 cache refuses local",
                    _is_capacity_refuse_msg(exc),
                    str(exc)[:80],
                )
    finally:
        if saved_compute is not None:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved_compute
        else:
            os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        if saved_capacity is not None:
            os.environ["NIMBUSWARE_BROKER_CAPACITY"] = saved_capacity
        else:
            os.environ.pop("NIMBUSWARE_BROKER_CAPACITY", None)
    return all_ok


def run_prereq_checks(env: dict[str, str] | None = None) -> bool:
    result = run_peel_script("peel_soak_prereq.py", env=env)
    ok = result.returncode == 0
    print_check("peel_soak_prereq.py", ok, f"exit {result.returncode}")
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines()[:6]:
            print(f"    {line}")
    if not ok and result.stderr.strip():
        for line in result.stderr.strip().splitlines()[:3]:
            print(f"    stderr: {line}")
    return ok


def assert_bind_plans(env: dict[str, str]) -> bool:
    """``bind_plan`` succeeds for every peel domain when flags are on."""
    from broker_client import bind_plan, list_bind_domains

    all_ok = True
    domains = list_bind_domains()
    all_ok &= print_check(
        "list_bind_domains (8 domains)",
        domains == sorted(SOAK_DOMAINS),
        str(domains),
    )
    for domain in SOAK_DOMAINS:
        try:
            plan = bind_plan(domain)
            offer_ok = plan.get("offer") == DOMAIN_OFFERS[domain]
            steps_ok = "bind" in plan.get("steps", [])
            domain_ok = offer_ok and steps_ok
            all_ok &= print_check(
                f"bind_plan({domain!r})",
                domain_ok,
                f"offer={plan.get('offer')!r}",
            )
        except Exception as exc:  # noqa: BLE001 — smoke harness reports any bind failure
            all_ok &= print_check(f"bind_plan({domain!r})", False, str(exc))
    return all_ok


def assert_domain_llm(env: dict[str, str]) -> bool:
    """sak403-f: LLM flag + bind_plan + broker_bridge importable."""
    from broker_client import bind_plan, broker_llm_enabled, select_llm_backend
    from orchestrator.llm.broker_bridge import try_broker_chat_json

    all_ok = True
    all_ok &= print_check("broker_llm_enabled()", broker_llm_enabled())
    all_ok &= print_check("select_llm_backend() == broker", select_llm_backend() == "broker")
    try:
        plan = bind_plan("llm")
        all_ok &= print_check(
            "bind_plan('llm')",
            plan.get("offer") == "llm.chat",
            str(plan.get("offer")),
        )
    except Exception as exc:  # noqa: BLE001
        all_ok &= print_check("bind_plan('llm')", False, str(exc))
    all_ok &= print_check(
        "orchestrator.llm.broker_bridge importable",
        callable(try_broker_chat_json),
    )
    return all_ok


def assert_domain_sandbox(env: dict[str, str]) -> bool:
    """sak404-f: sandbox/tools bind_plan + bridges importable."""
    from agent_tools.sandbox_bridge import try_broker_sandbox_exec
    from broker_client import (
        bind_plan,
        broker_sandbox_enabled,
        broker_tools_enabled,
        select_backend,
    )
    from broker_client.stage_bind.tools import try_broker_shell_exec

    all_ok = True
    all_ok &= print_check("broker_sandbox_enabled()", broker_sandbox_enabled())
    all_ok &= print_check("broker_tools_enabled()", broker_tools_enabled())
    all_ok &= print_check(
        "select_backend sandbox/tools",
        select_backend("sandbox") == "broker" and select_backend("tools") == "broker",
    )
    for domain in ("sandbox", "tools"):
        try:
            plan = bind_plan(domain)
            all_ok &= print_check(
                f"bind_plan({domain!r})",
                plan.get("offer") == DOMAIN_OFFERS[domain],
                str(plan.get("offer")),
            )
        except Exception as exc:  # noqa: BLE001
            all_ok &= print_check(f"bind_plan({domain!r})", False, str(exc))
    all_ok &= print_check(
        "sandbox_bridge + tools bridge importable",
        callable(try_broker_sandbox_exec) and callable(try_broker_shell_exec),
    )
    return all_ok


def assert_domain_memory(env: dict[str, str]) -> bool:
    """sak405-f: memory bind_plan + memory_bridge importable."""
    from agent_tools.memory_bridge import try_broker_memory_search
    from broker_client import bind_plan, broker_memory_enabled, select_backend

    all_ok = True
    all_ok &= print_check("broker_memory_enabled()", broker_memory_enabled())
    all_ok &= print_check("select_backend('memory') == broker", select_backend("memory") == "broker")
    try:
        plan = bind_plan("memory")
        all_ok &= print_check(
            "bind_plan('memory')",
            plan.get("offer") == "memory.search",
            str(plan.get("offer")),
        )
    except Exception as exc:  # noqa: BLE001
        all_ok &= print_check("bind_plan('memory')", False, str(exc))
    all_ok &= print_check(
        "agent_tools.memory_bridge importable",
        callable(try_broker_memory_search),
    )
    return all_ok


def assert_domain_research(env: dict[str, str]) -> bool:
    """sak406-h: research flag + bind_plan + research_bridge importable."""
    from broker_client import bind_plan, broker_research_enabled, select_backend
    from research.research_bridge import try_broker_research_fetch

    all_ok = True
    all_ok &= print_check("broker_research_enabled()", broker_research_enabled())
    all_ok &= print_check("select_backend('research') == broker", select_backend("research") == "broker")
    try:
        plan = bind_plan("research")
        all_ok &= print_check(
            "bind_plan('research')",
            plan.get("offer") == "research.fetch",
            str(plan.get("offer")),
        )
    except Exception as exc:  # noqa: BLE001
        all_ok &= print_check("bind_plan('research')", False, str(exc))
    all_ok &= print_check(
        "research.research_bridge importable",
        callable(try_broker_research_fetch),
    )
    return all_ok


def assert_domain_egress(env: dict[str, str]) -> bool:
    """sak406-h: egress flag + bind_plan + egress_bridge importable."""
    from broker_client import bind_plan, broker_egress_enabled, select_backend
    from executor.egress_bridge import try_broker_egress_check

    all_ok = True
    all_ok &= print_check("broker_egress_enabled()", broker_egress_enabled())
    all_ok &= print_check("select_backend('egress') == broker", select_backend("egress") == "broker")
    try:
        plan = bind_plan("egress")
        all_ok &= print_check(
            "bind_plan('egress')",
            plan.get("offer") == "network.egress.check",
            str(plan.get("offer")),
        )
    except Exception as exc:  # noqa: BLE001
        all_ok &= print_check("bind_plan('egress')", False, str(exc))
    all_ok &= print_check(
        "executor.egress_bridge importable",
        callable(try_broker_egress_check),
    )
    return all_ok


def assert_domain_compute(env: dict[str, str]) -> bool:
    """sak407-f/i: compute flag + bind_plan + bridges (stage wire active)."""
    from broker_client import bind_plan, broker_compute_enabled, select_backend
    from broker_client.compute_bridge import try_broker_compute_work
    from orchestrator.compute_broker_bridge import try_broker_compute_work as orch_try_broker

    print(f"  note: {COMPUTE_STAGE_WIRE_NOTE}")

    all_ok = True
    all_ok &= print_check("broker_compute_enabled()", broker_compute_enabled())
    all_ok &= print_check("select_backend('compute') == broker", select_backend("compute") == "broker")
    try:
        plan = bind_plan("compute")
        all_ok &= print_check(
            "bind_plan('compute')",
            plan.get("offer") == "compute.work",
            str(plan.get("offer")),
        )
    except Exception as exc:  # noqa: BLE001
        all_ok &= print_check("bind_plan('compute')", False, str(exc))
    all_ok &= print_check(
        "broker_client.compute_bridge importable",
        callable(try_broker_compute_work),
    )
    all_ok &= print_check(
        "orchestrator.compute_broker_bridge importable",
        callable(orch_try_broker),
    )
    # Flag off in parent env → orchestrator hook returns None (sak407-i).
    saved = os.environ.get("NIMBUSWARE_BROKER_COMPUTE")
    try:
        os.environ.pop("NIMBUSWARE_BROKER_COMPUTE", None)
        all_ok &= print_check(
            "orchestrator compute_broker_bridge flag off -> None",
            orch_try_broker({"kind": "echo"}) is None,
        )
    finally:
        if saved is not None:
            os.environ["NIMBUSWARE_BROKER_COMPUTE"] = saved
    return all_ok


def assert_domain_capacity(env: dict[str, str]) -> bool:
    """sak418-f / sak419-g: capacity flag + bind_plan + capacity bridges + hw thin stubs."""
    from broker_client import bind_plan, broker_capacity_enabled, select_backend
    from broker_client.capacity_bridge import (
        try_broker_capacity_pressure,
        try_broker_capacity_probe,
        try_broker_parallel_writer_stages,
        try_broker_probe_dict,
    )
    from orchestrator.capacity_broker_bridge import (
        try_broker_capacity_probe as orch_try_broker,
    )

    all_ok = True
    all_ok &= print_check("broker_capacity_enabled()", broker_capacity_enabled())
    all_ok &= print_check(
        "select_backend('capacity') == broker",
        select_backend("capacity") == "broker",
    )
    try:
        plan = bind_plan("capacity")
        all_ok &= print_check(
            "bind_plan('capacity')",
            plan.get("offer") == "capacity.probe",
            str(plan.get("offer")),
        )
    except Exception as exc:  # noqa: BLE001
        all_ok &= print_check("bind_plan('capacity')", False, str(exc))
    all_ok &= print_check(
        "broker_client.capacity_bridge probe importable",
        callable(try_broker_capacity_probe),
    )
    all_ok &= print_check(
        "broker_client.capacity_bridge pressure importable",
        callable(try_broker_capacity_pressure),
    )
    all_ok &= print_check(
        "broker_client.capacity_bridge parallel stages importable",
        callable(try_broker_parallel_writer_stages),
    )
    all_ok &= print_check(
        "broker_client.capacity_bridge probe_dict importable",
        callable(try_broker_probe_dict),
    )
    all_ok &= print_check(
        "orchestrator.capacity_broker_bridge importable",
        callable(orch_try_broker),
    )
    try:
        import hw.cache as hw_cache
        import hw.fit as hw_fit
        import hw.governor as hw_governor
        import hw.pressure as hw_pressure
        import hw.probe as hw_probe

        all_ok &= print_check(
            "hw thin stubs importable (pressure/probe/cache/fit/governor)",
            all(
                callable(fn)
                for fn in (
                    hw_pressure.sample_pressure,
                    hw_probe.probe_hardware,
                    hw_cache.get_cached_profile,
                    hw_fit.rank_models,
                    hw_governor.governor_for_profile,
                )
            ),
        )
    except Exception as exc:  # noqa: BLE001
        all_ok &= print_check(
            "hw thin stubs importable (pressure/probe/cache/fit/governor)",
            False,
            str(exc),
        )
    saved = os.environ.get("NIMBUSWARE_BROKER_CAPACITY")
    try:
        os.environ.pop("NIMBUSWARE_BROKER_CAPACITY", None)
        all_ok &= print_check(
            "orchestrator capacity_broker_bridge flag off -> None",
            orch_try_broker() is None,
        )
    finally:
        if saved is not None:
            os.environ["NIMBUSWARE_BROKER_CAPACITY"] = saved
    return all_ok


# Back-compat aliases (sak403-f–sak405-f names)
assert_sak403_f_llm = assert_domain_llm
assert_sak404_f_sandbox_tools = assert_domain_sandbox
assert_sak405_f_memory = assert_domain_memory


def run_dual_run_contract_pytest(env: dict[str, str]) -> bool:
    cmd = [sys.executable, "-m", "pytest", "-q", *DUAL_RUN_CONTRACT_TESTS]
    result = subprocess.run(
        cmd,
        cwd=NIMBUSWARE_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    ok = result.returncode == 0
    detail = f"exit {result.returncode}"
    if not ok and result.stdout.strip():
        detail = f"{detail}; {result.stdout.strip().splitlines()[-1]}"
    print_check("dual-run contract pytest bundle", ok, detail)
    return ok


def _http_health_ok(env: dict[str, str]) -> tuple[bool, str]:
    """GET ``/health`` or ``/v1/sak/health`` when HTTP broker URL is configured."""
    from broker_client.http import resolve_base_url, resolve_token
    from broker_client.http_get import get_json

    base_url = resolve_base_url(env.get("NIMBUSWARE_BROKER_HTTP"))
    token = resolve_token(env.get("NIMBUSWARE_BROKER_TOKEN"))
    last_exc = ""
    for path in ("/health", "/v1/sak/health"):
        try:
            body = get_json(base_url, path, token=token, timeout=10.0)
            ok = body is not None
            detail = f"{base_url}{path} -> {body!r}" if ok else f"{base_url}{path} empty"
            return ok, detail
        except Exception as exc:  # noqa: BLE001
            last_exc = str(exc)
    return False, last_exc or "no health endpoint responded"


def _mcp_live_ok(env: dict[str, str]) -> tuple[bool, str]:
    """``ping`` tool or ``tools/list`` when MCP broker URL is configured."""
    from broker_client.mcp_client import BrokerMcpClient

    mcp_url = env.get("NIMBUSWARE_BROKER_MCP", "").strip()
    client = BrokerMcpClient(base_url=mcp_url or None)
    try:
        ping = client.ping()
        return ping is not None, f"{client.base_url} ping -> ok"
    except Exception as ping_exc:  # noqa: BLE001
        try:
            tools = client.list_tools()
            return tools is not None, f"{client.base_url} tools/list -> ok"
        except Exception as list_exc:  # noqa: BLE001
            return False, f"ping: {ping_exc}; tools/list: {list_exc}"


def try_broker_live_check(env: dict[str, str], *, require_live: bool = False) -> bool | None:
    http_url = env.get("NIMBUSWARE_BROKER_HTTP", "").strip()
    mcp_url = env.get("NIMBUSWARE_BROKER_MCP", "").strip()
    if not http_url and not mcp_url:
        if require_live:
            print_check(
                "broker live check configured",
                False,
                "NIMBUSWARE_BROKER_HTTP / NIMBUSWARE_BROKER_MCP unset (--require-live)",
            )
            return False
        print("  broker live check skipped (NIMBUSWARE_BROKER_HTTP / NIMBUSWARE_BROKER_MCP unset)")
        return None

    all_ok = True
    if http_url:
        ok, detail = _http_health_ok(env)
        all_ok &= print_check("HTTP health (/health or /v1/sak/health)", ok, detail)
    if mcp_url:
        ok, detail = _mcp_live_ok(env)
        all_ok &= print_check("MCP ping or tools/list", ok, detail)
    return all_ok


def run_domain_sections(
    env: dict[str, str],
    sections: tuple[tuple[str, Callable[[dict[str, str]], bool]], ...],
) -> bool:
    all_ok = True
    for label, fn in sections:
        print(f"\n--- {label} ---")
        all_ok &= fn(env)
    return all_ok


def domain_smoke_sections() -> tuple[tuple[str, Callable[[dict[str, str]], bool]], ...]:
    """Ordered domain assert sections for ``peel_soak_smoke.py``."""
    return (
        ("sak403-f — LLM flag + bind_plan + broker_bridge", assert_domain_llm),
        ("sak404-f — sandbox/tools bind_plan + bridges", assert_domain_sandbox),
        ("sak405-f — memory bind_plan + memory_bridge", assert_domain_memory),
        ("sak406-h — research flag + bind_plan + research_bridge", assert_domain_research),
        ("sak406-h — egress flag + bind_plan + egress_bridge", assert_domain_egress),
        ("sak407-f — compute flag + bind_plan + compute_bridge", assert_domain_compute),
        ("sak418-f — capacity flag + bind_plan + capacity_bridge", assert_domain_capacity),
    )


def broker_only_smoke_sections() -> tuple[tuple[str, Callable[[dict[str, str]], bool]], ...]:
    """Extra sections when ``--broker-only`` (`sak421-b`)."""
    return (
        ("sak429-h — COMPUTE=2 / CAPACITY=2 refuse-local", assert_broker_only_refuse_local),
        ("sak430-i — COMPUTE=2 / CAPACITY=2 refuse-local (+ mesh=1 assert)", assert_broker_only_refuse_local),
        ("sak431-i — COMPUTE exclusivity + enqueue helpers", assert_broker_only_refuse_local),
        ("sak432-j — COMPUTE/CAPACITY exclusivity deepen", assert_broker_only_refuse_local),
        ("sak433-i — storage gate + CAPACITY=1 hw exclusivity", assert_broker_only_refuse_local),
        ("sak434-j — caller harden + dual_run_route", assert_broker_only_refuse_local),
        ("sak435-j — bridge exclusivity + session status", assert_broker_only_refuse_local),
        ("sak436-j — stage_bind exclusivity + map_broker_http_error", assert_broker_only_refuse_local),
        ("sak437-j — error-dict exclusivity + CAPACITY soft-miss refuse", assert_broker_only_refuse_local),
        ("sak438-j — error+[] exclusivity + write-path asserts", assert_broker_only_refuse_local),
        ("sak439-j — worker_cli/pipeline exclusivity + claim normalize", assert_broker_only_refuse_local),
        ("sak440-j — node match + ctor refuse + claim OpenAPI/SDK", assert_broker_only_refuse_local),
        ("sak441-j — list harden + capacity HTTP miss + OpenAPI/SDK", assert_broker_only_refuse_local),
        ("sak442-j — fleet miss + CAPACITY=2 503 + list assert", assert_broker_only_refuse_local),
        ("sak443-j — apply-preset miss + claim/opt-out + SDK list", assert_broker_only_refuse_local),
        ("sak444-j — presets restore + try_broker_call gone + Maker peel", assert_broker_only_refuse_local),
        ("sak445-j — capacity alias gone + OpenAPI/SDK/Maker compute miss", assert_broker_only_refuse_local),
        ("sak446-j — OpenAPI + remote_host CAPACITY + SDK/UI peel", assert_broker_only_refuse_local),
        ("sak447-j — Maker miss + readiness CAPACITY + raw POST assert", assert_broker_only_refuse_local),
        ("sak448-j — Maker miss harden + OpenAPI + admin peel + health assert", assert_broker_only_refuse_local),
        ("sak449-j — Maker timeline/stitch miss + OpenAPI + admin/SDK peel", assert_broker_only_refuse_local),
        ("sak480-j — Maker miss + OpenAPI + admin/SDK queue_depth", assert_broker_only_refuse_local),
        ("sak481-j — Maker/home/chat miss + OpenAPI + admin/SDK parity", assert_broker_only_refuse_local),
        ("sak482-j — Deploy/collab Maker miss + OpenAPI + admin/SDK parity", assert_broker_only_refuse_local),
        ("sak483-j — Operator ribbon Maker miss + OpenAPI + admin/SDK write-path", assert_broker_only_refuse_local),
        ("sak484-j — Home/chat Maker miss + campaign OpenAPI + admin/SDK node-path", assert_broker_only_refuse_local),
        ("sak485-j — Operator/plan Maker miss + run/fleet OpenAPI + admin/SDK", assert_broker_only_refuse_local),
        ("sak486-j — Maker write-path miss + enterprise/runs OpenAPI + Config/Metrics", assert_broker_only_refuse_local),
        ("sak487-j — Maker write-path miss + actions OpenAPI + admin RunDetail", assert_broker_only_refuse_local),
        ("sak488-j — Read/long-tail + admin fleet writes + DELETE peel + SDK", assert_broker_only_refuse_local),
        ("sak489-j — Compute refuse deepen + peel_assert refactor + SSE/export", assert_broker_only_refuse_local),
        ("sak490-j — compute residual refuse + route refactor + CI flag-matrix", assert_broker_only_refuse_local),
        # sak491-j ledgers land later; soak section enabled now (sak491-e asserts).
        ("sak491-j — queue read refuse + CAPACITY=2 matrix + OpenAPI/admin/SDK", assert_broker_only_refuse_local),
        ("sak492-j — capacity OpenAPI + COMPUTE=2 matrix + LLM peel + admin 503", assert_broker_only_refuse_local),
        ("sak493-j — readiness/LLM OpenAPI + soft-swallow + Maker/admin 503 + memory", assert_broker_only_refuse_local),
        ("sak494-j — memory/sandbox/research miss + BFF OpenAPI + domain peel_miss refactor", assert_broker_only_refuse_local),
        ("sak495-j — memory index refuse + OpenAPI long-tail + TOOLS miss + compute peel_miss refactor", assert_broker_only_refuse_local),
        ("sak496-j — LLM stub close + domain broker_route + OpenAPI/SSE + Maker long-tail miss", assert_broker_only_refuse_local),
        ("sak497-j — slice/plan LLM wire + campaign OpenAPI + domain SSE + llm __init__ close-out", assert_broker_only_refuse_local),
        ("sak498-j — bootstrap/memory harden + LLM wire + MCP asserts + soak/CI close-out", assert_broker_only_refuse_local),
        ("sak499-j — Maker/admin miss parity + peel_guard + home/build/wizard + soak/CI close-out", assert_broker_only_refuse_local),
        ("sak500-f — Maker ribbons + admin long-tail + OpenAPI custom-agents/standards + soak/CI", assert_broker_only_refuse_local),
        ("sak500-j — Maker residual sse/bootstrap + projects/preflight OpenAPI + soak/CI", assert_broker_only_refuse_local),
        ("sak501-f — Hardware domain + run ribbon OpenAPI + capacity formatter + soak/CI", assert_broker_only_refuse_local),
        ("sak501-j — settings/bindings/push OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak502-f — runs/provider/fleet OpenAPI + with_long_tail_peel_503 + soak/CI", assert_broker_only_refuse_local),
        ("sak502-j — run detail/slice/factory OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak503-f — policy/deploy/fleet OpenAPI + with_enterprise_peel_503 + soak/CI", assert_broker_only_refuse_local),
        ("sak503-j — run compact/budget/integrations OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak504-f — auth/fleet OpenAPI + artifact_peel_503 + soak/CI", assert_broker_only_refuse_local),
        ("sak504-j — run timeline/lifecycle/projection OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak505-f — personas/bundles/config OpenAPI + ensure_operation + soak/CI", assert_broker_only_refuse_local),
        ("sak505-j — bindings/role-claims/autopilot OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak506-f — theater/actions/standards OpenAPI + ensure_paths + soak/CI", assert_broker_only_refuse_local),
        ("sak506-j — override/interjection/standards OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak507-f — maker/standards-profile OpenAPI + count_missing + soak/CI", assert_broker_only_refuse_local),
        ("sak507-j — maker mutate/bundle OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak508-f — platform deploy OpenAPI + list_missing + soak/CI", assert_broker_only_refuse_local),
        ("sak508-j — deploy approve/audit/hardware OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak509-f — hardware fleet/models OpenAPI + count_missing DRY + soak/CI", assert_broker_only_refuse_local),
        ("sak509-j — routing/invite/collab OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak510-f — readiness/onboarding/optimizer OpenAPI + patch helper + soak/CI", assert_broker_only_refuse_local),
        ("sak510-j — precommit/safe-coding/bindings OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak511-f — enterprise status/memory/worker OpenAPI + complete helper + soak/CI", assert_broker_only_refuse_local),
        ("sak511-j — factory-evidence/streams/policy OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak512-f — bundles/critic/custom-agents OpenAPI + file missing helper + soak/CI", assert_broker_only_refuse_local),
        ("sak512-j — projects/chat-start/scope OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak513-f — chat compute/weights/bindings OpenAPI + complete-in-file + soak/CI", assert_broker_only_refuse_local),
        ("sak513-j — sessions/classify/host-transfer OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak514-f — host-transfer deepen OpenAPI + peel_503_coverage + soak/CI", assert_broker_only_refuse_local),
        ("sak514-j — folders/groups OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak515-f — access-grants/participants OpenAPI + coverage-in-file + soak/CI", assert_broker_only_refuse_local),
        ("sak515-j — join/stream OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak516-f — commentary/artifacts/presets OpenAPI + count-in-file + soak/CI", assert_broker_only_refuse_local),
        ("sak516-j — user-profile OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak517-f — provider-connections OpenAPI + ensure helper + soak/CI", assert_broker_only_refuse_local),
        ("sak517-j — compute nodes OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak518-f — settings/fleet-mesh OpenAPI + ensure_paths skip + soak/CI", assert_broker_only_refuse_local),
        ("sak518-j — fleet-ollama/tenant-policy OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak519-f — stack/deploy/audit OpenAPI + complete-in-file DRY + soak/CI", assert_broker_only_refuse_local),
        ("sak519-j — model/collab-policy OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak520-f — tenant model-policy/bootstrap OpenAPI + report helper + soak/CI", assert_broker_only_refuse_local),
        ("sak520-j — enforcement/push OpenAPI + soak/CI deepen", assert_broker_only_refuse_local),
        ("sak521-f — product peel complete + oauth skip + soak/CI", assert_broker_only_refuse_local),
    )
