from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_enterprise_buyer_documents_regulated_bundle() -> None:
    text = (REPO / "docs" / "enterprise-buyer.md").read_text(encoding="utf-8")
    assert "Regulated / air-gapped bundle" in text
    assert "agent-sandbox.md" in text
    assert "headless-patch-ci.md" in text
    assert "charts/nimbusware" in text
