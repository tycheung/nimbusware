from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from agent_core.models import EventType
from nimbusware_env import find_repo_root
from nimbusware_executor.fetch import EgressResponseTooLarge
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.scraper_stage import ScraperFetchConfig, load_scraper_fetch_config

_DEFAULT_CFG = ScraperFetchConfig(
    enabled=True,
    fetch_urls=("https://www.example.test/",),
    actor_role_key="backend_writer",
    max_attempts=1,
    backoff_seconds=0.0,
    max_bytes=None,
    body_snippet_max_bytes=256,
    persist_artifacts_max_bytes_per_url=None,
)

_RUN_EGRESS = {
    "network_egress": {
        "scraper_role_allowlist": ["44444444-4444-4444-8444-444444444404"],
        "domain_allowlist": [".example.test"],
    },
}


def test_scraper_stage_skipped_when_workflow_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    orch.run_optional_scraper_fetch_stage(rid)
    stages = [
        r for r in mem.list_run_events(str(rid)) if r["event_type"] == EventType.STAGE_STARTED.value
    ]
    assert not any(
        str((r.get("payload") or {}).get("stage_name", "")).startswith("scraper:") for r in stages
    )


def test_scraper_stage_fails_when_env_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default", run_policy_overrides=_RUN_EGRESS)
    with patch(
        "nimbusware_orchestrator.pipeline.load_scraper_fetch_config",
        return_value=_DEFAULT_CFG,
    ):
        orch.run_optional_scraper_fetch_stage(rid)
    evs = mem.list_run_events(str(rid))
    assert any(
        r["event_type"] == EventType.STAGE_FAILED.value
        and (r.get("payload") or {}).get("reason_code") == "outbound_fetch_disabled"
        for r in evs
    )


def test_workflow_profile_scraper_artifacts_on_persist_cap() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    cfg = load_scraper_fetch_config(repo, "scraper_artifacts_on")
    assert cfg.persist_artifacts_max_bytes_per_url == 65_536


def test_persist_artifacts_max_bytes_clamped_to_2_mib(tmp_path: Path) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "persist_clamp_test.yaml").write_text(
        "version: 1\n"
        "finding_fix_strictness:\n"
        "  minimum_severity_requiring_fixes: MEDIUM\n"
        "  also_require_fixes_for_low_severity: false\n"
        "network_egress:\n"
        "  scraper_role_allowlist: null\n"
        "  domain_allowlist: null\n"
        "  budget_bytes_per_run: null\n"
        "scraper_fetch:\n"
        "  enabled: false\n"
        "  persist_artifacts_max_bytes_per_url: 9000000\n",
        encoding="utf-8",
    )
    cfg = load_scraper_fetch_config(tmp_path, "persist_clamp_test")
    assert cfg.persist_artifacts_max_bytes_per_url == 2_097_152


def test_scraper_no_disk_artifact_when_persist_cap_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """YAML ``null`` / config ``None`` for persist cap skips on-disk response writes."""
    monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", "1")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default", run_policy_overrides=_RUN_EGRESS)
    with patch(
        "nimbusware_orchestrator.pipeline.load_scraper_fetch_config",
        return_value=_DEFAULT_CFG,
    ):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.content = b"no-artifact-body"
        mock_resp.status_code = 200
        mock_resp.headers = httpx.Headers({})
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_resp
        orch.run_optional_scraper_fetch_stage(rid, client=client)
    evs = mem.list_run_events(str(rid))
    passed = [r for r in evs if r["event_type"] == EventType.STAGE_PASSED.value]
    fetch0 = ((passed[-1].get("metadata") or {}).get("scraper_fetch") or {}).get("fetches", [{}])[0]
    assert "artifact_relpath" not in fetch0
    assert "artifact_bytes_written" not in fetch0


def test_scraper_stage_success_with_mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", "1")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default", run_policy_overrides=_RUN_EGRESS)
    with patch(
        "nimbusware_orchestrator.pipeline.load_scraper_fetch_config",
        return_value=_DEFAULT_CFG,
    ):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.content = b"ok"
        mock_resp.status_code = 200
        mock_resp.headers = httpx.Headers({"content-length": "2"})
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_resp
        orch.run_optional_scraper_fetch_stage(rid, client=client)
    evs = mem.list_run_events(str(rid))
    passed = [r for r in evs if r["event_type"] == EventType.STAGE_PASSED.value]
    assert passed
    sf = (passed[-1].get("metadata") or {}).get("scraper_fetch") or {}
    fetches = sf.get("fetches") or []
    assert len(fetches) == 1
    assert fetches[0].get("content_length") == 2
    assert fetches[0].get("bytes") == 2
    assert len(fetches[0].get("body_sha256_hex", "")) == 64
    assert "body_snippet_preview" in fetches[0]


