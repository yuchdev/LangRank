"""Unit tests for the pure provider helpers in :mod:`langrank.providers.common`.

Covers the window filter, competition ranking, and the three validation helpers
extracted from the per-provider ``validate`` methods (subtask 05.0/01). The helpers
are pure, so every test builds its own in-memory fixtures - no cache, network, or
database is touched.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Optional

from langrank.models import Granularity, Observation, Severity, SourceRecord, ValidationReport
from langrank.providers.common import (
    compute_competition_ranks,
    filter_records_by_window,
    validate_bounded_values,
    validate_positive_ranks,
    validate_unique_observations,
)

_RETRIEVED_AT = datetime(2025, 9, 23, tzinfo=UTC)


def _record(*, year: int, language: str = "python", value: float = 1.0) -> SourceRecord:
    """Build a minimal annual :class:`SourceRecord` anchored on ``year``."""
    return SourceRecord(
        rating_id="demo",
        metric_id="demo-rank",
        language=language,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=None,
        value=value,
        unit="rank",
        source_url="demo://synthetic",
    )


def _observation(
    *,
    language_id: str = "python",
    metric_id: str = "demo-rank",
    year: int = 2025,
    rank: Optional[int] = 1,
    value: Optional[float] = 1.0,
) -> Observation:
    """Build a minimal annual :class:`Observation` for the validation helpers."""
    return Observation(
        rating_id="demo",
        metric_id=metric_id,
        language_id=language_id,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=rank,
        value=value,
        unit="rank",
        source_language_name=language_id,
        source_url="demo://synthetic",
        source_document_id=None,
        is_derived=False,
        derivation_method=None,
        retrieved_at=_RETRIEVED_AT,
        source_published_at=None,
        parser_version="demo-v1",
        raw_record_hash="deadbeef",
    )


# --------------------------------------------------------------------------------------
# filter_records_by_window
# --------------------------------------------------------------------------------------


def test_filter_window_defaults_to_latest_period_and_default_span() -> None:
    """With no bounds the window ends at the latest period and spans ``default_years``."""
    records = [_record(year=year) for year in (2010, 2014, 2020, 2024)]

    kept = filter_records_by_window(records, default_years=10)

    # Latest period is 2024 -> since = 2014-01-01, so 2010 drops and 2014..2024 stay.
    assert [record.period_label for record in kept] == ["2014", "2020", "2024"]


def test_filter_window_explicit_since_and_until_are_inclusive() -> None:
    """Explicit ``since``/``until`` bounds are both inclusive of matching periods."""
    records = [_record(year=year) for year in (2016, 2018, 2020, 2022)]

    kept = filter_records_by_window(records, since=date(2018, 1, 1), until=date(2020, 12, 31))

    assert [record.period_label for record in kept] == ["2018", "2020"]


def test_filter_window_years_zero_falls_back_to_default() -> None:
    """A zero ``years`` (falsy) falls back to ``default_years`` like the providers do."""
    records = [_record(year=year) for year in (2012, 2020, 2024)]

    kept = filter_records_by_window(records, years=0, default_years=10)

    assert [record.period_label for record in kept] == ["2020", "2024"]


def test_filter_window_empty_input_returns_empty_list() -> None:
    """An empty input never calls ``max`` and yields an empty list."""
    assert filter_records_by_window([]) == []


# --------------------------------------------------------------------------------------
# compute_competition_ranks
# --------------------------------------------------------------------------------------


def test_competition_ranks_orders_desc_with_tie_skip() -> None:
    """Highest value is rank 1; ties share a rank and the next value skips positions."""
    ranks = compute_competition_ranks([("python", 30.0), ("java", 20.0), ("go", 20.0), ("rust", 5.0)])

    assert ranks == {"python": 1, "java": 2, "go": 2, "rust": 4}


def test_competition_ranks_breaks_value_ties_by_ascending_id() -> None:
    """Equal values are ordered by id for determinism but share the same rank."""
    ranks = compute_competition_ranks([("zeta", 10.0), ("alpha", 10.0)])

    assert ranks == {"alpha": 1, "zeta": 1}


def test_competition_ranks_empty_input_returns_empty_dict() -> None:
    """Empty input yields an empty mapping."""
    assert compute_competition_ranks([]) == {}


# --------------------------------------------------------------------------------------
# validate_positive_ranks
# --------------------------------------------------------------------------------------


def test_positive_ranks_flags_non_positive_rank_with_default_message() -> None:
    """A rank at or below zero is an ERROR with the shared default message."""
    report = ValidationReport()

    validate_positive_ranks([_observation(rank=0)], report)

    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.severity is Severity.ERROR
    assert issue.code == "rank_positive"
    assert issue.message == "python rank must be positive"


def test_positive_ranks_ignores_none_rank_and_respects_metric_gate() -> None:
    """A ``None`` rank is never flagged and the ``metric_id`` gate skips other metrics."""
    report = ValidationReport()

    validate_positive_ranks(
        [
            _observation(rank=None),
            _observation(metric_id="demo-rating", rank=-1),
        ],
        report,
        metric_id="demo-rank",
    )

    assert report.issues == []


def test_positive_ranks_custom_message_and_code() -> None:
    """A custom message callable and code reproduce a provider's own phrasing."""
    report = ValidationReport()

    validate_positive_ranks(
        [_observation(rank=-2)],
        report,
        code="rank_check",
        message=lambda obs: f"{obs.language_id}: rank {obs.rank} must be positive",
    )

    assert report.issues[0].code == "rank_check"
    assert report.issues[0].message == "python: rank -2 must be positive"


