"""Shared helpers for escalation policy loader composite contract tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from unit.composite_repo_fixtures import write_escalation_policy


def assert_positive_int_loader_rejects_non_int(
    tmp_path: Path,
    *,
    loader: Callable[[Path], int | None],
    yaml_key: str,
    prefix: str,
) -> None:
    non_int_cases: list[tuple[str, str]] = [
        ("str_two", '"2"'),
        ("float_two", "2.0"),
        ("explicit_null", "null"),
        ("list_value", "[2]"),
    ]
    for name, raw in non_int_cases:
        repo = tmp_path / f"{prefix}_nonint_{name}"
        repo.mkdir()
        write_escalation_policy(
            repo,
            f"version: 1\nverification:\n  {yaml_key}: {raw}\n",
        )
        actual = loader(repo)
        assert actual is None, (
            f"{prefix} {name}: value `{raw}` is not a Python int -> None expected, got {actual!r}"
        )


def assert_positive_int_loader_boundary(
    tmp_path: Path,
    *,
    loader: Callable[[Path], int | None],
    yaml_key: str,
    prefix: str,
) -> None:
    for name, value in (("zero", 0), ("negative_one", -1)):
        repo = tmp_path / f"{prefix}_reject_{name}"
        repo.mkdir()
        write_escalation_policy(
            repo,
            f"version: 1\nverification:\n  {yaml_key}: {value}\n",
        )
        assert loader(repo) is None, f"{prefix} reject({name}): {value} must return None"

    for name, value in (("one", 1), ("two", 2), ("large", 99999)):
        repo = tmp_path / f"{prefix}_accept_{name}"
        repo.mkdir()
        write_escalation_policy(
            repo,
            f"version: 1\nverification:\n  {yaml_key}: {value}\n",
        )
        assert loader(repo) == value, f"{prefix} accept({name}): expected {value}"