def test_scraper_multi_url_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", "1")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default", run_policy_overrides=_RUN_EGRESS)
    cfg = ScraperFetchConfig(
        enabled=True,
        fetch_urls=(
            "https://a.example.test/one",
            "https://b.example.test/two",
        ),
        actor_role_key="backend_writer",
        max_attempts=1,
        backoff_seconds=0.0,
        max_bytes=None,
        body_snippet_max_bytes=0,
        persist_artifacts_max_bytes_per_url=None,
    )
    urls_seen: list[str] = []

    def fake_get(
        store: object,
        run: object,
        url: str,
        *,
        actor_role_id: object,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
        max_response_bytes: int | None = None,
    ) -> httpx.Response:
        urls_seen.append(url)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.content = b"x"
        mock_resp.status_code = 200
        mock_resp.headers = httpx.Headers({})
        return mock_resp

    with (
        patch("nimbusware_orchestrator.pipeline.load_scraper_fetch_config", return_value=cfg),
        patch("nimbusware_orchestrator.pipeline.egress_checked_get_for_run", side_effect=fake_get),
    ):
        orch.run_optional_scraper_fetch_stage(rid)
    assert len(urls_seen) == 2
    evs = mem.list_run_events(str(rid))
    passed = [r for r in evs if r["event_type"] == EventType.STAGE_PASSED.value]
    fetches = ((passed[-1].get("metadata") or {}).get("scraper_fetch") or {}).get("fetches") or []
    assert len(fetches) == 2
    assert "body_snippet_preview" not in fetches[0]


def test_scraper_budget_exceeded_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", "1")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default", run_policy_overrides=_RUN_EGRESS)
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_scraper_fetch_config",
            return_value=_DEFAULT_CFG,
        ),
        patch(
            "nimbusware_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=EgressResponseTooLarge("over"),
        ),
    ):
        orch.run_optional_scraper_fetch_stage(rid)
    evs = mem.list_run_events(str(rid))
    assert any(
        r["event_type"] == EventType.STAGE_FAILED.value
        and (r.get("payload") or {}).get("reason_code") == "scraper_budget_exceeded"
        for r in evs
    )


def test_scraper_retries_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", "1")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default", run_policy_overrides=_RUN_EGRESS)
    cfg = ScraperFetchConfig(
        enabled=True,
        fetch_urls=("https://www.example.test/",),
        actor_role_key="backend_writer",
        max_attempts=2,
        backoff_seconds=0.0,
        max_bytes=None,
        body_snippet_max_bytes=0,
        persist_artifacts_max_bytes_per_url=None,
    )
    req = httpx.Request("GET", "https://www.example.test/")
    first_err = httpx.RequestError("boom", request=req)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.content = b"ok"
    mock_resp.status_code = 200
    mock_resp.headers = httpx.Headers({})

    calls = {"n": 0}

    def side_effect(*_a: object, **_kw: object) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise first_err
        return mock_resp

    with (
        patch("nimbusware_orchestrator.pipeline.load_scraper_fetch_config", return_value=cfg),
        patch(
            "nimbusware_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=side_effect,
        ),
    ):
        orch.run_optional_scraper_fetch_stage(rid)
    assert calls["n"] == 2
    ev_rows = mem.list_run_events(str(rid))
    assert any(r["event_type"] == EventType.STAGE_PASSED.value for r in ev_rows)


def test_scraper_writes_artifact_when_configured(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", "1")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_DIR", str(tmp_path / "art"))
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default", run_policy_overrides=_RUN_EGRESS)
    cfg = ScraperFetchConfig(
        enabled=True,
        fetch_urls=("https://www.example.test/",),
        actor_role_key="backend_writer",
        max_attempts=1,
        backoff_seconds=0.0,
        max_bytes=None,
        body_snippet_max_bytes=0,
        persist_artifacts_max_bytes_per_url=10_000,
    )
    body = b"hello-artifact-world"
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.content = body
    mock_resp.status_code = 200
    mock_resp.headers = httpx.Headers({})
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_resp
    with patch("nimbusware_orchestrator.pipeline.load_scraper_fetch_config", return_value=cfg):
        orch.run_optional_scraper_fetch_stage(rid, client=client)
    evs = mem.list_run_events(str(rid))
    passed = [r for r in evs if r["event_type"] == EventType.STAGE_PASSED.value]
    fetch0 = ((passed[-1].get("metadata") or {}).get("scraper_fetch") or {}).get("fetches", [{}])[0]
    assert fetch0.get("artifact_bytes_written") == len(body)
    assert fetch0.get("artifact_sha256")
    rel = fetch0.get("artifact_relpath")
    assert isinstance(rel, str)
    art_file = (tmp_path / "art").joinpath(*rel.split("/"))
    assert art_file.is_file()
    assert art_file.read_bytes() == body
