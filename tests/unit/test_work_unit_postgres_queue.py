import pytest

from nimbusware_compute.work_unit import get_work_unit_queue, set_work_unit_queue


def test_get_work_unit_queue_postgres_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    set_work_unit_queue(None)
    monkeypatch.setenv("NIMBUSWARE_COMPUTE_WORK_QUEUE", "postgres")
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="NIMBUSWARE_DATABASE_URL"):
        get_work_unit_queue()
