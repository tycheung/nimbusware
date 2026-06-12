#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_DEFAULT_REPO = os.environ.get(
    "NIMBUSWARE_DEFAULT_REPO_URL",
    "https://github.com/nimbusware/nimbusware.git",
)


def _curl_bootstrap_line(repo_url: str) -> str:
    return (
        f"curl -fsSL {repo_url}/raw/main/scripts/install_nimbusware.py "
        f"| python - --clone {repo_url} --target-dir ./Nimbusware "
        "--non-interactive --skip-postgres"
    )


def _pip_hint() -> str:
    return (
        "pip install nimbusware  # future: thin bootstrap wheel delegates to install_nimbusware.py"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nimbusware consumer bootstrap helper")
    parser.add_argument("--repo-url", default=_DEFAULT_REPO)
    parser.add_argument("--print-only", action="store_true", help="Print bootstrap lines and exit")
    parser.add_argument("--run", action="store_true", help="Run non-interactive in-repo install")
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    install = repo_root / "scripts" / "install_nimbusware.py"
    lines = [
        _curl_bootstrap_line(args.repo_url),
        f"python {install} --non-interactive --skip-postgres --no-poetry-install",
        _pip_hint(),
    ]
    if args.print_only or not args.run:
        print("Nimbusware consumer bootstrap options:")
        for idx, line in enumerate(lines, start=1):
            print(f"  {idx}. {line}")
        return 0
    return subprocess.call(
        [
            sys.executable,
            str(install),
            "--non-interactive",
            "--skip-postgres",
            "--no-poetry-install",
        ],
        cwd=repo_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
