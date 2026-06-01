from __future__ import annotations

from unittest.mock import patch

from nimbusware_maker.services import runs as svc


def test_create_run_posts_payload() -> None:
    with patch("nimbusware_maker.services.runs.post_json") as post_json:
        post_json.return_value = {"run_id": "new"}
        out = svc.create_run({"workflow_profile": "micro_slice"})
    post_json.assert_called_once_with("/runs", {"workflow_profile": "micro_slice"})
    assert out["run_id"] == "new"


def test_fetch_maker_progress_includes_simple_query() -> None:
    with patch("nimbusware_maker.services.runs.get_json") as get_json:
        get_json.return_value = {"status": "in_progress"}
        svc.fetch_maker_progress("rid", simple=False)
    get_json.assert_called_once_with("/runs/rid/maker-progress?simple=false")


def test_approve_plan_posts_empty_body() -> None:
    with patch("nimbusware_maker.services.runs.post_json") as post_json:
        post_json.return_value = {}
        svc.approve_plan("rid")
    post_json.assert_called_once_with("/runs/rid/maker/plan/approve", {})
