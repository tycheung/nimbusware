#!/usr/bin/env python3
"""Nimbusware end-to-end operator smoke checks.

Exit 0 when all required checks pass. Attempts Docker Postgres when DB is down.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_URL = "postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware"
REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from nimbusware_env import load_dotenv

    load_dotenv(repo_root=REPO_ROOT)
except ImportError:
    pass


def _poetry() -> str:
    for name in ("poetry", "poetry.exe"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("Poetry not found on PATH; install Poetry or activate the Nimbusware venv.")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _log(msg: str) -> None:
    print(msg, flush=True)


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    _log(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=cwd or REPO_ROOT, env=env, text=True)
    return proc.returncode


def _postgres_reachable(url: str) -> bool:
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=3):
            return True
    except Exception:
        return False


def _docker_compose_cmd() -> list[str] | None:
    import shutil

    if not shutil.which("docker"):
        return None
    probe = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def _try_start_postgres_docker() -> bool:
    compose = REPO_ROOT / "docker-compose.yml"
    cmd = _docker_compose_cmd()
    if not compose.is_file() or not cmd:
        return False
    _log("Starting postgres via docker compose...")
    if _run([*cmd, "-f", str(compose), "up", "-d", "postgres"], cwd=REPO_ROOT) != 0:
        return False
    return True


def _wait_postgres(url: str, *, attempts: int = 60) -> bool:
    for i in range(attempts):
        if _postgres_reachable(url):
            return True
        time.sleep(2)
    return False


def _schema_applied(url: str) -> bool:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from postgres_schema import event_store_present  # noqa: PLC0415

    return event_store_present(url)


def _apply_schema(url: str) -> bool:
    sql_path = REPO_ROOT / "packages/hermes_store/schema/postgres.sql"
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from postgres_schema import apply_sql_file  # noqa: PLC0415

    return apply_sql_file(url, sql_path, log=_log)


def _poetry_run_python(snippet: str) -> int:
    return _run([_poetry(), "run", "python", "-c", snippet], cwd=REPO_ROOT)


def check_bootstrap() -> CheckResult:
    ok = (REPO_ROOT / "pyproject.toml").is_file() and (REPO_ROOT / "packages").is_dir()
    return CheckResult("bootstrap", ok, str(REPO_ROOT), required=True)


def check_poetry_env() -> CheckResult:
    code = _poetry_run_python("import nimbusware_api, hermes_orchestrator")
    return CheckResult(
        "poetry_env",
        code == 0,
        "imports nimbusware_api, hermes_orchestrator",
        required=True,
    )


def check_unit_tests(*, full_suite: bool) -> CheckResult:
    env = os.environ.copy()
    env.setdefault("HERMES_SKIP_PREFLIGHT", "1")
    env.setdefault("NIMBUSWARE_REPO_ROOT", str(REPO_ROOT))
    if full_suite:
        gate = REPO_ROOT / ".cursor/loop-artifacts/_round_gates.ps1"
        if sys.platform == "win32" and gate.is_file():
            cmd = ["powershell", "-File", str(gate)]
            label = "round_gates.ps1 aggregate pytest bundle"
        else:
            cmd = [_poetry(), "run", "pytest", "tests", "-q", "-m", "not integration"]
            label = "pytest -m 'not integration' (full unit gate)"
    else:
        cmd = [
            _poetry(),
            "run",
            "pytest",
            "tests/api/test_api.py::test_create_run_and_timeline",
            "tests/unit/test_extensions_yaml.py",
            "tests/e2e/test_operator_smoke_checks.py",
            "-q",
            "--maxfail=1",
        ]
        label = "pytest focused unit smoke"
    code = _run(cmd, env=env)
    return CheckResult("unit_tests", code == 0, label, required=True)


def check_postgres(url: str, *, try_docker: bool) -> CheckResult:
    if _postgres_reachable(url):
        return CheckResult("postgres", True, url, required=True)
    if try_docker and _try_start_postgres_docker() and _wait_postgres(url):
        return CheckResult("postgres", True, f"{url} (via docker compose)", required=True)
    return CheckResult("postgres", False, f"not reachable: {url}", required=True)


def check_schema(url: str) -> CheckResult:
    if not _postgres_reachable(url):
        return CheckResult("schema", False, "postgres down", required=True)
    if _schema_applied(url):
        return CheckResult("schema", True, "event_store present", required=True)
    _log("Applying postgres.sql...")
    if not _apply_schema(url):
        return CheckResult("schema", False, "apply failed", required=True)
    if _schema_applied(url):
        return CheckResult("schema", True, "event_store present after apply", required=True)
    return CheckResult("schema", False, "event_store missing after apply", required=True)


def check_integration(url: str) -> CheckResult:
    env = os.environ.copy()
    env["NIMBUSWARE_DATABASE_URL"] = url
    env.setdefault("NIMBUSWARE_REPO_ROOT", str(REPO_ROOT))
    env.setdefault("HERMES_SKIP_PREFLIGHT", "1")
    code = _run(
        [_poetry(), "run", "pytest", "tests", "-q", "-m", "integration", "--maxfail=3"],
        env=env,
    )
    return CheckResult("integration", code == 0, "pytest -m integration", required=True)


def check_api_smoke() -> CheckResult:
    snippet = """
