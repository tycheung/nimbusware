"""NIMBUSWARE_ROLES_FROM_DB`` compound AND-gate string-arm contract (fo70, §5 / §14 #16)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import hermes_orchestrator.runtime_bootstrap as _runtime_bootstrap
import nimbusware_api.app as _hermes_api_app_pkg  # noqa: F401 -- ensures submodule loads
from hermes_orchestrator.registry import RoleRegistry
from nimbusware_api.app import app
from nimbusware_iam.store import InMemoryIamStore

_FAKE_DB_URL = "postgresql://test:test@localhost/hermes"
_SENTINEL_REGISTRY = RoleRegistry.from_mapping(
    {},
    yaml_version=0,
    content_digest_sha256_16="db:hermes_roles_registry",
)

_APP_MODULE = sys.modules["nimbusware_api.app"]
"""Direct submodule reference because ``hermes_api/__init__.py`` does
``from nimbusware_api.app import app`` which rebinds ``nimbusware_api.app`` in
the package namespace to the **FastAPI instance** (shadowing the
submodule). ``mock.patch("nimbusware_api.app.X")`` follows the package
namespace via ``getattr`` and therefore lands on the FastAPI instance
rather than the submodule -- using ``patch.object(_APP_MODULE, ...)``
sidesteps that resolution and patches the function reference inside
the actual submodule namespace where the lifespan reads it.
"""


@contextmanager
def _run_lifespan(
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_url: str | None,
    roles_from_db: str | None,
) -> Iterator[tuple[MagicMock, MagicMock]]:
    """Drive the FastAPI lifespan with env scrubbed + the two DB call sites mocked.

    Yields ``(mock_db_loader, mock_postgres_store)`` so tests inspect
    call counts.

    ``db_url`` / ``roles_from_db``: ``None`` -> ``monkeypatch.delenv(...)``
    to exercise the absent-env arm; any string is set verbatim (no
    ``.strip()`` mirrors production semantics at
    [app.py:34](d:\\Hermes\\packages\\hermes_api\\app.py)).
    """
    if db_url is None:
        monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", db_url)
    if roles_from_db is None:
        monkeypatch.delenv("NIMBUSWARE_ROLES_FROM_DB", raising=False)
    else:
        monkeypatch.setenv("NIMBUSWARE_ROLES_FROM_DB", roles_from_db)
    monkeypatch.delenv("NIMBUSWARE_CONFIG_FROM_DB", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CONFIG_FROM_FILES", raising=False)
    with (
        patch.object(
            _runtime_bootstrap,
            "load_registry_from_postgres",
            return_value=_SENTINEL_REGISTRY,
        ) as mock_db_loader,
        patch.object(
            _runtime_bootstrap,
            "PostgresEventStore",
        ) as mock_postgres_store,
        patch.object(
            _APP_MODULE,
            "build_iam_store",
            return_value=InMemoryIamStore(),
        ),
        patch.object(
            _APP_MODULE,
            "build_project_store",
            return_value=MagicMock(),
        ),
    ):
        with TestClient(app):
            yield mock_db_loader, mock_postgres_store


def test_roles_from_db_env_force_on_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §5 / §14 #16 ``NIMBUSWARE_ROLES_FROM_DB`` force-on truthy tuple membership.

    With ``NIMBUSWARE_DATABASE_URL=_FAKE_DB_URL`` (AND-gate's first operand
    truthy), every truthy variant of ``NIMBUSWARE_ROLES_FROM_DB`` must reach
    ``load_registry_from_postgres`` once AND ``PostgresEventStore`` once
    (the latter is orthogonally controlled by ``url`` alone but serves
    as a sanity check that the lifespan reached the second branch).

    If the env-gate had rejected the variant, ``mock_db_loader.call_count``
    would be 0 (registry fell through to YAML) and the assertion fails
    loudly with a per-case message identifying the offending env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("upper_true", "TRUE"),
        ("title_true", "True"),
        ("upper_yes", "YES"),
        ("title_yes", "Yes"),
        ("mixed_true", "trUE"),
        ("mixed_yes", "yEs"),
    ]
    for _name, raw in cases:
        with _run_lifespan(
            monkeypatch,
            db_url=_FAKE_DB_URL,
            roles_from_db=raw,
        ) as (mock_db_loader, mock_postgres_store):
            pass
        assert mock_db_loader.call_count == 1, (
            f"force_on raw={raw!r}: DB loader call count "
            f"(expected 1, got {mock_db_loader.call_count})"
        )
        assert mock_postgres_store.call_count == 1, (
            f"force_on raw={raw!r}: PostgresEventStore call count "
            f"(expected 1, got {mock_postgres_store.call_count})"
        )


def test_roles_from_db_env_compound_and_gate_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §5 / §14 #16 compound AND-gate 2x2 matrix across orthogonal gates.

    Distinct from fo69 Part B (three branches inside a single env-gate
    accept arm with asymmetric call-count signatures): fo70 Part B has
    **four arms** across **two orthogonal gates** -- the registry path
    uses a compound ``url AND flag``, the store path uses bare ``url``,
    and only the both-truthy quadrant reaches the DB loader.

    Catches refactors that:

    1. Swap the AND operand order (``flag AND url``) -- Block 1 would
       evaluate the flag before short-circuiting and break.
    2. Loosen the compound to ``url OR flag`` -- Block 4 would flip
       from YAML to DB.
    3. Couple the store gate to the registry flag -- Block 4 would
       lose the Postgres store.
    4. Change the production default away from YAML + InMemory --
       Blocks 1 and 3 would fail simultaneously.
    """
    with _run_lifespan(
        monkeypatch,
        db_url=None,
        roles_from_db="1",
    ) as (mdl, mps):
        pass
    assert mdl.call_count == 0, (
        "url_absent_flag_on: DB loader unexpectedly called "
        f"(count={mdl.call_count}); url should short-circuit"
    )
    assert mps.call_count == 0, (
        f"url_absent_flag_on: PostgresEventStore unexpectedly called (count={mps.call_count})"
    )

    with _run_lifespan(
        monkeypatch,
        db_url=_FAKE_DB_URL,
        roles_from_db="1",
    ) as (mdl, mps):
        pass
    assert mdl.call_count == 1, (
        f"url_present_flag_on: DB loader not called once (count={mdl.call_count})"
    )
    assert mps.call_count == 1, (
        f"url_present_flag_on: PostgresEventStore not called once (count={mps.call_count})"
    )

    with _run_lifespan(
        monkeypatch,
        db_url=None,
        roles_from_db=None,
    ) as (mdl, mps):
        pass
    assert mdl.call_count == 0, (
        f"url_absent_flag_off: DB loader unexpectedly called (count={mdl.call_count})"
    )
    assert mps.call_count == 0, (
        f"url_absent_flag_off: PostgresEventStore unexpectedly called (count={mps.call_count})"
    )

    with _run_lifespan(
        monkeypatch,
        db_url=_FAKE_DB_URL,
        roles_from_db=None,
    ) as (mdl, mps):
        pass
    assert mdl.call_count == 0, (
        "url_present_flag_off: DB loader unexpectedly called "
        f"(count={mdl.call_count}); flag should reject"
    )
    assert mps.call_count == 1, (
        "url_present_flag_off: PostgresEventStore not called once "
        f"(count={mps.call_count}); store gate is orthogonal to flag"
    )


