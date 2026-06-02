"""Signed audit bundle export for a run (fo402)."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import tarfile
from typing import Any


def _signing_key() -> bytes | None:
    raw = os.environ.get("AUDIT_EXPORT_SIGNING_KEY", "").strip()
    return raw.encode("utf-8") if raw else None


def build_audit_bundle_bytes(
    *,
    run_id: str,
    events: list[dict[str, Any]],
    policy_snapshot: dict[str, Any],
) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        events_bytes = "\n".join(json.dumps(e, default=str) for e in events).encode("utf-8")
        ev_info = tarfile.TarInfo(name="events.jsonl")
        ev_info.size = len(events_bytes)
        tar.addfile(ev_info, io.BytesIO(events_bytes))
        pol_bytes = json.dumps(policy_snapshot, indent=2).encode("utf-8")
        pol_info = tarfile.TarInfo(name="policy_snapshot.json")
        pol_info.size = len(pol_bytes)
        tar.addfile(pol_info, io.BytesIO(pol_bytes))
        manifest = {"run_id": run_id, "event_count": len(events)}
        man_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        man_info = tarfile.TarInfo(name="manifest.json")
        man_info.size = len(man_bytes)
        tar.addfile(man_info, io.BytesIO(man_bytes))
    payload = buf.getvalue()
    key = _signing_key()
    if not key:
        return payload
    sig = hmac.new(key, payload, hashlib.sha256).hexdigest()
    outer = io.BytesIO()
    with tarfile.open(fileobj=outer, mode="w:gz") as tar:
        data_info = tarfile.TarInfo(name="bundle.tar.gz")
        data_info.size = len(payload)
        tar.addfile(data_info, io.BytesIO(payload))
        sig_bytes = sig.encode("utf-8")
        sig_info = tarfile.TarInfo(name="bundle.sig")
        sig_info.size = len(sig_bytes)
        tar.addfile(sig_info, io.BytesIO(sig_bytes))
    return outer.getvalue()


def verify_audit_bundle_signature(bundle_bytes: bytes, signature_hex: str) -> bool:
    key = _signing_key()
    if not key:
        return False
    with tarfile.open(fileobj=io.BytesIO(bundle_bytes), mode="r:gz") as tar:
        data_member = tar.getmember("bundle.tar.gz")
        inner = tar.extractfile(data_member)
        if inner is None:
            return False
        payload = inner.read()
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex.strip())
