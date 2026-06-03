from __future__ import annotations

from typing import Any

from nimbusware_maker.api_client import get_json, post_json


def fetch_run_research(run_id: str) -> dict[str, Any]:
    return get_json(f"/runs/{run_id}/research")


def approve_research_brief(run_id: str, brief_id: str, *, notes: str = "") -> dict[str, Any]:
    return post_json(
        f"/runs/{run_id}/research/{brief_id}/approve",
        {"notes": notes},
    )


def reject_research_brief(run_id: str, brief_id: str, *, notes: str = "") -> dict[str, Any]:
    return post_json(
        f"/runs/{run_id}/research/{brief_id}/reject",
        {"notes": notes},
    )
