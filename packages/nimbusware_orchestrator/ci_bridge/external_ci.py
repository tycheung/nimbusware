"""Map ``gate.decision.emitted`` to external CI (GitHub Checks / GitLab); env-gated, no-op in CI."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from uuid import UUID


def _github_token() -> str | None:
    raw = os.environ.get("GITHUB_TOKEN", "").strip()
    return raw or None


def _github_repo() -> tuple[str, str] | None:
    raw = os.environ.get("NIMBUSWARE_CI_GITHUB_REPO", "").strip()
    if "/" not in raw:
        return None
    owner, repo = raw.split("/", 1)
    if not owner or not repo:
        return None
    return owner, repo


def _post_json(url: str, body: dict[str, Any], token: str) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def notify_gate_decision_external(
    *,
    run_id: UUID,
    verdict: str,
    stage_name: str,
    timeline_base_url: str | None = None,
) -> dict[str, Any]:
    """Best-effort external CI notification; returns status dict (never raises)."""
    token = _github_token()
    repo = _github_repo()
    if not token or not repo:
        return {"status": "skipped", "reason": "github_not_configured"}
    owner, name = repo
    base = (timeline_base_url or os.environ.get("NIMBUSWARE_TIMELINE_BASE_URL", "")).strip()
    link = f"{base.rstrip('/')}/v1/runs/{run_id}/timeline" if base else ""
    conclusion = "success" if str(verdict).upper() == "PASS" else "failure"
    sha = os.environ.get("NIMBUSWARE_CI_HEAD_SHA", "0000000000000000000000000000000000000000")
    check_name = f"nimbusware/{stage_name}"
    url = f"https://api.github.com/repos/{owner}/{name}/check-runs"
    body: dict[str, Any] = {
        "name": check_name,
        "head_sha": sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": f"Nimbusware gate {stage_name}",
            "summary": f"Verdict: {verdict}",
        },
    }
    if link:
        body["output"]["text"] = f"Timeline: {link}"
    try:
        result = _post_json(url, body, token)
        return {"status": "posted", "check_run_id": result.get("id")}
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "error", "reason": str(exc)[:200]}
