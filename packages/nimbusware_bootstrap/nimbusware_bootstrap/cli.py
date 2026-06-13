from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_DEFAULT_REPO = "https://github.com/tycheung/nimbusware.git"


def curl_bootstrap_line(repo_url: str) -> str:
    return (
        f"curl -fsSL {repo_url}/raw/main/scripts/install_nimbusware.py "
        f"| python - --clone {repo_url} --target-dir ./Nimbusware "
        "--non-interactive --skip-postgres"
    )


def pip_hint() -> str:
    return "pip install nimbusware-bootstrap  # prints install hints via nimbusware-bootstrap"


def resolve_install_script() -> Path | None:
    repo_root = Path(__file__).resolve().parents[3]
    install = repo_root / "scripts" / "install_nimbusware.py"
    if install.is_file() and (repo_root / "pyproject.toml").is_file():
        return install
    return None


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nimbusware consumer bootstrap helper")
    parser.add_argument("--repo-url", default=_DEFAULT_REPO)
    parser.add_argument("--print-only", action="store_true", help="Print bootstrap lines and exit")
    parser.add_argument("--run", action="store_true", help="Run non-interactive in-repo install")
    args = parser.parse_args(argv)
    install = resolve_install_script()
    lines = [curl_bootstrap_line(args.repo_url), pip_hint()]
    if install is not None:
        lines.insert(
            1,
            f"python {install} --non-interactive --skip-postgres --no-poetry-install",
        )
    if args.print_only or not args.run:
        print("Nimbusware consumer bootstrap options:")
        for idx, line in enumerate(lines, start=1):
            print(f"  {idx}. {line}")
        return 0
    if install is None:
        print(
            "No monorepo checkout found. Use the curl line above on a clean machine.",
            file=sys.stderr,
        )
        return 1
    return subprocess.call(
        [
            sys.executable,
            str(install),
            "--non-interactive",
            "--skip-postgres",
            "--no-poetry-install",
        ],
        cwd=install.parents[1],
    )