# --------------------------------------------------------------------------------------
# validate_bounded_values
# --------------------------------------------------------------------------------------


def test_bounded_values_flags_out_of_range_value() -> None:
    """A value above the inclusive max is an ERROR with the given code."""
    report = ValidationReport()

    validate_bounded_values([_observation(value=150.0)], report, code="share_range")

    assert len(report.issues) == 1
    assert report.issues[0].code == "share_range"
    assert report.issues[0].severity is Severity.ERROR


def test_bounded_values_accepts_boundaries_and_none() -> None:
    """The bounds are inclusive and a ``None`` value is never flagged."""
    report = ValidationReport()

    validate_bounded_values(
        [
            _observation(value=0.0),
            _observation(value=100.0),
            _observation(value=None),
        ],
        report,
        code="share_range",
    )

    assert report.issues == []


def test_bounded_values_custom_bounds_and_metric_gate() -> None:
    """Custom bounds apply only to the gated metric; other metrics are untouched."""
    report = ValidationReport()

    validate_bounded_values(
        [
            _observation(metric_id="demo-score", value=1.5),
            _observation(metric_id="demo-other", value=1.5),
        ],
        report,
        code="score_range",
        metric_id="demo-score",
        max_value=1.0,
    )

    assert len(report.issues) == 1
    assert report.issues[0].code == "score_range"


# --------------------------------------------------------------------------------------
# validate_unique_observations
# --------------------------------------------------------------------------------------


def test_unique_observations_flags_repeated_natural_key() -> None:
    """A repeated ``(language_id, period_start, metric_id)`` triple is an ERROR."""
    report = ValidationReport()

    validate_unique_observations([_observation(), _observation()], report)

    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.severity is Severity.ERROR
    assert issue.code == "duplicate_language_period"
    assert issue.message == "duplicate language/period metric for python 2025"


def test_unique_observations_distinct_keys_are_not_flagged() -> None:
    """Observations differing in any key component are all unique."""
    report = ValidationReport()

    validate_unique_observations(
        [
            _observation(language_id="python"),
            _observation(language_id="java"),
            _observation(metric_id="demo-rating"),
            _observation(year=2024),
        ],
        report,
    )

    assert report.issues == []


def test_unique_observations_custom_code_and_message() -> None:
    """A custom code and message reproduce a provider's own phrasing verbatim."""
    report = ValidationReport()

    validate_unique_observations(
        [_observation(), _observation()],
        report,
        code="duplicate_language_year_metric",
        message=lambda obs: f"duplicate language/year/metric for {obs.language_id} {obs.period_label}",
    )

    assert report.issues[0].code == "duplicate_language_year_metric"
    assert report.issues[0].message == "duplicate language/year/metric for python 2025"