def test_roles_from_db_env_fail_closed_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §5 / §14 #16 asymmetric fail-closed string-arm with url orthogonally truthy.

    Loops 12 fail-closed variants spanning four sub-contracts (parallel
    to fo65 / 66 / 67 / 68 / 69 Part C). The double assertion (DB
    loader NOT called AND Postgres store IS called) is stronger than a
    single-sided check -- a refactor that silently accepts the flag
    would flip ``mock_db_loader.call_count`` to 1, and a refactor that
    coupled the store gate to the flag would flip
    ``mock_postgres_store.call_count`` to 0.

    1. **Env-absent** -- the production default (with url set) is
       YAML registry + Postgres store.
    2. **No ``.strip()``** -- whitespace-padded canonical fail-closed
       because ``.lower()`` alone does not trim whitespace. A future
       refactor adding ``.strip()`` silently flips ``" 1 "`` from
       "YAML registry" to "DB registry" -- this test fails loudly.
    3. **``"on"`` / ``"off"`` asymmetry** vs YAML coercer -- the env
       layer excludes ``"on"`` from the truthy tuple even though the
       workflow YAML coercer accepts it.
    4. **Single-tuple membership** -- case-folded falsy and unknown
       tokens both fail-closed via the same ``in`` predicate.
    """
    cases: list[tuple[str, str | None]] = [
        ("env_absent", None),
        ("ws_one_pad", "  1  "),
        ("ws_true_pad", " true "),
        ("ws_tab_yes_lf", "\tyes\n"),
        ("yaml_on_lower", "on"),
        ("yaml_on_upper", "ON"),
        ("upper_false", "FALSE"),
        ("upper_no", "NO"),
        ("empty", ""),
        ("junk_maybe", "maybe"),
        ("near_miss_true_bang", "true!"),
        ("interior_ws", " ye s "),
    ]
    for _name, raw in cases:
        with _run_lifespan(
            monkeypatch,
            db_url=_FAKE_DB_URL,
            roles_from_db=raw,
        ) as (mock_db_loader, mock_postgres_store):
            pass
        assert mock_db_loader.call_count == 0, (
            f"fail_closed raw={raw!r}: DB loader unexpectedly called "
            f"(count={mock_db_loader.call_count})"
        )
        assert mock_postgres_store.call_count == 1, (
            f"fail_closed raw={raw!r}: PostgresEventStore not called once "
            f"(count={mock_postgres_store.call_count}); "
            "store gate is orthogonal to flag and url is truthy here"
        )
