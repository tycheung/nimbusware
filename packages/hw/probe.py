"""Thin hardware probe (`sak419-a`). Prefer broker capacity; legacy under dual-run/`=0`."""

from __future__ import annotations

from typing import Any

from broker_client.flags import broker_capacity_enabled

_MSG = (
    "hw.probe local path unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
    "use SwissArmyNoife HTTP /v1/sak/capacity"
)


def _legacy():
    from hw import probe_legacy as legacy

    return legacy


def available_memory_gb() -> tuple[float | None, float | None]:
    """Prefer broker snapshot RAM; else local legacy."""
    if broker_capacity_enabled():
        from broker_client.capacity_bridge import try_broker_capacity_probe
        from broker_client.stage_bind.capacity import available_memory_gb_from_capacity

        hit = try_broker_capacity_probe()
        if hit is not None:
            return available_memory_gb_from_capacity(hit)
        # sak432-i: CAPACITY=1|2 refuse silent local fallback.
        raise RuntimeError(_MSG)
    return _legacy().available_memory_gb()


def classify_tier(*, ram_total_gb: float | None, cpu_count: int) -> str:
    return _legacy().classify_tier(ram_total_gb=ram_total_gb, cpu_count=cpu_count)


def probe_hardware_remote_ssh(host: str) -> dict[str, Any]:
    """SSH fleet probe — refused when CAPACITY peel is on (`sak432-i`)."""
    if broker_capacity_enabled():
        raise RuntimeError(
            "hw.probe remote SSH unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
            "use SwissArmyNoife /v1/sak/capacity"
        )
    return _legacy().probe_hardware_remote_ssh(host)


def probe_hardware(*, fixture: str | None = None, remote_host: str | None = None) -> dict[str, Any]:
    """Broker-first local probe; fixtures stay on the legacy path when CAPACITY off."""
    if remote_host and remote_host.strip():
        if broker_capacity_enabled():
            raise RuntimeError(
                "hw.probe remote_host unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
                "use SwissArmyNoife /v1/sak/capacity"
            )
        return _legacy().probe_hardware(remote_host=remote_host.strip())
    if fixture:
        # sak489-c: fixture probes are legacy-only; refuse under CAPACITY peel.
        if broker_capacity_enabled():
            raise RuntimeError(
                "hw.probe fixture unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
                "use SwissArmyNoife /v1/sak/capacity"
            )
        return _legacy().probe_hardware(fixture=fixture)
    from env.env_flags import hw_fixture

    if hw_fixture():
        # sak489-c: hw_fixture() env bypass is legacy-only under CAPACITY peel.
        if broker_capacity_enabled():
            raise RuntimeError(
                "hw.probe hw_fixture unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
                "use SwissArmyNoife /v1/sak/capacity"
            )
        return _legacy().probe_hardware(fixture=hw_fixture())
    if broker_capacity_enabled():
        from broker_client.capacity_bridge import try_broker_capacity_probe
        from broker_client.stage_bind.capacity import probe_dict_from_capacity

        hit = try_broker_capacity_probe()
        if hit is not None:
            return probe_dict_from_capacity(hit)
        raise RuntimeError(_MSG)
    return _legacy().probe_hardware()
