from __future__ import annotations

from typing import Any

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "nimbusware_prepare_slice",
        "description": "Prepare the next pending slice for maker approval.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_apply_slice",
        "description": "Apply a pending slice after operator approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "slice_id": {"type": "string"},
            },
            "required": ["run_id", "slice_id"],
        },
    },
    {
        "name": "nimbusware_skip_slice",
        "description": "Skip a pending slice without applying.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "slice_id": {"type": "string"},
            },
            "required": ["run_id", "slice_id"],
        },
    },
    {
        "name": "nimbusware_maker_pending",
        "description": "Fetch pending slice and plan approval state for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_resume_campaign",
        "description": "Resume a paused campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_run_status",
        "description": "Fetch run summary from GET /v1/runs/{run_id}.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_run_theater",
        "description": "Fetch plain-language theater messages for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_slice_diff",
        "description": "Fetch unified diff for a slice index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "slice_index": {"type": "integer", "minimum": 0},
            },
            "required": ["run_id", "slice_index"],
        },
    },
    {
        "name": "nimbusware_approve_plan",
        "description": "Approve the pending maker plan gate for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_campaign_status",
        "description": "Fetch campaign progress for a run/campaign id.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_pause_campaign",
        "description": "Pause an active campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "reason_code": {"type": "string"},
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_backlog_summary",
        "description": "Fetch delivery backlog tree summary for a campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_revert_workspace",
        "description": "Revert workspace changes for the latest applied slice on a run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_compact_run",
        "description": "Trigger campaign context compaction for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "scope": {"type": "string", "enum": ["all", "last_n", "source_refs"]},
                "n": {"type": "integer", "minimum": 1},
                "source_refs": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_factory_evidence",
        "description": "Fetch factory completion evidence bundle for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_replay_from",
        "description": "Replay a run from a checkpoint with optional compaction policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "checkpoint_seq": {"type": "integer", "minimum": 0},
                "operator_ack": {"type": "boolean"},
            },
            "required": ["run_id", "checkpoint_seq"],
        },
    },
    {
        "name": "nimbusware_launch_eval",
        "description": "Run launch eval rubric for a campaign run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_list_context_artifacts",
        "description": "List project-scoped context artifacts.",
        "inputSchema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "nimbusware_create_context_artifact",
        "description": "Create a project-scoped context artifact.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "kind": {"type": "string"},
            },
            "required": ["project_id", "title", "content"],
        },
    },
    {
        "name": "nimbusware_insert_context_artifact",
        "description": "Insert a context artifact into a run event stream.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "artifact_id": {"type": "string"},
            },
            "required": ["run_id", "artifact_id"],
        },
    },
    {
        "name": "nimbusware_classify_intent",
        "description": "Classify operator intent via POST /v1/chat/classify.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "project_id": {"type": "string"},
                "attachments": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["message"],
        },
    },
    {
        "name": "nimbusware_patch",
        "description": "Create a patch run and start the first slice (work_type_source=ide).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "message": {"type": "string"},
                "target_paths": {"type": "array", "items": {"type": "string"}},
                "failing_test": {"type": "string"},
                "stack_trace": {"type": "string"},
            },
            "required": ["project_id", "message"],
        },
    },
    {
        "name": "nimbusware_patch_from_selection",
        "description": (
            "Patch from IDE selection context (failing test, stack trace, target paths) "
            "without opening Maker."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "message": {"type": "string"},
                "target_paths": {"type": "array", "items": {"type": "string"}},
                "failing_test": {"type": "string"},
                "stack_trace": {"type": "string"},
            },
            "required": ["project_id", "message"],
        },
    },
    {
        "name": "nimbusware_interject",
        "description": "Enqueue an operator interjection (supports [patch]/[steer]/[skip] prefixes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "message": {"type": "string"},
                "priority": {"type": "string", "enum": ["next", "last"]},
                "force_break": {"type": "boolean"},
            },
            "required": ["run_id", "message"],
        },
    },
    {
        "name": "nimbusware_run_tests",
        "description": "Run targeted slice tests for a run workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_chat_graph",
        "description": "Fetch conversation DAG for a chat session.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "nimbusware_chat_fork",
        "description": "Fork a chat session from a prior turn (non-destructive branch).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "turn_id": {"type": "string"},
            },
            "required": ["session_id", "turn_id"],
        },
    },
    {
        "name": "nimbusware_chat_select_branch",
        "description": "Navigate to an existing branch leaf in a chat session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "leaf_turn_id": {"type": "string"},
            },
            "required": ["session_id", "leaf_turn_id"],
        },
    },
    {
        "name": "nimbusware_swap_role_model",
        "description": "Swap the model binding for an agent role on a run (mid-chat).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "agent_role": {"type": "string"},
                "provider_id": {"type": "string"},
                "provider_kind": {"type": "string", "enum": ["local", "cloud"]},
                "model_id": {"type": "string"},
            },
            "required": ["run_id", "agent_role", "provider_id", "model_id"],
        },
    },
    {
        "name": "nimbusware_set_discipline",
        "description": "Set default collab discipline hat (pm, architect, frontend, backend, qa, devops).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "discipline": {
                    "type": "string",
                    "description": "Discipline id, or empty string to clear.",
                },
            },
            "required": ["discipline"],
        },
    },
    {
        "name": "nimbusware_update_agent_overlay",
        "description": "Save per-discipline agent prompt overlay for the current user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "discipline": {"type": "string"},
                "prompt_extension": {"type": "string"},
                "custom_agent_id": {"type": "string"},
                "clear": {"type": "boolean"},
            },
            "required": ["discipline"],
        },
    },
]
