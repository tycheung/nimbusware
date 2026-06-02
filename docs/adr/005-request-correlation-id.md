# ADR 005: Request correlation id

## Status

Accepted (June 2026, Lane V3 fo633)

## Context

API access logs (ADR 004) lacked a correlation identifier, making it hard to tie client retries to server log lines.

## Decision

- Every HTTP response includes `X-Request-Id`.
- Clients may supply `X-Request-Id`; when absent or blank the API generates a UUID.
- `nimbusware_api.request` logs include `request_id=<value>` on each line.

## Consequences

- Operators can grep logs by request id without enabling body logging.
- Future OpenTelemetry spans can reuse the same header as trace parent (not implemented in V3).
