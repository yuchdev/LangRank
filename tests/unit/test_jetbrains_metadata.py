from __future__ import annotations

from pathlib import Path

from langrank.models import Granularity
from langrank.providers.jetbrains import (
    PUBLISHED_METRICS,
    RAW_DERIVATION_METHOD,
    RAW_METRICS,
    JetBrainsProvider,
    JetBrainsSource,
    _resolve_source,
    raw_metric_id,
)
from langrank.providers.jetbrains_questions import (
    METRIC_USED_LAST_12_MONTHS,
    wording_changes,
)
from langrank.providers.registry import ProviderRegistry


def _metadata(tmp_path: Path):
    return JetBrainsProvider(tmp_path).metadata()


def test_jetbrains_metadata_metric_families(tmp_path: Path) -> None:
    """The provider exposes six metrics in two disjoint, correctly-flagged families."""
    metadata = _metadata(tmp_path)
    metric_ids = [metric.id for metric in metadata.metrics]

    # Six metrics: three published plus three -raw, all distinct.
    assert len(metric_ids) == 6
    assert len(set(metric_ids)) == 6

    published = set(PUBLISHED_METRICS)
    raw = set(RAW_METRICS)
    assert set(metric_ids) == published | raw

    # The two families are disjoint and the raw family is the published family
    # with a -raw suffix, so a query can never conflate weighted and unweighted.
    assert published.isdisjoint(raw)
    assert raw == {raw_metric_id(metric_id) for metric_id in PUBLISHED_METRICS}
    assert all(metric_id.endswith("-raw") for metric_id in raw)

    # Every metric is a percentage.
    assert {metric.unit for metric in metadata.metrics} == {"percent"}

    # Defaults and granularity per spec.
    assert metadata.default_metric == METRIC_USED_LAST_12_MONTHS
    assert metadata.native_granularity is Granularity.YEAR


def test_jetbrains_caveats_cover_weighting_and_licence(tmp_path: Path) -> None:
    """Caveats spell out the weighted/unweighted split, distinct questions and licence."""
    caveats = " ".join(_metadata(tmp_path).caveats).lower()
    assert "weighted" in caveats and "unweighted" in caveats
    assert "different questions" in caveats
    assert "wording" in caveats
    assert "cc by-nc-sa" in caveats and "attribution" in caveats
    assert "never redistributed" in caveats


def test_jetbrains_methodology_notes_from_wording(tmp_path: Path) -> None:
    """Every methodology note traces to a verified wording change, one per change."""
    notes = _metadata(tmp_path).methodology_notes

    expected: list[tuple[str, int, str]] = [
        (metric_id, year, wording) for metric_id in PUBLISHED_METRICS for year, wording in wording_changes(metric_id)
    ]
    assert len(notes) == len(expected)

    # Six confirmed verbatim wordings are on record today (four used-in-12-months
    # editions plus one primary and one planned-adoption), so six notes exist and
    # each traces to a real, verified change - nothing is fabricated.
    assert len(notes) == 6
    for (metric_id, year, wording), note in zip(expected, notes, strict=True):
        assert note.rating_id == "jetbrains"
        assert note.valid_from is not None and note.valid_from.year == year
        assert wording in note.description
        assert str(year) in note.methodology_version
        assert metric_id in note.methodology_version


def test_jetbrains_raw_metrics_are_derived_marker() -> None:
    """The raw derivation method matches the unweighted-share contract."""
    assert RAW_DERIVATION_METHOD == "unweighted_respondent_share"


def test_resolve_source_auto_selects_published() -> None:
    """``auto`` / unset select the published mode; ``raw-data`` selects itself."""
    assert _resolve_source(None) is JetBrainsSource.PUBLISHED
    assert _resolve_source("auto") is JetBrainsSource.PUBLISHED
    assert _resolve_source("raw-data") is JetBrainsSource.RAW_DATA


def test_resolve_source_rejects_unknown() -> None:
    """An unknown ``--source`` is rejected rather than guessed."""
    import pytest

    from langrank.errors import ProviderError

    with pytest.raises(ProviderError):
        _resolve_source("weighted-guess")


def test_registry_contains_jetbrains(tmp_path: Path) -> None:
    """The provider is registered under ``jetbrains``."""
    provider = ProviderRegistry(tmp_path).get("jetbrains")
    assert provider.provider_id == "jetbrains"
    assert provider.metadata().display_name == "JetBrains Developer Ecosystem"
