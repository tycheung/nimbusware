"""Scraper artifact retention composite."""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.scraper_artifacts import prune_scraper_artifacts


def _local_removed(*args: object, **kwargs: object) -> int:
    return int(prune_scraper_artifacts(*args, **kwargs)["local_removed"])  # type: ignore[arg-type]


_VALUE_ERROR_MSG = "max_age_days must be >= 1"


def _set_mtime(path: Path, *, days_ago: float) -> None:
    """Set the mtime (and atime) of ``path`` to ``days_ago`` days before now.

    Wraps the recurring ``os.utime`` + ``time.time()`` boilerplate so each
    axis stays focused on the contract rather than the time arithmetic.
    Used to construct stale files (``days_ago`` large) and freshly-cutoff
    files (``days_ago`` exactly equal to ``max_age_days``).
    """
    ts = time.time() - days_ago * 86400
    os.utime(path, (ts, ts))


def _set_mtime_to(path: Path, when: datetime) -> None:
    """Set ``path`` mtime to a precise UTC ``when`` (for cutoff boundary axes).

    Distinct from ``_set_mtime``: this one accepts an absolute datetime
    rather than a relative offset, so the cutoff-boundary axis can
    construct ``mtime == cutoff`` precisely (no clock drift between
    ``time.time()`` and the function's own ``datetime.now`` call).
    """
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def test_prune_scraper_artifacts_value_error_boundary_contract(tmp_path: Path) -> None:
    """Pin ``prune_scraper_artifacts`` ValueError boundary arm (5 axes).

    The function begins with a strict input guard at
    [scraper_artifacts.py:33-35](packages/nimbusware_orchestrator/scraper_artifacts.py):

    .. code-block:: python

        if max_age_days < 1:
            msg = "max_age_days must be >= 1"
            raise ValueError(msg)

    Pins both the rejected boundary (0 / negative) AND the smallest
    accepted value (1), AND the diagnostic message verbatim. A refactor
    that loosened the guard (e.g. ``< 0`` instead of ``< 1``) would
    silently accept ``max_age_days=0`` and behave as "delete everything"
    -- catastrophic for operators -- which axes A1 and A4 catch in
    combination.

    A1 / A2 / A3 / A4 / A5 axes pin distinct boundaries; combined they
    form a tight equivalence class around the ``>= 1`` invariant.
    """
    base = tmp_path / "base"

    with pytest.raises(ValueError) as exc_zero:
        prune_scraper_artifacts(base, max_age_days=0)
    assert str(exc_zero.value) == _VALUE_ERROR_MSG, (
        "A1: max_age_days=0 is just below the valid range -> ValueError "
        "with exact message; a refactor loosening the guard to `< 0` "
        f"would accept 0 and silently delete EVERYTHING. Got: {exc_zero.value!s}"
    )

    with pytest.raises(ValueError) as exc_neg_one:
        prune_scraper_artifacts(base, max_age_days=-1)
    assert str(exc_neg_one.value) == _VALUE_ERROR_MSG, (
        "A2: max_age_days=-1 single negative -> ValueError; distinct from "
        "A1 because a refactor that special-cased only 0 (e.g. `if "
        "max_age_days == 0`) would accept -1 here"
    )

    with pytest.raises(ValueError) as exc_neg_large:
        prune_scraper_artifacts(base, max_age_days=-100)
    assert str(exc_neg_large.value) == _VALUE_ERROR_MSG, (
        "A3: max_age_days=-100 large negative -> ValueError; together "
        "with A2 pins that ALL negatives reject (catches an off-by-one "
        "or sign-magnitude regression)"
    )

    assert _local_removed(base, max_age_days=1) == 0, (
        "A4: max_age_days=1 is the smallest accepted value -- function "
        "proceeds past the guard; with base_dir absent the next short-"
        "circuit at line 36-37 returns 0. Together with A1 pins the "
        "tight `>= 1` boundary"
    )

    with pytest.raises(ValueError) as exc_msg:
        prune_scraper_artifacts(base, max_age_days=0)
    assert str(exc_msg.value) == _VALUE_ERROR_MSG, (
        "A5: ValueError message must be EXACTLY 'max_age_days must be >= 1' "
        "verbatim (no trailing dot, no operator-name shift). A refactor "
        f"rewording the message would surface here. Got: {exc_msg.value!s}"
    )


