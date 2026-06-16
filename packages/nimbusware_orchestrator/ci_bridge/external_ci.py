from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, cast
from uuid import UUID

from nimbusware_env.env_flags import (
    nimbusware_ci_github_repo,
    nimbusware_ci_gitlab_project,
    nimbusware_ci_head_sha,
    nimbusware_github_token,
    nimbusware_gitlab_api_base,
    nimbusware_gitlab_token,
    nimbusware_timeline_base_url,
)

_GITHUB_SHA_PLACEHOLDER = "0000000000000000000000000000000000000000"


def _timeline_link(run_id: UUID, timeline_base_url: str | None) -> str:
    base = nimbusware_timeline_base_url(fallback=timeline_base_url or "")
    if not base:
        return ""
    return f"{base.rstrip('/')}/v1/runs/{run_id}/timeline"


def _post_json(
    url: str,
    body: dict[str, Any],
    *,
    token: str,
    accept: str = "application/json",
    auth_header: str = "Bearer",
) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"{auth_header} {token}",
            "Accept": accept,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        if not raw.strip():
            return {}
        return cast(dict[str, Any], json.loads(raw))


def _notify_github(
    *,
    run_id: UUID,
    verdict: str,
    stage_name: str,
    timeline_base_url: str | None,
) -> dict[str, Any]:
    token = nimbusware_github_token()
    repo = nimbusware_ci_github_repo()
    if not token or not repo:
        return {"status": "skipped", "reason": "github_not_configured", "provider": "github"}
    owner, name = repo
    link = _timeline_link(run_id, timeline_base_url)
    conclusion = "success" if str(verdict).upper() == "PASS" else "failure"
    sha = nimbusware_ci_head_sha(default=_GITHUB_SHA_PLACEHOLDER)
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
        result = _post_json(url, body, token=token)
        return {"status": "posted", "provider": "github", "check_run_id": result.get("id")}
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "error", "provider": "github", "reason": str(exc)[:200]}


def _notify_gitlab(
    *,
    run_id: UUID,
    verdict: str,
    stage_name: str,
    timeline_base_url: str | None,
) -> dict[str, Any]:
    token = nimbusware_gitlab_token()
    project = nimbusware_ci_gitlab_project()
    if not token or not project:
        return {"status": "skipped", "reason": "gitlab_not_configured", "provider": "gitlab"}
    encoded = urllib.parse.quote(project, safe="")
    link = _timeline_link(run_id, timeline_base_url)
    state = "success" if str(verdict).upper() == "PASS" else "failed"
    sha = nimbusware_ci_head_sha()
    if not sha:
        return {"status": "skipped", "reason": "gitlab_missing_head_sha", "provider": "gitlab"}
    url = f"{nimbusware_gitlab_api_base()}/projects/{encoded}/statuses"
    body: dict[str, Any] = {
        "state": state,
        "name": f"nimbusware/{stage_name}",
        "description": f"Verdict: {verdict}",
        "sha": sha,
    }
    if link:
        body["target_url"] = link
    try:
        _post_json(url, body, token=token, auth_header="PRIVATE-TOKEN")
        return {"status": "posted", "provider": "gitlab", "sha": sha}
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "error", "provider": "gitlab", "reason": str(exc)[:200]}


def attach_external_ci_metadata(
    metadata: dict[str, Any],
    *,
    run_id: UUID,
    verdict: str,
    stage_name: str,
    timeline_base_url: str | None = None,
) -> dict[str, Any]:
    ci_status = notify_gate_decision_external(
        run_id=run_id,
        verdict=verdict,
        stage_name=stage_name,
        timeline_base_url=timeline_base_url,
    )
    if ci_status.get("status") != "skipped":
        metadata["external_ci"] = ci_status
    return metadata


def notify_gate_decision_external(
    *,
    run_id: UUID,
    verdict: str,
    stage_name: str,
    timeline_base_url: str | None = None,
) -> dict[str, Any]:
    github = _notify_github(
        run_id=run_id,
        verdict=verdict,
        stage_name=stage_name,
        timeline_base_url=timeline_base_url,
    )
    if github.get("status") != "skipped":
        return github
    gitlab = _notify_gitlab(
        run_id=run_id,
        verdict=verdict,
        stage_name=stage_name,
        timeline_base_url=timeline_base_url,
    )
    if gitlab.get("status") != "skipped":
        return gitlab
    return {"status": "skipped", "reason": "external_ci_not_configured"}
