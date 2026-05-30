"""Remove duplicate module docstrings from llm/*.py."""

from __future__ import annotations

from pathlib import Path

pkg = Path(__file__).resolve().parents[1] / "packages" / "hermes_orchestrator" / "llm"
for path in pkg.glob("*.py"):
    if path.name == "__init__.py":
        continue
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) >= 3 and lines[2].startswith('"""LLM-backed'):
        path.write_text("".join([lines[0], lines[1], *lines[4:]]), encoding="utf-8")
        print("fixed", path.name)