def test_prune_scraper_artifacts_nested_and_cutoff_contract(tmp_path: Path) -> None:
    """Pin nested ``rglob`` + mixed stale/fresh + cutoff inclusive + ``now=None`` (5 axes).

    The traversal at
    [scraper_artifacts.py:40](packages/nimbusware_orchestrator/scraper_artifacts.py)
    uses ``base_dir.rglob("*")`` (recursive) so files at any depth must
    be reachable. The cutoff comparison at line 45 uses
    ``mtime >= cutoff`` -> preserve, ``<`` -> remove (strict inclusive
    boundary). The ``now`` parameter at line 38 defaults to
    ``datetime.now(timezone.utc)`` via ``now or ...``.

    Pins 5 sub-contracts:

    * **B1** -- 2-deep nested subdirs across different run_ids: every
      stale file in any subdir is removed (rglob recursive).
    * **B2** -- mixed stale + fresh in the same dir: only the stale
      file is removed; the fresh file remains.
    * **B3** -- a 3-deep nested stale file is also removed (proof
      against a single-level ``iterdir`` refactor).
    * **B4** -- cutoff inclusive boundary: a file with
      ``mtime == cutoff`` is preserved (``>=`` not ``>``); a file
      with ``mtime`` 1 microsecond before cutoff is removed.
    * **B5** -- ``now=None`` default: omit the kwarg, use stale and
      fresh fixtures, verify stale removed and fresh preserved.
    """
    base_b1 = tmp_path / "b1_nested"
    base_b1.mkdir()
    run_a = base_b1 / "run_a"
    run_a.mkdir()
    stale_a = run_a / "url00_aaaa.bin"
    stale_a.write_bytes(b"a")
    _set_mtime(stale_a, days_ago=10)
    run_b_sub = base_b1 / "run_b" / "sub"
    run_b_sub.mkdir(parents=True)
    stale_b = run_b_sub / "url00_bbbb.bin"
    stale_b.write_bytes(b"b")
    _set_mtime(stale_b, days_ago=10)
    now = datetime.now(timezone.utc)
    removed_b1 = _local_removed(base_b1, max_age_days=7, now=now)
    assert removed_b1 == 2, (
        f"B1: 2 stale files across 2 nested run_dirs -> removed==2, "
        f"got {removed_b1!r}; pins rglob recursion across siblings"
    )
    assert not stale_a.exists() and not stale_b.exists(), (
        "B1: both stale files actually removed from disk (proof against "
        "a count-only refactor that doesn't call unlink)"
    )

    base_b2 = tmp_path / "b2_mixed"
    base_b2.mkdir()
    run_dir = base_b2 / "run"
    run_dir.mkdir()
    stale_b2 = run_dir / "url00_stale.bin"
    stale_b2.write_bytes(b"old")
    _set_mtime(stale_b2, days_ago=10)
    fresh_b2 = run_dir / "url01_fresh.bin"
    fresh_b2.write_bytes(b"new")
    removed_b2 = _local_removed(base_b2, max_age_days=7, now=now)
    assert removed_b2 == 1, (
        f"B2: mixed stale+fresh in one dir -> only 1 removed, got "
        f"{removed_b2!r}; pins per-file mtime check (not per-dir)"
    )
    assert not stale_b2.exists(), "B2: stale file removed"
    assert fresh_b2.is_file(), (
        "B2: fresh file PRESERVED (proof that the cutoff check at line "
        "45 short-circuits BEFORE the unlink at line 48)"
    )

    base_b3 = tmp_path / "b3_deep"
    base_b3.mkdir()
    deep_dir = base_b3 / "a" / "b" / "c"
    deep_dir.mkdir(parents=True)
    stale_deep = deep_dir / "url00_deep.bin"
    stale_deep.write_bytes(b"deep")
    _set_mtime(stale_deep, days_ago=10)
    removed_b3 = _local_removed(base_b3, max_age_days=7, now=now)
    assert removed_b3 == 1, (
        f"B3: 3-deep nested stale file -> removed==1, got {removed_b3!r}; "
        "pins rglob iterates ALL descendants (catches a naive iterdir "
        "refactor that would miss this file)"
    )
    assert not stale_deep.exists(), "B3: 3-deep stale file removed"

    base_b4 = tmp_path / "b4_cutoff"
    base_b4.mkdir()
    run_dir_b4 = base_b4 / "run"
    run_dir_b4.mkdir()
    fixed_now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    cutoff = fixed_now - timedelta(days=7)
    at_cutoff = run_dir_b4 / "url00_at_cutoff.bin"
    at_cutoff.write_bytes(b"at")
    _set_mtime_to(at_cutoff, cutoff)
    just_before = run_dir_b4 / "url01_before_cutoff.bin"
    just_before.write_bytes(b"before")
    _set_mtime_to(just_before, cutoff - timedelta(seconds=1))
    removed_b4 = _local_removed(base_b4, max_age_days=7, now=fixed_now)
    assert removed_b4 == 1, (
        f"B4: cutoff inclusive boundary -- 1 file AT cutoff (preserved) "
        f"+ 1 file 1s before cutoff (removed) -> removed==1, got "
        f"{removed_b4!r}; pins `mtime >= cutoff` -> preserve. A refactor "
        "swapping to strict `>` would flip B4 to removed==2"
    )
    assert at_cutoff.is_file(), (
        "B4: file with mtime EXACTLY at cutoff is PRESERVED (>= cutoff "
        "branch at line 45-46 short-circuits via `continue`)"
    )
    assert not just_before.exists(), (
        "B4: file 1s before cutoff is removed (proof of strict `<` on "
        "the other side of the boundary)"
    )

    base_b5 = tmp_path / "b5_default_now"
    base_b5.mkdir()
    run_dir_b5 = base_b5 / "run"
    run_dir_b5.mkdir()
    stale_b5 = run_dir_b5 / "url00_old.bin"
    stale_b5.write_bytes(b"old")
    _set_mtime(stale_b5, days_ago=30)
    fresh_b5 = run_dir_b5 / "url01_new.bin"
    fresh_b5.write_bytes(b"new")
    removed_b5 = _local_removed(base_b5, max_age_days=7)
    assert removed_b5 == 1, (
        f"B5: `now=None` default -> internal `datetime.now(timezone.utc)` "
        f"-> 30-day-old file is stale at 7-day cutoff. removed==1, got "
        f"{removed_b5!r}; pins the `now or datetime.now(...)` fallback at "
        "line 38 (a refactor that required `now` to be passed would "
        "break the CLI script which calls without `now`)"
    )
    assert not stale_b5.exists(), "B5: stale file removed via default now"
    assert fresh_b5.is_file(), "B5: fresh file preserved via default now"


