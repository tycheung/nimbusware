"""Library-level tests for ``prune_scraper_artifacts`` pattern filters."""

from __future__ import annotations

import os
import time
from pathlib import Path

from nimbusware_orchestrator.scraper_artifacts import (
    _matches_any,
    prune_scraper_artifacts,
)


def _local_removed(*args: object, **kwargs: object) -> int:
    return int(prune_scraper_artifacts(*args, **kwargs)["local_removed"])  # type: ignore[arg-type]


def _seed(base: Path, names: list[str], *, stale: bool) -> None:
    """Create files in ``base`` with the given basenames; set mtime to 10 days ago when stale."""
    base.mkdir(parents=True, exist_ok=True)
    for name in names:
        p = base / name
        p.write_bytes(b"x")
        if stale:
            old = time.time() - 10 * 86400
            os.utime(p, (old, old))


def _surviving_basenames(base: Path) -> set[str]:
    return {p.name for p in base.iterdir() if p.is_file()}


# _matches_any helper


def test_matches_any_handles_none_and_empty_list() -> None:
    assert _matches_any("foo.bin", None) is False
    assert _matches_any("foo.bin", []) is False
    assert _matches_any("foo.bin", ["*.bin"]) is True
    assert _matches_any("foo.txt", ["*.bin"]) is False
    # Repeated patterns OR together
    assert _matches_any("foo.txt", ["*.bin", "*.txt"]) is True


# prune_scraper_artifacts pattern filters


def test_include_pattern_alone_only_matches_subset(tmp_path: Path) -> None:
    """``include_patterns`` restricts the deletion set; non-matches stay on disk."""
    base = tmp_path / "nimbusware_scraper"
    _seed(base, ["url00.bin", "url01.bin", "meta.txt", "log.json"], stale=True)
    pruned = _local_removed(
        base,
        max_age_days=7,
        include_patterns=["*.bin"],
    )
    assert pruned == 2
    assert _surviving_basenames(base) == {"meta.txt", "log.json"}


def test_exclude_pattern_alone_preserves_matches(tmp_path: Path) -> None:
    """``exclude_patterns`` removes matches from the deletion set; rest is deleted."""
    base = tmp_path / "nimbusware_scraper"
    _seed(base, ["url00.bin", "url00.keep", "url01.bin"], stale=True)
    pruned = _local_removed(
        base,
        max_age_days=7,
        exclude_patterns=["*.keep"],
    )
    assert pruned == 2
    assert _surviving_basenames(base) == {"url00.keep"}


def test_exclude_wins_over_include_on_overlap(tmp_path: Path) -> None:
    """When a file matches BOTH lists, exclude takes precedence (documented contract)."""
    base = tmp_path / "nimbusware_scraper"
    _seed(base, ["url00.bin", "pinned.bin", "url01.bin", "data.txt"], stale=True)
    pruned = _local_removed(
        base,
        max_age_days=7,
        include_patterns=["*.bin"],
        exclude_patterns=["pinned.*"],
    )
    assert pruned == 2  # url00.bin and url01.bin
    assert _surviving_basenames(base) == {"pinned.bin", "data.txt"}


def test_empty_list_behaves_like_none(tmp_path: Path) -> None:
    """``[]`` ⇒ no filter, matching ``None`` semantics (argparse ``action='append'`` ergonomics)."""
    base = tmp_path / "nimbusware_scraper"
    _seed(base, ["url00.bin", "meta.txt"], stale=True)
    pruned = _local_removed(
        base,
        max_age_days=7,
        include_patterns=[],
        exclude_patterns=[],
    )
    assert pruned == 2
    assert _surviving_basenames(base) == set()


def test_patterns_evaluated_after_mtime_cutoff(tmp_path: Path) -> None:
    """A fresh file matching ``include_pattern`` MUST NOT be deleted (mtime gate first)."""
    base = tmp_path / "nimbusware_scraper"
    _seed(base, ["stale.bin"], stale=True)
    _seed(base, ["fresh.bin"], stale=False)
    pruned = _local_removed(
        base,
        max_age_days=7,
        include_patterns=["*.bin"],
    )
    assert pruned == 1
    assert _surviving_basenames(base) == {"fresh.bin"}


def test_backward_compat_no_pattern_args(tmp_path: Path) -> None:
    """Calling without the fo125 kwargs preserves the pre-fo125 4-arg signature behaviour."""
    base = tmp_path / "nimbusware_scraper"
    _seed(base, ["url00.bin", "meta.txt"], stale=True)
    pruned = _local_removed(base, max_age_days=7)
    assert pruned == 2
    assert _surviving_basenames(base) == set()
