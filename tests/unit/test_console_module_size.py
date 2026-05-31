"""Console module size guard — shrink allowlist as Lane X splits land."""

from __future__ import annotations

from pathlib import Path

_CONSOLE_ROOT = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"

# Modules still >400 lines (May 2026). Remove entries when splits land.
_ALLOWLIST_OVER_400: frozenset[str] = frozenset(
    {
        "agent_evaluator_display.py",
        "agent_evaluator_workflow_explainer.py",
        "bundle_catalog/catalog_local/search.py",
        "bundle_catalog/faiss_status/drilldown.py",
        "escalation_suppress_workflow_explainer.py",
        "integrator_gate/latest_delta.py",
        "integrator_preview/merge.py",
        "integrator_threshold_explainer.py",
        "pages/_state_run_list.py",
        "pages/config_tooling/bundles/catalog_search.py",
        "pages/config_tooling/workflows/persona_shelves.py",
        "pages/run_detail/_imports_display_a.py",
        "pages/run_detail/timeline_escalation.py",
        "pages/run_detail/timeline_integrator.py",
        "pages/run_detail/timeline_misc_security.py",
        "pages/run_detail/timeline_personas.py",
        "persona_catalog/summary.py",
        "preflight_cross_run_display.py",
        "prune_status_display.py",
        "run_list_pagination_display.py",
        "security_scan_metadata_workflow_explainer.py",
        "self_refinement_workflow_explainer.py",
        "universal_critique_timeline_display.py",
        "universal_critique_workflow_explainer.py",
    },
)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_console_module_over_400_lines() -> None:
    over_limit: list[str] = []
    for path in sorted(_CONSOLE_ROOT.rglob("*.py")):
        rel = path.relative_to(_CONSOLE_ROOT).as_posix()
        lines = _line_count(path)
        if lines > 400 and rel not in _ALLOWLIST_OVER_400:
            over_limit.append(f"{rel}: {lines} lines")
    assert not over_limit, "New console modules exceed 400 lines:\n" + "\n".join(over_limit)


def test_console_module_size_allowlist_is_current() -> None:
    """Allowlist must match modules still >400 lines (no stale entries)."""
    still_large = {
        path.relative_to(_CONSOLE_ROOT).as_posix()
        for path in _CONSOLE_ROOT.rglob("*.py")
        if _line_count(path) > 400
    }
    assert still_large == set(_ALLOWLIST_OVER_400), (
        f"Update _ALLOWLIST_OVER_400: extra={still_large - set(_ALLOWLIST_OVER_400)!r} "
        f"missing={set(_ALLOWLIST_OVER_400) - still_large!r}"
    )
