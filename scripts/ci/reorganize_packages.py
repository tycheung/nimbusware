#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

TEXT_SUFFIXES = {
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".json",
    ".ps1",
    ".sh",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".html",
}

# orchestrator root modules that stay at package root (entrypoints + cross-cutting)
ORCH_KEEP_ROOT = frozenset(
    {
        "__init__.py",
        "pipeline.py",
        "runtime_bootstrap.py",
        "run_worker.py",
        "run_dispatch.py",
        "ingress.py",
        "ports.py",
        "merge.py",
        "registry.py",
        "registry_db.py",
        "anti_deadlock.py",
        "completion_evaluator.py",
        "preflight.py",
        "preflight_cli.py",
        "preflight_histogram.py",
        "telemetry_cli.py",
        "routing_suggestions_cli.py",
        "fleet_ollama_sli_cli.py",
        "replay_cli.py",
        "parallel_writers.py",
        "role_execute.py",
        "role_telemetry.py",
        "variant_arena.py",
        "verify_fanout.py",
        "verifiers.py",
        "frontend_writer_stage.py",
        "loc_accord_stage.py",
        "test_writer_stage.py",
        "maintenance_architecture.py",
        "maintenance_refactor.py",
        "refactor_proposal.py",
        "refactor_stage.py",
        "interjection_queue.py",
        "interjection_slo.py",
        "surface_interjection_routing.py",
        "launch_eval_catalog.py",
        "launch_evaluator.py",
        "launch_flow_resolver.py",
        "launch_test_llm.py",
        "launch_test_stage.py",
        "context_artifacts.py",
        "context_compaction.py",
        "memory_run_insert.py",
        "patch_context.py",
        "diagnose_learn.py",
        "improvement_council.py",
        "improvement_council_backlog.py",
        "improvement_scope.py",
        "resolution_council.py",
        "browser_controller.py",
        "human_fidelity.py",
        "playwright_probe.py",
        "playwright_sync.py",
        "ui_flow_dsl.py",
        "ui_flow_synthesis.py",
        "interaction_surface_critic.py",
        "interaction_surface_map.py",
        "feature_gap_matrix.py",
        "git_outputs.py",
        "js_framework_detect.py",
        "network_egress_normalize.py",
        "outbound_http.py",
        "policy_snapshot_diff.py",
        "sql_profiler.py",
        "traceback_router.py",
        "learnings_catalog.py",
        "learnings_stitch_suggest.py",
        "self_refinement_policy.py",
        "config_blast_radius.py",
        "workspace_ci_runner.py",
        "workspace_layout.py",
        "enforcement_pipeline.py",
        "gate_override_execution.py",
        "escalation_execution.py",
        "escalation_policy_breadth.py",
        "escalation_threshold.py",
        "participant_output_packet.py",
        "role_claims_mesh.py",
        "provider_registry.py",
        "stage_provider_routing.py",
    }
)

# Shims deleted outright (importers rewritten separately)
ORCH_DELETE_SHIMS = frozenset(
    {
        "read_models.py",
        "llm_plan.py",
        "stage_graph.py",
        "prompt_tiers.py",
    }
)

# Prefix rules: longest first
ORCH_PREFIX_RULES: tuple[tuple[str, str], ...] = (
    ("integration_adapter_", "integrator"),
    ("enterprise_audit_", "replay"),
    ("dev_env_", "dev_env"),
    ("micro_slice_", "slice"),
    ("put_e2e_", "factory"),
    ("host_collab_", "collab"),
    ("scan_critique_", "critique"),
    ("scan_stub_", "critique"),
    ("workflow_", "workflow"),
    ("model_binding_", "routing"),
    ("campaign_", "campaign"),
    ("fleet_", "fleet"),
    ("slice_", "slice"),
    ("persona_", "persona"),
    ("integrator_", "integrator"),
    ("factory_", "factory"),
    ("scraper_", "scraper"),
    ("routing_", "routing"),
    ("binding_", "routing"),
    ("collab_", "collab"),
    ("replay_", "replay"),
    ("backlog_", "campaign"),
    ("code_intel_", "repo_intel"),
    ("repo_", "repo_intel"),
    ("mesh_", "collab"),
    ("ollama_", "routing"),
    ("put_", "factory"),
    ("critic_", "critique"),
    ("critique_", "critique"),
    ("stack_", "stack"),
)

