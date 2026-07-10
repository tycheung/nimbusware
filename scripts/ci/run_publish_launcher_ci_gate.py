#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    errors: list[str] = []
    spec = ROOT / "scripts" / "publish" / "NimbuswareLauncher.spec"
    text = spec.read_text(encoding="utf-8")
    if "install_nimbusware.py" not in text:
        errors.append("NimbuswareLauncher.spec must bundle install_nimbusware.py")
    if "assets" not in text:
        errors.append("NimbuswareLauncher.spec must bundle launcher assets")
    if 'join(SPECPATH, "..", "..")' not in text:
        errors.append("NimbuswareLauncher.spec must resolve REPO_ROOT from SPECPATH")

    logo_png = ROOT / "packages" / "env" / "assets" / "nimbusware_logo.png"
    if not logo_png.is_file():
        errors.append(f"missing launcher logo: {logo_png}")

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "publish" / "launcher_artifact_name.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        errors.append(f"launcher_artifact_name.py failed: {proc.stderr or proc.stdout}")
    else:
        name = proc.stdout.strip()
        if not name.startswith("NimbuswareLauncher-"):
            errors.append(f"unexpected artifact name: {name}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print(f"launcher publish gate ok ({name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
