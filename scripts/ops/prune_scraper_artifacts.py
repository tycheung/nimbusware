#!/usr/bin/env python3
"""Remove scraper response artifact files older than a TTL.

Requires ``--max-age-days`` or ``NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS`` (positive integer).
Uses ``NIMBUSWARE_SCRAPER_ARTIFACT_DIR`` when set, else ``<NIMBUSWARE_REPO_ROOT>/.cache/nimbusware_scraper``.

Scheduled pruning (no in-repo daemon): point a system scheduler at this entrypoint after exporting
the same env vars you use for runs (at minimum ``NIMBUSWARE_REPO_ROOT``).

Examples:

- **cron** (daily 03:15, 14-day TTL): ``15 3 * * * cd /path/to/nimbusware &&``
  ``NIMBUSWARE_REPO_ROOT=/path/to/nimbusware NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS=14``
  ``poetry run python scripts/ops/prune_scraper_artifacts.py``
- **Dry-run** (count only): add ``--dry-run`` to the same command to print how many files
  would be removed without deleting.
- **JSON** (log agents): add ``--json-summary`` to print one extra stdout line after the
  human-readable line. Standalone usage emits the **extended** object (base fields plus
  retention/object-store counters). When ``--summary-path`` is also set, stdout uses the
  **slim base** object so it byte-matches the state file (minus ``wrote_at``).
- **Include filter**: ``--include-pattern '*.bin'`` deletes only the on-disk
  artifact bodies and leaves any operator-written sidecar files alone. Repeat the flag
  to OR multiple patterns.
- **Exclude filter**: ``--exclude-pattern '*.keep'`` preserves marker files
  operators may write to pin a specific run's artifacts from auto-prune. Exclude wins
  on overlap with ``--include-pattern``.
- **Env pattern defaults**: when no CLI include/exclude flags are passed,
  ``NIMBUSWARE_PRUNE_INCLUDE_PATTERN`` / ``NIMBUSWARE_PRUNE_EXCLUDE_PATTERN`` supply comma-separated
  globs (same semantics as repeating ``--include-pattern`` / ``--exclude-pattern``).
  CLI flags always win when present.
- **State file**: ``--summary-path ~/.cache/nimbusware_scraper/.prune_status.json``
  writes the same JSON object as ``--json-summary`` plus a UTC ``wrote_at`` timestamp,
  atomically (tmp + ``os.replace``), so operator prune-status UIs can render
  the last-run summary. ``NIMBUSWARE_PRUNE_STATUS_PATH`` is the env equivalent; the CLI
  flag wins when both are set. Independent of ``--json-summary``: you can write the
  file without printing the extra stdout line, or do both.
- **Windows Task Scheduler**: Action ``Program`` = ``powershell.exe``; ``Arguments`` =
  ``-NoProfile -Command "Set-Location 'D:\\Nimbusware';``
  ``$env:NIMBUSWARE_REPO_ROOT='D:\\Nimbusware';``
  ``$env:NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS='14';``
  ``poetry run python scripts/ops/prune_scraper_artifacts.py"``
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.scraper_artifacts import (
    prune_scraper_artifacts,
    resolve_scraper_artifact_base_dir,
)


def _patterns_from_cli_or_env(
    cli_patterns: list[str] | None,
    env_name: str,
) -> list[str] | None:
    """CLI ``--include-pattern`` / ``--exclude-pattern`` win over env defaults.

    Env uses comma-separated globs (``NIMBUSWARE_PRUNE_INCLUDE_PATTERN``,
    ``NIMBUSWARE_PRUNE_EXCLUDE_PATTERN``) so operators can set one var in cron/Task
    Scheduler without repeating CLI flags.
    """
    if cli_patterns:
        return cli_patterns
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or None


def _resolve_summary_path(cli_value: str | None) -> Path | None:
    """CLI flag overrides ``NIMBUSWARE_PRUNE_STATUS_PATH``; blank / unset ⇒ no file written."""
    if cli_value:
        return Path(cli_value).expanduser()
    raw = os.environ.get("NIMBUSWARE_PRUNE_STATUS_PATH", "").strip()
    if raw:
        return Path(raw).expanduser()
    return None


def _write_status_atomically(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` as JSON to ``path`` via tmp + ``os.replace`` (atomic on POSIX & Windows).

    Creates parent dirs as needed. Tmp sibling is cleaned up on a successful replace; on
    failure the partial tmp may remain (operator can inspect / delete).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help="Delete files older than this many days (overrides env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many stale files would be removed without deleting",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help=(
            "After the human line, print one JSON object: schema_version, pruned count, "
            "base path, dry_run, max_age_days, include_patterns, exclude_patterns, "
            "include_pattern_count, exclude_pattern_count"
        ),
    )
    parser.add_argument(
        "--include-pattern",
        action="append",
        default=None,
        metavar="GLOB",
        help=(
            "Only consider files whose basename matches GLOB "
            "(fnmatch syntax; e.g. '*.bin', 'url*'). Repeat to OR multiple patterns. "
            "Evaluated AFTER the mtime cutoff."
        ),
    )
    parser.add_argument(
        "--exclude-pattern",
        action="append",
        default=None,
        metavar="GLOB",
        help=(
            "Skip files whose basename matches GLOB. Repeat to OR multiple patterns. "
            "Exclude takes precedence over --include-pattern when a file matches both."
        ),
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        metavar="PATH",
        help=(
            "Atomically write the JSON summary (same shape as --json-summary, plus "
            "wrote_at UTC timestamp) to PATH so operator prune-status panels can "
            "render it. Overrides NIMBUSWARE_PRUNE_STATUS_PATH when both are set."
        ),
    )
    args = parser.parse_args()
    days = args.max_age_days
    if days is None:
        raw = os.environ.get("NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS", "").strip()
        days = int(raw) if raw else None
    if days is None or days < 1:
        print(
            "Set --max-age-days or NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS (positive integer).",
            file=sys.stderr,
        )
        return 1
    root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    base = resolve_scraper_artifact_base_dir(root)
    include_patterns = _patterns_from_cli_or_env(
        args.include_pattern,
        "NIMBUSWARE_PRUNE_INCLUDE_PATTERN",
    )
    exclude_patterns = _patterns_from_cli_or_env(
        args.exclude_pattern,
        "NIMBUSWARE_PRUNE_EXCLUDE_PATTERN",
    )
    prune_result = prune_scraper_artifacts(
        base,
        max_age_days=days,
        dry_run=args.dry_run,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    n = int(prune_result["local_removed"])
    if args.dry_run:
        print(f"dry-run: would prune {n} file(s) under {base}")
    else:
        print(f"pruned {n} file(s) under {base}")
    summary_base = {
        "schema_version": 1,
        "pruned": n,
        "base": str(base),
        "dry_run": args.dry_run,
        "include_patterns": include_patterns,
        "exclude_patterns": exclude_patterns,
        "include_pattern_count": len(include_patterns or []),
        "exclude_pattern_count": len(exclude_patterns or []),
        "max_age_days": days,
    }
    summary_extended = {
        **summary_base,
        "local_removed": n,
        "object_store_attempted": int(prune_result.get("object_store_attempted", 0)),
        "object_store_removed": int(prune_result.get("object_store_removed", 0)),
        "object_store_failed": int(prune_result.get("object_store_failed", 0)),
        "object_store_last_error": prune_result.get("object_store_last_error"),
        "retention_execution_mode": prune_result.get("retention_execution_mode", "local_only"),
        "retention_stale_file_count": int(prune_result.get("retention_stale_file_count", 0)),
        "retention_stale_bytes": int(prune_result.get("retention_stale_bytes", 0)),
        "retention_alert_level": prune_result.get("retention_alert_level", "none"),
        "retention_lifecycle_state": prune_result.get("retention_lifecycle_state", "healthy"),
    }
    status_path = _resolve_summary_path(args.summary_path)
    if args.json_summary:
        # stdout uses extended fields unless a status file also consumes the base summary.
        stdout_summary = summary_base if status_path is not None else summary_extended
        print(json.dumps(stdout_summary, separators=(",", ":")))
    if status_path is not None:
        # status file adds wrote_at for console age checks.
        _write_status_atomically(
            status_path,
            {**summary_base, "wrote_at": datetime.now(timezone.utc).isoformat()},
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
