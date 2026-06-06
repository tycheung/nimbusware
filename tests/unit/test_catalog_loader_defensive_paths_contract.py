"""Catalog loader defensive paths composite."""

from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.integrator_gate import (
    load_bundle_tags_for_bundle_id,
    load_bundle_title_for_bundle_id,
    parse_integrator_gate_project_tags,
    select_bundle_id_for_workflow,
)


def _write_catalog(repo: Path, body: str) -> None:
    """Write ``configs/bundles/catalog.yaml`` under ``repo`` with the given body.

    Uses ``exist_ok=True`` so a single test can drop multiple successive
    catalogs into the same ``tmp_path`` for sub-axis sweeps.
    """
    cat_dir = repo / "configs" / "bundles"
    cat_dir.mkdir(parents=True, exist_ok=True)
    (cat_dir / "catalog.yaml").write_text(body, encoding="utf-8")


def test_select_bundle_id_for_workflow_ladder_defensive_arms_5_axis(
    tmp_path: Path,
) -> None:
    a1_repo = tmp_path / "a1_catalog_absent"
    a1_repo.mkdir()
    assert select_bundle_id_for_workflow(a1_repo, "default") == "auth-rbac-starter", (
        "A1: catalog.yaml absent -> `auth-rbac-starter` hardcoded fallback at "
        "pipeline-line 64-65. Today only covered indirectly via fo107 B3; "
        "this is the explicit direct pin"
    )

    a2_repo = tmp_path / "a2_no_bundles_list"
    a2_repo.mkdir()
    _write_catalog(a2_repo, "version: 1\n")
    assert select_bundle_id_for_workflow(a2_repo, "default") == "auth-rbac-starter", (
        "A2: catalog present but no `bundles` key -> final `auth-rbac-starter` "
        "fallback at line 75. Pins the loop-empty branch (bundles=[] yields "
        "`if bundles` False -> falls through)"
    )

    a3_repo = tmp_path / "a3_wmap_value_none"
    a3_repo.mkdir()
    _write_catalog(
        a3_repo,
        "version: 1\n"
        "workflow_bundle_map:\n"
        "  custom_wf: null\n"
        "bundles:\n"
        "  - id: real-bundle\n"
        "    tags: [a]\n",
    )
    assert select_bundle_id_for_workflow(a3_repo, "custom_wf") == "real-bundle", (
        "A3: `workflow_bundle_map.custom_wf: null` -> `wmap[key] is not None` "
        "guard at line 70 short-circuits the wmap arm; falls through to "
        "first-bundle (`real-bundle`). Pins `is not None` vs truthy: a "
        "refactor to `if wmap[key]:` truthy guard would still pass for null "
        "values (both falsy), but would FLIP for `wmap[key] == 0` or other "
        "falsy non-None scalars -- the explicit `is not None` matters"
    )

    a4_repo = tmp_path / "a4_wmap_not_dict"
    a4_repo.mkdir()
    _write_catalog(
        a4_repo,
        "version: 1\nworkflow_bundle_map:\n  - a\n  - b\nbundles:\n  - id: only-bundle\n",
    )
    assert select_bundle_id_for_workflow(a4_repo, "custom_wf") == "only-bundle", (
        "A4: `workflow_bundle_map` parsed as a list (not a dict) -> "
        "`isinstance(wmap, dict)` guard at line 68 skips the wmap arm; "
        "falls through to `bundles[0].id == only-bundle`. Pins the "
        "isinstance guard (a refactor that dropped the dict check would "
        "raise TypeError on `wmap[key]` indexing)"
    )

    a5a_repo = tmp_path / "a5a_bundles0_not_dict"
    a5a_repo.mkdir()
    _write_catalog(
        a5a_repo,
        "version: 1\nbundles:\n  - not-a-dict-string\n  - also-string\n",
    )
    assert select_bundle_id_for_workflow(a5a_repo, "default") == "auth-rbac-starter", (
        "A5(a): `bundles[0]` is a string -> "
        "`isinstance(bundles[0], dict)` guard at line 73 short-circuits; "
        "falls through to `auth-rbac-starter` final fallback. Pins the "
        "first inner guard (would silently regress under a refactor "
        "that dropped the isinstance check and called `bundles[0].get('id')` "
        "which would raise AttributeError on the string)"
    )

    a5b_repo = tmp_path / "a5b_bundles0_no_id"
    a5b_repo.mkdir()
    _write_catalog(
        a5b_repo,
        "version: 1\nbundles:\n  - tags: [a]\n",
    )
    assert select_bundle_id_for_workflow(a5b_repo, "default") == "auth-rbac-starter", (
        "A5(b): `bundles[0]` is a dict but missing `id` -> "
        "`bundles[0].get('id')` returns None (falsy) -> the AND short-circuits; "
        "falls through to `auth-rbac-starter`. Pins the SECOND inner guard "
        "(distinct from A5(a)'s isinstance guard; together they prove BOTH "
        "guards are independently necessary)"
    )


