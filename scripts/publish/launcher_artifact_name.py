#!/usr/bin/env python3

from __future__ import annotations

import platform
import sys


def launcher_platform_slug() -> str:
    system = sys.platform
    machine = platform.machine().lower()
    if system == "win32":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"windows-{arch}"
    if system == "darwin":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"macos-{arch}"
    if system.startswith("linux"):
        if machine in {"aarch64", "arm64"}:
            return "linux-arm64"
        if machine in {"x86_64", "amd64"}:
            return "linux-x86_64"
        return f"linux-{machine}"
    return f"{system}-{machine}"


def launcher_artifact_basename() -> str:
    return f"NimbuswareLauncher-{launcher_platform_slug()}"


def launcher_artifact_filename() -> str:
    base = launcher_artifact_basename()
    if sys.platform == "win32":
        return f"{base}.exe"
    return base


def main() -> int:
    print(launcher_artifact_filename())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
