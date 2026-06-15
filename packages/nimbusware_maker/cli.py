from __future__ import annotations

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from nimbusware_env.env_flags import nimbusware_api_base_url
from nimbusware_maker.quick_mode import apply_quick_mode_env


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Nimbusware Maker web UI.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="In-memory event store, stub critics, quick_local workflow (no Postgres).",
    )
    parser.add_argument(
        "--web-only",
        action="store_true",
        help="Print maker web URL (API must already be running).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args, _extra = parser.parse_known_args(raw)
    if args.quick:
        apply_quick_mode_env()

    base = nimbusware_api_base_url()
    url = f"{base.replace('/v1', '')}/v1/maker/app/"
    if args.web_only:
        print(url)
        return 0

    os.environ.setdefault("NIMBUSWARE_UI_BACKEND", "web")
    repo = Path(__file__).resolve().parents[2]
    subprocess.run(
        [
            sys.executable,
            str(repo / "packages" / "nimbusware_env" / "run_app.py"),
            "--repo-root",
            str(repo),
        ],
        check=False,
    )
    webbrowser.open(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
