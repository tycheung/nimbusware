"""Phase 3 performance / N+1 static scanners (§14 #18 optional depth)."""

from __future__ import annotations

import re
from pathlib import Path

_N_PLUS_ONE_PATTERNS = (
    re.compile(
        r"for\s+\w+\s+in\s+.+:\s*\n(?:.*\n){0,8}.*"
        r"(?:\.execute\(|session\.query|\.scalars\(|fetchall\()",
        re.MULTILINE,
    ),
    re.compile(
        r"while\s+.+:\s*\n(?:.*\n){0,6}.*(?:\.execute\(|session\.query)",
        re.MULTILINE,
    ),
)


def run_ruff_perf(workspace: Path, *, timeout_seconds: float = 60.0) -> tuple[int, str]:
    """Ruff PERF rules (lightweight performance lint)."""
    import subprocess

    target = workspace / "packages"
    if not target.is_dir():
        return 0, "ruff perf skipped (no packages/)\n"
    proc = subprocess.run(
        ["ruff", "check", str(target), "--select", "PERF"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def scan_n_plus_one_heuristic(workspace: Path, *, max_findings: int = 20) -> tuple[int, str]:
    """Static heuristic for query-in-loop patterns (not a runtime profiler)."""
    root = workspace / "packages"
    if not root.is_dir():
        return 0, "n+1 heuristic skipped (no packages/)\n"
    hits: list[str] = []
    for path in root.rglob("*.py"):
        if "test" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for pat in _N_PLUS_ONE_PATTERNS:
            for m in pat.finditer(text):
                line = text[: m.start()].count("\n") + 1
                rel = path.relative_to(workspace)
                hits.append(f"{rel}:{line}")
                if len(hits) >= max_findings:
                    break
            if len(hits) >= max_findings:
                break
        if len(hits) >= max_findings:
            break
    if not hits:
        return 0, "n+1 heuristic: no suspicious query-in-loop patterns\n"
    body = "\n".join(hits[:max_findings])
    return 1, f"n+1 heuristic findings ({len(hits)}):\n{body}\n"
