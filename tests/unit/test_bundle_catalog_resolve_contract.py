"""assert_bundle_catalog_maps_resolve`` wrapper-level + inner-helper coverage."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_extensions.catalog import assert_workflow_bundle_map_ids_resolve
from nimbusware_orchestrator.ingress import assert_bundle_catalog_maps_resolve

_REPO_ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])

_FNF_PREFIX = "missing bundle catalog:"
_VE_WMAP_PREFIX = "bundle catalog workflow_bundle_map:"
_VE_EMPTY_OR_NULL_FRAGMENT = "is empty or null"
_VE_UNKNOWN_ID_FRAGMENT = "unknown bundle id"
_VE_LOAD_YAML_PREFIX = "YAML root must be a mapping:"


# Invalid YAML bodies that should produce ValueError through both
# wrapper and helper layers. Each tuple is
# (case_id, body, exc_class, prefix_regex, fragment).
_REJECT_CASES: list[tuple[str, str, type[Exception], str, str]] = [
    (
        "load_yaml_scalar_root",
        "hello\n",
        ValueError,
        _VE_LOAD_YAML_PREFIX,
        "",
    ),
    (
        "empty_or_null_target",
        "bundles: [{id: a}]\nworkflow_bundle_map:\n  default: null\n",
        ValueError,
        _VE_WMAP_PREFIX,
        "['default'] is empty or null",
    ),
    (
        "empty_string_target",
        "bundles: [{id: a}]\nworkflow_bundle_map:\n  default: ''\n",
        ValueError,
        _VE_WMAP_PREFIX,
        "['default'] is empty or null",
    ),
    (
        "unknown_bundle_id",
        "bundles: [{id: a}]\nworkflow_bundle_map:\n  default: not-a-bundle\n",
        ValueError,
        _VE_WMAP_PREFIX,
        "['default'] -> unknown bundle id 'not-a-bundle'",
    ),
]


# Bodies that should cause early return (no exception) -- pins that
# the helper's flow at [catalog.py:34-36] handles missing /
# wrong-type / empty workflow_bundle_map without raising.
_EARLY_RETURN_CASES: list[tuple[str, str]] = [
    (
        "no_workflow_bundle_map_key",
        "bundles: [{id: a}]\n",
    ),
    (
        "wmap_not_a_dict",
        "bundles: [{id: a}]\nworkflow_bundle_map: [a, b]\n",
    ),
    (
        "wmap_empty_dict",
        "bundles: [{id: a}]\nworkflow_bundle_map: {}\n",
    ),
]


def _write_catalog(tmp_path: Path, body: str) -> Path:
    """Write ``configs/bundles/catalog.yaml`` under ``tmp_path``.

    Mirrors the directory layout the wrapper expects:
    ``{repo_root}/configs/bundles/catalog.yaml``.
    """
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True, exist_ok=True)
    cat_path = cat_dir / "catalog.yaml"
    cat_path.write_text(body, encoding="utf-8")
    return cat_path


def test_assert_bundle_catalog_maps_resolve_3_axis_wrapper_contract(
    tmp_path: Path,
) -> None:
    """Pin the wrapper's 3-axis contract (accept / FNF / VE propagation).

    Wrapper at
    [ingress.py:13-19](packages\\nimbusware_orchestrator\\ingress.py)
    delegates to ``assert_workflow_bundle_map_ids_resolve`` after
    joining ``configs/bundles/catalog.yaml`` to ``repo_root``. The
    accept arm exercises the real repo; FNF arm uses ``tmp_path``
    without the file; VE arm loops 3 invalid bodies (one per inner-
    helper reject sub-path).

    Pins the wrapper as a true passthrough: no swallow, no catch-
    and-default, no path-rewrite.
    """

    # Accept arm -- real repo's configs/bundles/catalog.yaml.
    accept_result = assert_bundle_catalog_maps_resolve(_REPO_ROOT)
    assert accept_result is None, (
        f"assert_bundle_catalog_maps_resolve({_REPO_ROOT}) returned "
        f"{accept_result!r}; expected None"
    )

    # FNF arm -- tmp_path has no configs/bundles/catalog.yaml.
    with pytest.raises(
        FileNotFoundError,
        match=re.escape(_FNF_PREFIX),
    ) as fnf_info:
        assert_bundle_catalog_maps_resolve(tmp_path)
    expected_path = tmp_path / "configs" / "bundles" / "catalog.yaml"
    assert str(expected_path) in str(fnf_info.value), (
        f"FileNotFoundError message {fnf_info.value!r} missing resolved path {expected_path!s}"
    )

    # VE arm -- 3 invalid bodies, one per inner-helper reject sub-path.
    wrapper_ve_cases = [
        ("load_yaml_scalar_root", _REJECT_CASES[0]),
        ("empty_or_null_target", _REJECT_CASES[1]),
        ("unknown_bundle_id", _REJECT_CASES[3]),
    ]
    for sub_id, (_case_id, body, _exc_class, prefix, _fragment) in wrapper_ve_cases:
        case_tmp = tmp_path / f"ve_{sub_id}"
        _write_catalog(case_tmp, body)
        with pytest.raises(ValueError, match=re.escape(prefix)):
            assert_bundle_catalog_maps_resolve(case_tmp)


def test_assert_workflow_bundle_map_ids_resolve_extended_reject_and_early_return_matrix(
    tmp_path: Path,
) -> None:
    """Pin the inner helper's reject + early-return matrix.

    Inner helper at
    [catalog.py:20-49](packages\\nimbusware_extensions\\catalog.py)
    has 5 reject sub-cases + 3 early-return cases; only "unknown
    bundle id" was tested in ``test_extensions_yaml.py``. fo82
    Part B closes the remainder.

    Reject sub-loop: 4 axes (load_yaml non-mapping, empty/null,
    empty-string, unknown id) + 1 error-truncation contract
    ("(+N more)" suffix when errors > 10). Each reject case asserts
    exception class + prefix + (where applicable) sentinel fragment.

    Early-return sub-loop: 3 cases (no wmap key, wmap not a dict,
    wmap empty) that all return None without raising. Pins that the
    helper's flow at [catalog.py:34-36] handles these gracefully
    (operators can omit ``workflow_bundle_map`` and the catalog
    validates).
    """

    for case_id, body, exc_class, prefix, fragment in _REJECT_CASES:
        case_tmp = tmp_path / f"reject_{case_id}"
        cat_path = _write_catalog(case_tmp, body)
        with pytest.raises(exc_class, match=re.escape(prefix)) as exc_info:
            assert_workflow_bundle_map_ids_resolve(cat_path)
        if fragment:
            msg = str(exc_info.value)
            assert fragment in msg, (
                f"{exc_class.__name__} message {msg!r} missing fragment "
                f"{fragment!r} (case={case_id})"
            )

    # Error-truncation: 15 workflow_bundle_map entries all unknown ->
    # errors[:10] joined + "(+5 more)" suffix at [catalog.py:46-48].
    trunc_entries = "\n".join(f"  prof_{i:02d}: missing-bundle-{i}" for i in range(15))
    trunc_body = f"bundles: [{{id: known-a}}]\nworkflow_bundle_map:\n{trunc_entries}\n"
    trunc_tmp = tmp_path / "reject_truncation"
    trunc_path = _write_catalog(trunc_tmp, trunc_body)
    with pytest.raises(ValueError, match=re.escape(_VE_WMAP_PREFIX)) as trunc_info:
        assert_workflow_bundle_map_ids_resolve(trunc_path)
    trunc_msg = str(trunc_info.value)
    assert "(+5 more)" in trunc_msg, (
        f"truncation suffix missing from message {trunc_msg!r}; "
        f"expected '(+5 more)' for 15 entries (10 joined + 5 truncated)"
    )

    # Early-return sub-loop: 3 cases that return None gracefully.
    for case_id, body in _EARLY_RETURN_CASES:
        case_tmp = tmp_path / f"early_{case_id}"
        cat_path = _write_catalog(case_tmp, body)
        result = assert_workflow_bundle_map_ids_resolve(cat_path)
        assert result is None, (
            f"assert_workflow_bundle_map_ids_resolve({cat_path}) returned "
            f"{result!r}; expected None (case={case_id})"
        )


def test_bundle_catalog_wrapper_vs_helper_consistency_contract(
    tmp_path: Path,
) -> None:
    """Pin wrapper-vs-helper exception + message parity.

    The wrapper at
    [ingress.py:13-19](packages\\nimbusware_orchestrator\\ingress.py)
    is a pure path-prefixing passthrough -- it joins
    ``configs/bundles/catalog.yaml`` to ``repo_root`` and delegates
    to ``assert_workflow_bundle_map_ids_resolve``. This test pins
    that:

    1. For a valid catalog at the expected sub-path, BOTH layers
       return None.
    2. For invalid bodies, BOTH layers raise the SAME exception
       class with the SAME message string (no swallow, no rewrite,
       no transformation).

    A future refactor that adds caching / logging / metrics to the
    wrapper MUST preserve this parity or this test fails loudly.
    """

    # Path plumbing equivalence -- valid body at expected sub-path.
    valid_body = "bundles: [{id: known-a}]\nworkflow_bundle_map: {default: known-a}\n"
    valid_tmp = tmp_path / "valid_path_plumbing"
    valid_path = _write_catalog(valid_tmp, valid_body)
    assert assert_bundle_catalog_maps_resolve(valid_tmp) is None, (
        f"wrapper failed on valid catalog at {valid_path}"
    )
    assert assert_workflow_bundle_map_ids_resolve(valid_path) is None, (
        f"helper failed on valid catalog at {valid_path}"
    )

    # Exception class + message parity across 3 axes (FNF + 2 VE).
    parity_axes: list[tuple[str, str | None]] = [
        # (case_id, body) -- body=None means no file (FNF axis).
        ("fnf_no_file", None),
        (
            "ve_empty_or_null_target",
            "bundles: [{id: a}]\nworkflow_bundle_map:\n  default: null\n",
        ),
        (
            "ve_unknown_bundle_id",
            "bundles: [{id: a}]\nworkflow_bundle_map:\n  default: not-a-bundle\n",
        ),
    ]
    for case_id, body in parity_axes:
        case_tmp = tmp_path / f"parity_{case_id}"
        case_tmp.mkdir(parents=True, exist_ok=True)
        if body is not None:
            _write_catalog(case_tmp, body)
        # If body is None we deliberately do NOT create the
        # catalog file -- both layers should raise FileNotFoundError.

        with pytest.raises(Exception) as wrapper_info:  # noqa: BLE001, PT011
            assert_bundle_catalog_maps_resolve(case_tmp)
        with pytest.raises(Exception) as helper_info:  # noqa: BLE001, PT011
            assert_workflow_bundle_map_ids_resolve(
                case_tmp / "configs" / "bundles" / "catalog.yaml",
            )
        assert type(wrapper_info.value) is type(helper_info.value), (
            f"wrapper raised {type(wrapper_info.value).__name__} but helper "
            f"raised {type(helper_info.value).__name__} (case={case_id}); "
            f"wrapper-vs-helper class parity broken"
        )
        assert str(wrapper_info.value) == str(helper_info.value), (
            f"wrapper message {str(wrapper_info.value)!r} does not match "
            f"helper message {str(helper_info.value)!r} (case={case_id}); "
            f"wrapper-vs-helper message parity broken"
        )
