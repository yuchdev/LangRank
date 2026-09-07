from __future__ import annotations

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
