#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

NIMBUSWARE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = NIMBUSWARE_ROOT / "scripts"
AGENTIC_DOCS = NIMBUSWARE_ROOT.parent / "docs"

PEEL_RUNBOOK = AGENTIC_DOCS / "peel-runbook.md"
PEEL_DELETE_INVENTORY = AGENTIC_DOCS / "peel-delete-inventory.md"
PEEL_SOAK_LOG = AGENTIC_DOCS / "peel-soak-log.md"

DEFAULT_ON_GATE_MARKER = "Default-on gate"


@dataclass(frozen=True)
class PeelCandidate:
    """Path relative to Nimbusware repo root."""

    rel_path: str
    action: str  # "delete" | "thin"


# Inventory executed 2026-07-24 (sak411–413) + 2026-07-24 (sak416-h/i research/egress)
# + 2026-07-24 (sak417-c compute thin stubs) + 2026-07-24 (sak418-g capacity pressure thin)
# + 2026-07-24 (sak419 probe/cache/fit thin stubs) + 2026-07-24 (sak420 governor thin).
# action=delete paths must be ABSENT (ci_peel_delete_guard --post-delete).
# action=thin paths must REMAIN as broker-only stubs.
# Kept bridges omitted: research_bridge, egress_bridge, memory/sandbox/llm bridges.
DOMAIN_CANDIDATES: dict[str, tuple[PeelCandidate, ...]] = {
    "llm": (
        # Kept local provider probe path while peel default-on is suspended (docs/peel-runbook.md).
        PeelCandidate("packages/orchestrator/llm/providers", "thin"),
        PeelCandidate("packages/orchestrator/llm/common.py", "delete"),
        PeelCandidate("packages/orchestrator/llm/prompt_cache.py", "thin"),
        PeelCandidate("packages/orchestrator/llm/provider_telemetry.py", "thin"),
        # Kept while peel default-on is suspended — rate-limited context.budget.sampled.
        PeelCandidate("packages/orchestrator/llm/budget_sample_emit.py", "thin"),
        PeelCandidate("packages/orchestrator/llm/plan_stage.py", "delete"),
        PeelCandidate("packages/orchestrator/llm/llm_slice.py", "delete"),
        PeelCandidate("packages/orchestrator/llm/implementation_critique.py", "delete"),
        PeelCandidate("packages/orchestrator/llm/self_refinement_critique.py", "delete"),
        PeelCandidate("packages/orchestrator/llm/post_verify_role_critique.py", "delete"),
        PeelCandidate("packages/orchestrator/llm/agent_evaluator.py", "delete"),
        PeelCandidate("packages/orchestrator/llm/backlog_generator.py", "delete"),
        PeelCandidate("packages/orchestrator/routing", "delete"),
        PeelCandidate("packages/orchestrator/stage_provider_routing.py", "thin"),
        PeelCandidate("packages/agent_tools/llm_facade.py", "delete"),
        PeelCandidate("packages/agent_tools/facades/llm.py", "delete"),
    ),
    "sandbox": (
        PeelCandidate("packages/agent_tools/sandbox.py", "delete"),
        PeelCandidate("packages/agent_tools/filesystem_jail.py", "delete"),
        PeelCandidate("packages/agent_tools/fleet_sandbox.py", "delete"),
        PeelCandidate("packages/agent_tools/risk_caps.py", "delete"),
        PeelCandidate("packages/agent_tools/runtime.py", "delete"),
        PeelCandidate("packages/agent_tools/tools.py", "delete"),
        PeelCandidate("packages/agent_tools/agent_loop.py", "delete"),
    ),
    "tools": (
        PeelCandidate("packages/agent_tools/sandbox.py", "delete"),
        PeelCandidate("packages/agent_tools/filesystem_jail.py", "delete"),
        PeelCandidate("packages/agent_tools/fleet_sandbox.py", "delete"),
        PeelCandidate("packages/agent_tools/risk_caps.py", "delete"),
        PeelCandidate("packages/agent_tools/runtime.py", "delete"),
        PeelCandidate("packages/agent_tools/tools.py", "delete"),
        PeelCandidate("packages/agent_tools/agent_loop.py", "delete"),
    ),
    "memory": (
        PeelCandidate("packages/memory/index", "delete"),
        PeelCandidate("packages/memory/store", "delete"),
        PeelCandidate("packages/memory/fleet", "delete"),
        PeelCandidate("packages/memory/factory.py", "delete"),
        PeelCandidate("packages/memory/sync.py", "delete"),
        PeelCandidate("packages/memory/sync_cli.py", "delete"),
        PeelCandidate("packages/memory/cli.py", "delete"),
        PeelCandidate("packages/memory/remote_store.py", "delete"),
        PeelCandidate("scripts/faiss/build_memory_faiss_index.py", "delete"),
    ),
    "research": (
        # fetch.py stays on disk as broker-only stub (thin); research_bridge kept.
        PeelCandidate("packages/research/fetch.py", "thin"),
    ),
    "egress": (
        PeelCandidate("packages/executor/egress.py", "delete"),
        # fetch.py stays as broker-only httpx wrapper (thin); egress_bridge kept.
        PeelCandidate("packages/executor/fetch.py", "thin"),
    ),
    "compute": (
        # Thin public modules; legacy implementations in *_legacy.py (sak417-c / sak421-g).
        PeelCandidate("packages/compute/mesh_host_sync.py", "thin"),
        PeelCandidate("packages/compute/mesh_event_replay.py", "thin"),
        PeelCandidate("packages/compute/mesh_workspace_merge.py", "thin"),
        PeelCandidate("packages/compute/mesh_stage_runner.py", "thin"),
    ),
    "capacity": (
        # Thin public hw modules; legacy in *_legacy.py (sak418–sak420).
        PeelCandidate("packages/hw/pressure.py", "thin"),
        PeelCandidate("packages/hw/probe.py", "thin"),
        PeelCandidate("packages/hw/cache.py", "thin"),
        PeelCandidate("packages/hw/fit.py", "thin"),
        PeelCandidate("packages/hw/governor.py", "thin"),
    ),
}


def run_peel_script(
    script: str,
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPTS_DIR / script), *args]
    return subprocess.run(
        cmd,
        cwd=cwd or NIMBUSWARE_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def path_exists(root: Path, rel_path: str) -> bool:
    return (root / rel_path).exists()


def candidate_rows(root: Path, domain: str) -> list[tuple[PeelCandidate, bool]]:
    rows: list[tuple[PeelCandidate, bool]] = []
    for candidate in DOMAIN_CANDIDATES[domain]:
        rows.append((candidate, path_exists(root, candidate.rel_path)))
    return rows


def default_on_gate_doc_ok() -> bool:
    if not PEEL_RUNBOOK.is_file():
        return False
    return DEFAULT_ON_GATE_MARKER in PEEL_RUNBOOK.read_text(encoding="utf-8")
