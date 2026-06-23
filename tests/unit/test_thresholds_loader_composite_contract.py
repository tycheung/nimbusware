from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.integrator_gate import (
    load_integrator_gate_emit_enabled,
    load_integrator_min_score_from_thresholds,
    parse_integrator_gate_min_score_to_pass,
)
from unit.composite_repo_fixtures import (
    write_integrator_thresholds,
    write_workflow_integrator_min_score,
)

_YAML_ROOT_MAPPING_PREFIX = "YAML root must be a mapping:"


def test_load_integrator_gate_emit_enabled_defensive_arms_contract(
    tmp_path: Path,
) -> None:
    a1_repo = tmp_path / "a1_file_absent"
    a1_repo.mkdir()
    assert load_integrator_gate_emit_enabled(a1_repo) is False, (
        "A1: thresholds.yaml absent -> `is_file()` fallback at line 55-56 "
        "returns False. A refactor that dropped the `is_file` guard would "
        "let `load_yaml` raise FileNotFoundError up to callers"
    )

    a2_repo = tmp_path / "a2_key_missing"
    a2_repo.mkdir()
    write_integrator_thresholds(a2_repo, "version: 1\nmin_score_to_pass: 0.5\n")
    assert load_integrator_gate_emit_enabled(a2_repo) is False, (
        "A2: file present without `enabled` key -> `raw.get('enabled', "
        "False)` returns the default False -> `bool(False) is False`. "
        "Pins the missing-key default (a refactor changing the default "
        "to True would flip this axis)"
    )

    a3_repo = tmp_path / "a3_explicit_null"
    a3_repo.mkdir()
    write_integrator_thresholds(a3_repo, "version: 1\nenabled: null\n")
    assert load_integrator_gate_emit_enabled(a3_repo) is False, (
        "A3: `enabled: null` -> `raw.get` returns None (key present, "
        "value None; NOT the default) -> `bool(None) is False`. "
        "Distinct path from A2 (missing-key default) but same end state. "
        "A refactor swapping `bool()` for a strict `is True` check would "
        "flip both A3 and A2 but Part A4 still pins explicit True"
    )

    a4_repo = tmp_path / "a4_explicit_true"
    a4_repo.mkdir()
    write_integrator_thresholds(a4_repo, "version: 1\nenabled: true\n")
    assert load_integrator_gate_emit_enabled(a4_repo) is True, (
        "A4: `enabled: true` -> happy explicit True path. Mirrors the "
        "fo21 sample but co-locates with the defensive matrix so a "
        "refactor regressing the happy path while passing every "
        "defensive axis would still fail here"
    )

    a5_repo = tmp_path / "a5_explicit_false"
    a5_repo.mkdir()
    write_integrator_thresholds(a5_repo, "version: 1\nenabled: false\n")
    assert load_integrator_gate_emit_enabled(a5_repo) is False, (
        "A5: `enabled: false` -> happy explicit False path. Distinct "
        "from A2/A3 because the YAML scalar reaches `bool(False)` "
        "directly (not via missing-key default or None coercion)"
    )


