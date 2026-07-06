from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.scraper.artifacts import prune_scraper_artifacts
from unit.composite_contract_fixtures import set_mtime_days_ago, set_mtime_to

VALUE_ERROR_MSG = "max_age_days must be >= 1"

PERSIST_CONTENT = b"hello world payload"
PERSIST_CAP = 1024
PERSIST_URL_INDEX = 5


def local_removed(*args: object, **kwargs: object) -> int:
    return int(prune_scraper_artifacts(*args, **kwargs)["local_removed"])  # type: ignore[arg-type]


def _write_file(base: Path, spec: dict[str, Any], *, fixed_now: datetime | None) -> None:
    path = base / spec["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(spec.get("content", b"x"))
    if "days_ago" in spec:
        set_mtime_days_ago(path, days_ago=spec["days_ago"])
    elif spec.get("at_cutoff") and fixed_now is not None:
        max_age = spec.get("max_age_days", 7)
        cutoff = fixed_now - timedelta(days=max_age)
        set_mtime_to(path, cutoff)
    elif spec.get("before_cutoff_secs") and fixed_now is not None:
        max_age = spec.get("max_age_days", 7)
        cutoff = fixed_now - timedelta(days=max_age)
        set_mtime_to(path, cutoff - timedelta(seconds=spec["before_cutoff_secs"]))


def setup_prune_case(tmp_path: Path, case: dict[str, Any]) -> tuple[Path, datetime | None]:
    base = tmp_path / case["case_id"]
    base.mkdir()
    fixed_now = case.get("fixed_now")
    if case.get("shared_now"):
        fixed_now = datetime.now(timezone.utc)
    max_age = case.get("max_age_days", 7)
    for spec in case.get("files", ()):
        file_spec = dict(spec)
        file_spec.setdefault("max_age_days", max_age)
        _write_file(base, file_spec, fixed_now=fixed_now)
    return base, fixed_now


def invoke_prune(case: dict[str, Any], base: Path, now: datetime | None) -> int:
    kwargs: dict[str, Any] = {"max_age_days": case["max_age_days"]}
    if now is not None:
        kwargs["now"] = now
    if case.get("dry_run"):
        kwargs["dry_run"] = True
    return local_removed(base, **kwargs)


def validate_prune_case(
    case: dict[str, Any],
    base: Path,
    removed: int,
    *,
    now: datetime | None,
    dry_run: bool = False,
) -> None:
    case_id = case["case_id"]
    assert removed == case["expected_removed"], (
        f"{case_id}: expected removed {case['expected_removed']!r}, got {removed!r}"
    )
    if not dry_run:
        for rel in case.get("must_not_exist", ()):
            assert not (base / rel).exists(), f"{case_id}: {rel!r} should not exist"
    for rel in case.get("must_exist_files", ()):
        assert (base / rel).is_file(), f"{case_id}: {rel!r} should remain a file"
    if not dry_run:
        for rel in case.get("must_not_exist_dirs", ()):
            assert not (base / rel).is_dir(), f"{case_id}: dir {rel!r} should be removed"
    for rel in case.get("must_exist_dirs", ()):
        assert (base / rel).is_dir(), f"{case_id}: dir {rel!r} should remain"
    if case.get("base_must_exist"):
        assert base.is_dir(), f"{case_id}: base dir must remain"


def run_prune_case(tmp_path: Path, case: dict[str, Any]) -> None:
    base, now = setup_prune_case(tmp_path, case)
    if case.get("dry_run_repeats"):
        for _ in range(case["dry_run_repeats"]):
            removed = invoke_prune({**case, "dry_run": True}, base, now)
            validate_prune_case(case, base, removed, now=now, dry_run=True)
        if case.get("then_real_run"):
            removed = invoke_prune({**case, "dry_run": False}, base, now)
            assert removed == case["expected_removed"], case["case_id"]
            for rel in case.get("must_not_exist", ()):
                assert not (base / rel).exists(), f"{case['case_id']}: {rel!r} should not exist"
        return
    removed = invoke_prune(case, base, now)
    validate_prune_case(case, base, removed, now=now, dry_run=bool(case.get("dry_run")))


PRUNE_MAX_AGE_EXCEPTION_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "a1_zero", "max_age_days": 0, "msg_equals": VALUE_ERROR_MSG},
    {"case_id": "a2_neg_one", "max_age_days": -1, "msg_equals": VALUE_ERROR_MSG},
    {"case_id": "a3_neg_large", "max_age_days": -100, "msg_equals": VALUE_ERROR_MSG},
    {"case_id": "a5_msg_exact", "max_age_days": 0, "msg_equals": VALUE_ERROR_MSG},
)

PRUNE_MAX_AGE_VALUE_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "a4_min_valid", "max_age_days": 1, "expected": 0},
)

