"""Base-class integration checks for the Milestone 0001 providers (subtask 05.0/04).

Confirms that ``github``, ``ieee-spectrum``, ``jetbrains`` and ``stackoverflow-tags``
inherit :class:`~langrank.providers.base.BaseRatingProvider`, still satisfy the
:class:`~langrank.providers.base.RatingProvider` protocol, expose a sensible
no-network :meth:`upstream_latest_period` (which previously crashed ``langrank
status`` for these four), and keep the shared request-window filtering behaviour that
now lives on the base class. Every check is offline: providers read only their
repo-bundled snapshots or an empty cache directory - no network, no database.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from langrank.models import FetchRequest, Granularity, SourceRecord
from langrank.providers.base import BaseRatingProvider, RatingProvider
from langrank.providers.github import GitHubProvider
from langrank.providers.ieee_spectrum import IeeeSpectrumProvider
from langrank.providers.jetbrains import JetBrainsProvider
from langrank.providers.stackoverflow_tags import StackOverflowTagsProvider

#: The four Milestone 0001 providers refactored onto :class:`BaseRatingProvider`.
_PROVIDER_CLASSES = (
    GitHubProvider,
    IeeeSpectrumProvider,
    JetBrainsProvider,
    StackOverflowTagsProvider,
)

#: Expected ``upstream_latest_period`` for each provider against an *empty* cache:
#: the annual providers report their bundled snapshot's latest edition year, GitHub
#: reports its bundled Octoverse edition on the quarterly ``YYYY-MM`` format, and
#: Stack Overflow Tags (cache-only, no bundled snapshot) reports ``None``.
_EXPECTED_EMPTY_CACHE_UPSTREAM = {
    "github": "2025-01",
    "ieee-spectrum": "2025",
    "jetbrains": "2025",
    "stackoverflow-tags": None,
}


@pytest.mark.parametrize("provider_cls", _PROVIDER_CLASSES)
def test_provider_is_base_and_rating_provider(provider_cls: type, tmp_path: Path) -> None:
    """Each refactored provider is a ``BaseRatingProvider`` and a ``RatingProvider``."""
    provider = provider_cls(tmp_path)

    assert isinstance(provider, BaseRatingProvider)
    assert isinstance(provider, RatingProvider)


@pytest.mark.parametrize("provider_cls", _PROVIDER_CLASSES)
def test_upstream_latest_period_empty_cache(provider_cls: type, tmp_path: Path) -> None:
    """With an empty cache each provider yields its bundled-or-None upstream period."""
    provider = provider_cls(tmp_path)

    expected = _EXPECTED_EMPTY_CACHE_UPSTREAM[provider.provider_id]
    assert provider.upstream_latest_period() == expected


def _record(period_start: date) -> SourceRecord:
    """Build a minimal quarterly source record anchored at ``period_start``."""
    return SourceRecord(
        rating_id="github",
        metric_id="github-innovation-graph-pushers",
        language="Python",
        period_start=period_start,
        period_end=period_start,
        period_label=period_start.isoformat(),
        granularity=Granularity.QUARTER,
        rank=None,
        value=1.0,
        unit="count",
        source_url="https://example.test",
    )


def test_base_filter_window_preserved_via_stashed_bounds(tmp_path: Path) -> None:
    """The inherited ``_filter_window`` still trims to the window stashed by ``fetch``."""
    provider = GitHubProvider(tmp_path)
    provider._stash_request_window(FetchRequest(since=date(2021, 1, 1), until=date(2021, 12, 31)))

    records = [_record(date(2020, 1, 1)), _record(date(2021, 4, 1)), _record(date(2022, 1, 1))]
    kept = provider._filter_window(records)

    assert [record.period_start for record in kept] == [date(2021, 4, 1)]


def test_base_filter_window_default_span_from_latest(tmp_path: Path) -> None:
    """With no stashed bounds the window ends at the latest period over ``default_years``."""
    provider = IeeeSpectrumProvider(tmp_path)

    records = [_record(date(2010, 1, 1)), _record(date(2020, 1, 1)), _record(date(2025, 1, 1))]
    kept = provider._filter_window(records, default_years=10)

    # Latest is 2025 -> since 2015-01-01, so the 2010 record drops.
    assert [record.period_start for record in kept] == [date(2020, 1, 1), date(2025, 1, 1)]