def test_bundle_entry_for_id_lookup_matrix_5_axis(tmp_path: Path) -> None:
    b1_repo = tmp_path / "b1_catalog_absent"
    b1_repo.mkdir()
    assert load_bundle_tags_for_bundle_id(b1_repo, "any-bundle") == [], (
        "B1: catalog.yaml absent -> `_bundle_entry_for_id` returns None at "
        "line 91-92 -> `load_bundle_tags` `if b is None: return []` at "
        "line 106-107. Pins the absent-arm short-circuit"
    )

    b2_repo = tmp_path / "b2_bundles_missing"
    b2_repo.mkdir()
    _write_catalog(b2_repo, "version: 1\n")
    assert load_bundle_tags_for_bundle_id(b2_repo, "any-bundle") == [], (
        "B2: catalog present without `bundles` key -> `raw.get('bundles')` "
        "returns None -> ternary at line 95 yields `bundles = []` -> loop "
        "empty -> entry None -> []"
    )

    b3_repo = tmp_path / "b3_bundles_not_a_list"
    b3_repo.mkdir()
    _write_catalog(b3_repo, "version: 1\nbundles: not-a-list-string\n")
    assert load_bundle_tags_for_bundle_id(b3_repo, "any-bundle") == [], (
        "B3: `bundles` is a string (not a list) -> "
        "`isinstance(bundles_raw, list)` at line 95 returns False -> "
        "`bundles = []` -> loop empty -> entry None -> []. Pins the "
        "isinstance ternary (a refactor that dropped this guard would "
        "raise TypeError on `for b in bundles:` when bundles is a string "
        "-- which would iterate character-by-character not error, but the "
        "isinstance check on each char would always fail anyway; the guard "
        "still matters for the dict-case which WOULD iterate over keys)"
    )

    b4_repo = tmp_path / "b4_non_dict_entries_filtered"
    b4_repo.mkdir()
    _write_catalog(
        b4_repo,
        "version: 1\n"
        "bundles:\n"
        '  - "string-entry"\n'
        "  - null\n"
        "  - id: real-bundle\n"
        "    tags: [auth]\n",
    )
    assert load_bundle_tags_for_bundle_id(b4_repo, "real-bundle") == ["auth"], (
        "B4: bundles list contains a string, a null, then the target dict "
        "entry. The `isinstance(b, dict)` filter at line 98 skips the string "
        "and the null without raising, and the loop continues to the dict "
        "entry which matches by id. Pins that non-dict entries do not abort "
        "the search (a refactor that raised on non-dict entries would break "
        "this; a refactor that dropped the isinstance check would raise "
        "AttributeError on `.get('id')` for the string)"
    )

    b5_repo = tmp_path / "b5_id_strip_tolerance"
    b5_repo.mkdir()
    _write_catalog(
        b5_repo,
        "version: 1\nbundles:\n  - id: real-bundle\n    tags: [auth]\n",
    )
    assert load_bundle_tags_for_bundle_id(
        b5_repo,
        "  real-bundle  ",
    ) == ["auth"], (
        "B5: caller passes `'  real-bundle  '` with leading/trailing "
        "whitespace; `bid = str(bundle_id).strip()` at line 96 normalizes "
        "to `'real-bundle'` and matches the catalog entry. Pins the "
        "caller-side whitespace tolerance (would silently break if the "
        "strip() were removed)"
    )


