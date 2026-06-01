"""Persona catalog HTTP API with optional editing surface.

GET stays unauthenticated (read-only catalog discovery); POST / PUT / PATCH /
DELETE require ``X-Nimbusware-Admin-Token`` since they mutate ``shelves.yaml`` and
emit a ``persona.shelf.updated`` audit event into the append-only store.

Optimistic concurrency: PATCH / PUT / DELETE all carry ``expected_version``
(int) that must match the on-disk ``version`` of the affected entry; mismatch
yields HTTP 409 ``persona_version_conflict``. POST honors ``Idempotency-Key``
(matches the ``POST /v1/runs`` precedent) — a replayed key returns the prior
catalog without appending a second event.
"""

from nimbusware_api.routes.personas_handlers import router

__all__ = ["router"]
