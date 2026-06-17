from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

_GUARDS: tuple[tuple[str, int, frozenset[str]], ...] = (
    (
        "packages/nimbusware_orchestrator",
        450,
        frozenset(
            {
                "micro_slice_executor.py",
                "slice_cycle_integration.py",
                "_pipeline/_helpers.py",
                "_pipeline/create_run.py",
                "_pipeline/protocol_hosts.py",
                "put_e2e_runner.py",
            }
        ),
    ),
    ("packages/nimbusware_api", 450, frozenset({"routes/chat.py"})),
    ("packages/nimbusware_memory", 450, frozenset()),
)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_package_module_size_limits() -> None:
    over_limit: list[str] = []
    for rel_root, limit, allowlist in _GUARDS:
        root = _REPO / rel_root
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            lines = _line_count(path)
            if lines > limit and rel not in allowlist:
                over_limit.append(f"{rel_root}/{rel}: {lines} lines (limit {limit})")
    assert not over_limit, "New modules exceed package size limits:\n" + "\n".join(over_limit)


def test_package_module_size_allowlists_are_current() -> None:
    stale: list[str] = []
    for rel_root, limit, allowlist in _GUARDS:
        root = _REPO / rel_root
        still_large = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*.py")
            if _line_count(path) > limit
        }
        if still_large != set(allowlist):
            stale.append(
                f"{rel_root}: extra={still_large - set(allowlist)!r} "
                f"missing={set(allowlist) - still_large!r}"
            )
    assert not stale, "Update package size allowlists:\n" + "\n".join(stale)