def test_load_integrator_gate_emit_enabled_python_bool_ladder_contract(
    tmp_path: Path,
) -> None:
    int_cases: list[tuple[str, str, bool]] = [
        ("int_zero", "enabled: 0", False),
        ("int_one", "enabled: 1", True),
        ("int_two", "enabled: 2", True),
        ("int_negative", "enabled: -1", True),
    ]
    for name, body, expected in int_cases:
        repo = tmp_path / f"b1_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_gate_emit_enabled(repo)
        assert actual is expected, (
            f"B1 {name}: `{body}` -> bool() of int -> expected "
            f"{expected!r}, got {actual!r}. Pins that ANY non-zero int "
            "is truthy (a refactor restricting to `== 1` like "
            "`_coerce_yaml_bool` would flip B1 int_two / int_negative)"
        )

    float_cases: list[tuple[str, str, bool]] = [
        ("float_zero", "enabled: 0.0", False),
        ("float_half", "enabled: 0.5", True),
        ("float_one", "enabled: 1.0", True),
    ]
    for name, body, expected in float_cases:
        repo = tmp_path / f"b2_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_gate_emit_enabled(repo)
        assert actual is expected, (
            f"B2 {name}: `{body}` -> bool() of float -> expected "
            f"{expected!r}, got {actual!r}. Pins that ANY non-zero "
            "float is truthy (mirrors B1 for the float arm)"
        )

    string_divergence_cases: list[tuple[str, str, bool]] = [
        ("str_false_literal", 'enabled: "false"', True),
        ("str_no_literal", 'enabled: "no"', True),
        ("str_off_literal", 'enabled: "off"', True),
        ("str_zero_literal", 'enabled: "0"', True),
        ("str_random", 'enabled: "anything"', True),
    ]
    for name, body, expected in string_divergence_cases:
        repo = tmp_path / f"b3_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_gate_emit_enabled(repo)
        assert actual is expected, (
            f"B3 KEY DIVERGENCE {name}: `{body}` -> Python `bool()` "
            "treats any non-empty string as truthy, so the literal "
            f'string `"false"` / `"no"` / `"off"` resolves to True. '
            f"Expected {expected!r}, got {actual!r}. A refactor swapping "
            "`bool(...)` for `_coerce_yaml_bool(...)` (which only "
            'accepts ("1", "true", "yes", "on") after '
            "`.strip().lower()`) would flip every case in B3 to False. "
            "This axis catches any silent migration from Python `bool()` "
            "to the strict YAML coercer"
        )

    falsy_container_cases: list[tuple[str, str, bool]] = [
        ("str_empty", 'enabled: ""', False),
        ("list_empty", "enabled: []", False),
        ("dict_empty", "enabled: {}", False),
    ]
    for name, body, expected in falsy_container_cases:
        repo = tmp_path / f"b4_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_gate_emit_enabled(repo)
        assert actual is expected, (
            f"B4 {name}: `{body}` -> Python `bool()` treats empty "
            f"string / empty list / empty dict as falsy. Expected "
            f"{expected!r}, got {actual!r}. Pins that the bool() ladder "
            "is symmetric -- container emptiness drives the answer not "
            "the container type"
        )

    truthy_container_cases: list[tuple[str, str, bool]] = [
        ("list_nonempty", 'enabled: ["any"]', True),
        ("dict_nonempty", "enabled: {key: val}", True),
    ]
    for name, body, expected in truthy_container_cases:
        repo = tmp_path / f"b5_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_gate_emit_enabled(repo)
        assert actual is expected, (
            f"B5 {name}: `{body}` -> Python `bool()` treats non-empty "
            f"list / dict as truthy. Expected {expected!r}, got "
            f"{actual!r}. Pairs with B4 to prove emptiness (not type) "
            "is the only thing that matters for the container ladder"
        )


