from __future__ import annotations

from typing import Any

from nimbusware_api.schemas.openapi_problem import _PROBLEM_JSON_CONTENT

CREATE_RUN_RESPONSE_200: dict[str, Any] = {
    "description": "Allocated run identifier (append-only store begins on first events)",
    "content": {
        "application/json": {
            "example": {"run_id": "11111111-1111-4111-8111-111111111111"},
        },
    },
}

CREATE_RUN_RESPONSE_422: dict[str, Any] = {
    "description": (
        "Structured validation error (unknown workflow, invalid persona assignment, "
        "incomplete critique pairings for registry producers, agent evaluator persona, etc.)"
    ),
    "content": _PROBLEM_JSON_CONTENT,
}

BUNDLE_SEARCH_RESPONSE_200: dict[str, Any] = {
    "description": (
        "Bundle catalog search hits (FAISS top-k when an index is built under "
        "``configs/bundles/index/``; otherwise tag/id overlap). ``k`` echoes the "
        "bounded request parameter (1..20) so clients can deduplicate hits, mirroring "
        "the Streamlit ``run_bundle_catalog_search`` payload. ``faiss_index_ready`` "
        "is ``true`` when both index files exist under the orchestrator repo root, "
        "mirroring the Streamlit FAISS readiness caption. ``faiss_index_stale`` mirrors "
        "``bundle_faiss_index_sync_state`` ``stale`` (``null`` when not comparable)."
    ),
    "content": {
        "application/json": {
            "example": {
                "query": "auth",
                "k": 5,
                "hits": [
                    {
                        "id": "auth-rbac-starter",
                        "title": "Admin RBAC starter",
                        "tags": ["auth", "rbac"],
                    }
                ],
                "faiss_index_ready": False,
                "faiss_index_stale": None,
            },
        },
    },
}

_PERSONA_ENTRY_FULL_EXAMPLE: dict[str, Any] = {
    "id": "commerce",
    "display_name": "Commerce",
    "instructions": (
        "You are the Commerce domain expert. Validate that any plan handles "
        "catalog / checkout / fulfillment edge cases (inventory races, "
        "split payments, partial refunds, multi-region tax) before signoff."
    ),
    "capability_profile": (
        "Deep e-commerce + payments familiarity; knows PCI-DSS scope basics "
        "and reads JSON API specs fluently."
    ),
    "boundary_statement": (
        "Does NOT authoritatively assess infra capacity or low-level GPU "
        "performance; defers to Performance / Network critics for those."
    ),
    "allowed_tools": ["bundle_search", "spec_lookup"],
    "success_metrics": [
        "Plan covers refund + chargeback flows",
        "Plan names a fallback when payment provider is down",
    ],
    "probation_status": "promoted",
    "version": 3,
}

PERSONAS_RESPONSE_200: dict[str, Any] = {
    "description": (
        "Persona shelves from ``configs/personas/shelves.yaml`` "
        "(``business_area`` and ``development_role`` lists). Each entry now "
        "carries the fo127 optional fields (``instructions``, "
        "``capability_profile``, ``boundary_statement``, ``allowed_tools``, "
        "``success_metrics``, ``probation_status``) plus a monotonic per-entry "
        "``version`` used for optimistic-concurrency on the write API. Legacy "
        "entries that lack any of these fields keep loading; the wire payload "
        "omits absent optional keys."
    ),
    "content": {
        "application/json": {
            "example": {
                "version": 1,
                "business_area": [_PERSONA_ENTRY_FULL_EXAMPLE],
                "development_role": [
                    {
                        "id": "backend_engineer",
                        "display_name": "Backend engineer",
                        "version": 1,
                    },
                ],
            },
        },
    },
}

PERSONA_UPSERT_RESPONSE_200: dict[str, Any] = {
    "description": (
        "Persona entry was upserted; response carries the refreshed shelf "
        "catalog (same shape as ``GET /v1/personas``). The mutated entry's "
        "``version`` is incremented by one (or set to 1 on first create)."
    ),
    "content": {
        "application/json": {
            "example": {
                "version": 1,
                "business_area": [_PERSONA_ENTRY_FULL_EXAMPLE],
                "development_role": [
                    {
                        "id": "backend_engineer",
                        "display_name": "Backend engineer",
                        "version": 1,
                    },
                ],
            },
        },
    },
}

