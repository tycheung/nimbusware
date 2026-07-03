from __future__ import annotations

from typing import Any

from maker.api_client import get_json, post_json


def create_run(payload: dict[str, Any]) -> dict[str, Any]:
    return post_json("/runs", payload)


def fetch_maker_progress(run_id: str, *, simple: bool = True) -> dict[str, Any]:
    path = f"/runs/{run_id}/maker-progress?simple={str(simple).lower()}"
    return get_json(path)


def fetch_run_timeline(run_id: str) -> dict[str, Any]:
    return get_json(f"/runs/{run_id}/timeline")


def fetch_pending(run_id: str) -> dict[str, Any]:
    return get_json(f"/runs/{run_id}/maker/pending")


def approve_plan(run_id: str) -> dict[str, Any]:
    return post_json(f"/runs/{run_id}/maker/plan/approve", {})


def prepare_slice(run_id: str) -> dict[str, Any]:
    return post_json(f"/runs/{run_id}/maker/slices/prepare", {})


def apply_slice(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return post_json(f"/runs/{run_id}/maker/slices/apply", payload)


def skip_slice(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return post_json(f"/runs/{run_id}/maker/slices/skip", payload)


def revert_workspace(run_id: str) -> dict[str, Any]:
    return post_json(f"/runs/{run_id}/workspace/revert", {})
