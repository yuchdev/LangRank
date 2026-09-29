"""Unit tests for the bootstrap providers refactored onto :class:`BaseRatingProvider`.

Subtask 05.0/03 moved ``demo``, ``pypl``, ``redmonk``, ``tiobe`` and
``stackoverflow-survey`` onto the shared base class, replaced their hardcoded
``upstream_latest_period`` overrides with a bundled-snapshot hook, and swapped their
duplicated validate loops for the shared helpers. These tests pin the two behaviours
that the refactor must preserve: the base-derived upstream period (from the bundled
snapshot, with no cache present) matches each provider's old constant, and every
provider is still both a :class:`BaseRatingProvider` and a :class:`RatingProvider`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from langrank.providers.base import BaseRatingProvider, RatingProvider
from langrank.providers.demo import DemoProvider
from langrank.providers.pypl import PyplProvider
from langrank.providers.redmonk import RedMonkProvider
from langrank.providers.stackoverflow_survey import StackOverflowSurveyProvider
from langrank.providers.tiobe import TiobeProvider

_PROVIDER_CLASSES = (
    DemoProvider,
    PyplProvider,
    RedMonkProvider,
    StackOverflowSurveyProvider,
    TiobeProvider,
)


@pytest.mark.parametrize(
    ("provider_cls", "expected_period"),
    [
        (TiobeProvider, "2025-12"),
        (PyplProvider, "2025-12"),
        (RedMonkProvider, "2025-06"),
        (StackOverflowSurveyProvider, "2025"),
        (DemoProvider, "2026"),
    ],
)
def test_upstream_latest_period_matches_old_constant(
    tmp_path: Path, provider_cls: type[BaseRatingProvider], expected_period: str
) -> None:
    """With no cache, the base-derived period equals each provider's old constant.

    The cache directory is empty, so :meth:`BaseRatingProvider.upstream_latest_period`
    falls back to the bundled snapshot and derives the latest ``period_start`` from it.
    """
    provider = provider_cls(tmp_path)

    assert provider.upstream_latest_period() == expected_period


@pytest.mark.parametrize("provider_cls", _PROVIDER_CLASSES)
def test_provider_is_base_and_rating_provider(tmp_path: Path, provider_cls: type[BaseRatingProvider]) -> None:
    """Each bootstrap provider is both a ``BaseRatingProvider`` and a ``RatingProvider``."""
    provider = provider_cls(tmp_path)

    assert isinstance(provider, BaseRatingProvider)
    assert isinstance(provider, RatingProvider)
