from __future__ import annotations

from pathlib import Path

from langrank.models import Granularity
from langrank.normalization import LanguageNormalizer
from langrank.providers.registry import ProviderRegistry
from langrank.providers.stackoverflow_tags import (
    METRIC_QUESTIONS,
    METRIC_RANK,
    METRIC_SHARE,
    TAG_TO_LANGUAGE,
    StackOverflowTagsProvider,
)


def test_stackoverflow_tags_metadata_metrics(tmp_path: Path) -> None:
    metadata = StackOverflowTagsProvider(tmp_path).metadata()

    metrics = {metric.id: metric for metric in metadata.metrics}
    assert set(metrics) == {METRIC_QUESTIONS, METRIC_SHARE, METRIC_RANK}

    assert metrics[METRIC_QUESTIONS].unit == "count"
    assert metrics[METRIC_QUESTIONS].higher_is_better is True

    assert metrics[METRIC_SHARE].unit == "percent"
    assert metrics[METRIC_SHARE].higher_is_better is True

    assert metrics[METRIC_RANK].unit == "rank"
    assert metrics[METRIC_RANK].higher_is_better is False

    assert metadata.default_metric == METRIC_SHARE
    assert metadata.native_granularity is Granularity.MONTH
    assert "denominator" in metrics[METRIC_SHARE].description.lower()


def test_stackoverflow_tags_tag_map_resolves() -> None:
    normalizer = LanguageNormalizer()
    known = {language.id for language in normalizer.languages()}

    assert len(TAG_TO_LANGUAGE) >= 30

    for tag, canonical in TAG_TO_LANGUAGE.items():
        resolved = normalizer.resolve(tag, rating_id="stackoverflow-tags")
        assert resolved == canonical
        assert resolved in known


def test_registry_contains_stackoverflow_tags(tmp_path: Path) -> None:
    registry = ProviderRegistry(tmp_path)
    provider = registry.get("stackoverflow-tags")

    assert provider.provider_id == "stackoverflow-tags"
    assert isinstance(provider, StackOverflowTagsProvider)
