from __future__ import annotations

import tempfile
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Optional

import pytest

from langrank.models import FetchRequest, Granularity, Observation, Severity
from langrank.providers.jetbrains import (
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
    RAW_DERIVATION,
    JetBrainsProvider,
    raw_metric_id,
)

#: Sentinel telling :func:`_obs` to omit the ``question_wording`` key entirely (as
#: opposed to setting it to ``None``, which is a legitimate unverified wording).
_OMIT = object()


def _provider() -> JetBrainsProvider:
    return JetBrainsProvider(Path(tempfile.mkdtemp()))


def _obs(
    *,
    metric_id: str = METRIC_USED_LAST_12_MONTHS,
    language_id: str = "python",
    year: int = 2024,
    value: Optional[float] = 50.0,
    is_derived: bool = False,
    derivation_method: Optional[str] = None,
    sample_size: Optional[int] = 1000,
    wording: Any = "Which programming languages have you used in the last 12 months?",
    wording_verified: bool = True,
) -> Observation:
    """Build one valid-by-default published observation for a survey year.

    :param metric_id: The metric ID (published or ``-raw``).
    :param language_id: Canonical language ID.
    :param year: Survey year (drives ``period_start``/``period_end``/label).
    :param value: The percentage value.
    :param is_derived: Whether the observation is derived (``-raw`` family).
    :param derivation_method: The derivation method, or ``None`` for published.
    :param sample_size: The survey denominator, or ``None`` to omit it.
    :param wording: The ``question_wording`` metadata value; pass :data:`_OMIT` to
        drop the key entirely.
    :param wording_verified: The ``wording_verified`` metadata flag.
    :returns: A fully populated :class:`~langrank.models.Observation`.
    """
    metadata: dict[str, Any] = {"wording_verified": wording_verified}
    if wording is not _OMIT:
        metadata["question_wording"] = wording
    return Observation(
        rating_id="jetbrains",
        metric_id=metric_id,
        language_id=language_id,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=None,
        value=value,
        unit="percent",
        source_language_name=language_id,
        source_url="https://www.jetbrains.com/lp/devecosystem-2024/",
        source_document_id=f"jetbrains-devecosystem-{year}",
        is_derived=is_derived,
        derivation_method=derivation_method,
        retrieved_at=datetime(2025, 1, 1, tzinfo=UTC),
        source_published_at=None,
        parser_version="jetbrains-v1",
        raw_record_hash="deadbeef",
        metadata_json=metadata,
        sample_size=sample_size,
    )


def _raw_obs(**kwargs: Any) -> Observation:
    """Build a valid-by-default derived ``-raw`` observation."""
    defaults: dict[str, Any] = {
        "metric_id": raw_metric_id(METRIC_USED_LAST_12_MONTHS),
        "is_derived": True,
        "derivation_method": RAW_DERIVATION,
    }
    defaults.update(kwargs)
    return _obs(**defaults)


def _percent_range(provider: JetBrainsProvider) -> list[Observation]:
    return [_obs(value=150.0)]


def _duplicate(provider: JetBrainsProvider) -> list[Observation]:
    return [_obs(), _obs()]


def _published_marked_derived(provider: JetBrainsProvider) -> list[Observation]:
    return [_obs(is_derived=True, derivation_method=RAW_DERIVATION)]


def _raw_not_derived_flag(provider: JetBrainsProvider) -> list[Observation]:
    return [_raw_obs(is_derived=False, derivation_method=None)]


def _raw_wrong_method(provider: JetBrainsProvider) -> list[Observation]:
    return [_raw_obs(derivation_method="something_else")]


def _metric_not_asked(provider: JetBrainsProvider) -> list[Observation]:
    # primary-language was not published for the 2018 edition.
    return [_obs(metric_id=METRIC_PRIMARY_LANGUAGE, year=2018, wording=None, wording_verified=False)]


