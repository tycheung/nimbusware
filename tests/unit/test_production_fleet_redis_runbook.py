from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RUNBOOK = _REPO / "docs" / "deploy" / "production-fleet-redis-secrets.md"
_VALUES = _REPO / "charts" / "nimbusware" / "values.yaml"
_SECRET = _REPO / "charts" / "nimbusware" / "templates" / "api-secret.yaml"


def test_production_fleet_redis_runbook_documents_fleet_urls() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    assert "NIMBUSWARE_REDIS_FLEET_URLS" in text
    assert "redisFleetUrls" in text
    assert "run_redis_fleet_soak_ci.py" in text


def test_helm_values_and_secret_support_fleet_urls() -> None:
    values = _VALUES.read_text(encoding="utf-8")
    secret = _SECRET.read_text(encoding="utf-8")
    assert "redisFleetUrls" in values
    assert "NIMBUSWARE_REDIS_FLEET_URLS" in secret
