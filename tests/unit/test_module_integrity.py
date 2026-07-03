from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

_MIN_LINES: dict[str, int] = {
    "packages/orchestrator/_pipeline/_helpers_bundle_runtime.py": 130,
    "packages/agent_core/models/events_foundation.py": 50,
    "packages/maker_web/static/js/app-shell.js": 20,
}

_REQUIRED_SNIPPETS: dict[str, tuple[str, ...]] = {
    "packages/orchestrator/_pipeline/_helpers_bundle_runtime.py": (
        "InMemoryEventStore",
    ),
    "packages/maker_web/static/js/api-client.js": ("apiJson",),
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
