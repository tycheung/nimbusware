from __future__ import annotations

import re
from typing import Any

_KEY_LIKE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|authorization|bearer\s+[a-z0-9._-]+)",
)
_ENV_PATH = re.compile(r"(?i)(\.env\b|/\.env[^/\s]*)")


def redact_collab_output(text: str) -> str:
    if not text:
        return ""
    out = _KEY_LIKE.sub("[redacted]", text)
    out = _ENV_PATH.sub("[env-path]", out)
    return out


def redact_participant_packet(payload: dict[str, Any]) -> dict[str, Any]:
    from nimbusware_orchestrator.participant_output_packet import ParticipantOutputPacket

    pkt = ParticipantOutputPacket.model_validate(payload)
    pkt.summary = redact_collab_output(pkt.summary)
    pkt.diff_excerpt = redact_collab_output(pkt.diff_excerpt)
    pkt.test_log_excerpt = redact_collab_output(pkt.test_log_excerpt)
    pkt.full_output = redact_collab_output(pkt.full_output)
    clean_findings = []
    for item in pkt.findings:
        if not isinstance(item, dict):
            continue
        clean = {
            k: redact_collab_output(str(v)) if isinstance(v, str) else v for k, v in item.items()
        }
        clean_findings.append(clean)
    pkt.findings = clean_findings
    return pkt.to_wire_dict()
