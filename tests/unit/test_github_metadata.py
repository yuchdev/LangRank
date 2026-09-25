from __future__ import annotations

from pathlib import Path

import pytest

from langrank.errors import ProviderError
from langrank.models import Granularity
from langrank.providers.github import (
    METRIC_IG_PUSHERS,
    METRIC_IG_RANK,
    METRIC_IG_SHARE,
    METRIC_OCTOVERSE_RANK,
    GitHubProvider,
    GitHubSource,
    _resolve_source,
)
from langrank.providers.registry import ProviderRegistry


def test_github_metadata_metrics(tmp_path: Path) -> None:
    metadata = GitHubProvider(tmp_path).metadata()

    metrics = {metric.id: metric for metric in metadata.metrics}
    assert set(metrics) == {
        METRIC_OCTOVERSE_RANK,
        METRIC_IG_PUSHERS,
        METRIC_IG_SHARE,
        METRIC_IG_RANK,
    }

    assert metrics[METRIC_OCTOVERSE_RANK].unit == "rank"
    assert metrics[METRIC_OCTOVERSE_RANK].higher_is_better is False

    assert metrics[METRIC_IG_PUSHERS].unit == "count"
    assert metrics[METRIC_IG_PUSHERS].higher_is_better is True

    assert metrics[METRIC_IG_SHARE].unit == "percent"
    assert metrics[METRIC_IG_SHARE].higher_is_better is True

    assert metrics[METRIC_IG_RANK].unit == "rank"
    assert metrics[METRIC_IG_RANK].higher_is_better is False

    assert metadata.default_metric == METRIC_IG_SHARE
    assert metadata.native_granularity is Granularity.QUARTER

    # Every metric ID is variant-scoped so a query can never mix the two variants.
    assert METRIC_OCTOVERSE_RANK.startswith("github-octoverse-")
    for metric_id in (METRIC_IG_PUSHERS, METRIC_IG_SHARE, METRIC_IG_RANK):
        assert metric_id.startswith("github-innovation-graph-")


def test_github_metadata_caveats_keep_variants_distinct(tmp_path: Path) -> None:
    caveats = " ".join(GitHubProvider(tmp_path).metadata().caveats).lower()

    # The two variants and RedMonk's GitHub component must all be kept separate.
    assert "redmonk" in caveats
    assert "octoverse" in caveats and "innovation-graph" in caveats
    assert "undercount" in caveats
    assert "chart" in caveats


def test_github_resolve_source() -> None:
    assert _resolve_source(None) is GitHubSource.INNOVATION_GRAPH
    assert _resolve_source("auto") is GitHubSource.INNOVATION_GRAPH
    assert _resolve_source("octoverse") is GitHubSource.OCTOVERSE
    assert _resolve_source("innovation-graph") is GitHubSource.INNOVATION_GRAPH

    with pytest.raises(ProviderError):
        _resolve_source("redmonk")


def test_registry_contains_github(tmp_path: Path) -> None:
    registry = ProviderRegistry(tmp_path)
    provider = registry.get("github")

    assert provider.provider_id == "github"
    assert isinstance(provider, GitHubProvider)