def _missing_question_wording(provider: JetBrainsProvider) -> list[Observation]:
    return [_obs(wording=_OMIT)]


def _missing_sample_size(provider: JetBrainsProvider) -> list[Observation]:
    return [_raw_obs(sample_size=None)]


def _question_wording_change(provider: JetBrainsProvider) -> list[Observation]:
    return [
        _obs(year=2018, wording="What programming language(s) do you regularly use?"),
        _obs(year=2019, wording="What programming languages have you used in the last 12 months?"),
    ]


def _unmapped_language(provider: JetBrainsProvider) -> list[Observation]:
    provider.last_unmapped = ["Nonexistent Lang"]
    return []


_CASES: list[tuple[str, Severity, Callable[[JetBrainsProvider], list[Observation]]]] = [
    ("percent_range", Severity.ERROR, _percent_range),
    ("duplicate_language_period", Severity.ERROR, _duplicate),
    ("published_marked_derived", Severity.ERROR, _published_marked_derived),
    ("raw_not_derived", Severity.ERROR, _raw_not_derived_flag),
    ("raw_not_derived", Severity.ERROR, _raw_wrong_method),
    ("metric_not_asked", Severity.ERROR, _metric_not_asked),
    ("missing_question_wording", Severity.ERROR, _missing_question_wording),
    ("missing_sample_size", Severity.WARNING, _missing_sample_size),
    ("question_wording_change", Severity.WARNING, _question_wording_change),
    ("unmapped_language", Severity.WARNING, _unmapped_language),
]


@pytest.mark.parametrize(("code", "severity", "build"), _CASES)
def test_jetbrains_validate_flags_each_code(
    code: str,
    severity: Severity,
    build: Callable[[JetBrainsProvider], list[Observation]],
) -> None:
    """Each named code fires at its stated severity for a targeted observation."""
    provider = _provider()
    observations = build(provider)
    report = provider.validate(observations)
    matches = [issue for issue in report.issues if issue.code == code]
    assert matches, f"expected code {code!r}; got {[(i.code, i.severity.value) for i in report.issues]}"
    assert all(issue.severity is severity for issue in matches)
    # An ERROR code blocks the upsert; a WARNING-only report stays ok.
    assert report.ok is (severity is Severity.WARNING)


def test_jetbrains_validate_never_mutates_observations() -> None:
    """Validation is read-only: the input observations are returned unchanged."""
    provider = _provider()
    original = _obs()
    provider.validate([original])
    assert original == _obs()


def test_jetbrains_validate_multiselect_sum_over_100_is_not_flagged() -> None:
    """Per-language shares that legitimately sum > 100 % raise no percent_range error."""
    provider = _provider()
    observations = [
        _raw_obs(language_id="python", value=80.0),
        _raw_obs(language_id="javascript", value=70.0),
    ]
    report = provider.validate(observations)
    assert report.ok
    assert not [issue for issue in report.issues if issue.code == "percent_range"]


def test_jetbrains_validate_distinct_questions_are_not_merged() -> None:
    """primary_language and used_last_12_months stay on distinct metric IDs (no merge)."""
    provider = _provider()
    observations = [
        _obs(metric_id=METRIC_USED_LAST_12_MONTHS, wording=None, wording_verified=False),
        _obs(metric_id=METRIC_PRIMARY_LANGUAGE, wording=None, wording_verified=False),
    ]
    report = provider.validate(observations)
    assert report.ok
    assert not any(issue.severity is Severity.ERROR for issue in report.issues)


def test_jetbrains_validate_bundled_dataset_ok() -> None:
    """The full bundled published dataset validates with zero ERRORs."""
    provider = _provider()
    payload = provider.fetch(FetchRequest(no_cache=True))
    records = provider.parse(payload)
    observations = provider.normalize(records)
    report = provider.validate(observations)
    errors = [issue for issue in report.issues if issue.severity is Severity.ERROR]
    assert errors == []
    assert report.ok
    assert observations
