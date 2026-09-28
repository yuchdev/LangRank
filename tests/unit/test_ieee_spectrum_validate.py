from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from langrank.models import FetchRequest, Granularity, Observation, Severity
from langrank.providers.ieee_spectrum import (
    IeeeProfile,
    IeeeSpectrumProvider,
    rank_metric_id,
    score_metric_id,
)

#: A safely-valid edition used by the fixtures below (2025 carries all three profiles).
_YEAR = 2025
_YEAR_START = date(_YEAR, 1, 1)
_YEAR_END = date(_YEAR, 12, 31)
_YEAR_LABEL = str(_YEAR)


def _provider(tmp_path: Path) -> IeeeSpectrumProvider:
    return IeeeSpectrumProvider(tmp_path)


def _rank_obs(
    *,
    profile: IeeeProfile = IeeeProfile.SPECTRUM,
    language_id: str = "python",
    rank: int = 1,
    is_derived: bool = True,
    year: int = _YEAR,
) -> Observation:
    """Build one derived-by-default rank observation with valid provenance."""
    return Observation(
        rating_id="ieee-spectrum",
        metric_id=rank_metric_id(profile),
        language_id=language_id,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=rank,
        value=float(rank),
        unit="rank",
        source_language_name=language_id,
        source_url="https://spectrum.ieee.org/top-programming-languages-2025",
        source_document_id=f"ieee-tpl-{year}-{profile.value}",
        is_derived=is_derived,
        derivation_method="rank_by_published_score" if is_derived else None,
        retrieved_at=datetime(2025, 9, 23, tzinfo=UTC),
        source_published_at=None,
        parser_version="ieee-spectrum-v1",
        raw_record_hash="deadbeef",
        metadata_json={"profile": profile.value},
    )


def _score_obs(
    *,
    profile: IeeeProfile = IeeeProfile.SPECTRUM,
    language_id: str = "python",
    value: float = 1.0,
    is_derived: bool = False,
    score_scale: str = "0-1",
    year: int = _YEAR,
) -> Observation:
    """Build one raw-by-default score observation with valid provenance."""
    return Observation(
        rating_id="ieee-spectrum",
        metric_id=score_metric_id(profile),
        language_id=language_id,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=None,
        value=value,
        unit="score",
        source_language_name=language_id,
        source_url="https://spectrum.ieee.org/top-programming-languages-2025",
        source_document_id=f"ieee-tpl-{year}-{profile.value}",
        is_derived=is_derived,
        derivation_method=None,
        retrieved_at=datetime(2025, 9, 23, tzinfo=UTC),
        source_published_at=None,
        parser_version="ieee-spectrum-v1",
        raw_record_hash="deadbeef",
        metadata_json={"profile": profile.value, "score_scale": score_scale},
    )


_ERROR_CASES: dict[str, list[Observation]] = {
    "rank_positive": [_rank_obs(rank=0)],
    "score_range": [_score_obs(value=1.5, score_scale="0-1")],
    "duplicate_language_period": [_rank_obs(rank=1), _rank_obs(rank=1)],
    "profile_not_in_edition": [_rank_obs(year=2019)],
    "mixed_profile": [
        _rank_obs(profile=IeeeProfile.SPECTRUM, language_id="python", rank=1),
        # Same metric id (spectrum-rank) but a conflicting metadata profile.
        replace(
            _rank_obs(profile=IeeeProfile.SPECTRUM, language_id="java", rank=2),
            metadata_json={"profile": IeeeProfile.JOBS.value},
        ),
    ],
    "derivation_flag_rank_not_derived": [_rank_obs(is_derived=False)],
    "derivation_flag_score_derived": [_score_obs(is_derived=True)],
    "duplicate_rank": [
        _rank_obs(language_id="python", rank=5),
        _rank_obs(language_id="java", rank=5),
        _score_obs(language_id="python", value=0.5),
        _score_obs(language_id="java", value=0.4),
    ],
}

#: The two ``derivation_flag`` fixtures above are distinct triggers of the one code.
_EXPECTED_CODE = {
    "derivation_flag_rank_not_derived": "derivation_flag",
    "derivation_flag_score_derived": "derivation_flag",
}


@pytest.mark.parametrize("case", sorted(_ERROR_CASES))
def test_ieee_validate_flags_each_code(case: str, tmp_path: Path) -> None:
    observations = _ERROR_CASES[case]
    report = _provider(tmp_path).validate(observations)
    codes = {issue.code for issue in report.issues}
    expected = _EXPECTED_CODE.get(case, case)
    assert expected in codes
    assert report.ok is False
    assert all(issue.severity is Severity.ERROR for issue in report.issues if issue.code == expected)


def test_ieee_validate_warnings_do_not_block(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.last_unmapped = ["Cobol", "Fortran"]

    # Top score 0.9 never reaches the 0-1 scale top -> top_score_not_100; the two
    # unmapped labels -> unmapped_language. Both are WARNING-only.
    report = provider.validate([_rank_obs(rank=1), _score_obs(value=0.9)])

    warning_codes = {issue.code for issue in report.issues}
    assert "top_score_not_100" in warning_codes
    assert "unmapped_language" in warning_codes
    assert all(issue.severity is Severity.WARNING for issue in report.issues)
    assert report.ok is True


def test_ieee_validate_tied_rank_equal_score_is_clean(tmp_path: Path) -> None:
    # A legitimate competition-ranking tie: two languages share rank 5 and an equal
    # score. Rank gaps/ties are never flagged; duplicate_rank fires only on a mismatch.
    edition = [
        _rank_obs(language_id="python", rank=5),
        _rank_obs(language_id="java", rank=5),
        _score_obs(language_id="python", value=1.0),
        _score_obs(language_id="java", value=1.0),
    ]

    report = _provider(tmp_path).validate(edition)

    assert report.ok is True
    assert {issue.code for issue in report.issues} == set()


def test_ieee_validate_score_range_uses_edition_scale(tmp_path: Path) -> None:
    # 100 is in range on the 2022 0-100 scale but far out of range on the 0-1 scale.
    on_scale = _score_obs(value=100.0, score_scale="0-100", year=2022)
    off_scale = _score_obs(value=100.0, score_scale="0-1", language_id="java")

    assert _provider(tmp_path).validate([on_scale]).ok is True
    off_report = _provider(tmp_path).validate([off_scale])
    assert "score_range" in {issue.code for issue in off_report.issues}
    assert off_report.ok is False


def test_ieee_validate_bundled_dataset_ok(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    observations = provider.normalize(provider.parse(provider.fetch(FetchRequest(years=100, no_cache=True))))

    report = provider.validate(observations)

    assert observations
    assert provider.last_unmapped == []
    assert [issue for issue in report.issues if issue.severity is Severity.ERROR] == []
    assert report.ok is True
