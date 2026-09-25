from __future__ import annotations

from pathlib import Path

import pytest

from langrank.models import FetchRequest
from langrank.providers.github import METRIC_IG_PUSHERS, GitHubProvider, _validate_commit_sha

pytestmark = [pytest.mark.integration, pytest.mark.live]


def test_github_innovation_graph_live_smoke(tmp_path: Path) -> None:
    """Fetch the real Innovation Graph CSV at a pinned SHA and parse a plausible shape.

    Opt-in only (``live`` marker); the ``tests/conftest.py`` collection hook skips
    it unless ``LANGRANK_LIVE_TESTS=1`` is set, so plain ``uv run pytest`` (CI)
    never reaches the network.
    """
    provider = GitHubProvider(tmp_path)
    payload = provider.fetch(FetchRequest(source="innovation-graph", since=None, until=None, years=2))

    assert payload.artifact is not None
    commit_sha = payload.artifact.metadata_json["commit_sha"]
    assert _validate_commit_sha(commit_sha) == commit_sha
    assert commit_sha in payload.artifact.url

    records = provider.parse(payload)
    assert records
    assert all(record.metric_id == METRIC_IG_PUSHERS for record in records)
    assert all(record.value is not None and record.value >= 0 for record in records)
    assert all(record.metadata["commit_sha"] == commit_sha for record in records)
