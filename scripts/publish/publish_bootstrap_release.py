#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PKG = _ROOT / "packages" / "nimbusware_bootstrap"
_DIST = _PKG / "dist"


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    proc = subprocess.run(cmd, cwd=cwd or _ROOT, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _require_token(env_name: str) -> str:
    token = os.environ.get(env_name, "").strip()
    if not token:
        raise SystemExit(f"{env_name} is required for upload (see docs/deploy/pypi-publish.md)")
    return token


def _build() -> None:
    if _DIST.is_dir():
        for path in _DIST.iterdir():
            path.unlink()
    _run([sys.executable, "-m", "pip", "install", "build", "twine", "-q"])
    _run([sys.executable, "-m", "build", str(_PKG)])
    wheels = list(_DIST.glob("*.whl"))
    if not wheels:
        raise SystemExit("build produced no wheel in packages/nimbusware_bootstrap/dist/")
    _run([sys.executable, "-m", "twine", "check", *map(str, _DIST.iterdir())])


def _upload(*, testpypi: bool) -> None:
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    if testpypi:
        _require_token("TESTPYPI_API_TOKEN")
        env["TWINE_PASSWORD"] = os.environ["TESTPYPI_API_TOKEN"].strip()
        cmd = [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--repository",
            "testpypi",
            "--skip-existing",
            *map(str, _DIST.iterdir()),
        ]
    else:
        _require_token("PYPI_API_TOKEN")
        env["TWINE_PASSWORD"] = os.environ["PYPI_API_TOKEN"].strip()
        cmd = [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--skip-existing",
            *map(str, _DIST.iterdir()),
        ]
    proc = subprocess.run(cmd, cwd=_ROOT, env=env, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _smoke(*, testpypi: bool) -> None:
    if testpypi:
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--index-url",
                "https://test.pypi.org/simple/",
                "--extra-index-url",
                "https://pypi.org/simple/",
                "nimbusware-bootstrap",
            ]
        )
    else:
        wheel = sorted(_DIST.glob("*.whl"))[-1]
        _run([sys.executable, "-m", "pip", "install", str(wheel)])
    _run([sys.executable, "-m", "nimbusware_bootstrap", "--print-only"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and optionally publish nimbusware-bootstrap"
    )
    parser.add_argument(
        "--testpypi",
        action="store_true",
        help="Upload to TestPyPI (requires TESTPYPI_API_TOKEN)",
    )
    parser.add_argument(
        "--pypi",
        action="store_true",
        help="Upload to production PyPI (requires PYPI_API_TOKEN)",
    )
    parser.add_argument(
        "--skip-gate",
        action="store_true",
        help="Skip publish bootstrap workflow contract gate",
    )
    args = parser.parse_args()
    if args.testpypi and args.pypi:
        raise SystemExit("Use --testpypi or --pypi, not both")

    if not args.skip_gate:
        _run([sys.executable, str(_ROOT / "scripts" / "ci" / "run_publish_bootstrap_ci_gate.py")])
        _run([sys.executable, str(_ROOT / "scripts" / "ci" / "run_bootstrap_ci_gate.py")])

    _build()
    print("bootstrap wheel build + twine check OK", flush=True)

    if not args.testpypi and not args.pypi:
        print("Build-only mode. Re-run with --testpypi or --pypi to upload.", flush=True)
        return 0

    _upload(testpypi=args.testpypi)
    _smoke(testpypi=args.testpypi)
    target = "TestPyPI" if args.testpypi else "PyPI"
    print(f"Published to {target} and smoke-tested nimbusware-bootstrap", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