def test_load_bundle_tags_for_bundle_id_defensive_arms_5_axis(
    tmp_path: Path,
) -> None:
    c1_repo = tmp_path / "c1_tags_key_missing"
    c1_repo.mkdir()
    _write_catalog(
        c1_repo,
        "version: 1\nbundles:\n  - id: tagless-bundle\n",
    )
    assert load_bundle_tags_for_bundle_id(c1_repo, "tagless-bundle") == [], (
        "C1: bundle entry exists without `tags` key -> `b.get('tags')` "
        "returns None -> `not isinstance(tags, list)` at line 109 is True "
        "-> []. Pins the no-tags-key arm"
    )

    c2a_repo = tmp_path / "c2a_tags_string"
    c2a_repo.mkdir()
    _write_catalog(
        c2a_repo,
        "version: 1\nbundles:\n  - id: bad-tags-string\n    tags: not-a-list-string\n",
    )
    assert load_bundle_tags_for_bundle_id(c2a_repo, "bad-tags-string") == [], (
        "C2(a): `tags: not-a-list-string` -> string fails `isinstance(tags, "
        "list)` -> []. First sub-case of the non-list guard"
    )

    c2b_repo = tmp_path / "c2b_tags_dict"
    c2b_repo.mkdir()
    _write_catalog(
        c2b_repo,
        "version: 1\n"
        "bundles:\n"
        "  - id: bad-tags-dict\n"
        "    tags:\n"
        "      auth: true\n"
        "      rbac: true\n",
    )
    assert load_bundle_tags_for_bundle_id(c2b_repo, "bad-tags-dict") == [], (
        "C2(b): `tags` is a dict -> fails isinstance -> []. Pins the dict-"
        "case (without the isinstance check, iteration over a dict would "
        "yield keys -- a fundamentally different result)"
    )

    c2c_repo = tmp_path / "c2c_tags_int"
    c2c_repo.mkdir()
    _write_catalog(
        c2c_repo,
        "version: 1\nbundles:\n  - id: bad-tags-int\n    tags: 42\n",
    )
    assert load_bundle_tags_for_bundle_id(c2c_repo, "bad-tags-int") == [], (
        "C2(c): `tags: 42` (int) -> fails isinstance -> []. Pins the "
        "scalar-int case (without the isinstance check, `for t in 42:` "
        "would raise TypeError)"
    )

    c3_repo = tmp_path / "c3_mixed_tags"
    c3_repo.mkdir()
    _write_catalog(
        c3_repo,
        'version: 1\nbundles:\n  - id: mixed\n    tags: [42, "  billing  ", null, "stripe", ""]\n',
    )
    assert load_bundle_tags_for_bundle_id(c3_repo, "mixed") == [
        "42",
        "billing",
        "None",
        "stripe",
    ], (
        "C3: mixed-types tags `[42, '  billing  ', null, 'stripe', '']` -> "
        "list comprehension at line 111 yields `['42', 'billing', 'None', "
        "'stripe']` (in order). Pins:\n"
        "  1. Integer 42 -> str(42).strip() = '42' (non-empty, included).\n"
        "  2. Whitespace-padded 'billing' stripped to 'billing'.\n"
        "  3. YAML null -> Python None -> str(None) = 'None' (truthy string "
        "after strip; INCLUDED -- same gotcha as fo21's "
        "`test_parse_integrator_gate_project_tags_filters_and_coerces_mixed`).\n"
        "  4. Plain 'stripe' passes through.\n"
        "  5. Empty string '' filtered out by `if str(t).strip()` guard.\n"
        "Consistent coercion semantics across both tag parsers"
    )

    c4_repo = tmp_path / "c4_whitespace_only_tags"
    c4_repo.mkdir()
    _write_catalog(
        c4_repo,
        'version: 1\nbundles:\n  - id: ws\n    tags: ["  ", "", "\\t"]\n',
    )
    actual_c4 = load_bundle_tags_for_bundle_id(c4_repo, "ws")
    assert actual_c4 == [], (
        f"C4: all-whitespace tags `['  ', '', '\\t']` -> every entry's "
        f"`str(t).strip()` reduces to empty -> filter predicate drops all "
        f"-> []. Pins the filter (`if str(t).strip()` at line 111); got "
        f"{actual_c4!r}"
    )

    actual_c5_tags = load_bundle_tags_for_bundle_id(c4_repo, "ws")
    actual_c5_project = parse_integrator_gate_project_tags(c4_repo, "default")
    assert actual_c5_tags == [] and actual_c5_tags is not None, (
        f"C5 (KEY DIVERGENCE part 1): `load_bundle_tags` returns the LITERAL "
        f"empty list `[]` for all-whitespace input -- NOT None. The function "
        f"has NO `out or None` collapse at the end; got {actual_c5_tags!r}. "
        "CRITICAL CONTRACT: a 'harmonize all tag parsers' refactor that "
        "added `return out or None` here would silently flip downstream "
        "consumers (e.g., the bundle-tags arm of `_emit_bundle_integrator_"
        "gate`'s project_tags ladder) from `bundle_tags non-empty -> use "
        "as project_tags` to `bundle_tags falsy -> singleton fallback`. "
        "Materially different emit-time behavior"
    )
    assert actual_c5_project is None, (
        f"C5 (KEY DIVERGENCE part 2): `parse_integrator_gate_project_tags` "
        f"returns None for the same all-whitespace input via the `return "
        f"out or None` at integrator_gate.py:189; got "
        f"{actual_c5_project!r}. Surfaces the structural asymmetry between "
        "the two parsers explicitly"
    )


