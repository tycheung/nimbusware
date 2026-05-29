"""Ad-hoc preflight probe CLI: ``poetry run hermes-preflight``.

Runs the same Ollama health probe that fires at ``run.start`` (see
:mod:`hermes_orchestrator.preflight`), captures a per-sample latency
distribution sourced from ``HERMES_PREFLIGHT_LATENCY_SAMPLES`` (or
``--samples``), and emits a single-line JSON summary including a latency
histogram. Output goes to stdout by default; pass ``--output FILE`` to write
a newline-terminated JSON record suitable for log shipping.

Exit codes:

* ``0`` — preflight passed and a model was selected
* ``1`` — :class:`~hermes_orchestrator.preflight.PreflightError` (runtime
  unreachable, no configured model available, …)
* ``2`` — invalid arguments or config (e.g. unreadable YAML)

This CLI mirrors the orchestrator's runtime selection (``configs/model-routing.yaml``
``runtime.*`` / ``models.*`` / ``preflight.*`` keys) so operators can validate
their environment WITHOUT spinning up a full run. Histogram bucket edges are
fixed (50 / 100 / 250 / 500 / 1000 / 2500 / 5000 / 10000 ms) for downstream
visualisation stability.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_orchestrator.merge import load_yaml
from hermes_orchestrator.pipeline import default_paths
from hermes_orchestrator.preflight import PreflightError, run_model_preflight
from hermes_orchestrator.preflight_histogram import (
    BUCKET_EDGES_MS,
    build_histogram,
    empty_histogram,
)

# Re-export private aliases so test code and other internal callers that
# referenced these names before the fo124 lift continue to work.
_BUCKET_EDGES_MS = BUCKET_EDGES_MS
_build_histogram = build_histogram
_empty_histogram = empty_histogram

_SCHEMA_VERSION = 1
_TOOL_NAME = "hermes-preflight"


@contextmanager
def _env_overrides(
    *,
    samples: int | None,
    json_probe: bool,
) -> Generator[None, None, None]:
    """Temporarily set ``HERMES_PREFLIGHT_*`` env vars for the duration of one probe.

    Restores prior values on exit so callers (and tests that invoke ``main``
    in-process repeatedly) observe a clean ``os.environ``. ``samples=None``
    leaves the env var untouched; ``json_probe=False`` likewise leaves it alone.
    """
    saved: dict[str, str | None] = {}
    try:
        if samples is not None:
            saved["HERMES_PREFLIGHT_LATENCY_SAMPLES"] = os.environ.get(
                "HERMES_PREFLIGHT_LATENCY_SAMPLES",
            )
            os.environ["HERMES_PREFLIGHT_LATENCY_SAMPLES"] = str(samples)
        if json_probe:
            saved["HERMES_PREFLIGHT_JSON_PROBE"] = os.environ.get(
                "HERMES_PREFLIGHT_JSON_PROBE",
            )
            os.environ["HERMES_PREFLIGHT_JSON_PROBE"] = "1"
        yield
    finally:
        for k, prior in saved.items():
            if prior is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prior


def _extract_routing(cfg: dict[str, Any]) -> dict[str, Any]:
    """Mirror ``RunOrchestrator.start_run_after_preflight`` config extraction.

    Returns a flat bundle with the keys ``run_model_preflight`` accepts; the
    CLI keeps the same defaults so a successful CLI probe implies a future
    ``run.start`` will succeed against the same Ollama host.
    """
    runtime = cfg.get("runtime") or {}
    models = cfg.get("models") or {}
    primary = (models.get("primary") or {}).get("id", "llama3.1:8b")
    fb_raw = models.get("fallbacks") or []
    fallbacks = [
        str(x.get("id"))
        for x in fb_raw
        if isinstance(x, dict) and x.get("id") is not None
    ]
    base_url = str(runtime.get("base_url", "http://localhost:11434"))
    health = str(runtime.get("health_endpoint", "/api/tags"))
    preflight_cfg = cfg.get("preflight") if isinstance(cfg.get("preflight"), dict) else {}
    request_timeout = float(runtime.get("request_timeout_seconds", 10))
    return {
        "base_url": base_url,
        "health_endpoint": health,
        "primary_model_id": primary,
        "fallback_model_ids": fallbacks,
        "preflight_cfg": preflight_cfg,
        "request_timeout_seconds": request_timeout,
    }


def _samples_from_evidence(evidence: dict[str, Any] | None) -> list[int]:
    """Pull integer-ms samples out of the preflight evidence dict.

    Falls back to a singleton ``[health_latency_ms]`` when multisample data
    is unavailable (``HERMES_PREFLIGHT_LATENCY_SAMPLES`` unset or ``1``).
    Non-int entries are filtered defensively so a corrupted upstream payload
    cannot crash the histogram build.
    """
    if not isinstance(evidence, dict):
        return []
    raw = evidence.get("health_latency_samples_ms")
    if isinstance(raw, list):
        return [int(x) for x in raw if isinstance(x, int)]
    single = evidence.get("health_latency_ms")
    if isinstance(single, int):
        return [single]
    return []


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_TOOL_NAME,
        description=(
            "Run the Hermes agent Ollama preflight probe ad-hoc and emit a JSON "
            "histogram summary. Mirrors `run.start` selection logic so a "
            "successful CLI probe implies the next run.start will succeed."
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Path to model-routing YAML "
            "(default: <repo_root>/configs/model-routing.yaml)."
        ),
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help=(
            "Latency sample count for the health probe (1..20). Overrides "
            "$HERMES_PREFLIGHT_LATENCY_SAMPLES for this invocation. "
            "Values <1 are rejected; values >20 are silently clamped by the "
            "orchestrator's preflight module."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=(
            "HTTP timeout in seconds for each probe request "
            "(default: runtime.request_timeout_seconds from config, else 10)."
        ),
    )
    parser.add_argument(
        "--json-probe",
        action="store_true",
        help="Force $HERMES_PREFLIGHT_JSON_PROBE=1 for this invocation.",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Output file path; '-' (default) writes to stdout.",
    )
    return parser


def _write_output(output: str, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, separators=(",", ":"), default=str) + "\n"
    if output == "-":
        sys.stdout.write(serialized)
        sys.stdout.flush()
    else:
        Path(output).write_text(serialized, encoding="utf-8")


def _error_record(message: str, *, exit_code: int) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "tool": _TOOL_NAME,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "result": {
            "status": "error",
            "selected_model_id": None,
            "used_primary": None,
            "evidence": None,
            "error": message,
            "exit_code": exit_code,
        },
        "histogram": empty_histogram(),
    }


def main(argv: list[str] | None = None) -> int:
    from hermes_env import load_dotenv

    load_dotenv()
    """CLI entrypoint. Returns the process exit code.

    Exposed as a function for both ``[tool.poetry.scripts]`` (which calls
    ``main()`` with no args) and unit tests (which can pass an explicit
    ``argv`` list). Mutations to ``os.environ`` from ``--samples`` /
    ``--json-probe`` are restored before returning, so the function is safe
    to invoke repeatedly in the same Python process.
    """
    args = _build_parser().parse_args(argv)

    if args.samples is not None and args.samples < 1:
        _write_output(
            args.output,
            _error_record(
                f"--samples must be >=1 (got {args.samples})",
                exit_code=2,
            ),
        )
        return 2

    config_path = Path(args.config) if args.config else default_paths()[0]
    try:
        cfg = load_yaml(config_path)
    except FileNotFoundError as exc:
        _write_output(
            args.output,
            _error_record(f"config not found: {exc}", exit_code=2),
        )
        return 2
    except (ValueError, OSError) as exc:
        _write_output(
            args.output,
            _error_record(f"failed to load config: {exc}", exit_code=2),
        )
        return 2

    routing = _extract_routing(cfg)
    timeout = args.timeout if args.timeout is not None else routing["request_timeout_seconds"]
    samples_requested = args.samples if args.samples is not None else (
        # Reflect the env-var value verbatim (no clamping here) so the user
        # can see the gap between what they asked for vs what the orchestrator
        # used (reported separately via samples_used).
        int(os.environ.get("HERMES_PREFLIGHT_LATENCY_SAMPLES", "1") or "1")
        if (os.environ.get("HERMES_PREFLIGHT_LATENCY_SAMPLES") or "").strip().lstrip("-").isdigit()
        else 1
    )

    result: dict[str, Any]
    evidence: dict[str, Any] | None
    exit_code: int
    with _env_overrides(samples=args.samples, json_probe=args.json_probe):
        try:
            selected, evidence, used_primary = run_model_preflight(
                base_url=routing["base_url"],
                health_path=routing["health_endpoint"],
                primary_model_id=routing["primary_model_id"],
                fallback_model_ids=routing["fallback_model_ids"],
                timeout_seconds=float(timeout),
                preflight_cfg=routing["preflight_cfg"],
            )
            result = {
                "status": "ok",
                "selected_model_id": selected,
                "used_primary": used_primary,
                "evidence": evidence,
                "error": None,
            }
            exit_code = 0
        except PreflightError as exc:
            evidence = None
            result = {
                "status": "failed",
                "selected_model_id": None,
                "used_primary": None,
                "evidence": None,
                "error": str(exc),
            }
            exit_code = 1

    samples_ms = _samples_from_evidence(evidence)
    samples_used: int | None = None
    if isinstance(evidence, dict):
        raw_used = evidence.get("preflight_latency_sample_count")
        if isinstance(raw_used, int):
            samples_used = raw_used

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "tool": _TOOL_NAME,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "base_url": routing["base_url"],
        "health_endpoint": routing["health_endpoint"],
        "primary_model_id": routing["primary_model_id"],
        "fallback_model_ids": routing["fallback_model_ids"],
        "samples_requested": samples_requested,
        "samples_used": samples_used,
        "timeout_seconds": float(timeout),
        "json_probe_forced": bool(args.json_probe),
        "result": result,
        "histogram": build_histogram(samples_ms),
    }
    _write_output(args.output, payload)
    return exit_code


if __name__ == "__main__":  # pragma: no cover - exercised via pyproject script
    raise SystemExit(main())
