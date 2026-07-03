from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from orchestrator.workflow_blocks_simple import EscalationWorkflowBlock
from orchestrator.workflow_registry import (
    WORKFLOW_BLOCK_LOADERS,
    WORKFLOW_MODULE_KEYS,
    WORKFLOW_MODULE_LOADERS,
    get_workflow_block_loader,
    parse_workflow_block,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_workflow_module_keys_match_loaders() -> None:
    assert WORKFLOW_MODULE_KEYS == frozenset(WORKFLOW_MODULE_LOADERS)
    assert len(WORKFLOW_MODULE_KEYS) == 20


def test_workflow_block_loaders_include_module_loaders() -> None:
    for key, loader in WORKFLOW_MODULE_LOADERS.items():
        assert WORKFLOW_BLOCK_LOADERS[key] is loader


def test_get_workflow_block_loader_unknown_key() -> None:
    try:
        get_workflow_block_loader("not_a_workflow")
    except KeyError as exc:
        assert "not_a_workflow" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_parse_workflow_block_escalation_default() -> None:
    block = parse_workflow_block("escalation", ROOT, "default")
    assert block == EscalationWorkflowBlock(suppress_automatic_escalation=False)
    assert get_workflow_block_loader("escalation") is WORKFLOW_MODULE_LOADERS["escalation"]
