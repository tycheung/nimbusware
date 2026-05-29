"""Scoped slice implementation (fo152 / PZ): real workspace mutations before diff budget."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hermes_orchestrator.micro_slice import SlicePlan


@dataclass(frozen=True)
class SliceImplementResult:
    mode: str
    exit_code: int
    log: str
    paths_touched: tuple[str, ...]


def slice_implement_mode() -> str:
    """``scoped`` (default): ruff; ``llm``: LLM file edits when ``HERMES_USE_LLM=1``; ``stub``: no-op."""
    raw = os.environ.get("HERMES_SLICE_IMPLEMENT", "scoped").strip().lower()
    if raw in ("stub", "0", "false", "no"):
        return "stub"
    if raw == "llm" or (
        raw in ("auto", "1", "true", "yes")
        and os.environ.get("HERMES_USE_LLM", "").lower() in ("1", "true", "yes")
    ):
        return "llm"
    return "scoped"


def _resolve_existing_files(workspace: Path, paths: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        candidate = workspace / p
        if candidate.is_file():
            out.append(candidate)
    return out


def _run_ruff_format(
    workspace: Path, files: list[Path], *, timeout_seconds: float
) -> tuple[int, str]:
    if not files:
        return 0, "ruff format skipped (no files)\n"
    proc = subprocess.run(
        ["ruff", "format", *[str(f) for f in files]],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _run_ruff_fix(workspace: Path, files: list[Path], *, timeout_seconds: float) -> tuple[int, str]:
    if not files:
        return 0, "ruff check --fix skipped (no files)\n"
    proc = subprocess.run(
        ["ruff", "check", "--fix", *[str(f) for f in files]],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def execute_slice_implement(
    workspace: Path,
    plan: SlicePlan,
    *,
    timeout_seconds: float = 120.0,
    llm_base_url: str | None = None,
    llm_model_id: str | None = None,
    llm_system_prompt: str | None = None,
) -> SliceImplementResult:
    """Apply bounded, scoped changes for one micro-slice (default: ruff format + --fix)."""
    mode = slice_implement_mode()
    if mode == "stub":
        return SliceImplementResult(
            mode="stub",
            exit_code=0,
            log="slice implement stub (HERMES_SLICE_IMPLEMENT=stub)\n",
            paths_touched=(),
        )

    if mode == "llm" and llm_base_url and llm_model_id:
        from hermes_orchestrator.llm_slice import execute_slice_implement_llm
        from hermes_orchestrator.slice_patch_apply import apply_slice_file_edits

        edits = execute_slice_implement_llm(
            plan=plan,
            workspace=workspace,
            base_url=llm_base_url,
            model_id=llm_model_id,
            timeout_seconds=timeout_seconds,
            system_prompt=llm_system_prompt,
        )
        if edits:
            touched, errors = apply_slice_file_edits(workspace, plan, edits)
            sections = [f"LLM applied {len(touched)} file(s)"]
            if errors:
                sections.append("errors: " + "; ".join(errors))
            files = [workspace / p for p in touched]
            if files:
                fmt_code, fmt_out = _run_ruff_format(
                    workspace,
                    files,
                    timeout_seconds=timeout_seconds,
                )
                sections.append(f"ruff format exit {fmt_code}")
                return SliceImplementResult(
                    mode="llm",
                    exit_code=fmt_code,
                    log="\n".join(sections) + "\n" + fmt_out[:2000],
                    paths_touched=tuple(touched),
                )
            return SliceImplementResult(
                mode="llm",
                exit_code=1 if errors else 0,
                log="; ".join(errors) or "no edits applied\n",
                paths_touched=(),
            )

    files = _resolve_existing_files(workspace, plan.target_paths)
    rel_paths = tuple(str(f.relative_to(workspace)).replace("\\", "/") for f in files)
    if not files:
        return SliceImplementResult(
            mode=mode,
            exit_code=0,
            log=f"no existing target files for slice {plan.slice_id}\n",
            paths_touched=(),
        )

    sections: list[str] = []
    fmt_code, fmt_out = _run_ruff_format(workspace, files, timeout_seconds=timeout_seconds)
    sections.append(f"=== ruff format (exit {fmt_code}) ===\n{fmt_out}")
    fix_code, fix_out = _run_ruff_fix(workspace, files, timeout_seconds=timeout_seconds)
    sections.append(f"=== ruff check --fix (exit {fix_code}) ===\n{fix_out}")
    worst = max(fmt_code, fix_code)
    return SliceImplementResult(
        mode="scoped",
        exit_code=worst,
        log="\n".join(sections),
        paths_touched=rel_paths,
    )
