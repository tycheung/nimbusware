from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


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
