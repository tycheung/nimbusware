"""Shared OpenAPI response fragments.

Routes import the ``PROBLEM_RESPONSE_*``, ``CREATE_RUN_RESPONSE_200``, and
``RUN_TIMELINE_RESPONSE_200`` dicts for ``responses=`` (timeline **200** merges description +
``Link`` header with ``response_model``). Timeline optional-key policy matches
``packages/nimbusware_api/routes/runs.py`` (presence-gated timeline helpers).
Problem bodies are documented under both ``application/json`` and ``application/problem+json``
(same schema). A full OpenAPI ``$ref`` component registry is optional if
generated schema size or fragment reuse becomes a problem; the Problem JSON shape is
single-sourced via ``Problem.model_json_schema()`` in ``_PROBLEM_JSON_CONTENT``.

**Read-path 5xx policy (§14 #3):** document ``500: PROBLEM_RESPONSE_500`` on each ``GET``
handler for OpenAPI parity with the app-level default and uncaught-exception handler; do not
introduce a separate component ``$ref`` registry unless schema duplication becomes costly.
"""

from __future__ import annotations

from typing import Any

from nimbusware_api.schemas.problem import Problem

_problem_schema = Problem.model_json_schema()
_PROBLEM_JSON_CONTENT: dict[str, Any] = {
    "application/json": {"schema": _problem_schema},
    "application/problem+json": {"schema": _problem_schema},
}

PROBLEM_RESPONSE_401: dict[str, Any] = {
    "description": "Missing or invalid admin token (``X-Nimbusware-Admin-Token``)",
    "content": _PROBLEM_JSON_CONTENT,
}

PROBLEM_RESPONSE_404: dict[str, Any] = {
    "description": "Run not found (no events for ``run_id``)",
    "content": _PROBLEM_JSON_CONTENT,
}

PROBLEM_RESPONSE_422: dict[str, Any] = {
    "description": "Structured error (``code``, ``message``, optional ``details``)",
    "content": _PROBLEM_JSON_CONTENT,
}

PROBLEM_RESPONSE_500: dict[str, Any] = {
    "description": "Uncaught server fault (``code`` is typically ``internal_error``)",
    "content": _PROBLEM_JSON_CONTENT,
}

PROBLEM_RESPONSE_503: dict[str, Any] = {
    "description": "Server misconfiguration (e.g. admin token not set)",
    "content": _PROBLEM_JSON_CONTENT,
}
