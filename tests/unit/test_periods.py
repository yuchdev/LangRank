from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from langrank.db import Database
from langrank.models import Granularity, Observation, QueryFilters
from langrank.providers.common import quarter_period
from langrank.providers.demo import DemoProvider
from langrank.services.query import QueryService


def test_quarter_period_bounds() -> None:
    """Each quarter maps to its calendar bounds and ``YYYY-Qn`` label."""
    assert quarter_period(2020, 1) == (date(2020, 1, 1), date(2020, 3, 31), "2020-Q1")
    assert quarter_period(2020, 2) == (date(2020, 4, 1), date(2020, 6, 30), "2020-Q2")
    assert quarter_period(2020, 3) == (date(2020, 7, 1), date(2020, 9, 30), "2020-Q3")
    assert quarter_period(2020, 4) == (date(2020, 10, 1), date(2020, 12, 31), "2020-Q4")


@pytest.mark.parametrize("quarter", [0, 5])
def test_quarter_period_rejects_invalid_quarter(quarter: int) -> None:
    """A quarter outside ``1..4`` raises :class:`ValueError`."""
    with pytest.raises(ValueError, match="quarter must be in 1..4"):
        quarter_period(2020, quarter)


def _quarter_observation() -> Observation:
    period_start, period_end, period_label = quarter_period(2020, 1)
    return Observation(
        rating_id="demo",
        metric_id="rank",
        language_id="python",
        period_start=period_start,
        period_end=period_end,
        period_label=period_label,
        granularity=Granularity.QUARTER,
        rank=1,
        value=1.0,
        unit="rank",
        source_language_name="python",
        source_url="demo://test",
        source_document_id="2020-Q1",
        is_derived=False,
        derivation_method=None,
        retrieved_at=datetime.now(UTC),
        source_published_at=None,
        parser_version="demo-v1",
        raw_record_hash="python-rank-2020-Q1",
    )


def test_quarter_observation_round_trips_db(database: Database) -> None:
    """A quarterly observation upserts and reads back with ``"quarter"`` intact."""
    database.upsert_provider_metadata(DemoProvider(database.db_path.parent).metadata())
    fetch_run_id = database.create_fetch_run("demo")
    database.upsert_observations([_quarter_observation()], fetch_run_id)

    results = QueryService(database).query(QueryFilters(rating_id="demo", metric_id="rank"))
    assert [row.period_label for row in results] == ["2020-Q1"]

    with database.connect() as connection:
        stored = connection.execute(
            "SELECT granularity FROM observations WHERE rating_id = 'demo' AND metric_id = 'rank'"
        ).fetchone()
    assert stored["granularity"] == "quarter"
