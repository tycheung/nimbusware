from __future__ import annotations

from typing import Any

from orchestrator.interaction.interaction_surface_map import InteractionSurfaceMap, coverage_pct


def critique_interaction_surfaces(
    ism: InteractionSurfaceMap,
    exercised: set[str],
    *,
    tier: str = "T1",
    min_coverage_pct: float = 50.0,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not ism.surfaces:
        findings.append(
            {
                "critic": "interaction_surface",
                "severity": "high",
                "kind": "ism_empty",
                "message": "Interaction surface map has no discovered surfaces",
                "tier": tier,
            },
        )
        return findings

    pct = coverage_pct(ism, exercised)
    if pct < min_coverage_pct:
        findings.append(
            {
                "critic": "interaction_surface",
                "severity": "medium",
                "kind": "ism_low_coverage",
                "message": f"ISM coverage {pct}% below threshold {min_coverage_pct}%",
                "ism_coverage_pct": pct,
                "tier": tier,
            },
        )

    uncovered = [
        s for s in ism.surfaces if s.surface_id not in exercised and s.path not in exercised
    ]
    for surface in uncovered[:5]:
        findings.append(
            {
                "critic": "interaction_surface",
                "severity": "operational",
                "kind": "ism_uncovered_surface",
                "message": f"Surface not exercised: {surface.path}",
                "surface_id": surface.surface_id,
                "surface_path": surface.path,
                "tier": tier,
            },
        )

    if not findings:
        findings.append(
            {
                "critic": "interaction_surface",
                "severity": "info",
                "kind": "ism_ok",
                "message": f"ISM coverage acceptable at {pct}%",
                "ism_coverage_pct": pct,
                "tier": tier,
            },
        )
    return findings
