from __future__ import annotations

import base64
import json
from uuid import UUID


def encode_run_list_cursor(seq: int, run_id: UUID) -> str:
    raw = json.dumps({"s": seq, "r": str(run_id)}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_run_list_cursor(value: str) -> tuple[int, UUID]:
    pad = "=" * ((4 - len(value) % 4) % 4)
    raw = base64.urlsafe_b64decode(value + pad)
    d = json.loads(raw.decode())
    return int(d["s"]), UUID(str(d["r"]))