def test_prune_scraper_artifacts_cleanup_and_dry_run_divergence_contract(
    tmp_path: Path,
) -> None:
    """Pin empty-dir cleanup + dry_run divergence + OSError + ordering (5 axes).

    The second-pass cleanup at
    [scraper_artifacts.py:50-57](packages/nimbusware_orchestrator/scraper_artifacts.py):

    .. code-block:: python

        if dry_run:
            return removed
        for path in sorted(base_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass

    runs **only** in non-dry-run mode. The ``reverse=True`` sort means
    deepest paths come first so a fully-empty subtree collapses cleanly
    from leaves to root.

    Pins 5 sub-contracts:

    * **C1** -- non-dry-run removes the only stale file AND the
      now-empty run_dir.
    * **C2** -- dry_run=True returns the count but PRESERVES files AND
      empty-dir cleanup is skipped (run_dir survives).
    * **C3** -- OSError suppression: a run_dir containing a fresh
      file has the stale file removed, but rmdir on the non-empty
      run_dir raises ``OSError`` which is caught -> run_dir kept.
    * **C4** -- reverse-len ordering: 3-deep nested chain
      (``<base>/a/b/c/stale.bin``) -> after cleanup, every empty
      intermediate dir ``a``, ``b``, ``c`` is gone (forward-sort
      would try to rmdir ``a`` first which fails because ``b`` is
      still non-empty).
    * **C5** -- dry_run composite: two dry-run calls preserve state,
      a third non-dry-run call removes (idempotence of preview +
      irreversibility of action).
    """
    now = datetime.now(timezone.utc)

    base_c1 = tmp_path / "c1_cleanup"
    base_c1.mkdir()
    run_dir_c1 = base_c1 / "run"
    run_dir_c1.mkdir()
    stale_c1 = run_dir_c1 / "url00.bin"
    stale_c1.write_bytes(b"x")
    _set_mtime(stale_c1, days_ago=10)
    removed_c1 = _local_removed(base_c1, max_age_days=7, now=now)
    assert removed_c1 == 1
    assert not stale_c1.exists(), "C1: stale file removed"
    assert not run_dir_c1.is_dir(), (
        "C1: empty run_dir cleaned up by the second-pass loop at "
        "lines 52-57 (a refactor dropping that loop would leave "
        "stranded empty dirs)"
    )

    base_c2 = tmp_path / "c2_dry_run"
    base_c2.mkdir()
    run_dir_c2 = base_c2 / "run"
    run_dir_c2.mkdir()
    stale_c2 = run_dir_c2 / "url00.bin"
    stale_c2.write_bytes(b"x")
    _set_mtime(stale_c2, days_ago=10)
    removed_c2 = _local_removed(
        base_c2,
        max_age_days=7,
        now=now,
        dry_run=True,
    )
    assert removed_c2 == 1, "C2: dry_run counts as if removing"
    assert stale_c2.is_file(), (
        "C2: dry_run preserves the file (the `if not dry_run: unlink` guard at line 47-48)"
    )
    assert run_dir_c2.is_dir(), (
        "C2: dry_run SKIPS empty-dir cleanup via the line 50-51 early "
        "return; a refactor that re-runs the cleanup pass for dry_run "
        "would silently delete empty dirs in preview mode"
    )

    base_c3 = tmp_path / "c3_oserror"
    base_c3.mkdir()
    run_dir_c3 = base_c3 / "run"
    run_dir_c3.mkdir()
    stale_c3 = run_dir_c3 / "url00_stale.bin"
    stale_c3.write_bytes(b"x")
    _set_mtime(stale_c3, days_ago=10)
    fresh_c3 = run_dir_c3 / "url01_fresh.bin"
    fresh_c3.write_bytes(b"y")
    removed_c3 = _local_removed(base_c3, max_age_days=7, now=now)
    assert removed_c3 == 1, "C3: only stale removed"
    assert not stale_c3.exists()
    assert fresh_c3.is_file(), "C3: fresh file preserved"
    assert run_dir_c3.is_dir(), (
        "C3: rmdir on non-empty run_dir raises OSError (ENOTEMPTY) "
        "which is caught at line 56-57 via `pass`. The dir survives. "
        "A refactor that re-raised OSError would surface here as an "
        "unhandled exception bubble"
    )

    base_c4 = tmp_path / "c4_ordering"
    base_c4.mkdir()
    deep = base_c4 / "a" / "b" / "c"
    deep.mkdir(parents=True)
    stale_c4 = deep / "url00.bin"
    stale_c4.write_bytes(b"x")
    _set_mtime(stale_c4, days_ago=10)
    removed_c4 = _local_removed(base_c4, max_age_days=7, now=now)
    assert removed_c4 == 1
    assert not (base_c4 / "a" / "b" / "c").is_dir(), (
        "C4: deepest empty dir removed first via reverse-len sort"
    )
    assert not (base_c4 / "a" / "b").is_dir(), "C4: middle dir removed AFTER its child was removed"
    assert not (base_c4 / "a").is_dir(), (
        "C4: top-level intermediate dir also cleaned up; the entire "
        "empty subtree collapses leaves-to-root. A forward-sort would "
        "fail to remove `a` first (still has `b/c` under it) and the "
        "`except OSError: pass` would skip it permanently"
    )
    assert base_c4.is_dir(), (
        "C4 control: base_c4 itself is NOT removed (the loop scopes "
        "to descendants via rglob; `base_c4` is not in the iteration set "
        "because rglob('*') excludes the root itself)"
    )

    base_c5 = tmp_path / "c5_idempotent_dry_run"
    base_c5.mkdir()
    run_dir_c5 = base_c5 / "run"
    run_dir_c5.mkdir()
    stale_c5 = run_dir_c5 / "url00.bin"
    stale_c5.write_bytes(b"x")
    _set_mtime(stale_c5, days_ago=10)
    for _ in range(2):
        removed_dry = _local_removed(
            base_c5,
            max_age_days=7,
            now=now,
            dry_run=True,
        )
        assert removed_dry == 1, "C5: dry_run idempotent count"
        assert stale_c5.is_file(), (
            "C5: dry_run preserves across REPEATED calls (proof that "
            "no state mutation leaks via shared rglob iteration)"
        )
    removed_real = _local_removed(base_c5, max_age_days=7, now=now)
    assert removed_real == 1
    assert not stale_c5.exists(), (
        "C5: non-dry-run finally removes -- pins the divergence is "
        "binary (dry_run=True N times then dry_run=False once === one "
        "real removal, NOT N+1)"
    )


