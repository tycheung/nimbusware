from __future__ import annotations

from pathlib import Path

import pytest

from env import find_repo_root
from orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    integrator_gate_workflow_enabled,
    load_bundle_tags_for_bundle_id,
    load_bundle_title_for_bundle_id,
    load_integrator_min_score_from_thresholds,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)
from unit.composite_repo_fixtures import write_workflow_profile


def test_integrator_gate_workflow_enabled_false_when_missing_block(
    tmp_path: Path,
) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "bare.yaml").write_text("version: 1\n", encoding="utf-8")
    assert not integrator_gate_workflow_enabled(tmp_path, "bare")


def test_integrator_gate_workflow_enabled_respects_enabled_flag(
    tmp_path: Path,
) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ig.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n",
        encoding="utf-8",
    )
    assert integrator_gate_workflow_enabled(tmp_path, "ig")


def test_integrator_gate_workflow_enabled_false_for_unknown_profile(tmp_path: Path) -> None:
    assert not integrator_gate_workflow_enabled(tmp_path, "nope")


def test_integrator_gate_workflow_enabled_repo_profile_integrator_gate_on() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert integrator_gate_workflow_enabled(root, "integrator_gate_on")


def test_load_bundle_tags_for_bundle_id_repo_catalog() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    tags = load_bundle_tags_for_bundle_id(root, "auth-rbac-starter")
    assert tags == ["auth", "rbac"]


def test_bundle_tag_and_title_loaders_use_materialized_catalog() -> None:
    class _Mat:
        use_db = True

        @staticmethod
        def get_bundle_catalog() -> dict[str, object]:
            return {
                "version": 1,
                "bundles": [
                    {
                        "id": "db-bundle",
                        "title": "DB Title",
                        "tags": ["one", "two"],
                    },
                ],
            }

    mat = _Mat()
    assert load_bundle_tags_for_bundle_id(Path("."), "db-bundle", config_materializer=mat) == [
        "one",
        "two",
    ]
    assert (
        load_bundle_title_for_bundle_id(Path("."), "db-bundle", config_materializer=mat)
        == "DB Title"
    )


def test_parse_integrator_gate_project_tags_missing_returns_none(tmp_path: Path) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ig.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n",
        encoding="utf-8",
    )
    assert parse_integrator_gate_project_tags(tmp_path, "ig") is None


def test_parse_integrator_gate_project_tags_malformed_returns_none(tmp_path: Path) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "bad.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n  project_tags: not-a-list\n",
        encoding="utf-8",
    )
    assert parse_integrator_gate_project_tags(tmp_path, "bad") is None


def test_load_bundle_title_for_bundle_id_repo_catalog() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert load_bundle_title_for_bundle_id(root, "auth-rbac-starter") == "Admin RBAC starter"
    assert load_bundle_title_for_bundle_id(root, "unknown-bundle-xyz") == ""


def test_parse_integrator_gate_min_score_from_workflow(tmp_path: Path) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ms.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: 0.85\n",
        encoding="utf-8",
    )
    assert parse_integrator_gate_min_score_to_pass(tmp_path, "ms") == pytest.approx(0.85)


def test_effective_integrator_min_score_env_overrides_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ms.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: 0.1\n",
        encoding="utf-8",
    )
    ig_dir = tmp_path / "configs" / "integrator"
    ig_dir.mkdir(parents=True)
    (ig_dir / "thresholds.yaml").write_text(
        "version: 1\nenabled: false\nmin_score_to_pass: 0.5\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS", "0.99")
    assert effective_integrator_min_score_to_pass(tmp_path, "ms") == pytest.approx(0.99)
    monkeypatch.delenv("NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS", raising=False)
    assert effective_integrator_min_score_to_pass(tmp_path, "ms") == pytest.approx(0.1)
    assert load_integrator_min_score_from_thresholds(tmp_path) == pytest.approx(0.5)


def test_parse_integrator_gate_project_tags_explicit_list(tmp_path: Path) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "tags.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n  project_tags: [billing, stripe]\n",
        encoding="utf-8",
    )
    assert parse_integrator_gate_project_tags(tmp_path, "tags") == ["billing", "stripe"]


def test_parse_integrator_gate_project_tags_empty_list_returns_none(
    tmp_path: Path,
) -> None:
    """Pin §14 #13: ``project_tags: []`` → ``None`` via the ``out or None`` fallback.

    Distinct from the missing-key case already covered by
    :func:`test_parse_integrator_gate_project_tags_missing_returns_none`: an *explicit*
    empty list must still collapse to ``None`` so downstream
    :class:`ModuleIntegrator.score_fit` treats it as "no project-tag override" (and
    thus aligns project tags with the selected bundle's catalog tags) rather than
    "operator asserted zero project tags". Any future refactor that wants to surface
    the explicit-empty-list intent (e.g. returning ``[]``) must update this test on
    purpose.
    """
    write_workflow_profile(
        tmp_path,
        "empty",
        "version: 1\nintegrator_gate:\n  enabled: true\n  project_tags: []\n",
    )
    assert parse_integrator_gate_project_tags(tmp_path, "empty") is None


