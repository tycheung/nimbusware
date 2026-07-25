"""Capacity stage bind helpers (`sak417-e`, `sak418-d`).

Prefer HTTP ``BrokerClient.capacity()`` over MCP ``capacity_probe`` (which requires
``binding_id``). Pressure / fit bind plans document MCP offers; client helpers derive
pressure and parallel-writer caps from the HTTP probe snapshot when MCP bind is not
wired yet.
"""

from __future__ import annotations

from typing import Any, Literal

from broker_client.client import BrokerClient
from broker_client.flags import broker_capacity_enabled
from broker_client.mcp_client import BrokerMcpClient
from broker_client.stage_bind.llm import BrokerDisabled

PressureLevel = Literal["ok", "warn", "throttle", "block"]


def bind_capacity_probe(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_capacity_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_CAPACITY is not enabled")
    return {
        "offer": "capacity.probe",
        "steps": ["provision", "bind", "invoke"],
        "transport": "http",
        "note": "Use BrokerClient.capacity() (HTTP /v1/sak/capacity); MCP capacity_probe needs binding_id",
    }


def bind_capacity_pressure(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_capacity_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_CAPACITY is not enabled")
    return {
        "offer": "capacity.pressure",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": (
            "MCP capacity_pressure needs binding_id; until bind lands, derive pressure "
            "from HTTP capacity_probe_via_broker() via pressure_from_capacity_probe()"
        ),
    }


def bind_capacity_fit(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_capacity_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_CAPACITY is not enabled")
    return {
        "offer": "capacity.fit",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": (
            "MCP capacity_fit needs binding_id + candidates; use "
            "capacity_fit_via_broker() when binding_id is available"
        ),
    }


def capacity_probe_via_broker(
    *,
    client: BrokerClient | None = None,
) -> dict[str, Any]:
    """Probe capacity via HTTP admin when the capacity dual-run flag is on."""
    if not broker_capacity_enabled():
        raise BrokerDisabled(
            "Set NIMBUSWARE_BROKER_CAPACITY=1 or =2 to route capacity through the broker"
        )
    http = client or BrokerClient()
    result = http.capacity()
    if not isinstance(result, dict):
        raise RuntimeError(f"broker_miss: capacity probe non-dict: {result!r}")
    # sak437-d: error dict is a miss under peel (no soft empty probe).
    if "error" in result and result.get("snapshot") is None and "total_ram_mb" not in result:
        raise RuntimeError(f"broker_miss: capacity probe: {result.get('error')!r}")
    return result


def _snapshot(capacity: dict[str, Any]) -> dict[str, Any]:
    snap = capacity.get("snapshot")
    return snap if isinstance(snap, dict) else capacity


def pressure_from_capacity_probe(
    capacity: dict[str, Any],
    *,
    max_system_ram_pct: float = 75.0,
) -> tuple[PressureLevel, dict[str, Any]]:
    snap = _snapshot(capacity)
    details: dict[str, Any] = {"source": "broker_capacity"}
    total = snap.get("total_ram_mb")
    avail = snap.get("available_ram_mb")
    if not isinstance(total, (int, float)) or not isinstance(avail, (int, float)) or total <= 0:
        # sak437-d: under CAPACITY peel, missing RAM is a miss (not silent ok).
        if broker_capacity_enabled():
            raise RuntimeError(
                "broker_miss: capacity pressure: ram_probe_unavailable under "
                "NIMBUSWARE_BROKER_CAPACITY=1|2"
            )
        return "ok", {**details, "reason": "ram_probe_unavailable"}
    used_pct = ((float(total) - float(avail)) / float(total)) * 100.0
    details["ram_used_pct"] = round(used_pct, 1)
    details["cpu_usage_pct"] = snap.get("cpu_usage_pct")
    cap = max_system_ram_pct
    if used_pct >= cap + 10:
        return "block", {**details, "reason": "ram_over_cap"}
    if used_pct >= cap + 5:
        return "throttle", {**details, "reason": "ram_near_cap"}
    if used_pct >= cap:
        return "warn", {**details, "reason": "ram_at_cap"}
    return "ok", details


def parallel_writer_stages_from_capacity(capacity: dict[str, Any]) -> int | None:
    for key in ("max_parallel_writer_stages", "max_parallel_writers"):
        raw = capacity.get(key)
        if isinstance(raw, int) and raw >= 1:
            return raw
    snap = _snapshot(capacity)
    for key in ("max_parallel_writer_stages", "max_parallel_writers"):
        raw = snap.get(key)
        if isinstance(raw, int) and raw >= 1:
            return raw
    total = snap.get("total_ram_mb")
    cpus = snap.get("cpu_logical")
    if not isinstance(total, (int, float)):
        # sak438-d: under CAPACITY peel, missing RAM is a miss (not soft None).
        if broker_capacity_enabled():
            raise RuntimeError(
                "broker_miss: parallel_writer_stages: ram_probe_unavailable under "
                "NIMBUSWARE_BROKER_CAPACITY=1|2"
            )
        return None
    # Rough tier: weak <8GiB → 1; medium <24GiB → 2; else 3 (capped by CPU).
    if total < 8_192:
        base = 1
    elif total < 24_576:
        base = 2
    else:
        base = 3
    if isinstance(cpus, int) and cpus > 0:
        return max(1, min(base, cpus))
    return base


def capacity_pressure_via_broker(
    *,
    client: BrokerClient | None = None,
    max_system_ram_pct: float = 75.0,
) -> dict[str, Any]:
    probe = capacity_probe_via_broker(client=client)
    level, details = pressure_from_capacity_probe(
        probe, max_system_ram_pct=max_system_ram_pct
    )
    return {"level": level, "details": details, "probe": probe}


def capacity_fit_via_broker(
    candidates: list[dict[str, Any]],
    *,
    binding_id: str,
    client: BrokerMcpClient | None = None,
) -> dict[str, Any]:
    """Invoke MCP ``capacity_fit`` when a binding_id is available (`sak439-d`)."""
    if not broker_capacity_enabled():
        raise BrokerDisabled(
            "Set NIMBUSWARE_BROKER_CAPACITY=1 or =2 to route capacity through the broker"
        )
    mcp = client or BrokerMcpClient()
    result = mcp.call_tool(
        "capacity_fit",
        {"binding_id": binding_id, "candidates": candidates},
    )
    if not isinstance(result, dict):
        raise RuntimeError(f"broker_miss: capacity_fit non-dict: {result!r}")
    if "error" in result:
        raise RuntimeError(f"broker_miss: capacity_fit: {result.get('error')!r}")
    return result


def probe_dict_from_capacity(capacity: dict[str, Any]) -> dict[str, Any]:
    snap = _snapshot(capacity)
    total_mb = snap.get("total_ram_mb")
    avail_mb = snap.get("available_ram_mb")
    cpus_raw = snap.get("cpu_logical")
    total_gb = float(total_mb) / 1024.0 if isinstance(total_mb, (int, float)) else None
    avail_gb = float(avail_mb) / 1024.0 if isinstance(avail_mb, (int, float)) else None
    cpu_count = int(cpus_raw) if isinstance(cpus_raw, (int, float)) and cpus_raw else 1
    # sak437-d: under CAPACITY peel, missing RAM must not soft-default to weak tier.
    if total_gb is None and broker_capacity_enabled():
        raise RuntimeError(
            "broker_miss: capacity probe_dict: ram_probe_unavailable under "
            "NIMBUSWARE_BROKER_CAPACITY=1|2"
        )
    # Local classify without importing hw (avoid peel cycles).
    total = total_gb or 0.0
    if total >= 32 and cpu_count >= 8:
        tier = "strong"
    elif total >= 16 and cpu_count >= 4:
        tier = "medium"
    else:
        tier = str(capacity.get("hardware_tier") or capacity.get("tier") or "weak")
        if tier not in ("weak", "medium", "strong"):
            tier = "weak"
    errors: list[str] = []
    if total_gb is None:
        errors.append("ram_probe_unavailable")
    vram_total = snap.get("total_vram_mb")
    vram_avail = snap.get("available_vram_mb")
    gpus: list[dict[str, Any]] = []
    if isinstance(vram_total, (int, float)) and vram_total > 0:
        gpus.append(
            {
                "name": "broker-gpu",
                "vram_gb": round(float(vram_total) / 1024.0, 2),
                "backend": "broker",
            }
        )
    return {
        "tier": tier,
        "ram_total_gb": round(total_gb, 2) if total_gb is not None else None,
        "ram_available_gb": round(avail_gb, 2) if avail_gb is not None else None,
        "cpu_count": cpu_count,
        "gpus": gpus,
        "gpu_groups": [[g["name"] for g in gpus]] if gpus else [],
        "unified_memory": False,
        "errors": errors,
        "platform": str(snap.get("source") or "broker_capacity"),
        "broker_capacity": True,
        "available_vram_mb": vram_avail if isinstance(vram_avail, (int, float)) else None,
    }


def available_memory_gb_from_capacity(
    capacity: dict[str, Any],
) -> tuple[float | None, float | None]:
    raw = probe_dict_from_capacity(capacity)
    return raw.get("ram_total_gb"), raw.get("ram_available_gb")


def governor_metadata_from_capacity(capacity: dict[str, Any]) -> dict[str, Any]:
    """Map capacity probe → Nimbusware ``ResourceGovernor.to_metadata`` shape (`sak420-a`).

    Uses explicit governor keys when present; otherwise derives tier/caps from the
    snapshot the same way ``probe_dict_from_capacity`` / parallel-writer helpers do.
    """
    # Prefer an already-normalized governor dict (nested or flat).
    nested = capacity.get("resource_governor")
    if isinstance(nested, dict) and "hardware_tier" in nested:
        # sak439-d: under peel, refuse soft defaults when tier/stages missing.
        if broker_capacity_enabled():
            if nested.get("hardware_tier") in (None, ""):
                raise RuntimeError(
                    "broker_miss: governor_metadata: missing hardware_tier under "
                    "NIMBUSWARE_BROKER_CAPACITY=1|2"
                )
        return {
            "max_system_ram_pct": float(nested.get("max_system_ram_pct", 75)),
            "max_vram_pct": float(nested.get("max_vram_pct", 85)),
            "reserve_ram_gb": float(nested.get("reserve_ram_gb", 2)),
            "max_parallel_writer_stages": int(nested.get("max_parallel_writer_stages", 1)),
            "allow_parallel_critics": bool(nested.get("allow_parallel_critics")),
            "auto_adjust": bool(nested.get("auto_adjust", True)),
            "hardware_tier": str(nested.get("hardware_tier") or "medium"),
            "capacity_source": "broker",
        }
    if "hardware_tier" in capacity and "max_parallel_writer_stages" in capacity:
        return {
            "max_system_ram_pct": float(capacity.get("max_system_ram_pct", 75)),
            "max_vram_pct": float(capacity.get("max_vram_pct", 85)),
            "reserve_ram_gb": float(capacity.get("reserve_ram_gb", 2)),
            "max_parallel_writer_stages": int(capacity.get("max_parallel_writer_stages", 1)),
            "allow_parallel_critics": bool(capacity.get("allow_parallel_critics")),
            "auto_adjust": bool(capacity.get("auto_adjust", True)),
            "hardware_tier": str(capacity.get("hardware_tier") or "medium"),
            "capacity_source": "broker",
        }

    # Derives via probe_dict_from_capacity (raises under peel on missing RAM).
    probe = probe_dict_from_capacity(capacity)
    tier = str(probe.get("tier") or "medium")
    if tier == "strong":
        parallel = 3
        ram_pct = 80.0
    elif tier == "medium":
        parallel = 2
        ram_pct = 75.0
    else:
        parallel = 1
        ram_pct = 70.0
    derived = parallel_writer_stages_from_capacity(capacity)
    if derived is not None:
        parallel = derived
    return {
        "max_system_ram_pct": ram_pct,
        "max_vram_pct": 85.0,
        "reserve_ram_gb": 2.0,
        "max_parallel_writer_stages": int(parallel),
        "allow_parallel_critics": tier == "strong",
        "auto_adjust": True,
        "hardware_tier": tier,
        "capacity_source": "broker",
    }
