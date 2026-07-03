from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.scraper_artifacts import resolve_scraper_artifact_base_dir

_ENV_NAME = "NIMBUSWARE_SCRAPER_ARTIFACT_DIR"
_DEFAULT_REL = (".cache", "nimbusware_scraper")


def _default_for(repo_root: Path) -> Path:
    """Return the canonical default ``base_dir`` for ``repo_root``.

    Mirrors the production fallthrough expression
    ``(repo_root / ".cache" / "nimbusware_scraper").resolve()`` and is the
    single source of truth for Parts B and C so a refactor that renames
    ``.cache/nimbusware_scraper`` surfaces as a per-block assertion failure.
    """
    return repo_root.joinpath(*_DEFAULT_REL).resolve()


def test_scraper_artifact_dir_env_accept_arm_passthrough_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #10 truthy-env accept arm: passthrough + ``.strip()`` rescue.

    Restricted to the **accept arm** (``if raw:`` branch) with canonical
    absolute paths so each case exercises the passthrough +
    normalization combo cleanly. Pattern A asymmetry, normalization on
    ``~`` / ``..``, and literal-path-no-parsing variants are pinned in
    Part C (which targets the normalization layer specifically) so
    Part A stays focused on the basic accept-arm shape.

    Pins 4 sub-contracts:

    1. **Passthrough** -- env-value reaches ``Path(raw)`` unchanged
       after ``.strip()``.
    2. **`.strip()` rescue** -- whitespace-padded canonical accepted
       (KEY: distinct from fo65-70 where ``.strip()`` is NOT applied;
       aligned with fo71-73).
    3. **`.resolve()` applied** -- result is absolute (catches
       refactors that drop ``.resolve()``).
    4. **Return type** -- concrete ``Path`` (catches refactors
       returning ``str``).
    """
    art = tmp_path / "art"
    nested = tmp_path / "a" / "b" / "c"
    cases: list[tuple[str, str, Path]] = [
        ("canon_absolute", str(art), art.resolve()),
        ("canon_nested", str(nested), nested.resolve()),
        ("ws_padded_ascii", f"  {art}  ", art.resolve()),
        ("ws_tab_lf", f"\t{art}\n", art.resolve()),
        ("ws_leading", f" {art}", art.resolve()),
        ("ws_trailing", f"{art} ", art.resolve()),
        ("ws_nested_padded", f"  {nested}  ", nested.resolve()),
    ]
    for _name, raw, expected in cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = resolve_scraper_artifact_base_dir(tmp_path)
        assert result == expected, f"accept raw={raw!r}: expected {expected}, got {result}"
        assert isinstance(result, Path), (
            f"accept raw={raw!r}: result type {type(result).__name__} (should be Path)"
        )
        assert result.is_absolute(), (
            f"accept raw={raw!r}: .resolve() should produce absolute path, got {result}"
        )


def test_scraper_artifact_dir_env_default_fallthrough_convergence_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #10 default-fallthrough multi-path convergence.

    The sharpest fo74 part -- mirror of fo73 Part B's three-path
    floor-convergence applied to the default-fallthrough branch. Five
    blocks pin the multi-path convergence on
    ``(repo_root / ".cache" / "nimbusware_scraper").resolve()``:

    * **Block 1 -- env-absent path:** ``os.environ.get(..., "")``
      default-arg supplies the empty string.
    * **Block 2 -- env-explicit-empty path:** distinguishable from
      Block 1 only at the OS layer; both converge inside the function
      at ``raw == ""`` post-strip.
    * **Block 3 -- `.strip()`-collapse-to-empty path** (whitespace-only
      inputs): KEY DIVERGENCE -- a refactor removing ``.strip()`` would
      make ``"   "`` truthy (non-empty string) and silently flow into
      the accept arm producing ``Path("   ").resolve()`` = ``<cwd>/   ``
      (a directory with literal whitespace in its name).
    * **Block 4 -- ``repo_root`` plumbing arm:** pins that the default
      uses the **passed `repo_root` argument** rather than a
      module-level constant or ``Path.cwd()``. A refactor that
      hardcoded the default would silently ignore the argument.
    * **Block 5 -- default `.resolve()` applied:** pins that the
      default branch ALSO normalizes ``..`` components -- catches
      refactors that drop the trailing ``.resolve()`` on the default
      branch specifically (the accept arm's ``.resolve()`` is pinned
      in Part C Block 2).
    """
    monkeypatch.delenv(_ENV_NAME, raising=False)
    result = resolve_scraper_artifact_base_dir(tmp_path)
    expected = _default_for(tmp_path)
    assert result == expected, f"env_absent raw=delenv: expected {expected}, got {result}"
    assert isinstance(result, Path) and result.is_absolute(), (
        f"env_absent raw=delenv: type/absolute check failed for {result}"
    )

    monkeypatch.setenv(_ENV_NAME, "")
    result = resolve_scraper_artifact_base_dir(tmp_path)
    assert result == expected, f"env_explicit_empty raw='': expected {expected}, got {result}"
    assert isinstance(result, Path) and result.is_absolute(), (
        f"env_explicit_empty raw='': type/absolute check failed for {result}"
    )

    strip_collapse_cases: list[str] = ["   ", "\t\n", " ", "\t", "\n"]
    for raw in strip_collapse_cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = resolve_scraper_artifact_base_dir(tmp_path)
        assert result == expected, (
            f"strip_collapse raw={raw!r}: expected {expected} via "
            f".strip()-reduces-to-empty fallthrough, got {result}"
        )
        assert isinstance(result, Path) and result.is_absolute(), (
            f"strip_collapse raw={raw!r}: type/absolute check failed for {result}"
        )

    monkeypatch.delenv(_ENV_NAME, raising=False)
    alt_root = tmp_path / "alt_root"
    result = resolve_scraper_artifact_base_dir(alt_root)
    expected_alt = _default_for(alt_root)
    assert result == expected_alt, (
        f"repo_root_plumbing: expected {expected_alt} (uses passed repo_root), got {result}"
    )
    assert isinstance(result, Path) and result.is_absolute(), (
        f"repo_root_plumbing: type/absolute check failed for {result}"
    )

    dotdot_root = tmp_path / "a" / ".." / "b"
    result = resolve_scraper_artifact_base_dir(dotdot_root)
    expected_dotdot = (tmp_path / "b").joinpath(*_DEFAULT_REL).resolve()
    assert result == expected_dotdot, (
        f"default_resolve repo_root={dotdot_root}: expected "
        f"{expected_dotdot} via default-branch .resolve() collapsing "
        f"'..', got {result}"
    )
    assert isinstance(result, Path) and result.is_absolute(), (
        f"default_resolve repo_root={dotdot_root}: type/absolute check failed for {result}"
    )


