from __future__ import annotations

import pytest

from nimbusware_console.components.ui_errors import render_api_error


def test_render_api_error_raises_for_web_console() -> None:
    with pytest.raises(RuntimeError, match="Streamlit UI removed"):
        render_api_error(ValueError("boom"))