def test_persist_scraper_response_artifact_value_error_fallback_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin ``_persist_scraper_response_artifact`` ValueError fallback (5 axes).

    Source at
    [pipeline.py:288-291](packages/nimbusware_orchestrator/pipeline.py):

    .. code-block:: python

        try:
            rel = out_path.relative_to(base_dir)
        except ValueError:
            rel = Path(fname)

    The happy fo101 matrix in
    [tests/test_scraper_pure_helpers_edges_contract.py:204-295](tests/test_scraper_pure_helpers_edges_contract.py)
    only exercises the try branch. fo110 Part D pins the fallback by
    patching ``Path.relative_to`` to raise ``ValueError`` -- the file
    is still written to its real on-disk location (write happens
    BEFORE the try/except) but the returned ``artifact_relpath`` drops
    the ``<run_id>/`` prefix and becomes a bare filename.

    Pins 5 sub-contracts:

    * **D1** -- bare-filename relpath: NO ``<run_id>/`` prefix.
    * **D2** -- file still written at real on-disk location
      (``<base>/<run_id>/<fname>``).
    * **D3** -- ``artifact_sha256`` unchanged (sha256 of blob is
      independent of the relative_to result).
    * **D4** -- ``artifact_bytes_written`` unchanged.
    * **D5** -- ``str(rel).replace("\\\\", "/")`` normalization chain
      still runs (vacuous on bare filename but verified to never
      raise); plus a control comparison vs the happy path that pins
      the divergence is SOLELY in the relpath shape.
    """
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_DIR", str(tmp_path))
    orch, _ = make_dev_orchestrator()
    base_dir = Path(str(tmp_path)).expanduser().resolve()

    run_id = uuid4()
    content = b"hello world payload"
    persist_cap = 1024
    expected_digest_full = hashlib.sha256(content).hexdigest()
    expected_fname = f"url05_{expected_digest_full[:32]}.bin"

    happy = orch._persist_scraper_response_artifact(  # noqa: SLF001
        run_id,
        5,
        content,
        persist_cap,
    )

    original_relative_to = Path.relative_to

    def _raise_value_error(self: Path, *args: object, **kwargs: object) -> Path:
        msg = "fo110 forced fallback"
        raise ValueError(msg)

    run_id_fb = uuid4()
    expected_fname_fb = f"url05_{expected_digest_full[:32]}.bin"
    with patch.object(Path, "relative_to", _raise_value_error):
        fallback = orch._persist_scraper_response_artifact(  # noqa: SLF001
            run_id_fb,
            5,
            content,
            persist_cap,
        )
    assert Path.relative_to is original_relative_to, (
        "D control: patch.object scope-restored Path.relative_to after the `with` block exited"
    )

    assert fallback["artifact_relpath"] == expected_fname_fb, (
        "D1: fallback `artifact_relpath` is the BARE filename "
        f"{expected_fname_fb!r} with NO `<run_id>/` prefix (pins "
        "`rel = Path(fname)` at line 290-291). A refactor that dropped "
        "the try/except would propagate ValueError to callers and this "
        f"axis would surface as an unhandled exception. Got: "
        f"{fallback['artifact_relpath']!r}"
    )
    assert str(run_id_fb) not in fallback["artifact_relpath"], (
        "D1 cross-cut: the run_id specifically must NOT appear in the "
        f"fallback relpath ({fallback['artifact_relpath']!r}); pins that "
        "the fallback uses `Path(fname)` (no parent) NOT a partial "
        "relative_to via some other branch"
    )

    on_disk_fb = base_dir / str(run_id_fb) / expected_fname_fb
    assert on_disk_fb.is_file(), (
        f"D2: file still written to its REAL on-disk location "
        f"{on_disk_fb!s} despite the fallback metadata. Pins that "
        "`out_path.write_bytes(blob)` at line 286 happens BEFORE the "
        "try/except at line 288-291 so the write succeeds even when "
        "relative_to fails. A refactor that moved the write after the "
        "try/except would break D2 silently"
    )
    assert on_disk_fb.read_bytes() == content, (
        "D2 cross-cut: file contents match the input (full content "
        "since under persist_cap); pins write succeeds with correct bytes"
    )

    assert fallback["artifact_sha256"] == happy["artifact_sha256"], (
        "D3: artifact_sha256 invariant -- identical input bytes "
        "produce identical sha256 across happy + fallback paths "
        "(sha256(blob) at line 287 is computed BEFORE try/except). "
        f"Got happy={happy['artifact_sha256']!r} vs "
        f"fallback={fallback['artifact_sha256']!r}"
    )
    expected_digest_blob = hashlib.sha256(content).hexdigest()
    assert fallback["artifact_sha256"] == expected_digest_blob, (
        "D3 cross-cut: fallback sha256 equals sha256(blob) explicit "
        "calculation (pins the digest formula itself, not just "
        "happy/fallback equality)"
    )

    assert fallback["artifact_bytes_written"] == happy["artifact_bytes_written"], (
        "D4: artifact_bytes_written invariant -- same input -> same "
        "byte count across happy + fallback (len(blob) at line 295 "
        "is independent of the relative_to result). Got "
        f"happy={happy['artifact_bytes_written']!r} vs "
        f"fallback={fallback['artifact_bytes_written']!r}"
    )
    assert fallback["artifact_bytes_written"] == len(content), (
        "D4 cross-cut: under-cap content -> bytes_written == len(content)"
    )

    assert "\\" not in fallback["artifact_relpath"], (
        "D5: forward-slash normalization `str(rel).replace('\\\\', '/')` "
        "at line 293 runs unconditionally; even though Path(fname) for "
        "a bare filename has no separators, the replace chain still "
        "executes and produces a backslash-free string. Pins the "
        "normalization is not gated on the try branch"
    )
    assert fallback["artifact_relpath"] != happy["artifact_relpath"], (
        f"D5 cross-cut (divergence proof): happy "
        f"{happy['artifact_relpath']!r} differs from fallback "
        f"{fallback['artifact_relpath']!r} (one has `<run_id>/`, the "
        "other doesn't). Pins the ValueError fallback IS the only "
        "place the relpath shape changes; all other return fields are "
        "invariant (D3 + D4)"
    )
    assert happy["artifact_relpath"].endswith("/" + expected_fname), (
        f"D5 control: happy-path relpath ends with `/<fname>` (proof "
        f"that the run_id segment is the ONLY structural difference vs "
        f"fallback). Got happy={happy['artifact_relpath']!r}, expected "
        f"suffix `/{expected_fname}`"
    )
