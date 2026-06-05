from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from nimbusware_research.enterprise_index import (
    append_enterprise_research_index,
    export_egress_audit_rows,
    list_enterprise_research_index,
)


def test_append_and_list_research_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_TENANT_ID", "acme")
    rid = uuid4()
    append_enterprise_research_index(
        tmp_path,
        run_id=rid,
        pattern_id="p1",
        domain_tag="payments",
    )
    rows = list_enterprise_research_index(tmp_path)
    assert len(rows) == 1
    assert rows[0]["pattern_id"] == "p1"
    assert rows[0]["tenant_id"] == "acme"


def test_export_egress_audit_reads_jsonl(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_TENANT_ID", "acme")
    rel = Path(".nimbusware") / "enterprise" / "acme" / "egress_audit.jsonl"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"host": "api.example.com", "allowed": True}) + "\n", encoding="utf-8"
    )
    rows = export_egress_audit_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["host"] == "api.example.com"
