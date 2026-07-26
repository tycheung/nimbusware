from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCRIPTS = ROOT / "scripts"


def test_audit_reverse_imports_exits_zero_and_agent_tools_cleared() -> None:

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "audit_reverse_imports.py"), "--package", "agent_tools"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0

    assert "agent_tools->orchestrator import sites: 0" in proc.stdout


def test_audit_reverse_imports_research_cleared() -> None:

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "audit_reverse_imports.py"), "--package", "research"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0

    assert "research->orchestrator import sites: 0" in proc.stdout


def test_forbidden_hits_product_edges_cleared() -> None:
    """sak408-e / sak409-e: product modules have zero forbidden CI edges (facades skipped)."""

    sys.path.insert(0, str(SCRIPTS))

    try:
        from ci_peel_import_graph import forbidden_hits, forbidden_hits_by_package

    finally:
        sys.path.pop(0)

    hits = forbidden_hits(ROOT)
    assert not any("agent_tools" in h and "orchestrator.llm" in h for h in hits)
    assert not any("research" in h and "orchestrator.registry" in h for h in hits)

    by_pkg = forbidden_hits_by_package(ROOT)
    assert by_pkg.get("agent_tools", []) == []
    assert by_pkg.get("research", []) == []


def test_ci_peel_import_graph_strict_clean_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "ci_peel_import_graph.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "peel import graph: ok" in proc.stdout


def test_ci_peel_import_graph_warn_only_on_violation(tmp_path: Path) -> None:
    pkg = tmp_path / "packages" / "agent_tools"
    pkg.mkdir(parents=True)
    offender = pkg / "bad_import.py"
    offender.write_text("from orchestrator.llm import chat\n", encoding="utf-8")

    strict = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "ci_peel_import_graph.py"),
            "--root",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1
    assert "forbidden edge" in (strict.stdout + strict.stderr).lower()

    warn = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "ci_peel_import_graph.py"),
            "--root",
            str(tmp_path),
            "--warn-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert warn.returncode == 0
    assert "forbidden edge" in warn.stdout.lower()


def test_peel_checklist_exits_zero() -> None:
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = "packages;tests"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "peel_checklist.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode == 0

    assert "broker_client importable: yes" in proc.stdout

    assert "peel bridges + stage_bind" in proc.stdout
    assert "bridges ready: yes" in proc.stdout

    assert "research->orchestrator:" in proc.stdout

    assert "default-on gate doc" in proc.stdout


def test_peel_checklist_strict_requires_default_on_gate() -> None:
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = "packages;tests"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "peel_checklist.py"), "--strict"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode == 0
    assert "default-on gate doc (`sak415-e`): ok" in proc.stdout


def test_peel_soak_prereq_exits_zero() -> None:
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = "packages;tests"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "peel_soak_prereq.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode == 0
    assert "overall: PASS" in proc.stdout
    assert "peel_checklist.py --strict" in proc.stdout


