"""Maker onboarding flag."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_maker.onboarding import is_onboarded, mark_onboarded, onboarding_flag_path


class _FakeSession:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value


def test_mark_onboarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_MAKER_STATE_DIR", str(tmp_path))
    session = _FakeSession()
    assert not is_onboarded(session)
    mark_onboarded(session)
    assert is_onboarded(session)
    assert onboarding_flag_path().is_file()
