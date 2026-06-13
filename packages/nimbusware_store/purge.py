from __future__ import annotations

from datetime import datetime
from typing import Any


def purge_events_before(conn: Any, cutoff: datetime) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM event_store WHERE occurred_at < %s",
            (cutoff,),
        )
        deleted = int(cur.rowcount or 0)
    conn.commit()
    return deleted