PRUNE_NESTED_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "b1_nested",
        "files": [
            {"path": "run_a/url00_aaaa.bin", "content": b"a", "days_ago": 10},
            {"path": "run_b/sub/url00_bbbb.bin", "content": b"b", "days_ago": 10},
        ],
        "max_age_days": 7,
        "shared_now": True,
        "expected_removed": 2,
        "must_not_exist": ["run_a/url00_aaaa.bin", "run_b/sub/url00_bbbb.bin"],
    },
    {
        "case_id": "b2_mixed",
        "files": [
            {"path": "run/url00_stale.bin", "content": b"old", "days_ago": 10},
            {"path": "run/url01_fresh.bin", "content": b"new"},
        ],
        "max_age_days": 7,
        "shared_now": True,
        "expected_removed": 1,
        "must_not_exist": ["run/url00_stale.bin"],
        "must_exist_files": ["run/url01_fresh.bin"],
    },
    {
        "case_id": "b3_deep",
        "files": [{"path": "a/b/c/url00_deep.bin", "content": b"deep", "days_ago": 10}],
        "max_age_days": 7,
        "shared_now": True,
        "expected_removed": 1,
        "must_not_exist": ["a/b/c/url00_deep.bin"],
    },
    {
        "case_id": "b4_cutoff",
        "fixed_now": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        "files": [
            {"path": "run/url00_at_cutoff.bin", "content": b"at", "at_cutoff": True},
            {"path": "run/url01_before_cutoff.bin", "content": b"before", "before_cutoff_secs": 1},
        ],
        "max_age_days": 7,
        "expected_removed": 1,
        "must_exist_files": ["run/url00_at_cutoff.bin"],
        "must_not_exist": ["run/url01_before_cutoff.bin"],
    },
    {
        "case_id": "b5_default_now",
        "files": [
            {"path": "run/url00_old.bin", "content": b"old", "days_ago": 30},
            {"path": "run/url01_new.bin", "content": b"new"},
        ],
        "max_age_days": 7,
        "expected_removed": 1,
        "must_not_exist": ["run/url00_old.bin"],
        "must_exist_files": ["run/url01_new.bin"],
    },
)

PRUNE_CLEANUP_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "c1_cleanup",
        "files": [{"path": "run/url00.bin", "days_ago": 10}],
        "max_age_days": 7,
        "shared_now": True,
        "expected_removed": 1,
        "must_not_exist": ["run/url00.bin"],
        "must_not_exist_dirs": ["run"],
    },
    {
        "case_id": "c2_dry_run",
        "files": [{"path": "run/url00.bin", "days_ago": 10}],
        "max_age_days": 7,
        "shared_now": True,
        "dry_run": True,
        "expected_removed": 1,
        "must_exist_files": ["run/url00.bin"],
        "must_exist_dirs": ["run"],
    },
    {
        "case_id": "c3_oserror",
        "files": [
            {"path": "run/url00_stale.bin", "content": b"x", "days_ago": 10},
            {"path": "run/url01_fresh.bin", "content": b"y"},
        ],
        "max_age_days": 7,
        "shared_now": True,
        "expected_removed": 1,
        "must_not_exist": ["run/url00_stale.bin"],
        "must_exist_files": ["run/url01_fresh.bin"],
        "must_exist_dirs": ["run"],
    },
    {
        "case_id": "c4_ordering",
        "files": [{"path": "a/b/c/url00.bin", "days_ago": 10}],
        "max_age_days": 7,
        "shared_now": True,
        "expected_removed": 1,
        "must_not_exist_dirs": ["a/b/c", "a/b", "a"],
        "base_must_exist": True,
    },
    {
        "case_id": "c5_idempotent_dry_run",
        "files": [{"path": "run/url00.bin", "days_ago": 10}],
        "max_age_days": 7,
        "shared_now": True,
        "dry_run_repeats": 2,
        "then_real_run": True,
        "expected_removed": 1,
        "must_exist_files": ["run/url00.bin"],
        "must_not_exist": ["run/url00.bin"],
    },
)


def run_persist_fallback_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_DIR", str(tmp_path))
    orch, _ = make_dev_orchestrator()
    base_dir = Path(str(tmp_path)).expanduser().resolve()

    run_id = uuid4()
    expected_digest_full = hashlib.sha256(PERSIST_CONTENT).hexdigest()
    expected_fname = f"url{PERSIST_URL_INDEX:02d}_{expected_digest_full[:32]}.bin"

    happy = orch._persist_scraper_response_artifact(  # noqa: SLF001
        run_id,
        PERSIST_URL_INDEX,
        PERSIST_CONTENT,
        PERSIST_CAP,
    )

    def _raise_value_error(self: Path, *args: object, **kwargs: object) -> Path:
        raise ValueError("fo110 forced fallback")

    run_id_fb = uuid4()
    original_relative_to = Path.relative_to
    with patch.object(Path, "relative_to", _raise_value_error):
        fallback = orch._persist_scraper_response_artifact(  # noqa: SLF001
            run_id_fb,
            PERSIST_URL_INDEX,
            PERSIST_CONTENT,
            PERSIST_CAP,
        )
    assert Path.relative_to is original_relative_to

    assert fallback["artifact_relpath"] == expected_fname
    assert str(run_id_fb) not in fallback["artifact_relpath"]

    on_disk_fb = base_dir / str(run_id_fb) / expected_fname
    assert on_disk_fb.is_file()
    assert on_disk_fb.read_bytes() == PERSIST_CONTENT

    assert fallback["artifact_sha256"] == happy["artifact_sha256"]
    assert fallback["artifact_sha256"] == hashlib.sha256(PERSIST_CONTENT).hexdigest()

    assert fallback["artifact_bytes_written"] == happy["artifact_bytes_written"]
    assert fallback["artifact_bytes_written"] == len(PERSIST_CONTENT)

    assert "\\" not in fallback["artifact_relpath"]
    assert fallback["artifact_relpath"] != happy["artifact_relpath"]
    assert happy["artifact_relpath"].endswith("/" + expected_fname)
