from __future__ import annotations

from typing import Any

from nimbusware_env.env_flags import env_str
from nimbusware_hw.probe import probe_hardware
from nimbusware_hw.profile import profile_from_probe

_TIER_RANK = {"weak": 0, "medium": 1, "strong": 2}


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


def rescan_fleet_hardware_hosts() -> dict[str, Any]:
    return probe_fleet_hardware_hosts()


def resolve_probe_hosts() -> list[str]:
    hosts = parse_fleet_hosts_env()
    if hosts:
        return hosts
    single = (env_str("NIMBUSWARE_HW_SSH_HOST") or "").strip()
    return [single] if single else []


def _host_passes(row: dict[str, Any], *, min_tier: str | None) -> tuple[bool, list[str]]:
    reasons: list[str] = list(row.get("errors") or [])
    if reasons:
        return False, reasons
    if min_tier:
        actual = str(row.get("tier") or "weak")
        if _TIER_RANK.get(actual, 0) < _TIER_RANK.get(min_tier, 0):
            reasons.append(f"tier_below_expectation:{actual}<{min_tier}")
            return False, reasons
    return True, []


def run_probe_matrix() -> dict[str, Any]:
    hosts = resolve_probe_hosts()
    if not hosts:
        return {
            "skipped": True,
            "reason": "no_hosts_configured",
            "host_count": 0,
            "passed": 0,
            "failed": 0,
            "hosts": [],
        }

    min_tier = (env_str("NIMBUSWARE_HW_EXPECT_MIN_TIER") or "").strip().lower() or None
    rows: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    for host in hosts:
        raw = probe_hardware(remote_host=host)
        profile = profile_from_probe(raw)
        row = {
            "host": host,
            "tier": profile.tier,
            "errors": list(profile.errors),
            "platform": profile.platform or raw.get("platform"),
        }
        ok, reasons = _host_passes(row, min_tier=min_tier)
        if ok:
            passed += 1
        else:
            failed += 1
        rows.append(
            {
                "host": row.get("host"),
                "tier": row.get("tier"),
                "ok": ok,
                "errors": reasons,
                "platform": row.get("platform"),
            },
        )
    return {
        "skipped": False,
        "host_count": len(rows),
        "passed": passed,
        "failed": failed,
        "expect_min_tier": min_tier,
        "hosts": rows,
    }
