from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from langrank.models import FetchRequest
from langrank.providers.stackoverflow_tags import StackOverflowTagsProvider

pytestmark = [pytest.mark.integration, pytest.mark.live]


def test_stackoverflow_tags_live_smoke(tmp_path: Path) -> None:
    """Fetch one complete month against the real API and assert a plausible payload.

    Opt-in only (``live`` marker); the ``tests/conftest.py`` collection hook skips
    it unless ``LANGRANK_LIVE_TESTS=1`` is set, so plain ``uv run pytest`` (CI)
    never reaches the network.
    """
    provider = StackOverflowTagsProvider(tmp_path)
    payload = provider.fetch(FetchRequest(since=date(2024, 1, 1), until=date(2024, 1, 31)))

    document = json.loads(payload.content)
    assert document["source"] == "api"
    assert document["denominator"] == "all_questions"
    assert len(document["months"]) == 1
    month = document["months"][0]
    assert month["month"] == "2024-01"
    assert month["total"] >= 0
    assert month["tags"]["python"] >= 0
