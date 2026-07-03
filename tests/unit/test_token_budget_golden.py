from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from agent_core.models.slice_handoff import SliceHandoffSummary
from agent_tools.agent_loop import _stable_system_prompt, _volatile_user_prompt
from agent_tools.runtime import _gather_context
from orchestrator.context_compaction import compact_campaign_context
from orchestrator.micro_slice import parse_slice_plan
from orchestrator.prompt_tiers import assemble_prompt
from orchestrator.slice_handoff import handoff_markdown_capped

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "token_budget"


def _baselines() -> dict:
    return json.loads((_FIXTURES / "baselines.json").read_text(encoding="utf-8"))


def _plan():
    raw = json.loads((_FIXTURES / "slice_plan.json").read_text(encoding="utf-8"))
    return parse_slice_plan(raw)


def _message_chars(messages: list[dict[str, str]]) -> int:
    return sum(len(m.get("content") or "") for m in messages)


def test_agent_jit_prompt_within_baselines_and_beats_legacy_preload() -> None:
    baselines = _baselines()
    plan = _plan()
    ws = _FIXTURES / "workspace"
    legacy = len(_gather_context(ws, plan))
    assert legacy <= baselines["agent_legacy_preload_max_chars"]

    stable = _stable_system_prompt(base_prompt=None)
    volatile = _volatile_user_prompt(plan)
    messages = assemble_prompt(stable=stable, volatile=volatile)
    stable_chars = len(stable)
    volatile_chars = len(volatile)
    total = _message_chars(messages)

    assert stable_chars <= baselines["agent_stable_max_chars"]
    assert volatile_chars <= baselines["agent_volatile_max_chars"]
    assert total <= baselines["agent_stable_max_chars"] + baselines["agent_volatile_max_chars"]
    assert volatile_chars <= legacy * baselines["jit_vs_legacy_max_ratio"]

    with patch("agent_tools.runtime._gather_context") as mock_gather:
        from agent_tools import agent_loop

        agent_loop.run(
            ws,
            plan,
            base_url="http://localhost:11434",
            model_id="test",
            chat_fn=lambda **_: {"done": True},
        )
        mock_gather.assert_not_called()


def test_handoff_and_compaction_within_baselines() -> None:
    baselines = _baselines()
    handoff = SliceHandoffSummary(
        goal="golden campaign",
        progress=("slice-1: passed", "slice-2: passed"),
        modified_files=("packages/demo/app.py",),
    )
    handoff_md = handoff_markdown_capped(handoff)
    assert len(handoff_md) <= baselines["handoff_max_chars"]

    events = []
    for i in range(4):
        summary = handoff.render_markdown() + ("x" * 400)
        events.append(
            {
                "seq": i + 1,
                "payload": {"stage_name": "slice.handoff"},
                "metadata": {
                    "handoff_summary": summary,
                    "slice_handoff": handoff.model_dump(mode="json"),
                },
            },
        )
    compacted = compact_campaign_context(events, keep_recent_tokens=200, reserve_tokens=50)
    assert compacted is not None
    assert len(compacted.summary) <= baselines["compaction_summary_max_chars"]
