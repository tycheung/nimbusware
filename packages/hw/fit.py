"""Thin model fit ranking (`sak419-e`). Prefer broker profile; legacy under dual-run/`=0`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from broker_client.flags import broker_capacity_enabled
from hw.profile import HardwareProfile

FIT_LEVELS = ("perfect", "good", "marginal", "too_tight")

_MSG = (
    "hw.fit local path unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
    "use SwissArmyNoife capacity probe + local rank on broker profile "
    "(MCP capacity_fit needs binding_id)"
)


def _legacy():
    from hw import fit_legacy as legacy

    return legacy


def rank_models(
    repo_root: Path,
    profile: HardwareProfile,
    *,
    installed_tags: list[str] | None = None,
    use_case: str = "coding",
    gpu_only: bool = False,
    gpu_group_index: int = 0,
    limit: int = 50,
    binding_id: str | None = None,
    candidates: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Rank models. Under CAPACITY=1|2 prefer broker-derived profile when ``profile`` is local-empty.

    When ``binding_id`` + ``candidates`` are provided, try MCP ``capacity_fit`` first (`sak430-g`).
    Ranking math otherwise stays in ``fit_legacy``; under CAPACITY=1|2 refuse when the
    capacity probe itself is unavailable (no local profile fallthrough).
    """
    if broker_capacity_enabled() and binding_id and candidates is not None:
        from hw.capacity_route import refuse_legacy

        try:
            from broker_client.stage_bind.capacity import capacity_fit_via_broker

            hit = capacity_fit_via_broker(candidates, binding_id=binding_id)
            ranked = hit.get("ranked") if isinstance(hit, dict) else None
            if isinstance(ranked, list):
                return [r for r in ranked if isinstance(r, dict)][:limit]
            result = hit.get("result") if isinstance(hit, dict) else None
            if isinstance(result, list):
                return [r for r in result if isinstance(r, dict)][:limit]
        except RuntimeError:
            # sak440-c / sak490-d: re-raise peel miss (error-dict / broker_miss) without swallowing.
            raise
        except Exception:
            refuse_legacy(_MSG)
    active_profile = profile
    if broker_capacity_enabled():
        from broker_client.capacity_bridge import try_broker_probe_dict
        from hw.capacity_route import refuse_legacy
        from hw.profile import profile_from_probe

        hit = try_broker_probe_dict()
        if hit is not None:
            active_profile = profile_from_probe(hit)
        else:
            refuse_legacy(_MSG)
    return _legacy().rank_models(
        repo_root,
        active_profile,
        installed_tags=installed_tags,
        use_case=use_case,
        gpu_only=gpu_only,
        gpu_group_index=gpu_group_index,
        limit=limit,
    )
