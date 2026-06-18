from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from nimbusware_bootstrap.platform import launcher_asset_filename, launcher_release_download_url

_DEFAULT_REPO = "https://github.com/tycheung/nimbusware.git"
_PROFILE_BAREBONES = "barebones"
_PROFILE_RECOMMENDED = "recommended"


def curl_bootstrap_line(
    repo_url: str,
    *,
    profile: str = _PROFILE_RECOMMENDED,
    target_dir: str = "./Nimbusware",
) -> str:
    extras = "--skip-postgres" if profile == _PROFILE_BAREBONES else "--postgres-choice docker"
    seed = "--seed-config" if profile == _PROFILE_RECOMMENDED else ""
    flags = f"--non-interactive {extras} {seed}".split()
    flag_str = " ".join(flag for flag in flags if flag)
    return (
        f"curl -fsSL {repo_url}/raw/main/scripts/install_nimbusware.py "
        f"| python - --clone {repo_url} --target-dir {target_dir} "
        f"{flag_str} --install-profile {profile}"
    )


def pip_hint() -> str:
    return "pip install nimbusware-bootstrap  # prints install hints via nimbusware-bootstrap"


def resolve_install_script() -> Path | None:
    repo_root = Path(__file__).resolve().parents[3]
    install = repo_root / "scripts" / "install" / "install_nimbusware.py"
    if install.is_file() and (repo_root / "pyproject.toml").is_file():
        return install
    return None


def install_script_argv(profile: str) -> list[str]:
    if profile == _PROFILE_RECOMMENDED:
        return [
            "--non-interactive",
            "--seed-config",
            "--postgres-choice",
            "docker",
            "--install-profile",
            _PROFILE_RECOMMENDED,
        ]
    return [
        "--non-interactive",
        "--skip-postgres",
        "--install-profile",
        _PROFILE_BAREBONES,
    ]


def run_remote_install(
    repo_url: str,
    *,
    profile: str,
    target_dir: str = "./Nimbusware",
) -> int:
    script_url = f"{repo_url.rstrip('/')}/raw/main/scripts/install_nimbusware.py"
    curl = subprocess.run(
        ["curl", "-fsSL", script_url],
        capture_output=True,
        text=True,
        check=False,
    )
    if curl.returncode != 0:
        print(curl.stderr or curl.stdout or "curl failed", file=sys.stderr)
        return curl.returncode or 1
    cmd = [
        sys.executable,
        "-",
        "--clone",
        repo_url,
        "--target-dir",
        target_dir,
        *install_script_argv(profile),
    ]
    return subprocess.call(cmd, input=curl.stdout, text=True)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nimbusware consumer bootstrap helper")
    parser.add_argument("--repo-url", default=_DEFAULT_REPO)
    parser.add_argument("--target-dir", default="./Nimbusware")
    parser.add_argument(
        "--install-profile",
        choices=(_PROFILE_BAREBONES, _PROFILE_RECOMMENDED),
        default=_PROFILE_BAREBONES,
    )
    parser.add_argument("--print-only", action="store_true", help="Print bootstrap lines and exit")
    parser.add_argument("--run", action="store_true", help="Run non-interactive in-repo install")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install Nimbusware (in-repo script or remote curl installer)",
    )
    parser.add_argument("--launcher-tag", default="latest", help="GitHub release tag for launcher")
    args = parser.parse_args(argv)
    install = resolve_install_script()
    launcher_name = launcher_asset_filename()
    launcher_url = launcher_release_download_url(args.repo_url, tag=args.launcher_tag)
    lines = [
        f"Launcher ({launcher_name}): {launcher_url}",
        curl_bootstrap_line(
            args.repo_url, profile=_PROFILE_RECOMMENDED, target_dir=args.target_dir
        ),
        curl_bootstrap_line(args.repo_url, profile=_PROFILE_BAREBONES, target_dir=args.target_dir),
        pip_hint(),
    ]
    if install is not None:
        lines.insert(
            2,
            f"python {install} {' '.join(install_script_argv(_PROFILE_BAREBONES))}",
        )
    if args.print_only or (not args.run and not args.install):
        print("Nimbusware consumer bootstrap options:")
        print(f"  Platform: {launcher_name}")
        for idx, line in enumerate(lines, start=1):
            print(f"  {idx}. {line}")
        return 0
    if install is not None:
        return subprocess.call(
            [sys.executable, str(install), *install_script_argv(args.install_profile)],
            cwd=install.parents[1],
        )
    if args.install or args.run:
        return run_remote_install(
            args.repo_url,
            profile=args.install_profile,
            target_dir=args.target_dir,
        )
    return 0
