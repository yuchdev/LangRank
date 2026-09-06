from __future__ import annotations

from pathlib import Path

from langrank.db import Database
from langrank.exports.csv_export import export_csv
from langrank.exports.json_export import export_json_nested
from langrank.models import FetchRequest, QueryFilters
from langrank.plotting.service import PlotService
from langrank.providers.demo import DemoProvider
from langrank.services.fetch import FetchService
from langrank.services.query import QueryService
from langrank.services.validation import ValidationService


def test_demo_provider_end_to_end(tmp_path: Path) -> None:
    database = Database(tmp_path / "langrank.sqlite")
    provider = DemoProvider(tmp_path / "cache")
    summary = FetchService(database).fetch(provider, FetchRequest())
    assert summary.records_seen > 0
    rows = QueryService(database).query(
        QueryFilters(rating_id="demo", language_ids=["python"], years=5)
    )
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
