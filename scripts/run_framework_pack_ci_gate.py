#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "NIMBUSWARE_FRAMEWORK_PACK_FIDELITY": "1",
        "NIMBUSWARE_MOUSE_FIDELITY": "1",
    }
    install = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        cwd=root,
        env=env,
    )
    if install.returncode != 0:
        return install.returncode
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/test_js_framework_detect.py",
        "tests/unit/test_framework_pack_smoke.py",
        "tests/e2e/journeys/test_launch_framework_detect_journey.py",
        "tests/e2e/journeys/test_launch_framework_put_preview_journey.py",
        "tests/e2e/journeys/test_launch_test_static_html_journey.py",
        "tests/e2e/journeys/test_launch_test_write_replan_journey.py",
        "tests/e2e/journeys/test_launch_test_unknown_spa.py",
        "-q",
        "--tb=short",
    ]
    proc = subprocess.run(cmd, cwd=root, env=env)
    if proc.returncode != 0:
        return proc.returncode
    print("framework pack CI gate OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
