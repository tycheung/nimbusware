"""Shared OpenAPI Problem+JSON response fragments for route ``responses=`` kwargs."""

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
