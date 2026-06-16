from __future__ import annotations

from agent_core.critique_stages import (
    CRITIQUE_STAGE_TO_PRODUCER,
    IMPLEMENTATION_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from agent_core.prompt_tiers import PromptTier, assemble_prompt, stable_slice_agent_block
from agent_core.read.critic_matrix import (
    build_live_critic_matrix_rows,
    critic_matrix_unanimous_summary,
)
from agent_core.slice_plan import SlicePlan, parse_slice_plan
from agent_core.stage_graph import (
    default_stage_graph,
    stage_graph_timeline_summary_from_metadata,
    topological_order,
)


def test_parse_slice_plan_normalizes_paths() -> None:
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "rationale": "fix",
            "target_paths": ["a.py", ""],
            "acceptance_criteria": "tests pass",
        },
    )
    assert plan == SlicePlan(
        slice_id="s1",
        rationale="fix",
        target_paths=("a.py",),
        acceptance_criteria="tests pass",
    )


def test_assemble_prompt_orders_tiers() -> None:
    messages = assemble_prompt(stable="stable", context="ctx", volatile="do work")
    assert messages[0]["role"] == "system"
    assert "stable" in messages[0]["content"]
    assert "ctx" in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "do work"}


def test_stable_slice_agent_block_includes_tool_rules() -> None:
    block = stable_slice_agent_block(tool_rules="use read only")
    assert "use read only" in block
    assert PromptTier.STABLE.value == "stable"


def test_critique_stage_constants_align_with_producer_map() -> None:
    assert CRITIQUE_STAGE_TO_PRODUCER[IMPLEMENTATION_CRITIQUE_STAGE] == "backend_writer"
    assert CRITIQUE_STAGE_TO_PRODUCER[TEST_WRITER_CRITIQUE_STAGE] == "test_writer"


def test_stage_graph_topological_order_matches_defaults() -> None:
    graph = default_stage_graph()
    ordered = topological_order(graph)
    assert ordered[0] == "plan"
    assert "implementation.critique" in ordered


def test_critic_matrix_rows_from_gate_events() -> None:
    events = [
        {
            "event_type": "run.created",
            "metadata": {
                "stage_graph": {
                    "ordered_stage_names": ["implementation.critique"],
                    "nodes": [],
                },
            },
        },
        {
            "event_type": "gate.decision.emitted",
            "payload": {
                "stage_name": "implementation.critique",
                "verdict": "PASS",
            },
        },
    ]
    rows = build_live_critic_matrix_rows(events)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "PASS"
    summary = critic_matrix_unanimous_summary(rows)
    assert summary["pass_count"] == 1


def test_stage_graph_timeline_summary_from_metadata() -> None:
    meta = {
        "stage_graph": {
            "ordered_stage_names": ["plan", "implementation"],
            "parallel_groups": {"writers": ["implementation", "test_writer"]},
        },
    }
    out = stage_graph_timeline_summary_from_metadata(meta)
    assert out is not None
    assert out["stage_count"] == 2
    assert out["parallel_group_count"] == 1
