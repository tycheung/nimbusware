from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS_UNIT = ROOT / "tests" / "unit"
MAX_LINES = 200
ALLOWLIST = frozenset(
    {
        "test_anti_deadlock_helpers_composite_contract.py",
        "test_critique_gate_fail_findings_composite_contract.py",
        "test_critique_routing_quartet_composite_contract.py",
        "test_read_models_composite_contract.py",
        "test_runs_list_composite_contract.py",
        "test_runs_list_wire_format_composite_contract.py",
        "test_scraper_artifact_retention_composite_contract.py",
        "test_security_scan_metadata_siblings_composite_contract.py",
        "test_strictness_context_critique_seam_composite_contract.py",
        "test_thresholds_loader_composite_contract.py",
        "test_timeline_summary_quintet_composite_contract.py",
    }
)


def main() -> int:
    offenders: list[str] = []
    for path in sorted(TESTS_UNIT.glob("test_*composite_contract*.py")):
        if path.name in ALLOWLIST:
            continue
        line_count = sum(1 for _ in path.open(encoding="utf-8"))
        if line_count > MAX_LINES:
            offenders.append(f"{path.name}: {line_count} lines (max {MAX_LINES})")
    if offenders:
        print("composite test size gate failed:", file=sys.stderr)
        for item in offenders:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"composite test size gate: ok (allowlist {len(ALLOWLIST)} pending migrations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
