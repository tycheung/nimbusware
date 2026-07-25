from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _mock_post_sequence(mock_client: MagicMock, responses: list[dict]) -> list[MagicMock]:
    posts: list[MagicMock] = []
    for body in responses:
        mock_response = MagicMock()
        mock_response.json.return_value = body
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}
        posts.append(mock_response)
    mock_client.post.side_effect = posts
    return posts


@pytest.fixture
def mock_post_sequence():
    return _mock_post_sequence
