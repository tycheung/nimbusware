from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pytest

from nimbusware_env import find_repo_root

_REPO_ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])

# ``nimbusware_api.app`` requires these env vars at import time (mirrors
# tests/test_api.py:11-13 and tests/test_workflow_profile_path_propagation.py).
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO_ROOT))
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)

from fastapi.testclient import TestClient  # noqa: E402

from nimbusware_api.app import app  # noqa: E402
from nimbusware_orchestrator.ingress import (  # noqa: E402
    assert_persona_shelves_valid,
    assert_taxonomy_keys_resolve,
)
from nimbusware_orchestrator.registry import RoleRegistry  # noqa: E402

_TAXONOMY_KEY_ERROR_PREFIX = "Unknown role taxonomy_key:"
_SHELVES_FNF_PREFIX = "missing persona catalog shelves:"
_SHELVES_ROOT_VE_PREFIX = "persona shelves:"
_LOAD_YAML_ROOT_VE_PREFIX = "YAML root must be a mapping:"


# Real taxonomy keys from configs/roles.yaml -- pinned so the accept
# arm fails loudly if roles.yaml drifts.
_KNOWN_TAXONOMY_KEYS: list[str] = ["planner", "backend_writer", "test_writer"]


# Unknown taxonomy keys -- breadth-sampled across the surface that
# RoleRegistry.resolve rejects (post-strip-lower lookup miss).
_UNKNOWN_TAXONOMY_KEYS: list[tuple[str, str]] = [
    ("not_a_real_role", "not_a_real_role"),
    ("fictional_critic_suffix", "fictional_critic"),
    ("empty_string", ""),
]


# Invalid persona shelves YAML bodies -- breadth-sampled across the
# four reject-arm sub-paths in PersonaShelf.validate_structure
# (plus one load_yaml-layer reject for the non-mapping root path).
_INVALID_SHELVES_BODIES: list[tuple[str, str, str]] = [
    (
        "scalar_root_via_load_yaml",
        "some-scalar\n",
        _LOAD_YAML_ROOT_VE_PREFIX,
    ),
    (
        "business_area_not_a_list",
        "business_area: 'not a list'\ndevelopment_role: []\n",
        f"{_SHELVES_ROOT_VE_PREFIX} 'business_area'",
    ),
    (
        "business_area_empty_list",
        "business_area: []\ndevelopment_role: [{id: r1}]\n",
        f"{_SHELVES_ROOT_VE_PREFIX} 'business_area'",
    ),
    (
        "business_area_entry_empty_id",
        "business_area: [{id: ''}]\ndevelopment_role: [{id: r1}]\n",
        "must include a non-empty string id",
    ),
]


# 3 HTTP-translation classes for Part C -- (axis_id, exception class,
# expected HTTP problem code at runs.py:644-658).
_HTTP_TRANSLATION_AXES: list[tuple[str, type[BaseException], str]] = [
    ("file_not_found", FileNotFoundError, "workflow_not_found"),
    ("value_error", ValueError, "invalid_request"),
    ("key_error", KeyError, "registry_key_error"),
]


from unit.composite_repo_fixtures import write_persona_shelves


def _make_create_run_raising(
    exc_class: type[BaseException],
    msg: str,
) -> Any:
    """Build a ``create_run`` replacement that raises ``exc_class(msg)``.

    Used by Part C to monkeypatch ``app.state.orchestrator.create_run``
    so each HTTP-translation axis is isolated from real-gate fixtures.
    """

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise exc_class(msg)

    return _raise


def test_assert_taxonomy_keys_resolve_2_axis_contract() -> None:
    """Pin ``assert_taxonomy_keys_resolve`` 2-axis contract (accept / KE).

    The function is a thin loop over ``RoleRegistry.resolve`` at
    [ingress.py:58-61](packages\\nimbusware_orchestrator\\ingress.py):

    ```python
    def assert_taxonomy_keys_resolve(registry, keys):
        for k in keys:
            registry.resolve(k)
    ```

    Reject contract from
    [registry.py:67-72](packages\\nimbusware_orchestrator\\registry.py):
    ``Unknown role taxonomy_key: {taxonomy_key!r}``. Zero existing
    direct tests anywhere in ``tests/`` (only mentioned in fo80
    docstrings) -- fo81 Part A is the first.
    """

    reg = RoleRegistry.from_yaml(_REPO_ROOT / "configs" / "roles.yaml")

    for known in _KNOWN_TAXONOMY_KEYS:
        result = assert_taxonomy_keys_resolve(reg, [known])
        assert result is None, (
            f"assert_taxonomy_keys_resolve(reg, [{known!r}]) returned {result!r}; expected None"
        )

    # Empty-list arm: no-op loop, no exception.
    empty_result = assert_taxonomy_keys_resolve(reg, [])
    assert empty_result is None, (
        f"assert_taxonomy_keys_resolve(reg, []) returned {empty_result!r}; "
        f"expected None (no-op for empty input)"
    )

    for case_id, unknown_key in _UNKNOWN_TAXONOMY_KEYS:
        with pytest.raises(
            KeyError,
            match=re.escape(_TAXONOMY_KEY_ERROR_PREFIX),
        ) as exc_info:
            assert_taxonomy_keys_resolve(reg, [unknown_key])
        msg = str(exc_info.value)
        assert repr(unknown_key) in msg, (
            f"KeyError message {msg!r} missing repr({unknown_key!r}) (case={case_id})"
        )


