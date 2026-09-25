from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from langrank.db import Database
from langrank.exports.csv_export import export_csv
from langrank.exports.json_export import export_json_nested
from langrank.models import FetchRequest, QueryFilters
from langrank.plotting.service import PlotService
from langrank.providers.demo import DemoProvider
from langrank.providers.pypl import PyplProvider
from langrank.providers.redmonk import RedMonkProvider
from langrank.providers.stackoverflow_survey import StackOverflowSurveyProvider
from langrank.providers.stackoverflow_tags import METRIC_SHARE, StackOverflowTagsProvider
from langrank.providers.tiobe import TiobeProvider
from langrank.services.fetch import FetchService
from langrank.services.query import QueryService
from langrank.services.validation import ValidationService

pytestmark = pytest.mark.integration


def test_demo_provider_end_to_end(tmp_path: Path) -> None:
    database = Database(tmp_path / "langrank.sqlite")
    provider = DemoProvider(tmp_path / "cache")
    summary = FetchService(database).fetch(provider, FetchRequest())
    assert summary.records_seen > 0
    rows = QueryService(database).query(QueryFilters(rating_id="demo", language_ids=["python"], years=5))
    assert rows
    csv_path = tmp_path / "demo.csv"
    json_path = tmp_path / "demo.json"
    plot_path = tmp_path / "demo.svg"
    export_csv(rows, csv_path)
    export_json_nested(rows, json_path)
    PlotService().plot(
        rows,
        metric_id="rating",
        output=plot_path,
        title=None,
        width=8,
        height=4,
        dpi=100,
        markers=False,
        invert_rank=True,
    )
    assert csv_path.exists()
    assert json_path.exists()
    assert plot_path.exists()
    assert ValidationService(database).validate().ok


def test_production_providers_fetch_query(tmp_path: Path) -> None:
    database = Database(tmp_path / "langrank.sqlite")
    cache = tmp_path / "cache"
    service = FetchService(database)
    for provider in [
        TiobeProvider(cache),
        PyplProvider(cache),
        RedMonkProvider(cache),
        StackOverflowSurveyProvider(cache),
    ]:
        summary = service.fetch(provider, FetchRequest(years=10))
        assert summary.records_seen > 0
        assert summary.validation_report.ok
    rows = QueryService(database).query(
        QueryFilters(rating_id="stackoverflow-survey", metric_id="worked_with_percent", years=10)
    )
    assert rows
    assert any(row.language_id == "python" for row in rows)


def test_stackoverflow_tags_offline_fetch_and_query(tmp_path: Path) -> None:
    """Offline fetch of the API fixture round-trips into queryable share rows.

    Seeds the provider cache with the checked-in API fixture, drives the real
    ``FetchService`` -> ``Database`` -> ``QueryService`` pipeline with
    ``offline=True`` (no network), and asserts the derived ``question-share`` rows
    land with the exact normalized values, not merely a non-empty result.
    """
    fixture = Path(__file__).parents[1] / "fixtures" / "stackoverflow-tags" / "api_sample.json"
    cache = tmp_path / "cache"
    provider_cache = cache / "stackoverflow-tags"
    provider_cache.mkdir(parents=True)
    (provider_cache / "stackoverflow-tags-fixture.json").write_bytes(fixture.read_bytes())

    database = Database(tmp_path / "langrank.sqlite")
    provider = StackOverflowTagsProvider(cache)
    summary = FetchService(database).fetch(provider, FetchRequest(offline=True))
    assert summary.validation_report.ok
    assert summary.records_inserted > 0

    rows = QueryService(database).query(
        QueryFilters(
            rating_id="stackoverflow-tags",
            metric_id=METRIC_SHARE,
            since=date(2024, 1, 1),
            until=date(2024, 3, 31),
        )
    )
    assert rows
    assert {row.unit for row in rows} == {"percent"}
    assert {row.metric_id for row in rows} == {METRIC_SHARE}
    python_jan = next(row for row in rows if row.language_id == "python" and row.period_label == "2024-01")
    assert python_jan.value == 12.8823

    empty = QueryService(database).query(
        QueryFilters(
            rating_id="stackoverflow-tags",
            metric_id="worked_with_percent",
            since=date(2024, 1, 1),
            until=date(2024, 3, 31),
        )
    )
    assert empty == []
