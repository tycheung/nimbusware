# ADR 004: API request logging middleware

## Status

Accepted (2026-05)

## Context

Operators debugging run lifecycle issues need structured HTTP access logs without turning on full ASGI debug tracing. FastAPI routes are numerous (`/v1/runs`, timeline, bundles, enterprise IAM).

## Decision

Add lightweight HTTP middleware on the FastAPI app that logs one INFO line per request:

- method and path
- response status code
- elapsed milliseconds

Logging uses the standard library `logging` module under logger `nimbusware_api.request`. Unhandled exceptions continue to flow through existing exception handlers (500 problem+json).

## Consequences

- Production can tune verbosity via `LOG_LEVEL` / uvicorn log config without code changes.
- Middleware runs after IAM middleware in the stack; logged status reflects the final response.
- No request/response bodies are logged (avoid leaking tokens and run payloads).

## References

- `packages/nimbusware_api/app.py` — `_request_logging_middleware`
