from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Optional

import pytest

from langrank.models import Granularity, Observation, Severity
from langrank.providers.github import (
    METRIC_IG_PUSHERS,
    METRIC_IG_RANK,
    METRIC_IG_SHARE,
    METRIC_OCTOVERSE_RANK,
    GitHubProvider,
)

#: A safely-valid quarter used by the Innovation Graph fixtures below.
_Q_START = date(2020, 1, 1)
_Q_END = date(2020, 3, 31)
_Q_LABEL = "2020-Q1"

#: A safely-valid Octoverse edition used by the annual fixtures below.
_YEAR_START = date(2024, 1, 1)
_YEAR_END = date(2024, 12, 31)
_YEAR_LABEL = "2024"


def _provider(tmp_path: Path) -> GitHubProvider:
    return GitHubProvider(tmp_path)


def _obs(
    *,
    metric_id: str,
    language_id: str = "python",
    value: Optional[float],
    rank: Optional[int] = None,
    is_derived: bool = True,
    period_start: date = _Q_START,
    period_end: date = _Q_END,
    period_label: str = _Q_LABEL,
) -> Observation:
    """Build a single observation with sensible, valid-by-default provenance."""
    return Observation(
        rating_id="github",
        metric_id=metric_id,
        language_id=language_id,
        period_start=period_start,
        period_end=period_end,
        period_label=period_label,
        granularity=Granularity.QUARTER,
        rank=rank,
        value=value,
        unit="rank" if metric_id in (METRIC_IG_RANK, METRIC_OCTOVERSE_RANK) else "count",
        source_language_name=language_id,
        source_url="https://raw.githubusercontent.com/github/innovationgraph/deadbeef/data/languages.csv",
        source_document_id="innovationgraph@deadbeef",
        is_derived=is_derived,
        derivation_method="sum_over_economies:suppressed_below_100" if is_derived else None,
        retrieved_at=datetime(2021, 1, 1, tzinfo=UTC),
        source_published_at=None,
        parser_version="github-v1",
        raw_record_hash="deadbeef",
        metadata_json={},
    )


def _octoverse_obs(*, rank: int, language_id: str = "python") -> Observation:
    """Build one raw (non-derived) annual Octoverse rank observation."""
    return _obs(
        metric_id=METRIC_OCTOVERSE_RANK,
        language_id=language_id,
        value=float(rank),
        rank=rank,
        is_derived=False,
        period_start=_YEAR_START,
        period_end=_YEAR_END,
        period_label=_YEAR_LABEL,
    )


def _clean_ig_batch() -> list[Observation]:
    """A valid derived pushers/share/rank triple for one language and quarter."""
    return [
        _obs(metric_id=METRIC_IG_PUSHERS, value=1200.0),
        _obs(metric_id=METRIC_IG_SHARE, value=60.0),
        _obs(metric_id=METRIC_IG_RANK, value=1.0, rank=1),
    ]


_ERROR_CASES: dict[str, list[Observation]] = {
    "rank_positive": [_obs(metric_id=METRIC_IG_RANK, value=0.0, rank=0)],
    "count_non_negative": [_obs(metric_id=METRIC_IG_PUSHERS, value=-1.0)],
    "share_range": [_obs(metric_id=METRIC_IG_SHARE, value=150.0)],
    "duplicate_language_period": [
        _obs(metric_id=METRIC_IG_PUSHERS, value=1.0),
        _obs(metric_id=METRIC_IG_PUSHERS, value=2.0),
    ],
    "aggregate_not_derived": [_obs(metric_id=METRIC_IG_PUSHERS, value=1200.0, is_derived=False)],
    "mixed_variant": [
        _obs(metric_id=METRIC_IG_PUSHERS, value=1200.0),
        _octoverse_obs(rank=1),
    ],
}


@pytest.mark.parametrize("code", sorted(_ERROR_CASES))
def test_github_validate_flags_each_error_code(code: str, tmp_path: Path) -> None:
    observations = _ERROR_CASES[code]
    report = _provider(tmp_path).validate(observations)
    codes = {issue.code for issue in report.issues}
    assert code in codes
    assert report.ok is False
    assert all(issue.severity is Severity.ERROR for issue in report.issues if issue.code == code)


def test_github_validate_warnings_do_not_block(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.last_unmapped = ["dockerfile", "brainfuck"]

    # Octoverse ranks 1 and 3 skip 2 -> octoverse_rank_gap; unmapped -> unmapped_language.
    report = provider.validate([_octoverse_obs(rank=1), _octoverse_obs(rank=3, language_id="rust")])

    warning_codes = {issue.code for issue in report.issues}
    assert "octoverse_rank_gap" in warning_codes
    assert "unmapped_language" in warning_codes
    assert all(issue.severity is Severity.WARNING for issue in report.issues)
    assert report.ok is True


def test_github_validate_clean_ig_batch_ok(tmp_path: Path) -> None:
    report = _provider(tmp_path).validate(_clean_ig_batch())

    assert report.issues == []
    assert report.ok is True


def test_github_validate_clean_octoverse_edition_ok(tmp_path: Path) -> None:
    edition = [_octoverse_obs(rank=1), _octoverse_obs(rank=2, language_id="rust")]

    report = _provider(tmp_path).validate(edition)

    assert report.issues == []
    assert report.ok is True