PERSONA_DELETE_RESPONSE_204: dict[str, Any] = {
    "description": (
        "Persona entry was removed. ``persona.shelf.updated`` event recorded "
        "the deletion (``fields_changed = ['__deleted__']``)."
    ),
}

PERSONA_VERSION_CONFLICT_409: dict[str, Any] = {
    "description": (
        "Optimistic-concurrency conflict: caller's ``expected_version`` does "
        "not match the current ``version`` on disk. Re-read the entry via "
        "``GET /v1/personas`` and retry. Same shape as other Problem-JSON "
        "errors (``code = 'persona_version_conflict'``)."
    ),
    "content": _PROBLEM_JSON_CONTENT,
}

PERSONA_ALREADY_EXISTS_409: dict[str, Any] = {
    "description": (
        "``POST /v1/personas/{shelf}`` rejected: a persona with the supplied "
        "``id`` already lives on the shelf. Use ``PUT`` / ``PATCH`` to update."
    ),
    "content": _PROBLEM_JSON_CONTENT,
}

PREFLIGHT_HISTORY_RESPONSE_200: dict[str, Any] = {
    "description": (
        "Fleet preflight history: one entry per recent ``run_id`` with the same "
        "top-level ``preflight`` projection as ``GET /v1/runs/{run_id}/timeline`` "
        "(``null`` when no ``model.preflight.passed`` event exists). Also includes "
        "bounded aggregate SLI fields: ``runs_with_preflight``, "
        "``runs_without_preflight``, ``runs_with_p95_latency``, "
        "``avg_p95_latency_ms``, ``max_p95_latency_ms``, ``preflight_coverage_ratio``, "
        "``p95_latency_coverage_ratio``, ``runs_with_multisample_preflight``, "
        "``runs_with_checks_passed``, and ``distinct_validated_model_id_count``. "
        "Query ``include_metrics_export=1`` attaches a stable ``metrics_export`` "
        "object (``export_schema_version``, ``export_window_consistent``, echoed "
        "filters) for external metrics scrapers. Performs O(limit) replay reads."
    ),
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "entries": {"type": "array"},
                    "limit": {"type": "integer"},
                    "total": {"type": "integer"},
                    "has_more": {"type": "boolean"},
                    "order": {"type": "string"},
                    "runs_with_preflight": {"type": "integer"},
                    "runs_without_preflight": {"type": "integer"},
                    "runs_with_p95_latency": {"type": "integer"},
                    "avg_p95_latency_ms": {"type": ["number", "null"]},
                    "max_p95_latency_ms": {"type": ["integer", "null"]},
                    "preflight_coverage_ratio": {"type": ["number", "null"]},
                    "p95_latency_coverage_ratio": {"type": ["number", "null"]},
                    "runs_with_multisample_preflight": {"type": "integer"},
                    "runs_with_checks_passed": {"type": "integer"},
                    "distinct_validated_model_id_count": {"type": "integer"},
                    "metrics_export": {
                        "type": ["object", "null"],
                        "properties": {
                            "generated_at": {"type": "string"},
                            "export_schema_version": {"type": "integer"},
                            "export_window_consistent": {"type": "boolean"},
                            "window_limit": {"type": "integer"},
                            "window_offset": {"type": "integer"},
                            "order": {"type": "string"},
                            "window_total_matching_runs": {"type": "integer"},
                            "runs_scanned": {"type": "integer"},
                            "has_more": {"type": "boolean"},
                            "runs_with_preflight": {"type": "integer"},
                            "runs_without_preflight": {"type": "integer"},
                            "runs_with_p95_latency": {"type": "integer"},
                            "runs_with_multisample_preflight": {"type": "integer"},
                            "runs_with_checks_passed": {"type": "integer"},
                            "distinct_validated_model_id_count": {"type": "integer"},
                            "avg_p95_latency_ms": {"type": ["number", "null"]},
                            "max_p95_latency_ms": {"type": ["integer", "null"]},
                            "preflight_coverage_ratio": {"type": ["number", "null"]},
                            "p95_latency_coverage_ratio": {"type": ["number", "null"]},
                            "filters": {
                                "type": "object",
                                "properties": {
                                    "workflow_profile": {"type": ["string", "null"]},
                                    "workflow_profile_prefix": {"type": ["string", "null"]},
                                    "created_after": {"type": ["string", "null"]},
                                    "created_before": {"type": ["string", "null"]},
                                    "has_escalation": {"type": ["boolean", "null"]},
                                    "status": {"type": ["string", "null"]},
                                },
                            },
                        },
                    },
                },
            },
            "example": {
                "entries": [],
                "limit": 10,
                "total": 0,
                "has_more": False,
                "order": "newest_first",
                "runs_with_preflight": 0,
                "runs_without_preflight": 0,
                "runs_with_p95_latency": 0,
                "avg_p95_latency_ms": None,
                "max_p95_latency_ms": None,
                "preflight_coverage_ratio": None,
                "p95_latency_coverage_ratio": None,
                "runs_with_multisample_preflight": 0,
                "runs_with_checks_passed": 0,
                "distinct_validated_model_id_count": 0,
                "metrics_export": {
                    "generated_at": "2026-05-27T12:00:00+00:00",
                    "export_schema_version": 1,
                    "export_window_consistent": True,
                    "window_limit": 10,
                    "window_offset": 0,
                    "order": "newest_first",
                    "window_total_matching_runs": 0,
                    "runs_scanned": 0,
                    "has_more": False,
                    "runs_with_preflight": 0,
                    "runs_without_preflight": 0,
                    "runs_with_p95_latency": 0,
                    "runs_with_multisample_preflight": 0,
                    "runs_with_checks_passed": 0,
                    "distinct_validated_model_id_count": 0,
                    "avg_p95_latency_ms": None,
                    "max_p95_latency_ms": None,
                    "preflight_coverage_ratio": None,
                    "p95_latency_coverage_ratio": None,
                    "filters": {
                        "workflow_profile": None,
                        "workflow_profile_prefix": None,
                        "created_after": None,
                        "created_before": None,
                        "has_escalation": None,
                        "status": None,
                    },
                },
            },
        },
    },
}

