from __future__ import annotations

from typing import Any

from nimbusware_env.env_flags import env_str
from nimbusware_hw.probe import probe_hardware
from nimbusware_hw.profile import profile_from_probe


def parse_fleet_hosts_env() -> list[str]:
    raw = env_str("NIMBUSWARE_HW_FLEET_HOSTS")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def probe_fleet_hardware_hosts() -> dict[str, Any]:
    hosts = parse_fleet_hosts_env()
    rows: list[dict[str, Any]] = []
    for host in hosts:
        raw = probe_hardware(remote_host=host)
        profile = profile_from_probe(raw)
        rows.append(
            {
                "host": host,
                "tier": profile.tier,
                "ram_total_gb": profile.ram_total_gb,
                "ram_available_gb": profile.ram_available_gb,
                "cpu_count": profile.cpu_count,
                "gpu_count": len(profile.gpus),
                "errors": list(profile.errors),
                "platform": profile.platform or raw.get("platform"),
            },
        )
    return {"host_count": len(rows), "hosts": rows}