ORCH_EXACT_SUBDIR: dict[str, str] = {
    "campaign.py": "campaign/campaign.py",
    "micro_slice.py": "slice/micro_slice.py",
    "audit_export.py": "replay/audit_export.py",
    "replay_from.py": "replay/replay_from.py",
    "fast_slice_critique.py": "slice/fast_slice_critique.py",
    "llm_slice.py": "llm/llm_slice.py",
    "default_workflow_profile.py": "workflow/profile.py",
    "security_scan.py": "critique/security_scan.py",
    "security_semgrep.py": "critique/security_semgrep.py",
    "performance_scan.py": "critique/performance_scan.py",
    "network_resilience_scan.py": "critique/network_resilience_scan.py",
    "simplification_gate.py": "critique/simplification_gate.py",
    "simplification_metrics.py": "critique/simplification_metrics.py",
    "simplification_rubric_critique.py": "critique/simplification_rubric_critique.py",
    "unanimous_gate.py": "critique/unanimous_gate.py",
    "verifier_escalation.py": "critique/verifier_escalation.py",
    "code_graph.py": "repo_intel/code_graph.py",
    "cohesion_graph.py": "repo_intel/cohesion_graph.py",
    "orphan_index.py": "repo_intel/orphan_index.py",
    "similarity_index.py": "repo_intel/similarity_index.py",
    "ism_diff.py": "repo_intel/ism_diff.py",
    "autopilot_profiles.py": "profiles/autopilot_profiles.py",
    "enforcement_profiles.py": "profiles/enforcement_profiles.py",
    "user_autopilot_profiles.py": "profiles/user_autopilot_profiles.py",
    "user_enforcement_profiles.py": "profiles/user_enforcement_profiles.py",
    "user_operator_profiles.py": "profiles/user_operator_profiles.py",
}

MEMORY_MOVES: dict[str, str] = {
    "store_memory.py": "store/memory.py",
    "store_postgres.py": "store/postgres.py",
    "store_protocol.py": "store/protocol.py",
    "fleet_sync.py": "fleet/sync.py",
    "fleet_index.py": "fleet/index.py",
    "indexer.py": "index/indexer.py",
    "embeddings.py": "index/embeddings.py",
    "faiss_store.py": "index/faiss_store.py",
    "faiss_index.py": "index/faiss_index.py",
    "chunking.py": "index/chunking.py",
    "manifest.py": "index/manifest.py",
    "search.py": "index/search.py",
    "models.py": "index/models.py",
    "contribution.py": "index/contribution.py",
    "audit.py": "index/audit.py",
    "user_scope.py": "index/user_scope.py",
    "repo_scope.py": "index/repo_scope.py",
}

MEMORY_DELETE_SHIMS = frozenset({"store.py"})

MAKER_PREFIX_RULES: tuple[tuple[str, str], ...] = (
    ("chat_store_", "chat"),
    ("chat_library_", "chat"),
    ("deploy_", "deploy"),
    ("collab_", "collab"),
    ("intent_", "intent"),
    ("readiness_", "readiness"),
    ("workspace_", "workspace"),
)

MAKER_EXACT: dict[str, str] = {
    "chat_service.py": "chat/service.py",
    "chat_acl.py": "chat/acl.py",
    "scope_discovery.py": "intent/scope_discovery.py",
    "intent.py": "intent/requirements.py",
    "readiness.py": "readiness/platform.py",
}

MAKER_KEEP_ROOT = frozenset(
    {
        "__init__.py",
        "cli.py",
        "session.py",
        "onboarding.py",
        "push_subscriptions.py",
        "slice_engine.py",
        "quick_mode.py",
        "git_outputs.py",
        "tenant_collab_defaults.py",
        "collab_policy_enforcement.py",
    }
)

# Import string replacements (longest keys first when applied)
IMPORT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (
        "from orchestrator.read_models import build_run_summary",
        "from projections.run_summary import build_run_summary",
    ),
    (
        "from orchestrator.read_models import run_has_started",
        "from projections.run_summary import run_has_started",
    ),
    (
        "from orchestrator.read_models import RUN_LIST_FILTER_STATUSES",
        "from projections.run_summary import RUN_LIST_FILTER_STATUSES",
    ),
    (
        "from orchestrator.read_models import persona_assignment_from_run_created_metadata",
        "from agent_core.timeline_metadata import persona_assignment_from_run_created_metadata",
    ),
    ("from orchestrator.llm_plan import", "from orchestrator.llm import"),
    ("from orchestrator.stage_graph import", "from agent_core.stage_graph import"),
    ("from orchestrator.prompt_tiers import", "from agent_core.prompt_tiers import"),
    (
        "from orchestrator.default_workflow_profile import default_workflow_profile",
        "from orchestrator.workflow.profile import default_workflow_profile",
    ),
    (
        "from memory.store import InMemoryMemoryChunkStore",
        "from memory.store.memory import InMemoryMemoryChunkStore",
    ),
    (
        "from memory.store import PostgresMemoryChunkStore",
        "from memory.store.postgres import PostgresMemoryChunkStore",
    ),
    (
        "from memory.store import MemoryChunkStore",
        "from memory.store.protocol import MemoryChunkStore",
    ),
    (
        "from memory.store import IndexGenerationRow",
        "from memory.store.protocol import IndexGenerationRow",
    ),
    ("from console.operator_chat import", "from console.operator_chat_core import"),
)


def _orch_target(filename: str) -> str | None:
    if filename in ORCH_KEEP_ROOT or filename in ORCH_DELETE_SHIMS:
        return None
    if filename in ORCH_EXACT_SUBDIR:
        return ORCH_EXACT_SUBDIR[filename]
    stem = filename[:-3]
    for prefix, subdir in ORCH_PREFIX_RULES:
        bare = prefix.rstrip("_")
        if stem == bare:
            return f"{subdir}/{stem}.py"
        if prefix.endswith("_") and stem.startswith(prefix):
            rest = stem[len(prefix) :]
            if rest:
                return f"{subdir}/{rest}.py"
    return None


