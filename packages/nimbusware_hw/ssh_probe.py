from __future__ import annotations

import re
import subprocess
from typing import Any

_REMOTE_PROBE_SHELL = (
    "grep -E '^(MemTotal|MemAvailable):' /proc/meminfo 2>/dev/null; "
    "echo CPU_COUNT=$(nproc 2>/dev/null || echo 1); "
    "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || true"
)


def build_ssh_probe_argv(host: str, *, identity_path: str | None) -> list[str]:
    argv = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=12",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    if identity_path:
        argv.extend(["-i", identity_path])
    argv.extend([host, "sh", "-c", _REMOTE_PROBE_SHELL])
    return argv


def parse_remote_probe_output(text: str) -> dict[str, Any]:
    mem_total_kb: int | None = None
    mem_avail_kb: int | None = None
    cpu_count = 1
    gpus: list[dict[str, Any]] = []
    errors: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("MemTotal:"):
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    mem_total_kb = int(parts[1])
                except ValueError:
                    errors.append("memtotal_parse_failed")
        elif stripped.startswith("MemAvailable:"):
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    mem_avail_kb = int(parts[1])
                except ValueError:
                    errors.append("memavailable_parse_failed")
        elif stripped.startswith("CPU_COUNT="):
            raw_cpu = stripped.split("=", 1)[-1].strip()
            try:
                cpu_count = max(1, int(raw_cpu))
            except ValueError:
                errors.append("cpu_count_parse_failed")
        elif "," in stripped and not stripped.startswith("CPU_COUNT"):
            name_part, _, vram_part = stripped.partition(",")
            name = name_part.strip().strip('"')
            vram_gb: float | None = None
            vram_m = re.search(r"([\d.]+)\s*MiB", vram_part, re.I)
            if vram_m:
                vram_gb = round(float(vram_m.group(1)) / 1024.0, 2)
            if name:
                gpus.append({"name": name, "vram_gb": vram_gb, "backend": "cuda"})

    total_gb = (mem_total_kb / (1024**2)) if mem_total_kb is not None else None
    avail_gb = (mem_avail_kb / (1024**2)) if mem_avail_kb is not None else None
    from nimbusware_hw.probe import classify_tier

    tier = classify_tier(ram_total_gb=total_gb, cpu_count=cpu_count)
    gpu_groups = [[g["name"]] for g in gpus if g.get("name")]
    return {
        "tier": tier,
        "ram_total_gb": round(total_gb, 2) if total_gb is not None else None,
        "ram_available_gb": round(avail_gb, 2) if avail_gb is not None else None,
        "cpu_count": cpu_count,
        "gpus": gpus,
        "gpu_groups": gpu_groups,
        "unified_memory": False,
        "errors": errors,
        "platform": "ssh-linux",
    }


def run_ssh_hardware_probe(
    host: str,
    *,
    identity_path: str | None,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            build_ssh_probe_argv(host, identity_path=identity_path),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "tier": "weak",
            "errors": [f"ssh_exec_failed:{exc!s}"[:200]],
            "platform": "ssh",
            "remote_host": host,
        }
    if proc.returncode != 0:
        err_tail = (proc.stderr or proc.stdout or "ssh_failed")[:300]
        return {
            "tier": "weak",
            "errors": [f"ssh_exit_{proc.returncode}:{err_tail}"],
            "platform": "ssh",
            "remote_host": host,
        }
    parsed = parse_remote_probe_output(proc.stdout or "")
    parsed["remote_host"] = host
    parsed["ssh_identity_configured"] = bool(identity_path)
    if not parsed.get("errors"):
        parsed["errors"] = []
    return parsed
