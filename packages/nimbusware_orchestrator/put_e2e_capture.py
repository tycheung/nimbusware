from __future__ import annotations

import shutil
import subprocess

from nimbusware_orchestrator.put_e2e_types import PutE2EFinding

_HTTP_CONSOLE_STUB = "console capture stub (no browser session)"
_HTTP_NETWORK_STUB = "network capture stub (no requests recorded)"


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


def http_flow_stub_findings(
    *,
    console_on: bool,
    network_on: bool,
    exercised_paths: set[str] | None = None,
) -> list[PutE2EFinding]:
    findings: list[PutE2EFinding] = []
    if console_on:
        findings.append(
            PutE2EFinding(kind="console", message=_HTTP_CONSOLE_STUB, severity="info"),
        )
    if network_on:
        paths = exercised_paths or set()
        for path in sorted(paths):
            findings.append(
                PutE2EFinding(
                    kind="network",
                    message=f"request observed: {path}",
                    surface_path=path,
                    severity="info",
                ),
            )
        if not paths:
            findings.append(
                PutE2EFinding(kind="network", message=_HTTP_NETWORK_STUB, severity="info"),
            )
    return findings


def stub_console_capture(*, enabled: bool) -> list[PutE2EFinding]:
    return http_flow_stub_findings(console_on=enabled, network_on=False)


def stub_network_capture(
    *,
    enabled: bool,
    exercised_paths: set[str],
) -> list[PutE2EFinding]:
    return http_flow_stub_findings(
        console_on=False,
        network_on=enabled,
        exercised_paths=exercised_paths,
    )


def stub_capture_sections(
    *,
    console_on: bool,
    network_on: bool,
    exercised_paths: set[str] | None = None,
) -> dict[str, list[dict[str, object]]]:
    findings = http_flow_stub_findings(
        console_on=console_on,
        network_on=network_on,
        exercised_paths=exercised_paths,
    )
    return {
        "console": [f.to_dict() for f in findings if f.kind == "console"],
        "network": [f.to_dict() for f in findings if f.kind == "network"],
    }
