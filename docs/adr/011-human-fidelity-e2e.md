# ADR 011: Human-fidelity E2E stage

## Status

Accepted.

## Decision

Bundle negative-path templates, keyboard nav smoke, and axe stub into `human_fidelity` module; workflow stage `dev_env.human_fidelity` is enabled on `micro_slice_fullstack` and frozen on `run.created` as `dev_env_effective.human_fidelity_enabled`.
