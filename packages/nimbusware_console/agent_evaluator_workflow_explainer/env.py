from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nimbusware_config.workflow_read import parse_agent_evaluator_workflow_block


def _hermes_agent_evaluator_env_summary() -> dict[str, Any]:
    raw = os.environ.get("HERMES_AGENT_EVALUATOR", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "forces_off": True,
            "forces_on": False,
            "unset": False,
        }
    if low in ("1", "true", "yes"):
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "forces_off": False,
        "forces_on": False,
        "unset": True,
        "unrecognised_value": True,
    }


def _hermes_agent_evaluator_auto_promote_env_summary() -> dict[str, Any]:
    raw = os.environ.get("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "disables_auto_promote": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "disables_auto_promote": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "disables_auto_promote": False,
        "unset": False,
        "unrecognised_value": True,
    }


def _hermes_agent_evaluator_auto_create_env_summary() -> dict[str, Any]:
    raw = os.environ.get("HERMES_AGENT_EVALUATOR_AUTO_CREATE", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "disables_auto_create": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "disables_auto_create": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "disables_auto_create": False,
        "unset": False,
        "unrecognised_value": True,
    }


def _would_emit_agent_evaluator_stage(repo_root: Path, workflow_profile: str | None) -> bool:
    env_raw = os.environ.get("HERMES_AGENT_EVALUATOR", "").strip().lower()
    if env_raw in ("0", "false", "no"):
        return False
    env_on = env_raw in ("1", "true", "yes")
    block = parse_agent_evaluator_workflow_block(repo_root, workflow_profile)
    return env_on or block.enabled


def _would_emit_llm_evaluation(repo_root: Path, workflow_profile: str | None) -> bool:
    if not _would_emit_agent_evaluator_stage(repo_root, workflow_profile):
        return False
    if os.environ.get("HERMES_USE_LLM", "").strip().lower() not in ("1", "true", "yes"):
        return False
    block = parse_agent_evaluator_workflow_block(repo_root, workflow_profile)
    return block.llm_evaluation_enabled
