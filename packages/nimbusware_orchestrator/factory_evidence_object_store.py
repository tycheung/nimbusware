from __future__ import annotations

from typing import Any

import httpx

from nimbusware_env.env_flags import env_str


def factory_evidence_object_store_url() -> str:
    return env_str("NIMBUSWARE_FACTORY_EVIDENCE_OBJECT_STORE_URL").strip()


def factory_evidence_object_store_bucket() -> str:
    return env_str("NIMBUSWARE_FACTORY_EVIDENCE_OBJECT_STORE_BUCKET").strip()


def factory_evidence_object_store_configured() -> bool:
    return bool(factory_evidence_object_store_url() and factory_evidence_object_store_bucket())


def put_factory_evidence_object(
    *,
    run_id: str,
    payload: bytes,
    content_type: str = "application/zip",
) -> dict[str, Any]:
    if not factory_evidence_object_store_configured():
        return {"status": "skipped", "reason": "object_store_not_configured"}
    bucket = factory_evidence_object_store_bucket()
    key = f"factory-evidence/{run_id}.zip"
    base = factory_evidence_object_store_url().rstrip("/")
    url = f"{base}/{bucket}/{key}"
    try:
        resp = httpx.put(url, content=payload, headers={"Content-Type": content_type}, timeout=60.0)
        if resp.status_code >= 400:
            return {"status": "error", "code": resp.status_code, "detail": resp.text[:200]}
        return {"status": "uploaded", "object_store_key": key, "url": url}
    except httpx.HTTPError as exc:
        return {"status": "error", "detail": str(exc)[:200]}
