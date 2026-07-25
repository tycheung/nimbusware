"""Fleet hardware aggregate (`sak421-d` — broker-first local row under CAPACITY)."""

from __future__ import annotations

from typing import Any

from broker_client.flags import broker_capacity_enabled
from env.env_flags import env_str
from hw.probe import probe_hardware
from hw.profile import profile_from_probe

_TIER_RANK = {"weak": 0, "medium": 1, "strong": 2}


def parse_fleet_hosts_env() -> list[str]:
    raw = env_str("NIMBUSWARE_HW_FLEET_HOSTS")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _local_broker_row() -> dict[str, Any] | None:
    """When CAPACITY is on, prefer a broker probe row for the local host."""
    if not broker_capacity_enabled():
        return None
    from broker_client.capacity_bridge import try_broker_probe_dict

    hit = try_broker_probe_dict()
    if hit is None:
        # sak432-i: CAPACITY=1|2 refuse silent empty local fleet row.
        raise RuntimeError(
            "fleet_hardware local probe unavailable under "
            "NIMBUSWARE_BROKER_CAPACITY=1|2; use SwissArmyNoife /v1/sak/capacity"
        )
    profile = profile_from_probe(hit)
    return {
        "host": "local-broker",
        "tier": profile.tier,
        "ram_total_gb": profile.ram_total_gb,
        "ram_available_gb": profile.ram_available_gb,
        "cpu_count": profile.cpu_count,
        "gpu_count": len(profile.gpus),
        "errors": list(profile.errors),
        "platform": profile.platform or hit.get("platform"),
        "capacity_source": "broker",
    }


def probe_fleet_hardware_hosts() -> dict[str, Any]:
    hosts = parse_fleet_hosts_env()
    rows: list[dict[str, Any]] = []
    if not hosts:
        broker_row = _local_broker_row()
        if broker_row is not None:
            rows.append(broker_row)
            return {"host_count": 1, "hosts": rows, "capacity_source": "broker"}
    # sak425-h / sak432-i: when CAPACITY peel is on, prefer broker; no SSH fallthrough.
    if hosts and broker_capacity_enabled():
        broker_row = _local_broker_row()
        if broker_row is not None:
            return {
                "host_count": 1,
                "hosts": [broker_row],
                "capacity_source": "broker",
                "note": "NIMBUSWARE_HW_FLEET_HOSTS ignored when CAPACITY peel is on",
            }
        raise RuntimeError(
            "fleet_hardware SSH hosts unavailable under "
            "NIMBUSWARE_BROKER_CAPACITY=1|2; unset NIMBUSWARE_HW_FLEET_HOSTS "
            "and use SwissArmyNoife /v1/sak/capacity"
        )
    for host in hosts:
        # SSH remote probes stay on local probe path (enterprise); not HTTP capacity.
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
                "capacity_source": "ssh",
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
        broker_row = _local_broker_row()
        if broker_row is not None:
            ok, reasons = _host_passes(broker_row, min_tier=None)
            return {
                "skipped": False,
                "host_count": 1,
                "passed": 1 if ok else 0,
                "failed": 0 if ok else 1,
                "expect_min_tier": None,
                "capacity_source": "broker",
                "hosts": [
                    {
                        "host": broker_row["host"],
                        "tier": broker_row["tier"],
                        "ok": ok,
                        "errors": reasons,
                        "platform": broker_row.get("platform"),
                    }
                ],
            }
        return {
            "skipped": True,
            "reason": "no_hosts_configured",
            "host_count": 0,
            "passed": 0,
            "failed": 0,
            "hosts": [],
        }

    if broker_capacity_enabled():
        raise RuntimeError(
            "fleet_hardware SSH probe matrix unavailable under "
            "NIMBUSWARE_BROKER_CAPACITY=1|2; unset NIMBUSWARE_HW_FLEET_HOSTS / "
            "NIMBUSWARE_HW_SSH_HOST and use SwissArmyNoife /v1/sak/capacity"
        )

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
