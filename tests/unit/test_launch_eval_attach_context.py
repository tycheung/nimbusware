from __future__ import annotations

from orchestrator.launch_eval_catalog import (
    attach_context_from_run,
    match_prompt_id,
)


def test_match_prompt_id_basic_crm() -> None:
    assert match_prompt_id("Build a minimal CRM with user authentication") == "basic_crm"


def test_match_prompt_id_todo_api() -> None:
    assert match_prompt_id("Build a minimal todo list REST API") == "todo_api"


def test_match_prompt_id_contacts_api() -> None:
    assert (
        match_prompt_id("REST contacts API campaign with health check and contact list endpoints")
        == "contacts_api"
    )


def test_attach_context_from_run_created() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "workflow_profile": "micro_slice",
                "requirements": {"business_prompt": "Build a minimal CRM with auth"},
            },
        }
    ]
    ctx = attach_context_from_run(rows)
    assert ctx["workflow_profile"] == "micro_slice"
    assert ctx["prompt_id"] == "basic_crm"
    assert "business_prompt" in ctx
