from __future__ import annotations

import io
import json
import tarfile
from uuid import uuid4

from nimbusware_iam.store import InMemoryIamStore
from nimbusware_orchestrator.enterprise_audit_export import build_enterprise_audit_bundle_bytes
from nimbusware_research.enterprise_index import append_enterprise_research_index
from nimbusware_store.memory import InMemoryEventStore


def test_enterprise_audit_bundle_contains_iam_actions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_TENANT_ID", "acme")
    iam = InMemoryIamStore()
    iam.log_iam_action(action="tenant.created", detail={"slug": "ops"})
    append_enterprise_research_index(
        tmp_path,
        run_id=uuid4(),
        pattern_id="p1",
        domain_tag="x",
    )
    payload = build_enterprise_audit_bundle_bytes(
        iam_store=iam,
        event_store=InMemoryEventStore(),
        repo_root=tmp_path,
    )
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}
    assert "iam_actions.jsonl" in names
    assert "manifest.json" in names
    assert "research_index.jsonl" in names
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())  # type: ignore[union-attr]
    assert manifest["iam_action_count"] >= 1
