from __future__ import annotations

import logging
import threading
from typing import Any

import psycopg

from nimbusware_config.notify import NOTIFY_CHANNEL, ConfigNotifyHub

logger = logging.getLogger(__name__)


def config_notify_listener_enabled() -> bool:
    from nimbusware_config import config_from_db_enabled, config_notify_enabled

    return config_from_db_enabled() and config_notify_enabled()


def start_config_notify_listener(
    conninfo: str,
    hub: ConfigNotifyHub,
    stop_event: threading.Event,
) -> threading.Thread:
    """Background thread: LISTEN on ``nimbusware_config_document`` until ``stop_event``."""

    def _run() -> None:
        try:
            with psycopg.connect(conninfo, autocommit=True) as conn:
                conn.execute(f"LISTEN {NOTIFY_CHANNEL}")
                logger.info("config NOTIFY listener started on channel %s", NOTIFY_CHANNEL)
                while not stop_event.is_set():
                    for notify in conn.notifies(timeout=1.0):
                        hub.handle_payload(notify.payload)
        except Exception:
            if not stop_event.is_set():
                logger.exception("config NOTIFY listener failed")
        finally:
            logger.info("config NOTIFY listener stopped")

    thread = threading.Thread(target=_run, name="nimbusware-config-notify", daemon=True)
    thread.start()
    return thread


def listener_status(hub: ConfigNotifyHub) -> dict[str, Any]:
    last = hub.last_event
    return {
        "channel": NOTIFY_CHANNEL,
        "delivery_count": hub.delivery_count,
        "last_event": (
            {
                "type": last.event_type,
                "namespace": last.namespace,
                "document_key": last.document_key,
                "version": last.version,
            }
            if last is not None
            else None
        ),
    }