def test_scraper_artifact_dir_env_normalization_and_literal_path_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #10 ``.expanduser()`` + ``.resolve()`` + literal-path no-parsing.

    Locks two distinct contract families in five blocks:

    * **Normalization layer** (Blocks 1-3) -- the accept-arm chain
      ``Path(raw).expanduser().resolve()`` exercises each link.
    * **Literal-path no-parsing** (Blocks 4-5) -- the string
      passthrough subtype's defining contract: any string-like input
      becomes a valid ``Path`` without any semantic interpretation.

    Block-level breakdown:

    * **Block 1 -- ``~`` expansion via ``.expanduser()``:** a refactor
      dropping ``.expanduser()`` would return
      ``Path("~/...").resolve()`` which on POSIX/Windows resolves to
      ``<cwd>/~/...`` (literal ``~`` in the path).
    * **Block 2 -- ``..`` traversal normalized via ``.resolve()``:**
      catches a refactor that drops ``.resolve()`` on the truthy arm
      (Part B Block 5 pins the same call on the default arm).
    * **Block 3 -- relative path resolved against CWD:** pins the
      implicit CWD anchoring done by ``.resolve()`` on a bare relative
      string.
    * **Block 4 -- Pattern A truthy tokens as literal subdirectory
      names (ASYMMETRY catch):** A refactor that adds a truthy-tuple
      short-circuit (e.g. ``if raw.lower() in ("1","true","yes"):
      return alt_default``) would silently flip these from
      "subdirectory named `true`" to "default cache dir" -- the
      ``result.name == raw`` assertion catches it precisely.
    * **Block 5 -- numeric strings + junk as literal paths (no
      parsing, no fail-mode):** Pins that no ``int()`` / ``float()``
      parsing is applied (which would have raised in fo72 or swallowed
      in fo73), confirming the string-passthrough subtype.
    """
    home_subdir = "scraper_art_fo74_test"
    monkeypatch.setenv(_ENV_NAME, f"~/{home_subdir}")
    result = resolve_scraper_artifact_base_dir(tmp_path)
    expected_home = (Path.home() / home_subdir).resolve()
    assert result == expected_home, (
        f"expanduser raw='~/{home_subdir}': expected {expected_home} "
        f"via .expanduser() expansion, got {result}"
    )
    assert isinstance(result, Path) and result.is_absolute(), (
        f"expanduser: type/absolute check failed for {result}"
    )

    dotdot_raw = str(tmp_path / "a" / ".." / "b")
    monkeypatch.setenv(_ENV_NAME, dotdot_raw)
    result = resolve_scraper_artifact_base_dir(tmp_path)
    expected_dotdot = (tmp_path / "b").resolve()
    assert result == expected_dotdot, (
        f"dotdot_normalize raw={dotdot_raw!r}: expected "
        f"{expected_dotdot} via .resolve() collapsing '..', got "
        f"{result}"
    )
    assert isinstance(result, Path) and result.is_absolute(), (
        f"dotdot_normalize: type/absolute check failed for {result}"
    )

    rel_name = "scraper_art_rel"
    monkeypatch.setenv(_ENV_NAME, rel_name)
    result = resolve_scraper_artifact_base_dir(tmp_path)
    expected_rel = (Path.cwd() / rel_name).resolve()
    assert result == expected_rel, (
        f"relative_cwd raw={rel_name!r}: expected {expected_rel} via "
        f".resolve() anchoring against CWD, got {result}"
    )
    assert isinstance(result, Path) and result.is_absolute(), (
        f"relative_cwd: type/absolute check failed for {result}"
    )

    pattern_a_cases: list[str] = ["true", "yes", "on", "TRUE", "1", "YES"]
    for raw in pattern_a_cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = resolve_scraper_artifact_base_dir(tmp_path)
        expected_literal = (Path.cwd() / raw).resolve()
        assert result == expected_literal, (
            f"pattern_a_literal raw={raw!r}: expected "
            f"{expected_literal} (literal subdir, NOT binary signal), "
            f"got {result}"
        )
        assert result.name == raw, (
            f"pattern_a_literal raw={raw!r}: result.name should equal "
            f"raw token (ASYMMETRY vs fo65-70 Pattern A binary gates), "
            f"got {result.name!r}"
        )
        assert isinstance(result, Path) and result.is_absolute(), (
            f"pattern_a_literal raw={raw!r}: type/absolute check failed for {result}"
        )

    literal_cases: list[str] = ["5", "5.5", "abc", "1e2", "5x"]
    for raw in literal_cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = resolve_scraper_artifact_base_dir(tmp_path)
        expected_literal = (Path.cwd() / raw).resolve()
        assert result == expected_literal, (
            f"literal_path raw={raw!r}: expected {expected_literal} "
            f"(no int()/float() parsing, no fail-mode), got {result}"
        )
        assert isinstance(result, Path) and result.is_absolute(), (
            f"literal_path raw={raw!r}: type/absolute check failed for {result}"
        )
