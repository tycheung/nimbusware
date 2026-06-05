from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import httpx
from pydantic import ValidationError

from nimbusware_orchestrator.llm.common import *  # noqa: F403
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_store.protocol import EventStore


def _ollama_chat_json(*args: object, **kwargs: object) -> object:
    import nimbusware_orchestrator.llm_plan as _patch

    return _patch.ollama_chat_json(*args, **kwargs)


def execute_agent_evaluator_policy_llm(
    store: EventStore,
    registry: RoleRegistry,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    rules_eval: dict[str, Any],
    persona_id: str,
    timeout_seconds: float = 120.0,
) -> dict[str, Any] | None:
    """Optional LLM policy branch for agent evaluator (metadata only; no new event types).

    Rules ``evaluate()`` remains authoritative for timeline status fields. Returns a dict
    with ``status``, ``gaps``, and ``summary`` for pipeline metadata enrichment.
    """
    _ = store, registry, run_id
    pid = str(persona_id).strip() or "default"
    rules_status = rules_eval.get("status")
    rules_gaps = rules_eval.get("gaps")
    gaps_list = [str(g) for g in rules_gaps] if isinstance(rules_gaps, list) else []
    system = (
        "You are a Nimbusware agent-evaluator policy helper. Reply with JSON only. "
        "Schema: status ok|needs_work|invalid, gaps string array, summary string. "
        "Complement rules evaluation; do not contradict obvious invalid shelf states."
    )
    user = f"persona_id={pid!r}. rules_status={rules_status!r}. rules_gaps={gaps_list!r}"
    try:
        data = _ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmAgentEvaluatorPolicyResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return None
    status_raw = str(parsed.status).strip().lower()
    if status_raw in ("ok", "needs_work", "invalid"):
        status_out = status_raw
    else:
        status_out = "needs_work"
    gaps_out = [str(g).strip() for g in parsed.gaps if str(g).strip()][:20]
    summary = str(parsed.summary or "").strip()[:500]
    return {"status": status_out, "gaps": gaps_out, "summary": summary}
