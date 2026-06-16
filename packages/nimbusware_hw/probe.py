from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Any


def available_memory_gb() -> tuple[float | None, float | None]:
    """Return (total_gb, available_gb) when detectable."""
    if sys.platform == "win32":
        try:

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total = float(stat.ullTotalPhys / (1024**3))
                avail = float(stat.ullAvailPhys / (1024**3))
                return total, avail
        except (AttributeError, OSError, TypeError):
            return None, None
    elif sys.platform.startswith("linux"):
        try:
            meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
        except OSError:
            return None, None
        total_kb: int | None = None
        avail_kb: int | None = None
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2:
                    total_kb = int(parts[1])
            elif line.startswith("MemAvailable:"):
                parts = line.split()
                if len(parts) >= 2:
                    avail_kb = int(parts[1])
        if total_kb is not None and avail_kb is not None:
            return total_kb / (1024**2), avail_kb / (1024**2)
    return None, None


def classify_tier(*, ram_total_gb: float | None, cpu_count: int) -> str:
    total = ram_total_gb or 0.0
    if total >= 32 and cpu_count >= 8:
        return "strong"
    if total >= 16 and cpu_count >= 4:
        return "medium"
    return "weak"


def probe_hardware_remote_ssh(host: str) -> dict[str, Any]:
    """Enterprise SSH hardware probe (subprocess ssh + /proc/meminfo parse)."""
    from nimbusware_env.edition import is_enterprise

    if not is_enterprise():
        return {"errors": ["ssh_probe_requires_enterprise"], "tier": "weak"}
    host = host.strip()
    if not host:
        return {"errors": ["ssh_host_empty"], "tier": "weak"}
    from nimbusware_env.env_flags import env_str, env_truthy

    key_path = env_str("NIMBUSWARE_HW_SSH_IDENTITY") or None
    if env_truthy("NIMBUSWARE_HW_SSH_MOCK"):
        return {
            "tier": "medium",
            "ram_total_gb": 32.0,
            "ram_available_gb": 16.0,
            "cpu_count": 8,
            "gpus": [{"name": "mock-ssh-gpu", "vram_gb": 8.0, "backend": "cuda"}],
            "gpu_groups": [["mock-ssh-gpu"]],
            "unified_memory": False,
            "errors": [],
            "platform": "ssh-mock",
            "remote_host": host,
            "ssh_identity_configured": bool(key_path),
        }
    from nimbusware_hw.ssh_probe import run_ssh_hardware_probe

    return run_ssh_hardware_probe(host, identity_path=key_path)


def probe_hardware(*, fixture: str | None = None, remote_host: str | None = None) -> dict[str, Any]:
    if remote_host and remote_host.strip():
        return probe_hardware_remote_ssh(remote_host.strip())
    from nimbusware_env.env_flags import nimbusware_hw_fixture

    fix = fixture or nimbusware_hw_fixture()
    if fix:
        from nimbusware_hw.fixtures import fixture_probe

        return fixture_probe(fix)

    errors: list[str] = []
    total_gb, avail_gb = available_memory_gb()
    if total_gb is None:
        errors.append("ram_probe_unavailable")
    cpu_count = os.cpu_count() or 1
    tier = classify_tier(ram_total_gb=total_gb, cpu_count=cpu_count)
    return {
        "tier": tier,
        "ram_total_gb": round(total_gb, 2) if total_gb is not None else None,
        "ram_available_gb": round(avail_gb, 2) if avail_gb is not None else None,
        "cpu_count": cpu_count,
        "gpus": [],
        "gpu_groups": [],
        "unified_memory": False,
        "errors": errors,
        "platform": sys.platform,
    }
