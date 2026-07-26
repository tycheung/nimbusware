"""Shell/memory tool surface after sak412 tools.py thin delete."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_core.context_budget import (
    strip_ansi,
    truncate_for_active_read,
    truncate_shell_output,
)
from agent_tools.allowlist import validate_shell_invocation
from env.env_flags import nimbusware_read_max_chars


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    llm_output: str
    audit_output: str

    @property
    def output(self) -> str:
        return self.llm_output


def _result(tool: str, ok: bool, llm: str, *, audit: str | None = None) -> ToolResult:
    return ToolResult(
        tool=tool,
        ok=ok,
        llm_output=llm,
        audit_output=audit if audit is not None else llm,
    )


def shell_from_string(command: str) -> tuple[str, list[str]]:
    parts = command.strip().split()
    if not parts:
        raise ValueError("empty shell command")
    return parts[0], parts[1:]


def _tool_result_from_broker_shell(broker_result: dict[str, Any]) -> ToolResult | None:
    exit_code = broker_result.get("exit_code", broker_result.get("returncode"))
    if exit_code is None:
        return None
    stdout = (
        broker_result.get("stdout")
        or broker_result.get("combined_output")
        or broker_result.get("output")
        or ""
    )
    stderr = broker_result.get("stderr") or ""
    combined = stdout
    if stderr:
        combined = f"{stdout}\n{stderr}".strip() if stdout else stderr
    ok = int(exit_code) == 0
    raw = combined or f"exit {exit_code}"
    audit = truncate_shell_output(raw) or f"exit {exit_code}"
    llm = truncate_shell_output(strip_ansi(raw)) or f"exit {exit_code}"
    return _result("shell", ok, llm, audit=audit)


def _format_broker_memory_hits(broker_result: dict[str, Any], *, max_chars: int) -> str:
    hits = broker_result.get("hits") or broker_result.get("results") or []
    if not isinstance(hits, list):
        return truncate_for_active_read(str(broker_result), max_chars=max_chars)
    parts: list[str] = []
    for i, hit in enumerate(hits, start=1):
        if isinstance(hit, dict):
            excerpt = hit.get("excerpt") or hit.get("text") or hit.get("body") or str(hit)
            cid = hit.get("chunk_id") or hit.get("id") or "?"
            score = hit.get("score")
            if score is not None:
                block = f"[{i}] chunk={cid} score={score}\n{excerpt}"
            else:
                block = f"[{i}] chunk={cid}\n{excerpt}"
        else:
            block = f"[{i}] {hit}"
        parts.append(block)
    body = "\n\n".join(parts) if parts else "no hits"
    return truncate_for_active_read(body, max_chars=max_chars)


def tool_run_shell(
    workspace: Path,
    command: str,
    args: list[str] | None = None,
    *,
    timeout_seconds: float = 120.0,
) -> ToolResult:
    try:
        if args is None and " " in command.strip():
            cmd, cmd_args = shell_from_string(command)
        else:
            cmd, cmd_args = validate_shell_invocation(command, list(args or []))
        from agent_tools.broker_route import raise_sandbox_peel_miss, raise_tools_peel_miss
        from agent_tools.sandbox_bridge import try_broker_sandbox_exec

        broker_result = try_broker_sandbox_exec([cmd, *cmd_args], cwd=str(workspace))
        if isinstance(broker_result, dict):
            mapped = _tool_result_from_broker_shell(broker_result)
            if mapped is not None:
                return mapped
        raise_sandbox_peel_miss("shell")  # sak494-d / sak496-d
        if broker_result is None:
            from broker_client.stage_bind.tools import try_broker_shell_exec

            broker_result = try_broker_shell_exec([cmd, *cmd_args], cwd=str(workspace))
        if isinstance(broker_result, dict):
            mapped = _tool_result_from_broker_shell(broker_result)
            if mapped is not None:
                return mapped
        raise_tools_peel_miss("shell")  # sak495-i / sak496-d
        from agent_tools.sandbox_bridge import run_subprocess_in_sandbox

        proc = run_subprocess_in_sandbox(
            workspace,
            [cmd, *cmd_args],
            timeout_seconds=timeout_seconds,
        )
        out = proc.combined_output
        ok = proc.returncode == 0
        tag = f"[{proc.backend}] " if proc.backend != "none" else ""
        raw = tag + out
        audit = truncate_shell_output(raw) or f"exit {proc.returncode}"
        llm = truncate_shell_output(strip_ansi(raw)) or f"exit {proc.returncode}"
        return _result("shell", ok, llm, audit=audit)
    except RuntimeError as exc:
        if str(exc).startswith("broker_miss:"):
            raise
        return _result("shell", False, str(exc))
    except (OSError, TimeoutError, ValueError) as exc:
        return _result("shell", False, str(exc))


def tool_memory_search(
    query: str,
    *,
    limit: int | None = None,
    memory_store: object | None = None,
    repo_root: Path | None = None,
    max_chars: int | None = None,
) -> ToolResult:
    from agent_tools.memory_bridge import try_broker_memory_search

    cap = max_chars if max_chars is not None else nimbusware_read_max_chars()
    q = query.strip()
    if not q:
        return _result("memory_search", False, "empty query")

    broker_result = try_broker_memory_search(q, limit=limit)
    if isinstance(broker_result, dict):
        body = _format_broker_memory_hits(broker_result, max_chars=cap)
        hits_raw = broker_result.get("hits") or broker_result.get("results") or []
        n_hits = len(hits_raw) if isinstance(hits_raw, list) else 0
        return _result("memory_search", True, body, audit=f"broker hits={n_hits}")

    from broker_client.flags import broker_memory_enabled

    if broker_memory_enabled():  # sak494-d: no local search when MEMORY=1|2
        raise RuntimeError(
            "broker_miss: memory_search: unavailable under NIMBUSWARE_BROKER_MEMORY=1|2"
        )

    if memory_store is not None:
        try:
            from memory.peel_index.search import format_memory_excerpt, search_memory
            from memory.peel_store.protocol import MemoryChunkStore
        except Exception:
            return _result("memory_search", False, "memory peel unavailable")
        if isinstance(MemoryChunkStore, type) and isinstance(memory_store, MemoryChunkStore):
            k = limit if limit is not None else 5
            hits = search_memory(
                memory_store,
                q,
                repo_root=repo_root or Path.cwd(),
                k=k,
            )
            body = format_memory_excerpt(hits, max_chars=cap)
            if body:
                return _result(
                    "memory_search",
                    True,
                    body,
                    audit=f"local hits={len(hits)}",
                )
            return _result("memory_search", True, "no hits", audit="local hits=0")
        return _result("memory_search", False, "memory search unavailable")

    return _result("memory_search", False, "memory search unavailable")