def test_load_integrator_min_score_from_thresholds_defensive_arms_contract(
    tmp_path: Path,
) -> None:
    c1_repo = tmp_path / "c1_file_absent"
    c1_repo.mkdir()
    assert load_integrator_min_score_from_thresholds(c1_repo) == 0.0, (
        "C1: thresholds.yaml absent -> `is_file()` fallback at line "
        "126-127 returns 0.0. Pins the absent-arm short-circuit (a "
        "refactor that dropped the `is_file` guard would let `load_yaml` "
        "raise FileNotFoundError up to callers via `effective_...`)"
    )

    c2_repo = tmp_path / "c2_key_missing"
    c2_repo.mkdir()
    write_integrator_thresholds(c2_repo, "version: 1\nenabled: true\n")
    assert load_integrator_min_score_from_thresholds(c2_repo) == 0.0, (
        "C2: file present without `min_score_to_pass` -> "
        "`raw.get('min_score_to_pass', 0.0)` returns the default 0.0 -> "
        "`float(0.0)` returns 0.0. Distinct path from C3 (the default "
        "reaches float() directly, no exception is raised)"
    )

    c3_repo = tmp_path / "c3_explicit_null"
    c3_repo.mkdir()
    write_integrator_thresholds(c3_repo, "version: 1\nmin_score_to_pass: null\n")
    assert load_integrator_min_score_from_thresholds(c3_repo) == 0.0, (
        "C3: `min_score_to_pass: null` -> `raw.get` returns None (key "
        "PRESENT, value None; NOT the default) -> `float(None)` raises "
        "`TypeError` -> caught -> 0.0. DISTINCT path from C2. A refactor "
        "narrowing `except (TypeError, ValueError)` to only "
        "`except ValueError` would surface TypeError to callers here"
    )

    type_error_cases: list[tuple[str, str]] = [
        ("list_value", "min_score_to_pass: [0.5]"),
        ("dict_value", "min_score_to_pass: {nested: 0.5}"),
    ]
    for name, body in type_error_cases:
        repo = tmp_path / f"c4_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_min_score_from_thresholds(repo)
        assert actual == 0.0, (
            f"C4 {name}: `{body}` -> `float()` raises TypeError on "
            f"non-scalar containers -> caught -> 0.0. Got {actual!r}. "
            "Pins the TypeError half of the catch tuple (a refactor "
            "swapping `(TypeError, ValueError)` for `ValueError` alone "
            "would surface TypeError here)"
        )

    value_error_cases: list[tuple[str, str]] = [
        ("str_abc", 'min_score_to_pass: "abc"'),
        ("str_near_miss", 'min_score_to_pass: "0.5x"'),
        ("str_double_dot", 'min_score_to_pass: "0.5.6"'),
    ]
    for name, body in value_error_cases:
        repo = tmp_path / f"c5_ve_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_min_score_from_thresholds(repo)
        assert actual == 0.0, (
            f"C5(ve) {name}: `{body}` -> `float()` raises ValueError "
            "on un-parseable strings -> caught -> 0.0. Got "
            f"{actual!r}. Pins the ValueError half of the catch tuple"
        )

    happy_cases: list[tuple[str, str, float]] = [
        ("float_half", "min_score_to_pass: 0.5", 0.5),
        ("float_zero", "min_score_to_pass: 0", 0.0),
        ("int_one", "min_score_to_pass: 1", 1.0),
        ("float_boundary", "min_score_to_pass: 1.0", 1.0),
    ]
    for name, body, expected in happy_cases:
        repo = tmp_path / f"c5_happy_{name}"
        repo.mkdir()
        write_integrator_thresholds(repo, f"version: 1\n{body}\n")
        actual = load_integrator_min_score_from_thresholds(repo)
        assert actual == pytest.approx(expected), (
            f"C5(happy) {name}: `{body}` -> `float()` passthrough -> "
            f"expected {expected!r}, got {actual!r}. Pins int-to-float "
            "coercion (the int_one case proves YAML scalar int reaches "
            "float() and coerces, distinct from explicit `1.0`)"
        )