import os
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", %r)
from fastapi.testclient import TestClient
from nimbusware_api.app import app
with TestClient(app) as client:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    t = client.get(f"/v1/runs/{run_id}/timeline")
    assert t.status_code == 200, t.text
    assert len(t.json().get("events", [])) >= 1
print("api_smoke ok")
""" % str(REPO_ROOT)
    code = _poetry_run_python(snippet)
    return CheckResult("api_run_smoke", code == 0, "TestClient POST /v1/runs + timeline", required=True)


def check_console_smoke() -> CheckResult:
    snippet = """
import importlib.util
spec = importlib.util.find_spec("nimbusware_console.app")
assert spec is not None
print("console_smoke ok")
"""
    code = _poetry_run_python(snippet)
    return CheckResult("console_import", code == 0, "import nimbusware_console.app", required=True)


def check_faiss_stale_rebuild() -> CheckResult:
    script = REPO_ROOT / "scripts" / "rebuild_bundle_faiss_if_stale.py"
    if not script.is_file():
        return CheckResult("faiss_rebuild", False, "missing rebuild_bundle_faiss_if_stale.py", required=False)
    code = _run([sys.executable, str(script), "--dry-run"], cwd=REPO_ROOT)
    return CheckResult(
        "faiss_rebuild",
        code == 0,
        "rebuild_bundle_faiss_if_stale.py --dry-run",
        required=False,
    )


def check_install_script() -> CheckResult:
    script = REPO_ROOT / "scripts" / "install_nimbusware.py"
    code = _run([sys.executable, str(script), "--check-only"], cwd=REPO_ROOT)
    return CheckResult("install_check", code == 0, "install_nimbusware.py --check-only", required=True)


def run_checks(
    *,
    profile: str,
    database_url: str,
    try_docker: bool,
    skip_integration: bool,
    skip_install: bool,
) -> list[CheckResult]:
    full = profile == "full"
    results: list[CheckResult] = []
    results.append(check_bootstrap())
    if not skip_install:
        results.append(check_install_script())
    results.append(check_poetry_env())
    pg = check_postgres(database_url, try_docker=try_docker and full)
    if full:
        results.append(pg)
        if pg.ok:
            results.append(check_schema(database_url))
    results.append(check_unit_tests(full_suite=full))
    if full and pg.ok and not skip_integration:
        schema_ok = next((r for r in results if r.name == "schema"), None)
        if schema_ok and schema_ok.ok:
            results.append(check_integration(database_url))
    else:
        results.append(
            CheckResult(
                "postgres",
                pg.ok,
                pg.detail if pg.ok else f"skipped in app profile ({pg.detail})",
                required=False,
            ),
        )
    results.append(check_api_smoke())
    results.append(check_console_smoke())
    results.append(check_faiss_stale_rebuild())
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nimbusware end-to-end operator smoke checks.")
    parser.add_argument("--database-url", default=os.environ.get("NIMBUSWARE_DATABASE_URL", DEFAULT_DATABASE_URL))
    parser.add_argument("--no-docker", action="store_true", help="Do not try docker compose for Postgres")
    parser.add_argument("--skip-integration", action="store_true")
    parser.add_argument("--skip-install-check", action="store_true")
    parser.add_argument(
        "--profile",
        choices=("app", "full"),
        default="app",
        help="app=fast smoke without Postgres; full=CI parity including integration",
    )
    args = parser.parse_args(argv)

    _log(f"Nimbusware E2E smoke (profile={args.profile})")
    results = run_checks(
        profile=args.profile,
        database_url=args.database_url.strip(),
        try_docker=not args.no_docker,
        skip_integration=args.skip_integration,
        skip_install=args.skip_install_check,
    )
    failed = 0
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        req = "required" if r.required else "optional"
        _log(f"  [{mark}] {r.name} ({req}): {r.detail}")
        if r.required and not r.ok:
            failed += 1
    _log("")
    if failed:
        _log(f"E2E smoke: {failed} required check(s) failed")
        return 1
    _log("E2E smoke: all required checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
