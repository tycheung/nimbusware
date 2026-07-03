from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from unit.composite_repo_fixtures import write_escalation_policy

LoaderFn = Callable[[Path], Any]

KEY_AUTO = "auto_escalate_after_cumulative_findings"
KEY_NOTICE = "notice_escalate_at_cumulative_findings"
KEY_STAGE = "escalate_after_cumulative_stage_failures"
KEY_GATE = "escalate_after_cumulative_gate_failures"


def assert_policy_absent_returns_none(loader: LoaderFn, tmp_path: Path, prefix: str) -> None:
    repo = tmp_path / f"{prefix}_absent"
    repo.mkdir()
    assert loader(repo) is None, f"{prefix}: policy.yaml absent -> None"


def assert_verification_non_dict_returns_none(
    tmp_path: Path,
    *,
    loader: LoaderFn,
    yaml_key: str,
    prefix: str,
    body: str,
    label: str,
) -> None:
    repo = tmp_path / f"{prefix}_nondict_{label}"
    repo.mkdir()
    write_escalation_policy(repo, f"version: 1\n{body}")
    assert loader(repo) is None, f"{prefix} nondict {label}: expected None"


def assert_verification_non_dict_matrix(
    tmp_path: Path,
    *,
    loader: LoaderFn,
    prefix: str,
) -> None:
    cases: list[tuple[str, str]] = [
        ("list", "verification:\n  - 1\n  - 2\n"),
        ("scalar_str", 'verification: "not a dict"\n'),
        ("scalar_int", "verification: 5\n"),
        ("explicit_null", "verification: null\n"),
    ]
    for label, body in cases:
        assert_verification_non_dict_returns_none(
            tmp_path,
            loader=loader,
            yaml_key="",
            prefix=prefix,
            body=body,
            label=label,
        )


def assert_empty_or_missing_key_returns_none(
    tmp_path: Path,
    *,
    loader: LoaderFn,
    yaml_key: str,
    prefix: str,
) -> None:
    empty_repo = tmp_path / f"{prefix}_empty_verification"
    empty_repo.mkdir()
    write_escalation_policy(empty_repo, "version: 1\nverification: {}\n")
    assert loader(empty_repo) is None, f"{prefix}: empty verification dict -> None"

    missing_repo = tmp_path / f"{prefix}_key_missing"
    missing_repo.mkdir()
    write_escalation_policy(
        missing_repo,
        "version: 1\nverification:\n  unrelated_key: 7\n",
    )
    assert loader(missing_repo) is None, f"{prefix}: unrelated key only -> None"


def assert_positive_int_loader_rejects_non_int(
    tmp_path: Path,
    *,
    loader: LoaderFn,
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
    loader: LoaderFn,
    yaml_key: str,
    prefix: str,
) -> None:
    for name, value in (("zero", 0), ("negative_one", -1), ("negative_large", -100)):
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


def assert_loaders_read_distinct_keys(
    tmp_path: Path,
    *,
    key_a: str,
    loader_a: LoaderFn,
    value_a: int,
    key_b: str,
    loader_b: LoaderFn,
    prefix: str,
) -> None:
    only_a = tmp_path / f"{prefix}_only_a"
    only_a.mkdir()
    write_escalation_policy(only_a, f"version: 1\nverification:\n  {key_a}: {value_a}\n")
    assert loader_b(only_a) is None, f"{prefix}: loader_b must not read key_a"
    assert loader_a(only_a) == value_a, f"{prefix}: loader_a must read key_a"

    only_b = tmp_path / f"{prefix}_only_b"
    only_b.mkdir()
    write_escalation_policy(only_b, f"version: 1\nverification:\n  {key_b}: {value_a + 10}\n")
    assert loader_a(only_b) is None, f"{prefix}: loader_a must not read key_b"
    assert loader_b(only_b) == value_a + 10, f"{prefix}: loader_b must read key_b"


def assert_quartet_isolation_matrix(
    tmp_path: Path,
    *,
    loaders: tuple[tuple[str, LoaderFn, str], ...],
    values: tuple[int, int, int, int],
    prefix: str,
) -> None:
    repo = tmp_path / prefix
    repo.mkdir()
    lines = ["version: 1", "verification:"]
    for idx, (_label, _loader, yaml_key) in enumerate(loaders):
        lines.append(f"  {yaml_key}: {values[idx]}")
    write_escalation_policy(repo, "\n".join(lines) + "\n")
    actual = tuple(loader(repo) for _label, loader, _key in loaders)
    assert actual == values, f"{prefix}: expected {values}, got {actual}"


def assert_bool_yaml_true_accepted_by_all(
    tmp_path: Path,
    *,
    loaders: tuple[tuple[str, LoaderFn, str], ...],
) -> None:
    for label, loader, yaml_key in loaders:
        repo = tmp_path / f"bool_true_{label}"
        repo.mkdir()
        write_escalation_policy(repo, f"version: 1\nverification:\n  {yaml_key}: true\n")
        assert loader(repo) is True, f"{label}: YAML true -> Python True accepted"


def assert_bool_yaml_false_rejected_by_all(
    tmp_path: Path,
    *,
    loaders: tuple[tuple[str, LoaderFn, str], ...],
) -> None:
    for label, loader, yaml_key in loaders:
        repo = tmp_path / f"bool_false_{label}"
        repo.mkdir()
        write_escalation_policy(repo, f"version: 1\nverification:\n  {yaml_key}: false\n")
        assert loader(repo) is None, f"{label}: YAML false -> None (False >= 1 fails)"


def assert_call_order_idempotent(
    tmp_path: Path,
    *,
    loaders: tuple[tuple[str, LoaderFn, str], ...],
    values: tuple[int, int, int, int],
) -> None:
    repo = tmp_path / "call_order"
    repo.mkdir()
    body = "version: 1\nverification:\n"
    for (_label, _loader, yaml_key), value in zip(loaders, values, strict=True):
        body += f"  {yaml_key}: {value}\n"
    write_escalation_policy(repo, body)
    forward = tuple(loader(repo) for _label, loader, _key in loaders)
    reverse = tuple(reversed([loader(repo) for _label, loader, _key in loaders]))
    assert forward == values
    assert reverse == tuple(reversed(values))
    interleaved = (
        loaders[0][1](repo),
        loaders[0][1](repo),
        loaders[1][1](repo),
        loaders[2][1](repo),
        loaders[3][1](repo),
        loaders[3][1](repo),
    )
    assert interleaved == (values[0], values[0], values[1], values[2], values[3], values[3])
