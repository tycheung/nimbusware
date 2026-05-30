from __future__ import annotations


def test_maker_package_imports() -> None:
    import nimbusware_maker.app  # noqa: F401
    from nimbusware_maker.ui import render_main

    assert callable(render_main)


def test_maker_runs_latest_for_project(monkeypatch) -> None:
    from nimbusware_maker import runs as maker_runs

    def fake_get_json(path: str) -> dict:
        assert "include_summary=1" in path
        return {
            "run_ids": ["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"],
            "summaries": {
                "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                    "run_created_metadata": {
                        "project": {"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
                    },
                },
            },
        }

    monkeypatch.setattr(maker_runs, "get_json", fake_get_json)
    found = maker_runs.latest_run_id_for_project("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    assert found == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    missing = maker_runs.latest_run_id_for_project("00000000-0000-4000-8000-000000000001")
    assert missing is None
