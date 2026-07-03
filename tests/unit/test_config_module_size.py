from __future__ import annotations

from pathlib import Path

_CONFIG_ROOT = Path(__file__).resolve().parents[2] / "packages" / "config"

_ALLOWLIST_OVER_450: frozenset[str] = frozenset()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_config_module_over_450_lines() -> None:
    over_limit: list[str] = []
    for path in sorted(_CONFIG_ROOT.rglob("*.py")):
        rel = path.relative_to(_CONFIG_ROOT).as_posix()
        lines = _line_count(path)
        if lines > 450 and rel not in _ALLOWLIST_OVER_450:
            over_limit.append(f"{rel}: {lines} lines")
    assert not over_limit, "New config modules exceed 450 lines:\n" + "\n".join(over_limit)


def test_config_module_size_allowlist_is_current() -> None:
    still_large = {
        path.relative_to(_CONFIG_ROOT).as_posix()
        for path in _CONFIG_ROOT.rglob("*.py")
        if _line_count(path) > 450
    }
    assert still_large == set(_ALLOWLIST_OVER_450), (
        f"Update _ALLOWLIST_OVER_450: extra={still_large - set(_ALLOWLIST_OVER_450)!r} "
        f"missing={set(_ALLOWLIST_OVER_450) - still_large!r}"
    )
