from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from langrank.providers.base import FetchPayload
from langrank.providers.pypl import PyplProvider
from langrank.providers.redmonk import RedMonkProvider
from langrank.providers.stackoverflow_survey import RANK_DERIVATION_METHOD, StackOverflowSurveyProvider
from langrank.providers.tiobe import TiobeProvider


def test_survey_computed_rank_has_derived_provenance(tmp_path: Path) -> None:
    """Computed ranks are derived while published survey percentages remain raw."""
    provider = StackOverflowSurveyProvider(tmp_path)
    content = (Path(__file__).parents[1] / "fixtures/stackoverflow-survey/sample.csv").read_bytes()
    observations = provider.normalize(provider.parse(FetchPayload(None, content)))
    ranks = [o for o in observations if o.metric_id == "stackoverflow-survey-rank"]
    percentages = [o for o in observations if o.metric_id == "worked_with_percent"]
    assert ranks and percentages
    assert all(o.is_derived and bool(o.derivation_method) and o.value == float(o.rank) for o in ranks)
    assert {o.derivation_method for o in ranks} == {RANK_DERIVATION_METHOD}
    assert all(not o.is_derived and o.derivation_method is None for o in percentages)
    invalid = replace(ranks[0], is_derived=False, derivation_method=None)
    report = provider.validate([invalid])
    assert not report.ok
    assert [issue.code for issue in report.issues] == ["rank_not_derived"]


@pytest.mark.parametrize(("provider_cls", "column"), [(TiobeProvider, "rating"), (PyplProvider, "share")])
def test_monthly_periods_use_calendar_end(tmp_path: Path, provider_cls, column: str) -> None:
    """Monthly observations cover the complete month, including leap-year February."""
    content = (
        f"period,language,rank,{column},source_url\n"
        "2024-01-01,Python,1,50,https://example.test\n"
        "2024-02-01,Python,1,50,https://example.test\n"
        "2024-04-01,Python,1,50,https://example.test\n"
    ).encode()
    provider = provider_cls(tmp_path)
    observations = provider.normalize(provider.parse(FetchPayload(None, content)))
    assert {o.period_label: o.period_end for o in observations} == {
        "2024-01": date(2024, 1, 31),
        "2024-02": date(2024, 2, 29),
        "2024-04": date(2024, 4, 30),
    }


@pytest.mark.parametrize(
    ("provider_cls", "fixture", "expected_metrics"),
    [
        (TiobeProvider, "tiobe/sample.csv", {"tiobe-rank", "tiobe-rating"}),
        (PyplProvider, "pypl/sample.csv", {"pypl-rank", "pypl-share"}),
        (RedMonkProvider, "redmonk/sample.csv", {"redmonk-rank"}),
        (
            StackOverflowSurveyProvider,
            "stackoverflow-survey/sample.csv",
            {"worked_with_percent", "stackoverflow-survey-rank"},
        ),
    ],
)
def test_provider_fixture_parse_normalize(
    tmp_path: Path, provider_cls, fixture: str, expected_metrics: set[str]
) -> None:
    provider = provider_cls(tmp_path)
    payload = FetchPayload(
        artifact=None,
        content=(Path(__file__).parents[1] / "fixtures" / fixture).read_bytes(),
    )
    records = provider.parse(payload)
    assert records
    assert {record.metric_id for record in records} == expected_metrics
    observations = provider.normalize(records)
    assert observations
    report = provider.validate(observations)
    assert report.ok
