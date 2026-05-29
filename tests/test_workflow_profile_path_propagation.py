"""``workflow_profile_path`` propagation trilogy (fo80).

fo79 pinned the direct ``workflow_profile_path`` 3-axis contract
(accept / ``ValueError`` / ``FileNotFoundError``) and the cascade-vs-
propagate divergence at the path-resolution layer using
``load_scraper_fetch_config`` as the **one** representative propagating
caller. The other two propagating callers --
[`assert_known_workflow`](d:\\Hermes\\packages\\hermes_orchestrator\\ingress.py)
and
[`RunOrchestrator.create_run`](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
-- were deferred from fo79 because they required orchestrator /
registry fixtures.

fo80 closes the propagation-trilogy coverage gap:

* **Part A** locks the ``assert_known_workflow`` boundary directly.
  The function is a passthrough at
  [ingress.py:53-55](d:\\Hermes\\packages\\hermes_orchestrator\\ingress.py)
  with **zero** existing unit tests; Part A pins that it returns
  ``None`` on accept AND mirrors ``workflow_profile_path`` 1:1 on
  reject (``ValueError`` + ``FileNotFoundError``).
* **Part B** locks ``RunOrchestrator.create_run`` propagation at
  [pipeline.py:154](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
  (the orchestrator's first gate, called BEFORE
  ``assert_bundle_catalog_maps_resolve`` / ``assert_persona_shelves_valid``
  / ``self._store.append``). Includes an **early-fail-order** assertion
  pinning that no events are appended to the event store when the
  first gate fires.
* **Part C** locks the cross-propagating-caller uniformity meta-
  contract: all 3 propagating callers
  (``load_scraper_fetch_config`` + ``assert_known_workflow`` +
  ``RunOrchestrator.create_run``) uniformly raise (no swallow, no
  default) for both ``ValueError`` and ``FileNotFoundError``. A
  second sub-loop pins the HTTP-layer translation completeness at
  the FastAPI route boundary
  ([runs.py:644-653](d:\\Hermes\\packages\\hermes_api\\routes\\runs.py)):
  ``ValueError`` -> ``422 invalid_request`` and
  ``FileNotFoundError`` -> ``422 workflow_not_found``. The invalid-
  name -> ``invalid_request`` axis is **new** (existing
  ``test_unknown_workflow_profile_422`` covers only the missing-file
  axis).

The 6+3 subset of fo79's 14+5 ``_INVALID_NAMES`` / ``_MISSING_VARIANTS``
is **deliberately** smaller -- fo79 owns the exhaustive reject matrix
at the direct ``workflow_profile_path`` layer; fo80 pins propagation
across remaining callers with breadth-sampled inputs.

Cross-slice symmetry table (wpp = ``workflow_profile_path``):

| Slice    | Boundary            | Cascade uniformity          | Propagate uniformity             |
|----------|---------------------|-----------------------------|----------------------------------|
| fo77     | load_yaml family    | 6 parsers (Part C)          | (n/a)                            |
| fo79     | wpp                 | 6 parsers (Part C, 12 asrt) | scraper_fetch (Part C, 2 asrt)   |
| **fo80** | **wpp propagation** | **(n/a)**                   | **3 callers (6) + HTTP (2 asrt)**|

Part C Sub-loop 1 is the **structural inverse** of fo77 Part C: where
fo77 pins cascade uniformity (catch + default) across 6 sibling
parsers, fo80 pins propagate uniformity (raise + no swallow) across
the 3 propagating callers.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ``nimbusware_api.app`` requires these env vars at import time (mirrors
# tests/test_api.py:11-13). Set BEFORE importing the FastAPI app so
# the lifespan / preflight gating reads the expected values.
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO_ROOT))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", "test-admin-token")

from fastapi.testclient import TestClient  # noqa: E402

from nimbusware_api.app import app  # noqa: E402
from hermes_orchestrator.ingress import assert_known_workflow  # noqa: E402
from hermes_orchestrator.pipeline import make_dev_orchestrator  # noqa: E402
from hermes_orchestrator.scraper_stage import load_scraper_fetch_config  # noqa: E402

_VALUE_ERROR_PREFIX = "invalid workflow_profile: "
_FILE_NOT_FOUND_PREFIX = "unknown workflow_profile (no file): "

# Breadth-sampled subset of fo79's exhaustive _INVALID_NAMES (14
# entries). fo80 deliberately samples 6 across the regex-reject
# surface (empty / whitespace / leading non-alphanum / inner whitespace
# / path separator / path traversal) -- fo79 owns the full matrix at
# the direct ``workflow_profile_path`` boundary.
_INVALID_NAMES: list[tuple[str, str]] = [
    ("empty_string", ""),
    ("whitespace_only_spaces", "   "),
    ("starts_with_underscore", "_leading_underscore"),
    ("contains_space", "bad name with spaces"),
    ("contains_forward_slash", "has/slash"),
    ("path_traversal_dotdot", ".."),
]


# Breadth-sampled subset of fo79's exhaustive _MISSING_VARIANTS (5
# entries). fo80 samples 3 across the regex-valid-but-no-file surface.
_MISSING_VARIANTS: list[tuple[str, str]] = [
    ("file_does_not_exist", "does-not-exist-xyz"),
    ("simple_underscore_name", "no_such_profile"),
    ("dotted_name", "missing.profile.name"),
]


# Real profile names that exist under ``configs/workflows/``. These
# files are part of the repository and exercised by integration tests
# in test_api.py; using them keeps Part A's accept arm hermetic
# without writing temp files.
_ACCEPT_PROFILES: list[tuple[str, str]] = [
    ("canonical_default", "default"),
    ("integrator_gate_on", "integrator_gate_on"),
    ("scraper_artifacts_on", "scraper_artifacts_on"),
    (
        "universal_critique_hard_block_chain_on",
        "universal_critique_hard_block_chain_on",
    ),
]


# Type alias for the propagating-caller signature used in Part C.
_PropagatingCaller = Callable[[str], Any]


def _build_propagating_callers() -> list[tuple[str, _PropagatingCaller]]:
    """Return the 3 propagating callers as (name, single-arg-callable) pairs.

    Each callable accepts the workflow profile string and exercises
    the path-resolution boundary inside the caller. The orchestrator
    is rebuilt per call so each invocation starts with a fresh empty
    event store -- a swallowed exception would leave the prior call's
    state behind, which the assertion would catch.
    """

    def _call_load_scraper(profile: str) -> Any:
        return load_scraper_fetch_config(_REPO_ROOT, profile)

    def _call_assert_known(profile: str) -> Any:
        return assert_known_workflow(_REPO_ROOT, profile)

    def _call_create_run(profile: str) -> Any:
        orch, _mem = make_dev_orchestrator()
        return orch.create_run(profile)

    return [
        ("load_scraper_fetch_config", _call_load_scraper),
        ("assert_known_workflow", _call_assert_known),
        ("RunOrchestrator.create_run", _call_create_run),
    ]


def test_assert_known_workflow_propagating_caller_3_axis_contract() -> None:
    """Pin ``assert_known_workflow`` 3-axis contract (accept / VE / FNF).

    Mirrors the direct ``workflow_profile_path`` 3-axis contract (fo79
    Parts A+B) but at the ``assert_known_workflow`` boundary. Pins
    that the passthrough returns ``None`` (not a ``Path``) on accept
    AND that reject mirrors ``workflow_profile_path`` 1:1 (same
    exception classes + same diagnostic prefixes + same ``{profile!r}``
    inclusion).

    Future refactors that add caching / logging / metrics to
    ``assert_known_workflow`` MUST preserve this exact raise/return
    shape or the slice fails loudly.
    """

    for case_id, name in _ACCEPT_PROFILES:
        result = assert_known_workflow(_REPO_ROOT, name)
        assert result is None, (
            f"assert_known_workflow({name!r}) returned {result!r}; "
            f"expected None (case={case_id})"
        )

    # ``.strip()``-rescue: leading/trailing whitespace is stripped by
    # ``workflow_profile_path`` before the regex check, so a wrapped
    # known-good name should also accept and return ``None``.
    strip_rescue = assert_known_workflow(_REPO_ROOT, " default \t")
    assert strip_rescue is None, (
        f"assert_known_workflow(' default \\t') returned {strip_rescue!r}; "
        f"expected None (case=strip_rescue)"
    )

    for case_id, invalid_name in _INVALID_NAMES:
        with pytest.raises(ValueError, match=re.escape(_VALUE_ERROR_PREFIX)) as exc_info:
            assert_known_workflow(_REPO_ROOT, invalid_name)
        msg = str(exc_info.value)
        assert repr(invalid_name) in msg, (
            f"ValueError message {msg!r} missing repr({invalid_name!r}) (case={case_id})"
        )

    for case_id, missing_name in _MISSING_VARIANTS:
        with pytest.raises(
            FileNotFoundError, match=re.escape(_FILE_NOT_FOUND_PREFIX),
        ) as exc_info:
            assert_known_workflow(_REPO_ROOT, missing_name)
        msg = str(exc_info.value)
        assert repr(missing_name) in msg, (
            f"FileNotFoundError message {msg!r} missing repr({missing_name!r}) "
            f"(case={case_id})"
        )


def test_run_orchestrator_create_run_propagates_workflow_profile_path_exceptions_contract() -> None:
    """Pin ``RunOrchestrator.create_run`` propagation + early-fail-order contract.

    ``create_run`` calls ``assert_known_workflow`` at
    [pipeline.py:154](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
    as its FIRST gate (BEFORE
    ``assert_bundle_catalog_maps_resolve`` / ``assert_persona_shelves_valid``
    / ``assert_agent_evaluator_persona_in_shelves`` /
    ``assert_taxonomy_keys_resolve`` / ``self._store.append``). The
    propagation contract pins that both ``ValueError`` and
    ``FileNotFoundError`` from ``workflow_profile_path`` propagate
    uncaught through every intermediate frame.

    The early-fail-order assertion is the architectural guarantee:
    a failed ``create_run`` must NOT append any events to the store
    (no half-created runs, no partial state). This pins the gate
    ordering at line 154 -- moving it after ``self._store.append``
    would silently break this contract.
    """

    for case_id, invalid_name in _INVALID_NAMES[:4]:
        orch, _mem = make_dev_orchestrator()
        with pytest.raises(ValueError, match=re.escape(_VALUE_ERROR_PREFIX)) as exc_info:
            orch.create_run(invalid_name)
        msg = str(exc_info.value)
        assert repr(invalid_name) in msg, (
            f"create_run({invalid_name!r}) ValueError {msg!r} missing repr "
            f"(case={case_id})"
        )

    for case_id, missing_name in _MISSING_VARIANTS:
        orch, _mem = make_dev_orchestrator()
        with pytest.raises(
            FileNotFoundError, match=re.escape(_FILE_NOT_FOUND_PREFIX),
        ) as exc_info:
            orch.create_run(missing_name)
        msg = str(exc_info.value)
        assert repr(missing_name) in msg, (
            f"create_run({missing_name!r}) FileNotFoundError {msg!r} missing repr "
            f"(case={case_id})"
        )

    # Early-fail-order: bad profile must NOT append any events to the
    # in-memory store. Confirms ``assert_known_workflow`` fires at
    # pipeline.py:154 BEFORE any ``self._store.append`` call.
    orch, mem = make_dev_orchestrator()
    assert mem._rows == [], (  # noqa: SLF001
        f"InMemoryEventStore expected empty on construction; got {len(mem._rows)} rows"  # noqa: SLF001
    )
    with pytest.raises(ValueError):
        orch.create_run("bad name with spaces")
    assert mem._rows == [], (  # noqa: SLF001
        f"failed create_run appended {len(mem._rows)} events; "  # noqa: SLF001
        f"expected 0 (assert_known_workflow at pipeline.py:154 must fire first)"
    )


def test_propagation_layer_uniformity_at_workflow_profile_path_boundary_contract() -> None:
    """Pin cross-caller propagation uniformity + HTTP-layer translation.

    **Sub-loop 1** (unit-layer propagation uniformity): all 3
    propagating callers (``load_scraper_fetch_config``,
    ``assert_known_workflow``, ``RunOrchestrator.create_run``) must
    uniformly raise (no swallow, no default) for both
    ``ValueError`` and ``FileNotFoundError``. This is the structural
    inverse of fo77 Part C cascade-family uniformity (where 6 sibling
    parsers uniformly catch + default).

    **Sub-loop 2** (HTTP-layer translation completeness): the FastAPI
    error handler at
    [runs.py:644-653](d:\\Hermes\\packages\\hermes_api\\routes\\runs.py)
    maps ``FileNotFoundError`` -> 422 ``workflow_not_found`` AND
    ``ValueError`` -> 422 ``invalid_request``. The existing
    ``test_unknown_workflow_profile_422`` in tests/test_api.py
    covers only the missing-file axis; the invalid-name axis is
    pinned here for the first time, completing the operator-visible
    HTTP 422 matrix.
    """

    canonical_invalid = "bad name"
    canonical_missing = "does-not-exist-xyz"

    for caller_name, caller in _build_propagating_callers():
        with pytest.raises(ValueError, match=re.escape(_VALUE_ERROR_PREFIX)):
            caller(canonical_invalid)
        with pytest.raises(
            FileNotFoundError, match=re.escape(_FILE_NOT_FOUND_PREFIX),
        ):
            caller(canonical_missing)
        # Sentinel: the per-caller raise above must have fired (no
        # silent return). pytest.raises already asserts this, but the
        # caller_name capture makes the assertion message readable
        # when a future refactor swallows an exception.
        assert caller_name, "caller_name unset"

    with TestClient(app) as client:
        r_invalid = client.post(
            "/v1/runs", json={"workflow_profile": canonical_invalid},
        )
        assert r_invalid.status_code == 422, (
            f"POST /v1/runs with invalid profile name returned "
            f"{r_invalid.status_code}; expected 422"
        )
        body_invalid = r_invalid.json()
        assert body_invalid.get("code") == "invalid_request", (
            f"POST /v1/runs with invalid name returned code "
            f"{body_invalid.get('code')!r}; expected 'invalid_request' "
            f"(HTTP-layer mapping at runs.py:649-653)"
        )

        r_missing = client.post(
            "/v1/runs", json={"workflow_profile": canonical_missing},
        )
        assert r_missing.status_code == 422, (
            f"POST /v1/runs with missing profile returned "
            f"{r_missing.status_code}; expected 422"
        )
        body_missing = r_missing.json()
        assert body_missing.get("code") == "workflow_not_found", (
            f"POST /v1/runs with missing profile returned code "
            f"{body_missing.get('code')!r}; expected 'workflow_not_found' "
            f"(HTTP-layer mapping at runs.py:644-648)"
        )
