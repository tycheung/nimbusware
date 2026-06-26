from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Any


def playwright_bootstrap_status() -> dict[str, Any]:
    cli = shutil.which("playwright")
    if cli:
        return {"status": "ready", "plain_summary": "Playwright CLI is available."}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode == 0:
            return {"status": "installing", "plain_summary": "Installing browser checks…"}
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {
        "status": "missing",
        "plain_summary": "Browser checks need Playwright — use Prepare workspace on Home.",
    }


def run_playwright_bootstrap() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "plain_summary": str(exc)}
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-400:]
        return {"status": "error", "plain_summary": tail or "Playwright install failed"}
    return {"status": "ready", "plain_summary": "Browser checks are ready."}