def test_parse_integrator_gate_project_tags_whitespace_only_entries_return_none(
    tmp_path: Path,
) -> None:
    """Pin §14 #13: all-whitespace ``project_tags`` entries → ``None``.

    The list-comprehension filter ``if str(t).strip()`` drops every entry that
    reduces to an empty string after :py:meth:`str.strip`. When every entry is
    whitespace-only the resulting ``out`` is empty and falls through ``out or None``
    to ``None`` (same end state as the explicit-empty-list case above). Locks the
    silent-drop semantics so operators can't accidentally "disable" project-tag
    override by typing only whitespace and assuming an empty-list signal survives.
    """
    write_workflow_profile(
        tmp_path,
        "ws",
        'version: 1\nintegrator_gate:\n  enabled: true\n  project_tags: ["  ", "", "\\t"]\n',
    )
    assert parse_integrator_gate_project_tags(tmp_path, "ws") is None


def test_parse_integrator_gate_project_tags_filters_and_coerces_mixed_entries(
    tmp_path: Path,
) -> None:
    """Pin §14 #13: mixed non-string entries get ``str()``-coerced + stripped.

    ``project_tags`` runs every entry through ``str(t).strip()`` (both as the filter
    predicate and as the produced value). This pins two subtle gotchas:

    1. Integer YAML scalars survive as their string representation (``42`` → ``"42"``)
       rather than being dropped by an ``isinstance(str)`` filter.
    2. YAML ``null`` becomes the literal **truthy** string ``"None"`` because
       ``str(None) == "None"`` (length 4, non-empty after strip), so a stray ``null``
       in the list silently leaks into the integrator's matched-tags audit metadata
       rather than being filtered out as "no tag here".

    A refactor that wants strict-string filtering (e.g. ``if isinstance(t, str)``) or
    a None-aware filter would break this test on purpose. Quoted ``"  billing  "``
    and an unquoted empty string sibling are included to confirm strip + empty-filter
    still run alongside the coercion path.
    """
    write_workflow_profile(
        tmp_path,
        "mixed",
        "version: 1\nintegrator_gate:\n  enabled: true\n"
        '  project_tags: [42, "  billing  ", null, "stripe", ""]\n',
    )
    assert parse_integrator_gate_project_tags(tmp_path, "mixed") == [
        "42",
        "billing",
        "None",
        "stripe",
    ]


def test_parse_integrator_gate_project_tags_malformed_block_returns_none(
    tmp_path: Path,
) -> None:
    """Pin §14 #13: scalar / list ``integrator_gate:`` block → ``None``.

    The shared ``_integrator_gate_workflow_dict`` outer guard (``block if
    isinstance(block, dict) else None``) returns ``None`` when ``integrator_gate:``
    is not a dict, and :func:`parse_integrator_gate_project_tags` then short-circuits
    on its ``block is None`` check. Mirrors the malformed-block style of follow-ons
    52 / 53 / 55 so any refactor that wants to accept scalar shortcuts must update
    this test on purpose.
    """
    write_workflow_profile(
        tmp_path,
        "block_scalar",
        "version: 1\nintegrator_gate: true\n",
    )
    write_workflow_profile(
        tmp_path,
        "block_list",
        "version: 1\nintegrator_gate: []\n",
    )
    for name in ("block_scalar", "block_list"):
        assert parse_integrator_gate_project_tags(tmp_path, name) is None, name


def test_parse_integrator_gate_min_score_clamping_and_malformed(
    tmp_path: Path,
) -> None:
    """Pin §14 #13: ``min_score_to_pass`` clamping + malformed-value contract.

    The parser runs ``float(raw)`` inside a ``TypeError``/``ValueError`` guard and
    then ``max(0.0, min(1.0, v))`` to clamp into ``[0.0, 1.0]``. This single test
    locks every branch:

    - Negative / over-1.0 numeric values are clamped to the closest boundary so
      operators can't accidentally set "always fail" / "always pass" via signed
      gradients (``-0.5`` → ``0.0``; ``1.5`` → ``1.0``).
    - Boundary values pass through unchanged.
    - String YAML literals (``"abc"``) raise ``ValueError`` → ``None`` (caller falls
      back to ``configs/integrator/thresholds.yaml`` via
      ``effective_integrator_min_score_to_pass``).
    - YAML ``null`` short-circuits at the explicit ``raw is None`` guard *before*
      reaching the ``float()`` call.
    - Non-scalar containers (list / dict) raise ``TypeError`` → ``None``.

    Locks the contract so any refactor (e.g. relaxing clamping or raising on
    malformed values) must update this test on purpose.
    """
    cases: list[tuple[str, str, float | None]] = [
        ("neg_clamp", "-0.5", 0.0),
        ("over_clamp", "1.5", 1.0),
        ("zero_boundary", "0.0", 0.0),
        ("one_boundary", "1.0", 1.0),
        ("str_bad", '"abc"', None),
        ("null_short_circuit", "null", None),
        ("list_val", "[0.5]", None),
        ("dict_val", "{nested: 0.5}", None),
    ]
    for name, raw, expected in cases:
        write_workflow_profile(
            tmp_path,
            name,
            f"version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: {raw}\n",
        )
        actual = parse_integrator_gate_min_score_to_pass(tmp_path, name)
        if expected is None:
            assert actual is None, name
        else:
            assert actual == pytest.approx(expected), name
