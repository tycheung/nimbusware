#!/usr/bin/env python3
"""CI gate: block new hand-written ``*_table_rows_csv`` exports outside explainer_core."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE_ROOT = ROOT / "packages" / "nimbusware_console"

# Existing modules with hand-written ``def *_table_rows_csv`` (migrate via explainer_core).
ALLOWLISTED_HAND_WRITTEN_TABLE_ROWS_CSV: frozenset[str] = frozenset(
    {
        "packages/nimbusware_console/agent_evaluator_display/captions.py",
        "packages/nimbusware_console/agent_evaluator_display/metrics.py",
        "packages/nimbusware_console/bundle_catalog/catalog_local/rollup_without_id.py",
        "packages/nimbusware_console/bundle_catalog/catalog_local/rollup_without_tags.py",
        "packages/nimbusware_console/bundle_catalog/catalog_local/search/hits.py",
        "packages/nimbusware_console/bundle_catalog/catalog_local/search/local_bundles.py",
        "packages/nimbusware_console/bundle_catalog/catalog_local/summary.py",
        "packages/nimbusware_console/bundle_catalog/catalog_local/tags.py",
        "packages/nimbusware_console/bundle_catalog/faiss_status/drilldown/tables.py",
        "packages/nimbusware_console/bundle_catalog/faiss_status/index_status.py",
        "packages/nimbusware_console/bundle_catalog/faiss_status/readiness.py",
        "packages/nimbusware_console/components/operator_metrics.py",
        "packages/nimbusware_console/components/workflow_explainer_helpers.py",
        "packages/nimbusware_console/critic_matrix_display.py",
        "packages/nimbusware_console/escalation_suppress_workflow_explainer/policy_tables.py",
        "packages/nimbusware_console/findings_display.py",
        "packages/nimbusware_console/integrator_gate/history.py",
        "packages/nimbusware_console/integrator_gate/latest_delta/exports.py",
        "packages/nimbusware_console/integrator_preview/exports.py",
        "packages/nimbusware_console/persona_assignment_display.py",
        "packages/nimbusware_console/persona_catalog/pairings.py",
        "packages/nimbusware_console/persona_catalog/summary/build.py",
        "packages/nimbusware_console/preflight_history_display.py",
        "packages/nimbusware_console/run_escalated/rows.py",
        "packages/nimbusware_console/run_list_pagination_display/run_detail_summary.py",
        "packages/nimbusware_console/run_list_pagination_display/timeline_events.py",
        "packages/nimbusware_console/scraper_fetch_display.py",
        "packages/nimbusware_console/security_scan_on_verify/latest.py",
        "packages/nimbusware_console/security_scan_on_verify/timeline.py",
        "packages/nimbusware_console/self_refinement/latest.py",
        "packages/nimbusware_console/self_refinement/marker_history.py",
        "packages/nimbusware_console/self_refinement_workflow_explainer/marker_exports.py",
    }
)

_TABLE_ROWS_CSV_DEF = re.compile(r"^def \w+_table_rows_csv\b", re.MULTILINE)


def _rel_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def find_violations() -> list[str]:
    offenders: list[str] = []
    for path in sorted(CONSOLE_ROOT.rglob("*.py")):
        if "explainer_core" in path.parts:
            continue
        rel = _rel_posix(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not _TABLE_ROWS_CSV_DEF.search(text):
            continue
        if rel not in ALLOWLISTED_HAND_WRITTEN_TABLE_ROWS_CSV:
            offenders.append(rel)
    return offenders


def main() -> int:
    offenders = find_violations()
    if offenders:
        print(
            "New hand-written *_table_rows_csv exports outside explainer_core/ — "
            "use explainer_core.operator_metrics_exports instead:",
            file=sys.stderr,
        )
        for rel in offenders:
            print(f"  {rel}", file=sys.stderr)
        return 1
    print("explainer export lint gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
