from __future__ import annotations

from pathlib import Path

import pytest

from langrank.providers.base import FetchPayload
from langrank.providers.pypl import PyplProvider
from langrank.providers.redmonk import RedMonkProvider
from langrank.providers.stackoverflow_survey import StackOverflowSurveyProvider
from langrank.providers.tiobe import TiobeProvider


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