def test_thresholds_loader_cross_function_composite_and_divergence_contract(
    tmp_path: Path,
) -> None:
    d1_repo = tmp_path / "d1_shared_path"
    d1_repo.mkdir()
    write_integrator_thresholds(
        d1_repo,
        "version: 1\nenabled: true\nmin_score_to_pass: 0.75\n",
    )
    emit_enabled = load_integrator_gate_emit_enabled(d1_repo)
    min_score = load_integrator_min_score_from_thresholds(d1_repo)
    assert emit_enabled is True, (
        "D1(a): shared `configs/integrator/thresholds.yaml` -- a single "
        "write should make BOTH loaders return their happy values. "
        f"emit_enabled returned {emit_enabled!r} not True. A refactor "
        "moving either path would break this composite"
    )
    assert min_score == pytest.approx(0.75), (
        "D1(b): shared `configs/integrator/thresholds.yaml` -- a single "
        "write should make BOTH loaders return their happy values. "
        f"min_score returned {min_score!r} not 0.75. Pins that the "
        "hardcoded path string is consistent between the two loaders"
    )

    d2_repo = tmp_path / "d2_independent_probes"
    d2_repo.mkdir()
    assert load_integrator_gate_emit_enabled(d2_repo) is False
    assert load_integrator_min_score_from_thresholds(d2_repo) == 0.0, (
        "D2(absent): file absent -> BOTH loaders fail-closed "
        "independently. Pins that neither short-circuit depends on the "
        "other"
    )
    write_integrator_thresholds(d2_repo, "version: 1\nenabled: true\n")
    assert load_integrator_gate_emit_enabled(d2_repo) is True
    assert load_integrator_min_score_from_thresholds(d2_repo) == 0.0, (
        "D2(partial): file present with only `enabled` -> emit-enabled "
        "loader reads True, min-score loader cascades to 0.0 default. "
        "Pins that the two loaders process the same file independently "
        "and do NOT share parsed state"
    )

    no_clamp_cases: list[tuple[str, str, float]] = [
        ("negative_small", "-0.5", -0.5),
        ("over_one_small", "1.5", 1.5),
        ("negative_large", "-100.0", -100.0),
        ("over_one_large", "100.0", 100.0),
    ]
    for name, raw, expected in no_clamp_cases:
        repo = tmp_path / f"d3_noclamp_{name}"
        repo.mkdir()
        write_integrator_thresholds(
            repo,
            f"version: 1\nenabled: true\nmin_score_to_pass: {raw}\n",
        )
        thresholds_value = load_integrator_min_score_from_thresholds(repo)
        assert thresholds_value == pytest.approx(expected), (
            f"D3(thresholds) {name}: `min_score_to_pass: {raw}` -> "
            f"thresholds loader returns RAW unclamped value {expected!r}, "
            f"got {thresholds_value!r}. KEY DIVERGENCE: the workflow-"
            "layer parser clamps to [0.0, 1.0] but the thresholds-layer "
            "loader does NOT. A refactor adding clamping `to unify` "
            "would FLIP every case in D3"
        )

        write_workflow_integrator_min_score(repo, name, raw)
        wf_value = parse_integrator_gate_min_score_to_pass(repo, name)
        clamped_expected = max(0.0, min(1.0, expected))
        assert wf_value == pytest.approx(clamped_expected), (
            f"D3(wf) {name}: same `{raw}` through "
            "parse_integrator_gate_min_score_to_pass -> clamps to "
            f"{clamped_expected!r}, got {wf_value!r}. Pairs with D3"
            "(thresholds) to prove the asymmetry IS the contract (each "
            "function clamps OR doesn't clamp deliberately)"
        )

    d4_repo = tmp_path / "d4_return_types"
    d4_repo.mkdir()
    write_integrator_thresholds(d4_repo, "version: 1\nenabled: true\n")
    thresholds_no_key = load_integrator_min_score_from_thresholds(d4_repo)
    assert isinstance(thresholds_no_key, float), (
        f"D4(thresholds): missing-key returns float ({thresholds_no_key!r}, "
        f"type {type(thresholds_no_key).__name__}), NEVER None. Pins "
        "binary contract (caller `effective_...` can ALWAYS chain into "
        "this loader as a terminal default; a refactor returning None "
        "for missing-key would break that terminal-floor invariant)"
    )
    assert thresholds_no_key == 0.0
    write_workflow_integrator_min_score(d4_repo, "d4_no_key", "")
    wf_dir = d4_repo / "configs" / "workflows"
    (wf_dir / "d4_no_key.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n",
        encoding="utf-8",
    )
    wf_no_key = parse_integrator_gate_min_score_to_pass(d4_repo, "d4_no_key")
    assert wf_no_key is None, (
        f"D4(wf): missing `min_score_to_pass` key in workflow YAML "
        f"returns None ({wf_no_key!r}). Pins tri-state contract (caller "
        "`effective_...` USES `is not None` to distinguish 'wf has a "
        "valid override' from 'wf doesn't have one' and falls through "
        "to the thresholds loader). KEY DIVERGENCE vs D4(thresholds): "
        "asymmetric return types are deliberate, NOT an oversight"
    )

    d5_repo = tmp_path / "d5_propagate_non_mapping"
    d5_repo.mkdir()
    write_integrator_thresholds(d5_repo, '"just a string"\n')
    with pytest.raises(ValueError) as exc_emit:
        load_integrator_gate_emit_enabled(d5_repo)
    assert str(exc_emit.value).startswith(_YAML_ROOT_MAPPING_PREFIX), (
        "D5(emit): non-mapping YAML root -> load_yaml raises ValueError "
        "with message `YAML root must be a mapping: ...` (from "
        "merge.py:22) -> load_integrator_gate_emit_enabled has NO "
        "outer try/except so the ValueError PROPAGATES. KEY DIVERGENCE "
        "vs the fo77 cascade family which catches "
        "`(OSError, ValueError, UnicodeDecodeError)`. Got message: "
        f"{exc_emit.value!s}"
    )
    with pytest.raises(ValueError) as exc_score:
        load_integrator_min_score_from_thresholds(d5_repo)
    assert str(exc_score.value).startswith(_YAML_ROOT_MAPPING_PREFIX), (
        "D5(min_score): non-mapping YAML root -> propagates same "
        "ValueError. Pins that the NARROW `(TypeError, ValueError)` "
        "catch around `float()` does NOT extend to `load_yaml` (a "
        "refactor widening the catch to wrap `load_yaml` would silently "
        "swallow this and return 0.0 instead). Got message: "
        f"{exc_score.value!s}"
    )
