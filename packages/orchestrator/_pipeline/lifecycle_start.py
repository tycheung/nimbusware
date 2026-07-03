from __future__ import annotations

from typing import Any

from orchestrator._pipeline._helpers import (
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
    mapping_or_empty,
    run_model_preflight,
    timezone,
    uuid4,
)
from orchestrator._pipeline.protocol_hosts import LifecycleStartHost
from orchestrator.binding_preflight import (
    build_binding_preflight_report,
    cloud_only_roles_satisfied,
)
from orchestrator.preflight import PreflightError


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
        preflight_cfg = mapping_or_empty(base.get("preflight"))

        meta: dict[str, Any] = {}
        if hasattr(self, "_run_created_metadata"):
            raw = self._run_created_metadata(run_id)
            if isinstance(raw, dict):
                meta = raw
        wf_profile = meta.get("workflow_profile")
        work_type = meta.get("work_type")
        repo_root = getattr(self, "_repo_root", None)
        binding_report: dict[str, Any] = {}
        if repo_root is not None:
            binding_report = build_binding_preflight_report(
                repo_root,
                workflow_profile=wf_profile if isinstance(wf_profile, str) else None,
                work_type=work_type if isinstance(work_type, str) else None,
                materializer=getattr(self, "_config_materializer", None),
            )

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

        try:
            selected, evidence, used_primary = run_model_preflight(
                base_url=base_url,
                health_path=health,
                primary_model_id=primary,
                fallback_model_ids=fallbacks,
                timeout_seconds=float(runtime.get("request_timeout_seconds", 60)),
                preflight_cfg=preflight_cfg,
            )
        except PreflightError:
            if binding_report and cloud_only_roles_satisfied(binding_report):
                role_rows = binding_report.get("roles") or []
                cloud_model = primary
                for row in role_rows:
                    if isinstance(row, dict) and row.get("model_id"):
                        cloud_model = str(row["model_id"])
                        break
                selected = cloud_model
                used_primary = True
                evidence = {
                    "skipped": True,
                    "reason": "ollama_unreachable_cloud_bindings_ok",
                    "checks_passed": ["binding_preflight_cloud_only"],
                    "context_tokens": 8192,
                    "p95_latency_ms": 0,
                    "health_latency_ms": 0,
                    "inference_mode": binding_report.get("inference_mode"),
                    "inference_mode_label": binding_report.get("inference_mode_label"),
                }
            else:
                raise
        else:
            if binding_report:
                evidence["inference_mode"] = binding_report.get("inference_mode")
                evidence["inference_mode_label"] = binding_report.get("inference_mode_label")

        checks = list(evidence.get("checks_passed", []))
        mode_label = evidence.get("inference_mode_label")
        if isinstance(mode_label, str) and mode_label.strip():
            checks.append(f"inference_mode:{evidence.get('inference_mode', 'unknown')}")
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
