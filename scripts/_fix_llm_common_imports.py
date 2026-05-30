"""Add common imports to llm stage modules."""

from __future__ import annotations

from pathlib import Path

pkg = Path(__file__).resolve().parents[1] / "packages" / "hermes_orchestrator" / "llm"
import_line = "from hermes_orchestrator.llm.common import *  # noqa: F403\n\n"
for path in pkg.glob("*.py"):
    if path.name in {"__init__.py", "common.py"}:
        continue
    text = path.read_text(encoding="utf-8")
    if import_line.strip() in text:
        continue
    marker = "from hermes_store.protocol import EventStore\n"
    if marker not in text:
        print("skip", path.name)
        continue
    text = text.replace(marker, marker + "\n" + import_line, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path.name)
