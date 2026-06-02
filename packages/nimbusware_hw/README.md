# nimbusware_hw

Local hardware probe, tier classification, resource governor, and model fit ranking.

- **Probe** — RAM and CPU on Windows and Linux (`probe.py`).
- **API** — `GET /v1/platform/hardware`, `POST /v1/platform/hardware/rescan`.
- **Governor** — frozen on `run.created` as `metadata.resource_governor`.
- **Fixtures** — set `NIMBUSWARE_HW_FIXTURE=weak|medium|strong` for CI without GPU.
