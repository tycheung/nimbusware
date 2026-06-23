from __future__ import annotations

import json
from typing import Any

import httpx

from nimbusware_orchestrator.put_e2e_types import PutE2EFinding

def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path if path.startswith('/') else '/' + path}"


def _run_http_step(
    client: httpx.Client,
    base_url: str,
    step: dict[str, Any],
    *,
    exercised: set[str],
    findings: list[PutE2EFinding],
) -> bool:
    action = str(step.get("action") or "").strip().lower()
    path = str(step.get("path") or "/")
    exercised.add(path)

    if action == "goto":
        try:
            resp = client.get(_url(base_url, path), follow_redirects=True)
        except httpx.HTTPError as exc:
            findings.append(
                PutE2EFinding(kind="step_fail", message=f"goto {path}: {exc}", surface_path=path),
            )
            return False
        if resp.status_code >= 500:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"goto {path}: status {resp.status_code}",
                    surface_path=path,
                ),
            )
            return False
        return True

    if action == "expect_status":
        expected = int(step.get("status") or 200)
        try:
            resp = client.get(_url(base_url, path), follow_redirects=True)
        except httpx.HTTPError as exc:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"expect_status {path}: {exc}",
                    surface_path=path,
                ),
            )
            return False
        if resp.status_code != expected:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"expect_status {path}: got {resp.status_code}, want {expected}",
                    surface_path=path,
                ),
            )
            return False
        return True

    if action == "api_check":
        method = str(step.get("method") or "GET").upper()
        expected = int(step.get("status") or 200)
        body = step.get("json_body")
        try:
            resp = client.request(
                method,
                _url(base_url, path),
                json=body if isinstance(body, dict) else None,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"api_check {method} {path}: {exc}",
                    surface_path=path,
                ),
            )
            return False
        if resp.status_code != expected:
            findings.append(
                PutE2EFinding(
                    kind="step_fail",
                    message=f"api_check {method} {path}: got {resp.status_code}, want {expected}",
                    surface_path=path,
                ),
            )
            return False
        keys = step.get("expect_json_keys")
        if isinstance(keys, list) and keys:
            try:
                payload = resp.json()
            except (json.JSONDecodeError, ValueError):
                findings.append(
                    PutE2EFinding(
                        kind="step_fail",
                        message=f"api_check {path}: response is not JSON",
                        surface_path=path,
                    ),
                )
                return False
            if not isinstance(payload, dict):
                findings.append(
                    PutE2EFinding(
                        kind="step_fail",
                        message=f"api_check {path}: JSON root is not object",
                        surface_path=path,
                    ),
                )
                return False
            missing = [k for k in keys if k not in payload]
            if missing:
                findings.append(
                    PutE2EFinding(
                        kind="step_fail",
                        message=f"api_check {path}: missing keys {missing}",
                        surface_path=path,
                    ),
                )
                return False
        return True

    findings.append(PutE2EFinding(kind="step_skip", message=f"unknown action: {action}"))
    return True
