from __future__ import annotations

import shutil
import subprocess

from nimbusware_orchestrator.put_e2e_types import PutE2EFinding


def _playwright_available() -> bool:
    return shutil.which("playwright") is not None or shutil.which("npx") is not None


def _playwright_module_ready() -> tuple[bool, str]:
    if not _playwright_available():
        return False, "playwright CLI not on PATH"
    probe = subprocess.run(
        ["python", "-m", "playwright", "--version"],
        capture_output=True,
        text=True,
        timeout=30.0,
        check=False,
    )
    if probe.returncode != 0:
        return False, (probe.stderr or probe.stdout or "playwright module not installed")[:500]
    return True, (probe.stdout or probe.stderr or "ok").strip()


def stub_console_capture(*, enabled: bool) -> list[PutE2EFinding]:
    if not enabled:
        return []
    return [
        PutE2EFinding(
            kind="console",
            message="console capture stub (no browser session)",
            severity="info",
        ),
    ]


def stub_network_capture(
    *,
    enabled: bool,
    exercised_paths: set[str],
) -> list[PutE2EFinding]:
    if not enabled:
        return []
    findings: list[PutE2EFinding] = []
    for path in sorted(exercised_paths):
        findings.append(
            PutE2EFinding(
                kind="network",
                message=f"request observed: {path}",
                surface_path=path,
                severity="info",
            ),
        )
    if not findings:
        findings.append(
            PutE2EFinding(
                kind="network",
                message="network capture stub (no requests recorded)",
                severity="info",
            ),
        )
    return findings