def test_load_bundle_title_for_bundle_id_defensive_arms_5_axis(
    tmp_path: Path,
) -> None:
    d1_repo = tmp_path / "d1_catalog_absent"
    d1_repo.mkdir()
    assert load_bundle_title_for_bundle_id(d1_repo, "any") == "", (
        'D1: catalog.yaml absent -> entry None at line 117 -> `""` '
        "early-return. Mirrors B1 for the title loader"
    )

    d2_repo = tmp_path / "d2_bundle_not_found"
    d2_repo.mkdir()
    _write_catalog(
        d2_repo,
        "version: 1\nbundles:\n  - id: other\n    title: Other Bundle\n",
    )
    assert load_bundle_title_for_bundle_id(d2_repo, "missing") == "", (
        "D2: catalog present, target bundle id `'missing'` not in list -> "
        "loop exits with no match -> `_bundle_entry_for_id` returns None "
        "-> title returns `''`. Cross-cut with fo21's "
        "`test_load_bundle_title_for_bundle_id_repo_catalog` "
        "(`unknown-bundle-xyz` against the real repo) but isolated to "
        "tmp_path so the test does not depend on the repo catalog shape"
    )

    d3_repo = tmp_path / "d3_title_key_missing"
    d3_repo.mkdir()
    _write_catalog(
        d3_repo,
        "version: 1\nbundles:\n  - id: titleless\n    tags: [a]\n",
    )
    assert load_bundle_title_for_bundle_id(d3_repo, "titleless") == "", (
        "D3: bundle entry exists without `title` key -> `b.get('title')` "
        "returns None -> `t is not None` guard at line 120 short-circuits "
        '-> `""`. Pins the no-title-key arm'
    )

    d4_repo = tmp_path / "d4_title_yaml_null"
    d4_repo.mkdir()
    _write_catalog(
        d4_repo,
        "version: 1\nbundles:\n  - id: nulled\n    title: null\n",
    )
    assert load_bundle_title_for_bundle_id(d4_repo, "nulled") == "", (
        "D4: explicit YAML `title: null` -> `b.get('title')` returns "
        "Python None -> `t is not None` guard at line 120 short-circuits "
        '-> `""`. **CRITICAL PIN**: without the `is not None` guard, '
        "`str(None).strip()` would return the literal string `'None'`, "
        "silently producing a misleading title. The guard catches None "
        "BEFORE the str() coercion runs"
    )

    d5_repo = tmp_path / "d5_title_whitespace_only"
    d5_repo.mkdir()
    _write_catalog(
        d5_repo,
        'version: 1\nbundles:\n  - id: ws_title\n    title: "   "\n',
    )
    assert load_bundle_title_for_bundle_id(d5_repo, "ws_title") == "", (
        "D5: `title: '   '` -> `t = '   '` is non-None -> "
        '`str(t).strip()` collapses to `""`. Pins the `.strip()` call '
        "at line 120 (a refactor dropping `.strip()` would surface the "
        "raw whitespace string `'   '` as a valid title)"
    )
