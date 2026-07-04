from __future__ import annotations

import json
from typing import Any

from client.http import get_json, post_json, put_response


def _text_result(payload: Any) -> dict[str, Any]:
    text = json.dumps(payload, indent=2, default=str)
    return {"content": [{"type": "text", "text": text}]}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "nimbusware_set_discipline":
        return _call_set_discipline(arguments)
    if name == "nimbusware_update_agent_overlay":
        return _call_update_agent_overlay(arguments)
    if name == "nimbusware_classify_intent":
        return _call_classify_tool(arguments)
    if name in ("nimbusware_patch", "nimbusware_patch_from_selection"):
        return _call_patch_tool(arguments)
    if name == "nimbusware_chat_graph":
        session_id = str(arguments.get("session_id") or "").strip()
        if not session_id:
            raise ValueError("session_id is required")
        return _text_result(get_json(f"/chat/sessions/{session_id}/graph"))
    if name == "nimbusware_chat_fork":
        session_id = str(arguments.get("session_id") or "").strip()
        turn_id = str(arguments.get("turn_id") or "").strip()
        if not session_id or not turn_id:
            raise ValueError("session_id and turn_id are required")
        return _text_result(
            post_json(f"/chat/sessions/{session_id}/fork", {"turn_id": turn_id}),
        )
    if name == "nimbusware_chat_select_branch":
        session_id = str(arguments.get("session_id") or "").strip()
        leaf_turn_id = str(arguments.get("leaf_turn_id") or "").strip()
        if not session_id or not leaf_turn_id:
            raise ValueError("session_id and leaf_turn_id are required")
        resp = put_response(
            f"/chat/sessions/{session_id}/active-leaf",
            {"leaf_turn_id": leaf_turn_id},
        )
        leaf_body = resp.json()
        return _text_result(leaf_body if isinstance(leaf_body, dict) else {"data": leaf_body})
    if name in ("nimbusware_list_context_artifacts", "nimbusware_create_context_artifact"):
        return _call_project_tool(name, arguments)
    if name in (
        "nimbusware_campaign_status",
        "nimbusware_pause_campaign",
        "nimbusware_backlog_summary",
        "nimbusware_resume_campaign",
    ):
        campaign_id = str(arguments.get("campaign_id") or "").strip()
        if not campaign_id:
            raise ValueError("campaign_id is required")
        if name == "nimbusware_campaign_status":
            progress = get_json(f"/runs/{campaign_id}/maker-progress")
            return _text_result(progress.get("campaign_progress") or progress)
        if name == "nimbusware_pause_campaign":
            reason = str(arguments.get("reason_code") or "mcp")
            return _text_result(
                post_json(f"/campaigns/{campaign_id}/pause", {"reason_code": reason}),
            )
        if name == "nimbusware_resume_campaign":
            return _text_result(post_json(f"/campaigns/{campaign_id}/resume", {}))
        return _text_result(get_json(f"/campaigns/{campaign_id}/backlog"))

    run_id = str(arguments.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("run_id is required")
    if name == "maker_pending":
        return _text_result(get_json(f"/runs/{run_id}/maker/pending"))
    if name == "nimbusware_prepare_slice":
        return _text_result(post_json(f"/runs/{run_id}/maker/slices/prepare", {}))
    if name == "nimbusware_apply_slice":
        slice_id = str(arguments.get("slice_id") or "").strip()
        if not slice_id:
            raise ValueError("slice_id is required")
        return _text_result(
            post_json(f"/runs/{run_id}/maker/slices/apply", {"slice_id": slice_id}),
        )
    if name == "nimbusware_skip_slice":
        slice_id = str(arguments.get("slice_id") or "").strip()
        if not slice_id:
            raise ValueError("slice_id is required")
        return _text_result(
            post_json(f"/runs/{run_id}/maker/slices/skip", {"slice_id": slice_id}),
        )
    if name == "nimbusware_run_status":
        return _text_result(get_json(f"/runs/{run_id}"))
    if name == "nimbusware_run_theater":
        limit = int(arguments.get("limit") or 50)
        return _text_result(
            get_json(f"/runs/{run_id}/theater", params={"cursor": 0, "limit": limit}),
        )
    if name == "nimbusware_slice_diff":
        raw_idx = arguments.get("slice_index")
        if raw_idx is None:
            raise ValueError("slice_index is required")
        idx = int(raw_idx)
        return _text_result(get_json(f"/runs/{run_id}/slices/{idx}/diff"))
    if name == "nimbusware_approve_plan":
        return _text_result(post_json(f"/runs/{run_id}/maker/plan/approve", {}))
    if name == "nimbusware_revert_workspace":
        return _text_result(post_json(f"/runs/{run_id}/workspace/revert", {}))
    if name == "nimbusware_compact_run":
        body: dict[str, Any] = {}
        scope = str(arguments.get("scope") or "").strip()
        if scope:
            body["scope"] = scope
        if arguments.get("n") is not None:
            body["n"] = int(arguments["n"])
        refs = arguments.get("source_refs")
        if isinstance(refs, list) and refs:
            body["source_refs"] = [str(r) for r in refs]
        return _text_result(post_json(f"/runs/{run_id}/compact", body))
    if name == "nimbusware_factory_evidence":
        return _text_result(get_json(f"/runs/{run_id}/factory-evidence"))
    if name == "nimbusware_replay_from":
        seq = arguments.get("checkpoint_seq")
        if seq is None:
            raise ValueError("checkpoint_seq is required")
        return _text_result(
            post_json(
                f"/runs/{run_id}/replay-from",
                {
                    "checkpoint_seq": int(seq),
                    "operator_ack": bool(arguments.get("operator_ack", True)),
                },
            ),
        )
    if name == "nimbusware_launch_eval":
        return _text_result(post_json(f"/runs/{run_id}/maker/launch-eval", {}))
    if name == "nimbusware_insert_context_artifact":
        aid = str(arguments.get("artifact_id") or "").strip()
        if not aid:
            raise ValueError("artifact_id is required")
        return _text_result(
            post_json(f"/runs/{run_id}/context-artifacts/{aid}/insert", {}),
        )
    if name == "nimbusware_interject":
        message = str(arguments.get("message") or "").strip()
        if not message:
            raise ValueError("message is required")
        priority = str(arguments.get("priority") or "next").strip().lower()
        interject_body: dict[str, Any] = {
            "message": message,
            "priority": priority,
            "force_break": bool(arguments.get("force_break", False)),
        }
        return _text_result(post_json(f"/runs/{run_id}/interjection-queue", interject_body))
    if name == "nimbusware_run_tests":
        return _text_result(post_json(f"/runs/{run_id}/maker/run-tests", {}))
    if name == "nimbusware_standards_run":
        standards_body: dict[str, Any] = {}
        stream = str(arguments.get("stream") or "").strip()
        bundle = str(arguments.get("bundle") or "").strip()
        profile = str(arguments.get("profile") or "").strip()
        if stream:
            standards_body["stream"] = stream
        if bundle:
            standards_body["bundle"] = bundle
        if profile:
            standards_body["profile"] = profile
        return _text_result(post_json(f"/runs/{run_id}/standards/run", standards_body))
    if name == "nimbusware_standards_report":
        return _text_result(get_json(f"/runs/{run_id}/standards/report"))
    if name == "nimbusware_standards_profile":
        if arguments.get("facade_id") is not None or arguments.get("bundles") is not None:
            put_body: dict[str, Any] = {}
            facade_id = str(arguments.get("facade_id") or "").strip()
            if facade_id:
                put_body["facade_id"] = facade_id
            bundles = arguments.get("bundles")
            if isinstance(bundles, list):
                put_body["bundles"] = [str(b) for b in bundles if str(b).strip()]
            connectors = arguments.get("connectors")
            if isinstance(connectors, list):
                put_body["connectors"] = [str(c) for c in connectors if str(c).strip()]
            overrides = arguments.get("verdict_overrides")
            if isinstance(overrides, dict):
                put_body["verdict_overrides"] = overrides
            resp = put_response(f"/runs/{run_id}/standards", put_body)
            payload = resp.json()
            return _text_result(payload if isinstance(payload, dict) else {"data": payload})
        return _text_result(get_json(f"/runs/{run_id}/standards"))
    if name == "nimbusware_swap_role_model":
        agent_role = str(arguments.get("agent_role") or "").strip()
        provider_id = str(arguments.get("provider_id") or "").strip()
        model_id = str(arguments.get("model_id") or "").strip()
        provider_kind = str(arguments.get("provider_kind") or "local").strip()
        if not agent_role or not provider_id or not model_id:
            raise ValueError("agent_role, provider_id, and model_id are required")
        return _text_result(
            post_json(
                f"/runs/{run_id}/model-bindings/swap",
                {
                    "agent_role": agent_role,
                    "provider_id": provider_id,
                    "provider_kind": provider_kind,
                    "model_id": model_id,
                },
            ),
        )
    raise ValueError(f"unknown tool: {name}")


def _call_set_discipline(arguments: dict[str, Any]) -> dict[str, Any]:
    discipline = str(arguments.get("discipline") or "").strip()
    body: dict[str, Any] = {"default_discipline": discipline or None}
    resp = put_response("/users/me/discipline-profile", body)
    payload = resp.json()
    return _text_result(payload if isinstance(payload, dict) else {"data": payload})


def _call_update_agent_overlay(arguments: dict[str, Any]) -> dict[str, Any]:
    discipline = str(arguments.get("discipline") or "").strip()
    if not discipline:
        raise ValueError("discipline is required")
    if arguments.get("clear"):
        body: dict[str, Any] = {"prompt_extension": None, "custom_agent_id": None}
    else:
        body = {}
        if "prompt_extension" in arguments:
            ext = str(arguments.get("prompt_extension") or "").strip()
            body["prompt_extension"] = ext or None
        if "custom_agent_id" in arguments:
            agent_id = str(arguments.get("custom_agent_id") or "").strip()
            body["custom_agent_id"] = agent_id or None
        if not body:
            raise ValueError("prompt_extension, custom_agent_id, or clear is required")
    resp = put_response(f"/users/me/agent-overlays/{discipline}", body)
    payload = resp.json()
    return _text_result(payload if isinstance(payload, dict) else {"data": payload})


def _call_classify_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    message = str(arguments.get("message") or "").strip()
    if not message:
        raise ValueError("message is required")
    body: dict[str, Any] = {"message": message}
    project_id = str(arguments.get("project_id") or "").strip()
    if project_id:
        body["project_id"] = project_id
    attachments = arguments.get("attachments")
    if isinstance(attachments, list) and attachments:
        body["attachments"] = attachments
    return _text_result(post_json("/chat/classify", body))


def _patch_workflow_profile(project_id: str) -> str:
    from pathlib import Path

    try:
        proj = get_json(f"/projects/{project_id}")
        ws = Path(str(proj.get("workspace_path") or ""))
        if (ws / "go.mod").is_file():
            return "patch_go"
        if (ws / "pom.xml").is_file():
            return "patch_jvm"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return "patch"


def _call_patch_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_id = str(arguments.get("project_id") or "").strip()
    message = str(arguments.get("message") or "").strip()
    if not project_id:
        raise ValueError("project_id is required")
    if not message:
        raise ValueError("message is required")
    profile = str(arguments.get("workflow_profile") or "").strip() or _patch_workflow_profile(
        project_id,
    )
    patch_ctx: dict[str, Any] = {}
    paths = arguments.get("target_paths")
    if isinstance(paths, list) and paths:
        patch_ctx["target_paths"] = [str(p) for p in paths if str(p).strip()]
    failing = str(arguments.get("failing_test") or "").strip()
    if failing:
        patch_ctx["failing_test"] = failing
    trace = str(arguments.get("stack_trace") or "").strip()
    if trace:
        patch_ctx["stack_trace"] = trace
    create_body: dict[str, Any] = {
        "project_id": project_id,
        "workflow_profile": profile,
        "work_type": "patch",
        "work_type_source": "ide",
        "requirements": {"business_prompt": message},
    }
    if patch_ctx:
        create_body["patch_context"] = patch_ctx
    created = post_json("/runs", create_body)
    run_id = str(created.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("create run response missing run_id")
    post_json(f"/runs/{run_id}/lifecycle/start", {})
    slice_result = post_json(f"/runs/{run_id}/lifecycle/slice?mode=auto", {})
    return _text_result({"run_id": run_id, "create": created, "slice": slice_result})


def _call_project_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    project_id = str(arguments.get("project_id") or "").strip()
    if not project_id:
        raise ValueError("project_id is required")
    if name == "nimbusware_list_context_artifacts":
        return _text_result(get_json(f"/projects/{project_id}/context-artifacts"))
    if name == "nimbusware_create_context_artifact":
        title = str(arguments.get("title") or "").strip()
        content = str(arguments.get("content") or "").strip()
        if not title or not content:
            raise ValueError("title and content are required")
        kind = str(arguments.get("kind") or "note")
        return _text_result(
            post_json(
                f"/projects/{project_id}/context-artifacts",
                {"title": title, "content": content, "kind": kind},
            ),
        )
    raise ValueError(f"unknown tool: {name}")
