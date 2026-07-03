# ADR 002: Edition gate

## Status

Accepted

## Context

The platform ships Individual (single-operator) and Enterprise (multi-tenant) editions from one codebase without forking packages.

## Decision

Use `NIMBUSWARE_EDITION` (`individual` | `enterprise`) via `env.edition`. Enterprise-only HTTP routes call `_require_enterprise()` and return **404** on Individual. IAM middleware requires `X-Nimbusware-Api-Key` on enterprise for nearly all `/v1/*` routes.

## Consequences

- Open-core defaults stay usable without IAM or fleet infra.
- Feature detection is centralized; console and API share the same gate.
- Tests can run Individual mode without Postgres IAM bootstrap.
