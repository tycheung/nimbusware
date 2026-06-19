from __future__ import annotations

from pathlib import Path

_MAKER_ROOT = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_maker"

_ALLOWLIST_OVER_400: frozenset[str] = frozenset({"intent_classifier.py"})


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_maker_module_over_400_lines() -> None:
    over_limit: list[str] = []
    for path in sorted(_MAKER_ROOT.rglob("*.py")):
        rel = path.relative_to(_MAKER_ROOT).as_posix()
        lines = _line_count(path)
        if lines > 400 and rel not in _ALLOWLIST_OVER_400:
            over_limit.append(f"{rel}: {lines} lines")
    assert not over_limit, "New maker modules exceed 400 lines:\n" + "\n".join(over_limit)


def test_maker_module_size_allowlist_is_current() -> None:
    still_large = {
        path.relative_to(_MAKER_ROOT).as_posix()
        for path in _MAKER_ROOT.rglob("*.py")
        if _line_count(path) > 400
    }
    assert still_large == set(_ALLOWLIST_OVER_400), (
        f"Update _ALLOWLIST_OVER_400: extra={still_large - set(_ALLOWLIST_OVER_400)!r} "
        f"missing={set(_ALLOWLIST_OVER_400) - still_large!r}"
    )
