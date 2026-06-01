"""Guards against gutted facade modules after unsafe auto-fixes."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

_MIN_LINES: dict[str, int] = {
    "packages/hermes_orchestrator/_pipeline/_helpers.py": 200,
    "packages/agent_core/models/events_foundation.py": 50,
    "packages/nimbusware_console/pages/config_tooling/_common.py": 5,
    "packages/nimbusware_console/pages/run_detail/_imports_display_b.py": 50,
}

_REQUIRED_SNIPPETS: dict[str, tuple[str, ...]] = {
    "packages/nimbusware_console/pages/config_tooling/_common.py": ("API_BASE",),
    "packages/hermes_orchestrator/_pipeline/_helpers.py": ("InMemoryEventStore",),
}


def _line_count(rel: str) -> int:
    path = _REPO / rel
    return len(path.read_text(encoding="utf-8").splitlines())


def test_critical_modules_meet_minimum_line_counts() -> None:
    short: list[str] = []
    for rel, minimum in _MIN_LINES.items():
        count = _line_count(rel)
        if count < minimum:
            short.append(f"{rel}: {count} lines (min {minimum})")
    assert not short, "Gutted or truncated modules detected:\n" + "\n".join(short)


def test_critical_modules_contain_required_symbols() -> None:
    missing: list[str] = []
    for rel, snippets in _REQUIRED_SNIPPETS.items():
        text = (_REPO / rel).read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                missing.append(f"{rel}: missing {snippet!r}")
    assert not missing, "Critical facade content missing:\n" + "\n".join(missing)


def test_run_detail_imports_display_a_init_is_non_empty() -> None:
    rel = "packages/nimbusware_console/pages/run_detail/_imports_display_a/__init__.py"
    text = (_REPO / rel).read_text(encoding="utf-8").strip()
    assert text, f"{rel} must not be empty"
