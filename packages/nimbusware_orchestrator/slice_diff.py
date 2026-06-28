from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from nimbusware_env.env_flags import env_str
from nimbusware_env.settings_resolve import resolve_int
from nimbusware_orchestrator.micro_slice import DiffBudgetResult, SlicePlan, validate_diff_budget
from nimbusware_orchestrator.workflow_micro_slice import MicroSliceWorkflowBlock


@dataclass(frozen=True)
class SliceDiffStats:
    changed_files: tuple[str, ...]
    loc_added: int
    loc_removed: int
    unified_diff: str
    source: str = "git"


def slice_replan_max_attempts() -> int:
    return max(0, min(10, resolve_int("NIMBUSWARE_SLICE_REPLAN_MAX", default=3)))


def _normalise_path(path: str) -> str:
    return path.replace("\\", "/")


def _git_numstat(workspace: Path, paths: tuple[str, ...]) -> SliceDiffStats | None:
    if not paths:
        return SliceDiffStats((), 0, 0, "", source="empty")
    if not (workspace / ".git").exists():
        return None
    rel_paths = [_normalise_path(p) for p in paths]
    try:
        proc = subprocess.run(
            ["git", "diff", "--numstat", "HEAD", "--", *rel_paths],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 and not proc.stdout.strip():
        proc = subprocess.run(
            ["git", "diff", "--numstat", "--", *rel_paths],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    changed: list[str] = []
    added = 0
    removed = 0
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        a, d, fname = parts[0], parts[1], parts[2]
        if a == "-" and d == "-":
            continue
        changed.append(_normalise_path(fname))
        try:
            added += int(a)
            removed += int(d)
        except ValueError:
            continue
    if not changed:
        changed = list(rel_paths)
    diff_proc = subprocess.run(
        ["git", "diff", "HEAD", "--", *rel_paths],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    unified = diff_proc.stdout if diff_proc.returncode == 0 else ""
    return SliceDiffStats(
        tuple(dict.fromkeys(changed)),
        added,
        removed,
        unified,
        source="git",
    )


def _plan_scope_loc_estimate(workspace: Path, paths: tuple[str, ...]) -> tuple[int, int]:
    """Fallback LOC when git has no diff (stub implement / clean tree)."""
    stub_per_file = env_str("NIMBUSWARE_SLICE_STUB_LOC_PER_FILE")
    if stub_per_file:
        try:
            per = max(0, int(stub_per_file))
            return per * len(paths), 0
        except ValueError:
            pass
    total = 0
    for p in paths:
        fp = workspace / p
        if fp.is_file():
            try:
                total += sum(1 for _ in fp.open(encoding="utf-8", errors="replace"))
            except OSError:
                total += 1
        else:
            total += 1
    return total, 0


def collect_slice_diff_stats(
    workspace: Path,
    plan: SlicePlan,
) -> SliceDiffStats:
    """Measure diff for slice paths; git when available, else plan-scope estimate."""
    paths = plan.target_paths
    git_stats = _git_numstat(workspace, paths)
    if git_stats is not None and (git_stats.loc_added + git_stats.loc_removed) > 0:
        return git_stats
    if git_stats is not None and git_stats.changed_files:
        added, removed = _plan_scope_loc_estimate(workspace, paths)
        if added + removed > 0:
            return SliceDiffStats(
                git_stats.changed_files,
                added,
                removed,
                git_stats.unified_diff,
                source="plan_estimate",
            )
        return git_stats
    added, removed = _plan_scope_loc_estimate(workspace, paths)
    return SliceDiffStats(
        tuple(_normalise_path(p) for p in paths),
        added,
        removed,
        "",
        source="plan_estimate",
    )


def check_slice_diff_budget(
    stats: SliceDiffStats,
    config: MicroSliceWorkflowBlock,
) -> DiffBudgetResult:
    files = list(stats.changed_files) if stats.changed_files else []
    return validate_diff_budget(
        changed_files=files,
        loc_added=stats.loc_added,
        loc_removed=stats.loc_removed,
        config=config,
    )


def subdivide_slice_plan(
    plan: SlicePlan,
    *,
    budget: DiffBudgetResult,
    config: MicroSliceWorkflowBlock,
    stats: SliceDiffStats,
    replan_attempt: int,
) -> SlicePlan | None:
    """Narrow ``target_paths`` when over budget; None when cannot subdivide further."""
    paths = list(stats.changed_files) if stats.changed_files else list(plan.target_paths)
    if not paths:
        return None

    new_paths: list[str]
    if len(paths) > config.max_files:
        new_paths = paths[: config.max_files]
    elif (stats.loc_added + stats.loc_removed) > config.max_loc:
        if len(paths) <= 1:
            return None
        keep = max(1, len(paths) // 2)
        new_paths = paths[:keep]
    else:
        return None

    if tuple(new_paths) == plan.target_paths:
        return None

    return SlicePlan(
        slice_id=f"{plan.slice_id}-r{replan_attempt}",
        rationale=(f"{plan.rationale} [replan {replan_attempt}: {budget.message}]").strip(),
        target_paths=tuple(new_paths),
        acceptance_criteria=plan.acceptance_criteria,
        surface_id=plan.surface_id,
        stack_id=plan.stack_id,
    )
