from __future__ import annotations

from datetime import date
from pathlib import Path

from langrank.models import Granularity
from langrank.providers.ieee_spectrum import (
    IEEE_EDITIONS,
    IeeeProfile,
    IeeeSpectrumProvider,
    rank_metric_id,
    score_metric_id,
)
from langrank.providers.registry import ProviderRegistry


def test_ieee_metadata_metric_pair_per_profile(tmp_path: Path) -> None:
    metadata = IeeeSpectrumProvider(tmp_path).metadata()
    metrics = {metric.id: metric for metric in metadata.metrics}

    # Two metrics per profile, never a single merged series.
    assert len(metadata.metrics) == 2 * len(IeeeProfile)
    expected_ids = {rank_metric_id(profile) for profile in IeeeProfile} | {
        score_metric_id(profile) for profile in IeeeProfile
    }
    assert set(metrics) == expected_ids

    for profile in IeeeProfile:
        rank = metrics[rank_metric_id(profile)]
        score = metrics[score_metric_id(profile)]
        assert rank.unit == "rank"
        assert rank.higher_is_better is False
        assert score.unit == "score"
        assert score.higher_is_better is True

    assert metadata.default_metric == "ieee-spectrum-spectrum-rank"
    assert metadata.native_granularity is Granularity.YEAR

    # Metric IDs are profile-scoped so a query can never mix profiles.
    for profile in IeeeProfile:
        assert rank_metric_id(profile) == f"ieee-spectrum-{profile.value}-rank"
        assert score_metric_id(profile) == f"ieee-spectrum-{profile.value}-score"


def test_ieee_metadata_caveats_keep_profiles_and_editions_distinct(tmp_path: Path) -> None:
    caveats = " ".join(IeeeSpectrumProvider(tmp_path).metadata().caveats).lower()

    # Profiles are distinct rankings, and scores are not comparable across editions.
    assert "different rankings" in caveats or "never one series" in caveats
    assert "not comparable across editions" in caveats
    assert "manual transcription" in caveats
    assert "weights differ per profile and per edition" in caveats


def test_ieee_methodology_note_per_edition(tmp_path: Path) -> None:
    notes = IeeeSpectrumProvider(tmp_path).metadata().methodology_notes

    # One note per edition row of the source-note table.
    assert len(notes) == len(IEEE_EDITIONS)

    by_version = {note.methodology_version: note for note in notes}
    for edition in IEEE_EDITIONS:
        note = by_version[edition.methodology_version]
        assert note.valid_from == date(edition.year, 1, 1)
        assert note.valid_to == date(edition.year, 12, 31)
        assert note.source_url == edition.source_url

    # Editions cover 2021-2025, each a single calendar year.
    years = sorted(note.valid_from.year for note in notes if note.valid_from is not None)
    assert years == [2021, 2022, 2023, 2024, 2025]


def test_registry_contains_ieee_spectrum(tmp_path: Path) -> None:
    registry = ProviderRegistry(tmp_path)
    provider = registry.get("ieee-spectrum")

    assert provider.provider_id == "ieee-spectrum"
    assert isinstance(provider, IeeeSpectrumProvider)
