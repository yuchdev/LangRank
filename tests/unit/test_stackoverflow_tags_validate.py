from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Optional

import pytest

from langrank.models import Granularity, Observation, Severity
from langrank.providers.stackoverflow_tags import (
    METRIC_QUESTIONS,
    METRIC_RANK,
    METRIC_SHARE,
    StackOverflowTagsProvider,
)

#: A safely-past, complete month used by every clean fixture below.
_PAST_START = date(2020, 1, 1)
_PAST_END = date(2020, 1, 31)
_PAST_LABEL = "2020-01"


def _provider(tmp_path: Path) -> StackOverflowTagsProvider:
    return StackOverflowTagsProvider(tmp_path)


def _obs(
    *,
    metric_id: str,
    language_id: str = "python",
    value: Optional[float],
    rank: Optional[int] = None,
    is_derived: bool = False,
    denominator: str = "all_questions",
    period_start: date = _PAST_START,
    period_end: date = _PAST_END,
    period_label: str = _PAST_LABEL,
) -> Observation:
    """Build a single observation with sensible, valid-by-default provenance."""
    return Observation(
        rating_id="stackoverflow-tags",
        metric_id=metric_id,
        language_id=language_id,
        period_start=period_start,
        period_end=period_end,
        period_label=period_label,
        granularity=Granularity.MONTH,
        rank=rank,
        value=value,
        unit="count" if metric_id == METRIC_QUESTIONS else ("rank" if metric_id == METRIC_RANK else "percent"),
        source_language_name=language_id,
        source_url="https://api.stackexchange.com/2.3/questions",
        source_document_id=f"api:{period_label}",
        is_derived=is_derived,
        derivation_method=None,
        retrieved_at=datetime(2021, 1, 1, tzinfo=UTC),
        source_published_at=None,
        parser_version="stackoverflow-tags-v1",
        raw_record_hash="deadbeef",
        metadata_json={"denominator": denominator},
    )


def _clean_batch() -> list[Observation]:
    """A valid questions/share/rank triple for one language and month."""
    return [
        _obs(metric_id=METRIC_QUESTIONS, value=250.0),
        _obs(metric_id=METRIC_SHARE, value=25.0, is_derived=True),
        _obs(metric_id=METRIC_RANK, value=1.0, rank=1, is_derived=True),
    ]


_CURRENT_MONTH_START = datetime.now(UTC).date().replace(day=1)

_ERROR_CASES: dict[str, list[Observation]] = {
    "count_non_negative": [_obs(metric_id=METRIC_QUESTIONS, value=-1.0)],
    "share_range": [_obs(metric_id=METRIC_SHARE, value=150.0, is_derived=True)],
    "rank_positive": [_obs(metric_id=METRIC_RANK, value=0.0, rank=0, is_derived=True)],
    "duplicate_language_period": [
        _obs(metric_id=METRIC_QUESTIONS, value=1.0),
        _obs(metric_id=METRIC_QUESTIONS, value=2.0),
    ],
    "mixed_denominator": [
        _obs(metric_id=METRIC_SHARE, language_id="python", value=10.0, is_derived=True, denominator="all_questions"),
        _obs(
            metric_id=METRIC_SHARE,
            language_id="java",
            value=10.0,
            is_derived=True,
            denominator="tracked_language_union",
        ),
    ],
    "share_not_derived": [_obs(metric_id=METRIC_SHARE, value=10.0, is_derived=False)],
    "incomplete_month": [
        _obs(
            metric_id=METRIC_QUESTIONS,
            value=5.0,
            period_start=_CURRENT_MONTH_START,
            period_end=_CURRENT_MONTH_START,
            period_label=_CURRENT_MONTH_START.strftime("%Y-%m"),
        )
    ],
}


@pytest.mark.parametrize("code", sorted(_ERROR_CASES))
def test_validate_flags_each_error_code(code: str, tmp_path: Path) -> None:
    observations = _ERROR_CASES[code]
    report = _provider(tmp_path).validate(observations)
    codes = {issue.code for issue in report.issues}
    assert code in codes
    assert report.ok is False
    assert all(issue.severity is Severity.ERROR for issue in report.issues if issue.code == code)


def test_validate_unmapped_is_warning_only(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.last_unmapped = ["brainfuck", "whitespace"]

    report = provider.validate(_clean_batch())

    warnings = [issue for issue in report.issues if issue.code == "unmapped_language"]
    assert len(warnings) == 2
    assert all(issue.severity is Severity.WARNING for issue in warnings)
    assert report.ok is True


def test_validate_clean_fixture_ok(tmp_path: Path) -> None:
    report = _provider(tmp_path).validate(_clean_batch())

    assert report.issues == []
    assert report.ok is True
