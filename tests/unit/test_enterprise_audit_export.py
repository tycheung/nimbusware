from __future__ import annotations

import io
import json
import tarfile

from hermes_orchestrator.enterprise_audit_export import build_enterprise_audit_bundle_bytes
from hermes_store.memory import InMemoryEventStore
from nimbusware_iam.store import InMemoryIamStore


def test_enterprise_audit_bundle_contains_iam_actions() -> None:
    iam = InMemoryIamStore()
    iam.log_iam_action(action="tenant.created", detail={"slug": "ops"})
    payload = build_enterprise_audit_bundle_bytes(
        iam_store=iam,
        event_store=InMemoryEventStore(),
    )
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}
    assert "iam_actions.jsonl" in names
    assert "manifest.json" in names
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())  # type: ignore[union-attr]
    assert manifest["iam_action_count"] >= 1