def test_assert_persona_shelves_valid_3_axis_wrapper_contract(tmp_path: Path) -> None:
    """Pin ``assert_persona_shelves_valid`` 3-axis wrapper contract.

    Existing tests only hit the happy path (real repo); the
    wrapper-level ``FileNotFoundError`` (missing file) and
    ``ValueError`` (invalid structure) axes are unpinned. Wrapper at
    [ingress.py:22-28](packages\\nimbusware_orchestrator\\ingress.py)
    formats ``f"missing persona catalog shelves: {path}"`` for the
    FNF arm; ``PersonaShelf.validate_structure`` at
    [personas.py:14-37](packages\\nimbusware_extensions\\personas.py)
    + ``load_yaml`` at
    [merge.py:19-24](packages\\nimbusware_orchestrator\\merge.py)
    contribute the 4 ``ValueError`` sub-arms.

    All wrapper-layer errors are pinned as ``ValueError`` (not
    ``KeyError`` / ``AttributeError``) so the HTTP route's
    ``except ValueError`` block at runs.py:649-653 reliably catches
    every invalid-structure case.
    """

    # Accept arm -- real repo's configs/personas/shelves.yaml.
    accept_result = assert_persona_shelves_valid(_REPO_ROOT)
    assert accept_result is None, (
        f"assert_persona_shelves_valid({_REPO_ROOT}) returned {accept_result!r}; expected None"
    )

    # FNF arm -- tmp_path has no configs/personas/shelves.yaml file.
    with pytest.raises(
        FileNotFoundError,
        match=re.escape(_SHELVES_FNF_PREFIX),
    ) as fnf_info:
        assert_persona_shelves_valid(tmp_path)
    expected_path = tmp_path / "configs" / "personas" / "shelves.yaml"
    assert str(expected_path) in str(fnf_info.value), (
        f"FileNotFoundError message {fnf_info.value!r} missing resolved path {expected_path!s}"
    )

    # ValueError arm -- 4 invalid YAML bodies, one per sub-path.
    for case_id, body, expected_prefix in _INVALID_SHELVES_BODIES:
        body_tmp = tmp_path / case_id
        body_tmp.mkdir(parents=True, exist_ok=True)
        write_persona_shelves(body_tmp, body)
        with pytest.raises(ValueError, match=re.escape(expected_prefix)):
            assert_persona_shelves_valid(body_tmp)


def test_create_run_http_exception_translation_matrix_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin 3-class HTTP-translation matrix at runs.py:644-658.

    Bypasses real orchestrator gating by monkeypatching
    ``app.state.orchestrator.create_run`` to inject each exception
    class. Each axis is isolated from any specific source gate, so
    this test proves the runs.py:644-658 translation block is
    correct regardless of which gate (line 154-158) raised.

    Combined with the existing real-fixture coverage:

    * ``FileNotFoundError`` -> ``workflow_not_found`` (existing
      ``test_unknown_workflow_profile_422`` + here);
    * ``ValueError`` -> ``invalid_request`` (fo80 Part C +
      here);
    * ``KeyError`` -> ``registry_key_error`` (**new** -- this is
      the first test anywhere that exercises the
      ``except KeyError`` arm at runs.py:654-658).

    Pins per axis: HTTP status code 422, problem-code (``code``
    field), AND that the orchestrator exception's ``str(exc)`` flows
    through to the JSON ``message`` field (3 assertions per axis x 3
    axes = 9 assertions).
    """

    with TestClient(app) as client:
        for case_id, exc_class, expected_code in _HTTP_TRANSLATION_AXES:
            injected_msg = f"test {case_id} sentinel message"
            monkeypatch.setattr(
                app.state.orchestrator,
                "create_run",
                _make_create_run_raising(exc_class, injected_msg),
            )
            r = client.post(
                "/v1/runs",
                json={"workflow_profile": "default"},
            )
            assert r.status_code == 422, (
                f"POST /v1/runs with patched {exc_class.__name__} returned "
                f"{r.status_code}; expected 422 (case={case_id})"
            )
            body = r.json()
            assert body.get("code") == expected_code, (
                f"POST /v1/runs with patched {exc_class.__name__} returned code "
                f"{body.get('code')!r}; expected {expected_code!r} (case={case_id})"
            )
            assert injected_msg in str(body.get("message", "")), (
                f"POST /v1/runs with patched {exc_class.__name__} returned "
                f"message {body.get('message')!r}; expected to contain "
                f"{injected_msg!r} (case={case_id}; pins str(exc) plumbing at "
                f"runs.py:647/652/657)"
            )
