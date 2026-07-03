from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from typing import Any

_lock = threading.Lock()
_job_status: str = "idle"
_job_error: str = ""


def _set_job(status: str, error: str = "") -> None:
    global _job_status, _job_error
    with _lock:
        _job_status = status
        _job_error = error


def playwright_bootstrap_status() -> dict[str, Any]:
    with _lock:
        status = _job_status
        err = _job_error
    if status == "installing":
        return {"status": "installing", "plain_summary": "Installing browser checks…"}
    if status == "error":
        return {"status": "error", "plain_summary": err or "Playwright install failed"}
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
            return {"status": "ready", "plain_summary": "Browser checks are ready."}
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {
        "status": "missing",
        "plain_summary": "Browser checks need Playwright — use Prepare workspace on Home.",
    }


def _run_install_worker() -> None:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _set_job("error", str(exc))
        return
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-400:]
        _set_job("error", tail or "Playwright install failed")
        return
    _set_job("ready")


def run_playwright_bootstrap() -> dict[str, Any]:
    global _job_status, _job_error
    snap = playwright_bootstrap_status()
    if snap.get("status") == "ready":
        return snap
    with _lock:
        if _job_status == "installing":
            return {"status": "installing", "plain_summary": "Installing browser checks…"}
        _job_status = "installing"
        _job_error = ""
    thread = threading.Thread(target=_run_install_worker, daemon=True)
    thread.start()
    return {"status": "installing", "plain_summary": "Installing browser checks…"}