SCRAPER_ARTIFACT_INVENTORY_RESPONSE_200: dict[str, Any] = {
    "description": (
        "Read-only inventory of regular files under the configured scraper artifact "
        "base directory (missing directory ⇒ empty inventory, not an error). "
        "Includes retention-oriented metadata when available: "
        "``retention_max_age_days``, ``retention_stale_file_count``, "
        "``retention_stale_bytes``, object-store readiness "
        "``storage_backend`` / ``object_store_configured`` / ``object_store_ready``, "
        "object-store prune intent/effectiveness "
        "``object_store_prune_requested`` / ``object_store_prune_effective``, "
        "``retention_execution_mode``, and ``retention_alert_level``."
    ),
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "base_dir": {"type": "string"},
                    "exists": {"type": "boolean"},
                    "file_count": {"type": "integer"},
                    "total_bytes": {"type": "integer"},
                    "truncated": {"type": "boolean"},
                    "oldest_mtime_iso": {"type": ["string", "null"]},
                    "newest_mtime_iso": {"type": ["string", "null"]},
                    "retention_max_age_days": {"type": ["integer", "null"]},
                    "retention_stale_file_count": {"type": "integer"},
                    "retention_stale_bytes": {"type": "integer"},
                    "storage_backend": {"type": "string"},
                    "object_store_configured": {"type": "boolean"},
                    "object_store_ready": {"type": "boolean"},
                    "object_store_prune_requested": {"type": "boolean"},
                    "object_store_prune_effective": {"type": "boolean"},
                    "retention_execution_mode": {"type": "string"},
                    "retention_alert_level": {"type": "string"},
                    "entries": {"type": "array"},
                },
            },
            "example": {
                "base_dir": "/repo/.cache/hermes_scraper",
                "exists": True,
                "file_count": 2,
                "total_bytes": 4096,
                "truncated": False,
                "oldest_mtime_iso": "2026-05-20T00:00:00Z",
                "newest_mtime_iso": "2026-05-26T00:00:00Z",
                "retention_max_age_days": 14,
                "retention_stale_file_count": 0,
                "retention_stale_bytes": 0,
                "storage_backend": "local",
                "object_store_configured": False,
                "object_store_ready": False,
                "object_store_prune_requested": False,
                "object_store_prune_effective": False,
                "retention_execution_mode": "local_only",
                "retention_alert_level": "none",
                "entries": [],
            },
        },
    },
}
