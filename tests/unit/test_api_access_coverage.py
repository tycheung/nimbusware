from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException

from nimbusware_api import access


def test_run_created_metadata_extracts_first_created() -> None:
    meta = access._run_created_metadata(
        [
            {"event_type": "run.plan", "metadata": {}},
            {"event_type": "run.created", "metadata": {"project_id": "p1"}},
        ],
    )
    assert meta["project_id"] == "p1"


def test_assert_project_accessible_raises_on_tenant_mismatch() -> None:
    tid = UUID("00000000-0000-0000-0000-000000000001")

    class _Rec:
        tenant_id = UUID("00000000-0000-0000-0000-000000000002")

    with pytest.raises(HTTPException) as exc:
        access.assert_project_accessible(_Rec(), tenant_id=tid)
    assert exc.value.status_code == 404


def test_assert_run_accessible_non_enterprise_noop(monkeypatch) -> None:
    monkeypatch.setattr(access, "is_enterprise", lambda: False)
    access.assert_run_accessible([])


def test_assert_run_accessible_enterprise_tenant_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(access, "is_enterprise", lambda: True)
    tid = UUID("00000000-0000-0000-0000-000000000001")
    other = UUID("00000000-0000-0000-0000-000000000002")
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "project": {
                    "id": "p1",
                    "tenant_id": str(other),
                },
            },
        },
    ]
    with pytest.raises(HTTPException) as exc:
        access.assert_run_accessible(rows, tenant_id=tid)
    assert exc.value.status_code == 404
