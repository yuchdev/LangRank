"""Integration tests for the JetBrains provider: fixtures -> CLI/DB -> query.

These exercise the real ``Database`` natural-key upsert and ``QueryService`` with no
network. Two entry points are covered end to end:

- ``langrank import --rating jetbrains <raw.csv>`` over the synthetic raw fixture,
  which routes through the streaming ``SupportsRawImport`` path and must persist only
  derived ``-raw`` metrics (never the published family) with the correct denominators.
- the offline published fetch of the bundled dataset, which must land the three
  distinct published metrics and stay queryable per question.

The guarantee under test is that the published and ``-raw`` families never share a
series, that ``primary_language`` and ``used_last_12_months`` stay distinct, and that a
query which should match nothing reports empty rather than borrowing rows.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from langrank.cli import app
from langrank.db import Database
from langrank.models import FetchRequest, QueryFilters
from langrank.providers.jetbrains import (
    PUBLISHED_METRICS,
    JetBrainsProvider,
    raw_metric_id,
)
from langrank.providers.jetbrains_questions import (
    METRIC_PLANNED_ADOPTION,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
)
from langrank.services.fetch import FetchService
from langrank.services.query import QueryService

pytestmark = pytest.mark.integration

runner = CliRunner()

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "jetbrains"


def test_jetbrains_import_command_round_trip(tmp_path: Path) -> None:
    """``langrank import --rating jetbrains`` loads the synthetic raw CSV end to end.

    The raw fixture routes through the streaming import path, normalizes to derived
    ``-raw`` observations, validates, and persists. The stored rows must carry only
    ``-raw`` metric ids (never a published metric id), the used-question denominator of
    16, and ``is_derived=1`` - so a raw import can never masquerade as published data.
    """
    db_path = tmp_path / "langrank.sqlite"
    fixture = _FIXTURES / "raw_sample.csv"
    base = ["--db", str(db_path), "--cache", str(tmp_path / "cache")]

    imported = runner.invoke(app, [*base, "import", "--rating", "jetbrains", str(fixture)])
    assert imported.exit_code == 0, imported.stdout
    assert "Imported jetbrains" in imported.stdout
    # 11 records: 4 used + 3 primary + 2 planned + 2 meta-answer records (Other,
    # "I don't use ...") that normalize away, leaving 9 observations inserted.
    assert "seen=11" in imported.stdout
    assert "inserted=9" in imported.stdout

    with sqlite3.connect(db_path) as connection:
        metrics = {
            row[0]
            for row in connection.execute("SELECT DISTINCT metric_id FROM observations WHERE rating_id = 'jetbrains'")
        }
        used_python = connection.execute(
            "SELECT value, sample_size, is_derived FROM observations WHERE metric_id = ? AND language_id = 'python'",
            (raw_metric_id(METRIC_USED_LAST_12_MONTHS),),
        ).fetchone()

    assert metrics == {
        raw_metric_id(METRIC_USED_LAST_12_MONTHS),
        raw_metric_id(METRIC_PRIMARY_LANGUAGE),
        raw_metric_id(METRIC_PLANNED_ADOPTION),
    }
    # No published metric id was persisted by a raw import.
    assert metrics.isdisjoint(set(PUBLISHED_METRICS))
    value, sample_size, is_derived = used_python
    assert value == pytest.approx(62.5)  # 10 of 16 respondents
    assert sample_size == 16
    assert bool(is_derived) is True


def test_jetbrains_import_dry_run_persists_nothing(tmp_path: Path) -> None:
    """A ``--dry-run`` import reports its counts but writes no observation.

    Dry-run must never touch the store, so a query afterwards returns nothing rather
    than silently persisting a preview.
    """
    db_path = tmp_path / "langrank.sqlite"
    base = ["--db", str(db_path), "--cache", str(tmp_path / "cache")]

    result = runner.invoke(
        app, [*base, "import", "--rating", "jetbrains", str(_FIXTURES / "raw_sample.csv"), "--dry-run"]
    )
    assert result.exit_code == 0, result.stdout
    assert "dry_run=True" in result.stdout

    with sqlite3.connect(db_path) as connection:
        (count,) = connection.execute("SELECT COUNT(*) FROM observations WHERE rating_id = 'jetbrains'").fetchone()
    assert count == 0


def test_jetbrains_published_fetch_round_trips_distinct_metrics(tmp_path: Path) -> None:
    """The bundled dataset fetches offline; the three questions land as distinct series.

    Drives ``FetchService`` -> ``Database`` -> ``QueryService`` on the committed CSV
    (0 network requests). A 2024 ``used_last_12_months`` query returns only that metric
    with Python at 57, while ``primary_language`` for the same year and language is a
    different value (35) - proving the two questions are never merged onto one axis.
    """
    database = Database(tmp_path / "langrank.sqlite")
    summary = FetchService(database).fetch(JetBrainsProvider(tmp_path / "cache"), FetchRequest(years=20))
    assert summary.validation_report.ok
    assert summary.records_inserted > 0

    service = QueryService(database)
    used = service.query(
        QueryFilters(rating_id="jetbrains", metric_id=METRIC_USED_LAST_12_MONTHS, year=2024, language_ids=["python"])
    )
    primary = service.query(
        QueryFilters(rating_id="jetbrains", metric_id=METRIC_PRIMARY_LANGUAGE, year=2024, language_ids=["python"])
    )
    assert [row.value for row in used] == [57.0]
    assert [row.value for row in primary] == [35.0]
    assert all(row.metric_id == METRIC_USED_LAST_12_MONTHS for row in used)
    assert all(row.metric_id == METRIC_PRIMARY_LANGUAGE for row in primary)


def test_jetbrains_query_with_no_match_reports_empty(tmp_path: Path) -> None:
    """A query that should match nothing reports empty, not another metric's rows.

    A never-imported ``-raw`` metric and a year the survey never ran both come back
    empty, guarding against a filter silently borrowing a different series.
    """
    database = Database(tmp_path / "langrank.sqlite")
    FetchService(database).fetch(JetBrainsProvider(tmp_path / "cache"), FetchRequest(years=20))
    service = QueryService(database)

    raw = service.query(QueryFilters(rating_id="jetbrains", metric_id=raw_metric_id(METRIC_USED_LAST_12_MONTHS)))
    assert raw == []

    absent_year = service.query(QueryFilters(rating_id="jetbrains", metric_id=METRIC_USED_LAST_12_MONTHS, year=1999))
    assert absent_year == []

    present = service.query(QueryFilters(rating_id="jetbrains", metric_id=METRIC_USED_LAST_12_MONTHS, year=2024))
    assert present
