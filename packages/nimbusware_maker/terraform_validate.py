from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal


def _terraform_files(workspace: Path) -> list[Path]:
    if not workspace.is_dir():
        return []
    return sorted(workspace.rglob("*.tf"))


def validate_workspace_terraform(workspace: Path) -> dict[str, Any]:
    ws = workspace.resolve()
    tf_files = _terraform_files(ws)
    if not tf_files:
        return {
            "status": "skipped",
            "detail": "No .tf files in workspace",
            "terraform_available": shutil.which("terraform") is not None,
            "files_checked": 0,
        }

    terraform = shutil.which("terraform")
    if terraform is None:
        return {
            "status": "failed",
            "detail": "terraform CLI not found on PATH",
            "terraform_available": False,
            "files_checked": len(tf_files),
        }

    root = ws
    for candidate in {f.parent for f in tf_files}:
        if (candidate / "main.tf").is_file() or (candidate / "versions.tf").is_file():
            root = candidate
            break

    fmt = subprocess.run(
        [terraform, "fmt", "-check", "-recursive", str(root)],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )
    if fmt.returncode != 0:
        return {
            "status": "failed",
            "detail": "terraform fmt -check failed",
            "terraform_available": True,
            "files_checked": len(tf_files),
            "stderr": (fmt.stderr or fmt.stdout or "")[:2000],
        }

    init = subprocess.run(
        [terraform, "init", "-backend=false", "-input=false"],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )
    if init.returncode != 0:
        return {
            "status": "failed",
            "detail": "terraform init failed",
            "terraform_available": True,
            "files_checked": len(tf_files),
            "stderr": (init.stderr or init.stdout or "")[:2000],
        }

    validate = subprocess.run(
        [terraform, "validate"],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )
    if validate.returncode != 0:
        return {
            "status": "failed",
            "detail": "terraform validate failed",
            "terraform_available": True,
            "files_checked": len(tf_files),
            "stderr": (validate.stderr or validate.stdout or "")[:2000],
        }

    plan = subprocess.run(
        [terraform, "plan", "-input=false", "-no-color"],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )
    plan_ok = plan.returncode == 0
    plan_path = root / ".nimbusware" / "terraform.plan.txt"
    if plan_ok:
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text((plan.stdout or "")[:50000], encoding="utf-8")

    return {
        "status": "passed" if plan_ok else "failed",
        "detail": "terraform plan ok" if plan_ok else "terraform plan failed",
        "terraform_available": True,
        "files_checked": len(tf_files),
        "plan_artifact": str(plan_path.relative_to(ws)) if plan_ok else "",
        "stderr": "" if plan_ok else (plan.stderr or plan.stdout or "")[:2000],
    }


def _terraform_root(workspace: Path) -> tuple[Path, list[Path]]:
    ws = workspace.resolve()
    tf_files = _terraform_files(ws)
    if not tf_files:
        return ws, []
    root = ws
    for candidate in {f.parent for f in tf_files}:
        if (candidate / "main.tf").is_file() or (candidate / "versions.tf").is_file():
            root = candidate
            break
    return root, tf_files


def _snapshot_terraform_state(root: Path, workspace: Path) -> str:
    state = root / "terraform.tfstate"
    if not state.is_file():
        return ""
    backup_dir = root / ".nimbusware"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "terraform.tfstate.snapshot"
    shutil.copy2(state, backup)
    ws = workspace.resolve()
    try:
        return str(backup.relative_to(ws))
    except ValueError:
        return str(backup)


def apply_workspace_terraform(workspace: Path) -> dict[str, Any]:
    root, tf_files = _terraform_root(workspace)
    if not tf_files:
        return {
            "status": "skipped",
            "detail": "No .tf files in workspace",
            "terraform_available": shutil.which("terraform") is not None,
        }
    terraform = shutil.which("terraform")
    if terraform is None:
        return {
            "status": "failed",
            "detail": "terraform CLI not found on PATH",
            "terraform_available": False,
        }
    snapshot_ref = _snapshot_terraform_state(root, workspace)
    apply = subprocess.run(
        [terraform, "apply", "-auto-approve", "-input=false", "-no-color"],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )
    ok = apply.returncode == 0
    live_urls: dict[str, str] = {}
    if ok:
        outputs = subprocess.run(
            [terraform, "output", "-json"],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        if outputs.returncode == 0 and outputs.stdout.strip():
            try:
                import json

                parsed = json.loads(outputs.stdout)
                if isinstance(parsed, dict):
                    for key in ("api_url", "web_url"):
                        raw = parsed.get(key)
                        if isinstance(raw, dict) and raw.get("value"):
                            live_urls[key] = str(raw["value"])
            except json.JSONDecodeError:
                pass
    meta: dict[str, Any] = {}
    if live_urls:
        meta["live_urls"] = live_urls
        if live_urls.get("api_url"):
            meta["api_url"] = live_urls["api_url"]
        if live_urls.get("web_url"):
            meta["web_url"] = live_urls["web_url"]
    return {
        "status": "passed" if ok else "failed",
        "detail": "terraform apply ok" if ok else "terraform apply failed",
        "terraform_available": True,
        "stderr": "" if ok else (apply.stderr or apply.stdout or "")[:2000],
        "state_snapshot": snapshot_ref,
        **meta,
    }


RollbackMode = Literal["destroy", "previous"]


def rollback_workspace_terraform(workspace: Path, *, mode: RollbackMode = "destroy") -> dict[str, Any]:
    root, tf_files = _terraform_root(workspace)
    if not tf_files:
        return {
            "status": "skipped",
            "detail": "No .tf files in workspace",
            "terraform_available": shutil.which("terraform") is not None,
        }
    terraform = shutil.which("terraform")
    if terraform is None:
        return {
            "status": "failed",
            "detail": "terraform CLI not found on PATH",
            "terraform_available": False,
        }
    if mode == "previous":
        backup = root / ".nimbusware" / "terraform.tfstate.snapshot"
        if not backup.is_file():
            return {
                "status": "skipped",
                "detail": "No pre-apply state snapshot — run apply first",
                "terraform_available": True,
                "rollback_mode": mode,
            }
        shutil.copy2(backup, root / "terraform.tfstate")
        cmd = [terraform, "apply", "-auto-approve", "-input=false", "-no-color"]
        detail_ok = "terraform rollback to previous state ok"
        detail_fail = "terraform rollback to previous state failed"
    else:
        cmd = [terraform, "destroy", "-auto-approve", "-input=false", "-no-color"]
        detail_ok = "terraform destroy ok"
        detail_fail = "terraform destroy failed"
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=root, check=False)
    ok = proc.returncode == 0
    return {
        "status": "passed" if ok else "failed",
        "detail": detail_ok if ok else detail_fail,
        "terraform_available": True,
        "rollback_mode": mode,
        "stderr": "" if ok else (proc.stderr or proc.stdout or "")[:2000],
    }
