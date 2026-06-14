from __future__ import annotations

import hashlib
import hmac
import io
import json
import tarfile
from typing import Any


def _signing_key() -> bytes | None:
    from nimbusware_env.env_flags import env_str

    raw = env_str("NIMBUSWARE_AUDIT_EXPORT_SIGNING_KEY")
    return raw.encode("utf-8") if raw else None


def build_audit_bundle_bytes(
    *,
    run_id: str,
    events: list[dict[str, Any]],
    policy_snapshot: dict[str, Any],
    theater_transcript_md: str | None = None,
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
        if theater_transcript_md:
            th_bytes = theater_transcript_md.encode("utf-8")
            th_info = tarfile.TarInfo(name="theater_transcript.md")
            th_info.size = len(th_bytes)
            tar.addfile(th_info, io.BytesIO(th_bytes))
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
