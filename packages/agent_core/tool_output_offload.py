from __future__ import annotations

from pathlib import Path

from agent_core.context_budget import truncate_for_llm_history


def _offload_root(workspace: Path) -> Path:
    return workspace / ".cache" / "nimbusware" / "tool-output"


def offload_path(workspace: Path, run_id: str, step: int) -> Path:
    safe_run = run_id.replace("/", "_").replace("\\", "_").strip() or "run"
    return _offload_root(workspace) / safe_run / f"{step:04d}.txt"


def prepare_tool_output_for_llm(
    content: str,
    *,
    workspace: Path,
    run_id: str,
    step: int,
    preview_chars: int | None = None,
) -> tuple[str, Path | None]:
    """Write oversized tool output to disk; return LLM-facing preview and optional path."""
    threshold = _tool_offload_chars()
    if len(content) <= threshold:
        cap = preview_chars if preview_chars is not None else _default_preview_chars()
        return truncate_for_llm_history(content, max_chars=cap), None

    path = offload_path(workspace, run_id, step)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    cap = preview_chars if preview_chars is not None else _default_preview_chars()
    preview = truncate_for_llm_history(content, max_chars=cap)
    rel = path.relative_to(workspace).as_posix()
    llm_facing = (
        f"[offloaded {len(content)} chars to {rel}; preview below]\n{preview}"
    )
    return llm_facing, path


def _tool_offload_chars() -> int:
    from env.env_flags import nimbusware_tool_offload_chars

    return nimbusware_tool_offload_chars()


def _default_preview_chars() -> int:
    from env.env_flags import nimbusware_llm_history_max_chars

    return nimbusware_llm_history_max_chars()
