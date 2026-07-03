from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PACKAGES_ROOT = _REPO / "packages"

# Cohesion-based cap: one feature may live in one module up to this size.
MODULE_LINE_LIMIT = 1000

# Modules intentionally above the cap until a follow-on split lands.
_ALLOWLIST_OVER_LIMIT: frozenset[str] = frozenset()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _rel_package_path(path: Path) -> str:
    return path.relative_to(_PACKAGES_ROOT).as_posix()


def test_no_package_module_over_line_limit() -> None:
    over_limit: list[str] = []
    for path in sorted(_PACKAGES_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = _rel_package_path(path)
        lines = _line_count(path)
        if lines > MODULE_LINE_LIMIT and rel not in _ALLOWLIST_OVER_LIMIT:
            over_limit.append(f"{rel}: {lines} lines (limit {MODULE_LINE_LIMIT})")
    assert not over_limit, f"New modules exceed {MODULE_LINE_LIMIT}-line cap:\n" + "\n".join(
        over_limit
    )


def test_package_module_size_allowlist_is_current() -> None:
    still_large = {
        _rel_package_path(path)
        for path in _PACKAGES_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and _line_count(path) > MODULE_LINE_LIMIT
    }
    assert still_large == set(_ALLOWLIST_OVER_LIMIT), (
        f"Update _ALLOWLIST_OVER_LIMIT: extra={still_large - set(_ALLOWLIST_OVER_LIMIT)!r} "
        f"missing={set(_ALLOWLIST_OVER_LIMIT) - still_large!r}"
    )
