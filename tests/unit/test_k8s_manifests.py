from __future__ import annotations

from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[2]
_K8S = _REPO / "docs" / "deploy" / "k8s"

_MANIFESTS = (
    "api-deployment.yaml",
    "api-secrets.yaml",
    "redis-deployment.yaml",
    "worker-deployment.yaml",
    "schema-job.yaml",
    "console-deployment.yaml",
)


def _load_docs(name: str) -> list[dict]:
    text = (_K8S / name).read_text(encoding="utf-8")
    return list(yaml.safe_load_all(text))


def test_k8s_manifests_parse() -> None:
    for name in _MANIFESTS:
        docs = _load_docs(name)
        assert docs, f"empty manifest: {name}"


def test_api_deployment_has_probes() -> None:
    dep = next(d for d in _load_docs("api-deployment.yaml") if d.get("kind") == "Deployment")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    assert "readinessProbe" in container
    assert "livenessProbe" in container


def test_redis_service_selects_redis() -> None:
    svc = next(d for d in _load_docs("redis-deployment.yaml") if d.get("kind") == "Service")
    assert svc["spec"]["selector"]["app"] == "nimbusware-redis"


def test_worker_uses_redis_dispatch() -> None:
    dep = next(d for d in _load_docs("worker-deployment.yaml") if d.get("kind") == "Deployment")
    env = {e["name"]: e["value"] for e in dep["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env.get("HERMES_RUN_DISPATCH") == "redis"