def test_peel_delete_dry_run_llm_post_delete_reports_missing() -> None:
    """After sak411, inventory paths are gone; --strict fails, non-strict lists missing."""
    strict = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "peel_delete_dry_run.py"),
            "--domain",
            "llm",
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1, strict.stdout + strict.stderr
    assert "packages/orchestrator/llm/providers" in strict.stdout

    loose = subprocess.run(
        [sys.executable, str(SCRIPTS / "peel_delete_dry_run.py"), "--domain", "llm"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert loose.returncode == 0, loose.stdout + loose.stderr
    assert "NO DELETE" in loose.stdout
    assert "exist=no" in loose.stdout


def test_peel_delete_dry_run_sandbox_and_memory_post_delete() -> None:
    for domain in ("sandbox", "memory"):
        strict = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "peel_delete_dry_run.py"),
                "--domain",
                domain,
                "--strict",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert strict.returncode == 1, strict.stdout + strict.stderr

        loose = subprocess.run(
            [sys.executable, str(SCRIPTS / "peel_delete_dry_run.py"), "--domain", domain],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert loose.returncode == 0, loose.stdout + loose.stderr
        assert "exist=no" in loose.stdout


def test_peel_delete_dry_run_all_post_delete() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "peel_delete_dry_run.py"),
            "--domain",
            "all",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "domain=llm" in proc.stdout
    assert "domain=sandbox" in proc.stdout
    assert "domain=memory" in proc.stdout
    assert "domain=research" in proc.stdout
    assert "domain=egress" in proc.stdout
    assert "domain=all summary" in proc.stdout
    assert "missing_total=" in proc.stdout
    assert "missing_total=0" not in proc.stdout


def test_peel_delete_dry_run_research_and_egress() -> None:
    """sak416-f/g: research thin stub present; egress.py delete absent."""
    research = subprocess.run(
        [sys.executable, str(SCRIPTS / "peel_delete_dry_run.py"), "--domain", "research"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert research.returncode == 0, research.stdout + research.stderr
    assert "packages/research/fetch.py" in research.stdout
    assert "exist=yes" in research.stdout

    egress = subprocess.run(
        [sys.executable, str(SCRIPTS / "peel_delete_dry_run.py"), "--domain", "egress"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert egress.returncode == 0, egress.stdout + egress.stderr
    assert "packages/executor/egress.py" in egress.stdout
    assert "exist=no" in egress.stdout
    assert "packages/executor/fetch.py" in egress.stdout


def test_peel_delete_dry_run_tools_alias_matches_sandbox() -> None:
    """sak412-c: tools domain is an alias of sandbox inventory (paths absent post-delete)."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "peel_delete_dry_run.py"),
            "--domain",
            "tools",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "domain=tools" in proc.stdout
    assert "packages/agent_tools/sandbox.py" in proc.stdout
    assert "exist=no" in proc.stdout


def test_ci_peel_delete_guard_pre_delete_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "ci_peel_delete_guard.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "pre-delete" in proc.stdout


def test_ci_peel_delete_guard_post_delete_fails_when_paths_exist(tmp_path: Path) -> None:
    """--post-delete fails when inventory paths still exist on disk."""
    inv = tmp_path / "packages" / "orchestrator" / "llm" / "providers"
    inv.mkdir(parents=True)
    (inv / "stub.py").write_text("# peel guard test\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "ci_peel_delete_guard.py"),
            "--root",
            str(tmp_path),
            "--post-delete",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "post-delete" in (proc.stdout + proc.stderr).lower()
    assert "still exist" in (proc.stdout + proc.stderr).lower()


def test_ci_peel_delete_guard_post_delete_ok_on_repo() -> None:
    """sak411–413 executed: live repo inventory paths must be gone."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "ci_peel_delete_guard.py"), "--post-delete"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "post-delete: ok" in proc.stdout


def test_ci_peel_delete_guard_post_delete_ok_when_paths_gone(tmp_path: Path) -> None:
    """Empty root: delete paths absent OK; create thin stubs so thin-must-exist passes."""
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from ci_peel_delete_guard import inventory_candidates

    for candidate in inventory_candidates():
        if candidate.action != "thin":
            continue
        target = tmp_path / candidate.rel_path
        if candidate.rel_path.endswith(".py"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# thin stub\n", encoding="utf-8")
        else:
            target.mkdir(parents=True, exist_ok=True)
            (target / "__init__.py").write_text("# thin stub\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "ci_peel_delete_guard.py"),
            "--root",
            str(tmp_path),
            "--post-delete",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "post-delete: ok" in proc.stdout


def test_peel_soak_smoke_exits_zero() -> None:
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = "packages;tests"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "peel_soak_smoke.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "overall: PASS" in proc.stdout
    assert "sak406-h" in proc.stdout
    assert "sak407-f" in proc.stdout
    assert "stage wire active" in proc.stdout
