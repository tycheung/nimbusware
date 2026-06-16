from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_env.env_flags import nimbusware_run_perf_scan_enabled
from nimbusware_orchestrator.performance_scan import run_ruff_perf, scan_n_plus_one_heuristic
from nimbusware_orchestrator.security_semgrep import run_semgrep_scan
from nimbusware_orchestrator.verifiers import run_bandit, run_mypy, run_ruff_check

SECURITY_SCAN_CATEGORIES: tuple[str, ...] = (
    "ruff",
    "bandit",
    "mypy",
    "ruff_perf",
    "n_plus_one_heuristic",
    "semgrep",
    "sql_profiler",
)


def _optional_perf_scanners_enabled() -> bool:
    return nimbusware_run_perf_scan_enabled()


def run_security_scan(
    workspace: Path,
) -> tuple[int, str, int, int, int, int, int, int]:
    """Run security scanners and optional perf/N+1/semgrep when enabled.

    Returns ``(worst_exit, merged_log, ruff, bandit, mypy, ruff_perf, n_plus_one, semgrep)``.
    Skipped tools count as success (exit 0).
    """
    ruff_code, ruff_out = run_ruff_check(workspace)
    bandit_code, bandit_out = run_bandit(workspace)
    mypy_code, mypy_out = run_mypy(workspace)
    perf_code, perf_out = (0, "ruff perf skipped\n")
    n1_code, n1_out = (0, "n+1 heuristic skipped\n")
    if _optional_perf_scanners_enabled():
        perf_code, perf_out = run_ruff_perf(workspace)
        n1_code, n1_out = scan_n_plus_one_heuristic(workspace)
    semgrep_code, semgrep_out = run_semgrep_scan(workspace)
    worst = max(ruff_code, bandit_code, mypy_code, perf_code, n1_code, semgrep_code)
    log = (
        f"=== ruff (exit {ruff_code}) ===\n{ruff_out}\n"
        f"=== bandit (exit {bandit_code}) ===\n{bandit_out}\n"
        f"=== mypy (exit {mypy_code}) ===\n{mypy_out}\n"
        f"=== ruff_perf (exit {perf_code}) ===\n{perf_out}\n"
        f"=== n_plus_one_heuristic (exit {n1_code}) ===\n{n1_out}\n"
        f"{semgrep_out}"
    )
    return worst, log, ruff_code, bandit_code, mypy_code, perf_code, n1_code, semgrep_code


def security_scan_tool_summary(
    ruff_exit: int,
    bandit_exit: int,
    mypy_exit: int = 0,
    ruff_perf_exit: int = 0,
    n_plus_one_exit: int = 0,
    semgrep_exit: int = 0,
    sql_profiler_exit: int = 0,
) -> dict[str, Any]:
    return {
        "security_scan_categories": list(SECURITY_SCAN_CATEGORIES),
        "security_scan_tools": {
            "ruff": ruff_exit,
            "bandit": bandit_exit,
            "mypy": mypy_exit,
            "ruff_perf": ruff_perf_exit,
            "n_plus_one_heuristic": n_plus_one_exit,
            "semgrep": semgrep_exit,
            "sql_profiler": sql_profiler_exit,
        },
    }
