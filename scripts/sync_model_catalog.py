#!/usr/bin/env python3
"""Refresh configs/hardware/model_catalog.json from a local or URL JSON export."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_hw.catalog_sync import (
    build_catalog_from_source,
    catalog_info_from_path,
    load_catalog_doc,
    validate_catalog,
)


def _load_source_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_source_url(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read()
    doc = json.loads(data.decode("utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit("URL JSON must be an object with models[]")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync hardware model catalog subset")
    parser.add_argument(
        "source",
        type=Path,
        nargs="?",
        help="Path to source JSON with models[] (legacy positional)",
    )
    parser.add_argument("--from-json", type=Path, help="Path to source JSON")
    parser.add_argument("--from-url", type=str, help="Download curated JSON from URL (operator-only)")
    parser.add_argument("--merge", action="store_true", help="Merge by model id instead of replace")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    args = parser.parse_args(argv)

    root = find_repo_root()
    dest = root / "configs" / "hardware" / "model_catalog.json"
    dest.parent.mkdir(parents=True, exist_ok=True)

    if args.from_url:
        raw_doc = _load_source_url(args.from_url.strip())
        source_label = "url"
    elif args.from_json:
        raw_doc = _load_source_json(args.from_json)
        source_label = "json"
    elif args.source:
        raw_doc = _load_source_json(args.source)
        source_label = "json"
    else:
        parser.error("provide --from-json, --from-url, or a positional source path")

    existing = load_catalog_doc(dest) if args.merge else None
    catalog = build_catalog_from_source(raw_doc, existing=existing, merge=args.merge)
    errors = validate_catalog(catalog)
    if errors:
        for err in errors:
            print(f"validation error: {err}", file=sys.stderr)
        return 1

    print(
        f"catalog ready: version={catalog['version']} models={len(catalog['models'])} "
        f"merge={args.merge} source={source_label}",
    )
    if args.dry_run:
        return 0

    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    tmp.replace(dest)
    info = catalog_info_from_path(dest, source=source_label)
    print(f"Wrote {dest} ({info['model_count']} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
