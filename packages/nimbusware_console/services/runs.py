from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nimbusware_client.http import get_json, get_response, post_json

if TYPE_CHECKING:
    from httpx import Response


def fetch_run(run_id: str, *, timeout: float = 30.0) -> dict[str, Any]:
    return get_json(f"/runs/{run_id.strip()}", timeout=timeout)


def fetch_timeline(run_id: str, *, timeout: float = 30.0) -> dict[str, Any]:
    return get_json(f"/runs/{run_id.strip()}/timeline", timeout=timeout)


def fetch_findings(run_id: str, *, timeout: float = 30.0) -> dict[str, Any]:
    return get_json(f"/runs/{run_id.strip()}/findings", timeout=timeout)


def fetch_runs_list(
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> Response:
    return get_response("/runs", params=params, timeout=timeout)


def post_retry(run_id: str, *, timeout: float = 30.0) -> dict[str, Any]:
    return post_json(f"/runs/{run_id.strip()}/actions/retry", {}, timeout=timeout)


def post_escalate(
    run_id: str,
    body: dict[str, Any],
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return post_json(f"/runs/{run_id.strip()}/actions/escalate", body, timeout=timeout)
