from __future__ import annotations

from pathlib import Path

from agent_core.models import EventType, Verdict
from hermes_memory.event_scan import fetch_event_rows_for_memory_index
from hermes_memory.sync import memory_index_sync_state, memory_sync_manifest_stub
from hermes_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_api.access import assert_run_accessible
from nimbusware_config import keys
from nimbusware_config.notify import (
    ConfigDocumentUpdated,
    ConfigNotifyHub,
    encode_notify_payload,
    get_config_notify_hub,
    parse_notify_payload,
)
from nimbusware_config.persist import (
    load_bundle_catalog_dict,
    load_persona_shelf,
    load_workflow_profile_dict,
)
from nimbusware_projections.builders import stage_timeline
from nimbusware_projections.builders.integrator_gate import integrator_gate_timeline_summary


def test_config_notify_payload_roundtrip() -> None:
    payload = encode_notify_payload(
        namespace="workflows",
        document_key="default",
        version=3,
    )
    parsed = parse_notify_payload(payload)
    assert parsed == ConfigDocumentUpdated(
        namespace="workflows",
        document_key="default",
        version=3,
    )
    assert parse_notify_payload("") is None
    assert parse_notify_payload("{not json") is None
    assert parse_notify_payload('{"namespace":"x"}') is None


def test_config_persist_file_fallback(tmp_path: Path) -> None:
    personas = tmp_path / "configs" / "personas"
    personas.mkdir(parents=True)
    (personas / "shelves.yaml").write_text(
        "personas: []\n",
        encoding="utf-8",
    )
    workflows = tmp_path / "configs" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "default.yaml").write_text(
        "workflow_profile: default\nintegrator_gate:\n  enabled: false\n",
        encoding="utf-8",
    )
    bundles = tmp_path / "configs" / "bundles"
    bundles.mkdir(parents=True)
    (bundles / "catalog.yaml").write_text("bundles: []\n", encoding="utf-8")

    shelf = load_persona_shelf(tmp_path)
    assert shelf.raw.get("personas") == []
    profile = load_workflow_profile_dict(tmp_path, "default")
    assert profile.get("workflow_profile") == "default"
    catalog = load_bundle_catalog_dict(tmp_path)
    assert catalog.get("bundles") == []


def test_stage_timeline_parallel_writer_summary() -> None:
    events = [
        {
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {
                "stage_graph": {
                    "parallel_groups": {
                        "writers": ["implementation", "test_writer"],
                    },
                },
            },
        },
        {
            "event_type": EventType.STAGE_STARTED.value,
            "payload": {"stage_name": "implementation"},
            "metadata": {"dispatch_mode": "parallel"},
        },
        {
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {"stage_name": "implementation", "duration_ms": 10},
            "metadata": {"exit_code": 0},
        },
        {
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {
                "stage_name": "implementation.critique",
                "verdict": Verdict.PASS.value,
            },
        },
    ]
    rows = stage_timeline.parallel_writer_groups_timeline_summary(events)
    assert rows is not None
    assert len(rows) >= 1
    graph = stage_timeline.stage_graph_timeline_summary(events)
    assert graph is not None


def test_integrator_gate_timeline_empty() -> None:
    assert integrator_gate_timeline_summary([]) is None


def test_config_keys_constants() -> None:
    assert keys.NS_WORKFLOWS == "workflows"
    assert keys.KEY_BUNDLE_CATALOG == "bundle-catalog"


def test_memory_sync_state_empty_index(tmp_path: Path) -> None:
    state = memory_index_sync_state(tmp_path)
    assert state["faiss_ready"] is False
    assert state["manifest_exists"] is False
    manifest = memory_sync_manifest_stub(tmp_path)
    assert manifest.get("faiss_ready") is False
    assert manifest.get("remote_sync") == "not_configured"


def test_fetch_event_rows_in_memory_subset() -> None:
    rows = fetch_event_rows_for_memory_index(
        in_memory_rows=[
            {"event_type": EventType.RUN_CREATED.value, "store_seq": 2},
            {"event_type": "run.completed", "store_seq": 1},
            {"event_type": EventType.FINDING_CREATED.value, "store_seq": 3},
        ],
    )
    assert [int(r["store_seq"]) for r in rows] == [2, 3]


class _StubMaterializer:
    def __init__(self) -> None:
        self.refreshed: list[str] = []

    def refresh(self, namespace: str) -> None:
        self.refreshed.append(namespace)


def test_config_notify_hub_dispatch() -> None:
    hub = ConfigNotifyHub()
    mat = _StubMaterializer()
    hub.register(mat)
    event = hub.publish_local(namespace="workflows", document_key="default", version=1)
    assert event.version == 1
    assert mat.refreshed == ["workflows"]
    assert hub.delivery_count == 1
    hub.unregister(mat)
    assert get_config_notify_hub() is get_config_notify_hub()


def test_assert_run_accessible_individual_edition() -> None:
    assert_run_accessible(
        [{"event_type": EventType.RUN_CREATED.value, "metadata": {"project_id": "p1"}}],
    )


def test_unanimous_gate_pass_when_not_enforced() -> None:
    decision = gate_decision_from_critic_verdicts(
        [],
        stage_name="implementation.critique",
        enforce=False,
    )
    assert decision.verdict == Verdict.PASS
