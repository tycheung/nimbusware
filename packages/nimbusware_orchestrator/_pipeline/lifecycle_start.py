from __future__ import annotations

from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    EventType,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
    ModelPreflightStartedEvent,
    ModelPreflightStartedPayload,
    ModelSelectedFallbackEvent,
    ModelSelectedFallbackPayload,
    ModelSelectedPrimaryEvent,
    ModelSelectedPrimaryPayload,
    RunStartedEvent,
    RunStartedPayload,
    _coerce_samples_ms,
    datetime,
    run_model_preflight,
    timezone,
    uuid4,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import LifecycleStartHost


class LifecycleStartMixin:
    def start_run_after_preflight(self: LifecycleStartHost, run_id: UUID) -> None:
        base = self._base_cfg()
        runtime = base.get("runtime") or {}
        models = base.get("models") or {}
        primary = (models.get("primary") or {}).get("id", "llama3.1:8b")
        fb_raw = models.get("fallbacks") or []
        fallbacks = [
            str(x.get("id")) for x in fb_raw if isinstance(x, dict) and x.get("id") is not None
        ]

        base_url = str(runtime.get("base_url", "http://localhost:11434"))
        health = str(runtime.get("health_endpoint", "/api/tags"))
        preflight_cfg = base.get("preflight") if isinstance(base.get("preflight"), dict) else {}

        self._store.append(
            ModelPreflightStartedEvent(
                event_type=EventType.MODEL_PREFLIGHT_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=ModelPreflightStartedPayload(
                    provider=str(runtime.get("provider", "ollama")),
                    base_url=base_url,
                    requested_model_id=primary,
                ),
            ),
        )

        selected, evidence, used_primary = run_model_preflight(
            base_url=base_url,
            health_path=health,
            primary_model_id=primary,
            fallback_model_ids=fallbacks,
            timeout_seconds=float(runtime.get("request_timeout_seconds", 60)),
            preflight_cfg=preflight_cfg,
        )

        checks = list(evidence.get("checks_passed", []))
        self._store.append(
            ModelPreflightPassedEvent(
                event_type=EventType.MODEL_PREFLIGHT_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=ModelPreflightPassedPayload(
                    provider=str(runtime.get("provider", "ollama")),
                    validated_model_id=selected,
                    context_tokens=int(evidence.get("context_tokens", 8192)),
                    p95_latency_ms=int(evidence.get("p95_latency_ms", 0)),
                    checks_passed=checks,
                    preflight_latency_sample_count=evidence.get("preflight_latency_sample_count"),
                    p95_latency_source=evidence.get("p95_latency_source"),
                    health_latency_samples_ms=_coerce_samples_ms(
                        evidence.get("health_latency_samples_ms"),
                    ),
                ),
            ),
        )
        if used_primary:
            self._store.append(
                ModelSelectedPrimaryEvent(
                    event_type=EventType.MODEL_SELECTED_PRIMARY,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    model_id=selected,
                    payload=ModelSelectedPrimaryPayload(
                        provider=str(runtime.get("provider", "ollama")),
                        model_id=selected,
                    ),
                ),
            )
        else:
            self._store.append(
                ModelSelectedFallbackEvent(
                    event_type=EventType.MODEL_SELECTED_FALLBACK,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    model_id=selected,
                    payload=ModelSelectedFallbackPayload(
                        provider=str(runtime.get("provider", "ollama")),
                        selected_model_id=selected,
                        reason_code="primary_unavailable_or_failed_preflight",
                        original_model_id=primary,
                    ),
                ),
            )
        self._store.append(
            RunStartedEvent(
                event_type=EventType.RUN_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=RunStartedPayload(started_by="orchestrator"),
            ),
        )
