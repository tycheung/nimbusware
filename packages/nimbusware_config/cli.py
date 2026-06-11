from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from nimbusware_config.export import export_config_to_repo
from nimbusware_config.seed import preview_seed_from_repo, seed_config_from_repo
from nimbusware_config.store import PostgresConfigStore

_TOOL_NAME = "nimbusware-config"


def _repo_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    return Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()


def _database_url() -> str:
    url = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    if not url:
        msg = "NIMBUSWARE_DATABASE_URL is required for nimbusware-config"
        raise ValueError(msg)
    return url


def _namespace_filter(raw: list[str] | None) -> set[str] | None:
    if not raw:
        return None
    return {n.strip() for n in raw if n.strip()}


def _cmd_seed_from_repo(args: argparse.Namespace) -> int:
    repo = _repo_root(args.repo_root)
    store = PostgresConfigStore(_database_url())
    counts = seed_config_from_repo(repo, store)
    print(json.dumps({"action": "seed-from-repo", "counts": counts}, sort_keys=True))
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    repo = _repo_root(args.repo_root)
    store = PostgresConfigStore(_database_url())
    ns = _namespace_filter(args.namespace)
    counts = export_config_to_repo(store, repo, namespaces=ns)
    print(json.dumps({"action": "export", "counts": counts}, sort_keys=True))
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    repo = _repo_root(args.repo_root)
    store = PostgresConfigStore(_database_url())
    ns = _namespace_filter(args.namespace)
    if args.dry_run:
        preview = preview_seed_from_repo(repo, namespaces=ns)
        print(
            json.dumps(
                {"action": "import", "dry_run": True, "would_import": preview},
                sort_keys=True,
            ),
        )
        return 0
    counts = seed_config_from_repo(repo, store)
    print(json.dumps({"action": "import", "dry_run": False, "counts": counts}, sort_keys=True))
    return 0


def _add_repo_root_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: $NIMBUSWARE_REPO_ROOT or '.').",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_TOOL_NAME,
        description=(
            "Bootstrap or export Nimbusware operator config between Postgres "
            "(nimbusware_config_document) and repo configs/ YAML for git review."
        ),
    )
    _add_repo_root_arg(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    seed_p = sub.add_parser(
        "seed-from-repo",
        help="Load configs/**/*.yaml into Postgres (authoritative import).",
    )
    _add_repo_root_arg(seed_p)
    seed_p.set_defaults(handler=_cmd_seed_from_repo)

    export_p = sub.add_parser(
        "export",
        help="Write Postgres config rows to canonical configs/ paths.",
    )
    _add_repo_root_arg(export_p)
    export_p.add_argument(
        "--namespace",
        action="append",
        default=None,
        help="Limit to namespace (repeatable): personas, roles, workflows, policy.",
    )
    export_p.set_defaults(handler=_cmd_export)

    import_p = sub.add_parser(
        "import",
        help="Alias for seed-from-repo; use --dry-run to list existing rows only.",
    )
    _add_repo_root_arg(import_p)
    import_p.add_argument(
        "--dry-run",
        action="store_true",
        help="List existing document keys/digests without writing.",
    )
    import_p.add_argument(
        "--namespace",
        action="append",
        default=None,
        help="Limit dry-run listing to namespace (repeatable).",
    )
    import_p.set_defaults(handler=_cmd_import)

    return parser


def main(argv: list[str] | None = None) -> int:
    from nimbusware_env import load_dotenv

    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
