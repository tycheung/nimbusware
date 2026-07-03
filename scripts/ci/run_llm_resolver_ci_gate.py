#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "packages"

ALLOWLIST = {
    PACKAGES / "orchestrator" / "ollama_chat.py",
    PACKAGES / "orchestrator" / "stage_provider_routing.py",
    PACKAGES / "orchestrator" / "llm_plan.py",
    PACKAGES / "orchestrator" / "llm" / "common.py",
    PACKAGES / "orchestrator" / "llm" / "providers" / "ollama_provider.py",
}

PATTERNS = (
    re.compile(r"from orchestrator\.ollama_chat import"),
    re.compile(r"from orchestrator import ollama_chat\b"),
    re.compile(r"import orchestrator\.ollama_chat\b"),
)


def main() -> int:
    violations: list[str] = []
    for path in PACKAGES.rglob("*.py"):
        if path in ALLOWLIST or "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PATTERNS:
            if pattern.search(text):
                violations.append(str(path.relative_to(ROOT)))
                break
    if violations:
        sys.stderr.write("Direct ollama_chat imports outside allowlist (fo1401):\n")
        for item in sorted(violations):
            sys.stderr.write(f"  - {item}\n")
        return 1
    print("LLM resolver import gate OK (fo1401)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
