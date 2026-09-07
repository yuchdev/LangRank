from __future__ import annotations

from datetime import UTC, date, datetime

from langrank.models import Granularity, Observation, QueryFilters
from langrank.providers.demo import DemoProvider
from langrank.services.query import QueryService


def _observation(
    language_id: str, metric_id: str, year: int, rank: int, value: float
) -> Observation:
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
        unit="rank" if metric_id == "rank" else "percent",
        source_language_name=language_id,
        source_url="demo://test",
        source_document_id=str(year),
        is_derived=False,
        derivation_method=None,
        retrieved_at=datetime.now(UTC),
        source_published_at=None,
        parser_version="demo-v1",
        raw_record_hash=f"{language_id}-{metric_id}-{year}",
    )


def test_top_current_filters_latest_snapshot(database) -> None:
    database.upsert_provider_metadata(DemoProvider(database.db_path.parent).metadata())
    fetch_run_id = database.create_fetch_run("demo")
    rows = [
        _observation("python", "rank", 2024, 2, 2.0),
        _observation("rust", "rank", 2024, 1, 1.0),
        _observation("python", "rank", 2025, 1, 1.0),
        _observation("rust", "rank", 2025, 2, 2.0),
    ]
    database.upsert_observations(rows, fetch_run_id)
    results = QueryService(database).query(
        QueryFilters(rating_id="demo", metric_id="rank", top_current=1)
    )
    assert {row.language_id for row in results} == {"python"}