def _maker_target(filename: str) -> str | None:
    if filename in MAKER_KEEP_ROOT:
        return None
    if filename in MAKER_EXACT:
        return MAKER_EXACT[filename]
    stem = filename[:-3]
    for prefix, subdir in MAKER_PREFIX_RULES:
        bare = prefix.rstrip("_")
        if stem == bare:
            return f"{subdir}/{stem}.py"
        if prefix.endswith("_") and stem.startswith(prefix):
            rest = stem[len(prefix) :]
            if rest:
                return f"{subdir}/{rest}.py"
    return None


def git_mv(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=ROOT, check=True)
    except subprocess.CalledProcessError:
        shutil.move(str(src), str(dst))
        subprocess.run(["git", "add", "-A", str(dst)], cwd=ROOT, check=True)


def collect_orchestrator_moves() -> dict[str, str]:
    orch = ROOT / "packages" / "orchestrator"
    moves: dict[str, str] = {}
    for path in sorted(orch.glob("*.py")):
        target = _orch_target(path.name)
        if target:
            moves[f"orchestrator/{path.name}"] = f"orchestrator/{target}"
    return moves


def collect_memory_moves() -> dict[str, str]:
    return {f"memory/{k}": f"memory/{v}" for k, v in MEMORY_MOVES.items()}


def collect_maker_moves() -> dict[str, str]:
    maker = ROOT / "packages" / "maker"
    moves: dict[str, str] = {}
    for path in sorted(maker.glob("*.py")):
        target = _maker_target(path.name)
        if target:
            moves[f"maker/{path.name}"] = f"maker/{target}"
    return moves


def module_path(rel: str) -> str:
    return rel.replace("/", ".").removesuffix(".py")


def build_module_replacements(moves: dict[str, str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for old_rel, new_rel in moves.items():
        old_mod = module_path(old_rel)
        new_mod = module_path(new_rel)
        pairs.append((old_mod, new_mod))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def apply_module_replacements(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def rewrite_repo(pairs: list[tuple[str, str]], extra: tuple[tuple[str, str], ...]) -> int:
    updated = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(p in SKIP_DIR_NAMES for p in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new = apply_module_replacements(original, pairs)
        for old, new_s in extra:
            new = new.replace(old, new_s)
        if new != original:
            path.write_text(new, encoding="utf-8")
            updated += 1
    return updated


def execute_moves(moves: dict[str, str]) -> None:
    for old_rel, new_rel in sorted(moves.items()):
        src = ROOT / "packages" / old_rel
        dst = ROOT / "packages" / new_rel
        git_mv(src, dst)


def delete_shims(paths: list[Path]) -> None:
    for path in paths:
        if path.is_file():
            path.unlink()
            subprocess.run(["git", "add", "-A", str(path)], cwd=ROOT, check=True)


def remove_barrel_packages() -> None:
    """Remove orchestrator slice/critique barrels that only re-export moved modules."""
    for rel in ("orchestrator/slice/__init__.py", "orchestrator/critique/__init__.py"):
        path = ROOT / "packages" / rel
        if path.is_file():
            path.unlink()
            subprocess.run(["git", "add", "-A", str(path)], cwd=ROOT, check=True)


def ensure_init_py(moves: dict[str, str]) -> None:
    subdirs: set[Path] = set()
    for new_rel in moves.values():
        sub = ROOT / "packages" / Path(new_rel).parent
        subdirs.add(sub)
    for sub in subdirs:
        init = sub / "__init__.py"
        if not init.exists():
            init.write_text('"""Domain subpackage."""\n', encoding="utf-8")
            subprocess.run(["git", "add", str(init)], cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    all_moves: dict[str, str] = {}
    all_moves.update(collect_orchestrator_moves())
    all_moves.update(collect_memory_moves())
    all_moves.update(collect_maker_moves())

    if args.dry_run:
        for old, new in sorted(all_moves.items()):
            print(f"{old} -> {new}")
        print(f"total moves: {len(all_moves)}")
        return 0

    execute_moves(all_moves)
    ensure_init_py(all_moves)

    pairs = build_module_replacements(all_moves)
    count = rewrite_repo(pairs, IMPORT_REPLACEMENTS)

    shim_paths = [ROOT / "packages" / "orchestrator" / name for name in ORCH_DELETE_SHIMS] + [
        ROOT / "packages" / "memory" / name for name in MEMORY_DELETE_SHIMS
    ]
    shim_paths.append(ROOT / "packages" / "console" / "operator_chat.py")
    delete_shims(shim_paths)
    remove_barrel_packages()

    mem_init = ROOT / "packages" / "memory" / "__init__.py"
    if mem_init.is_file():
        text = mem_init.read_text(encoding="utf-8")
        text = text.replace("from memory.store import", "from memory.store.protocol import")
        text = text.replace(
            "from memory.store.memory import",
            "from memory.store.memory import",
        )
        mem_init.write_text(text, encoding="utf-8")

    print(f"moved {len(all_moves)} modules, updated {count} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
