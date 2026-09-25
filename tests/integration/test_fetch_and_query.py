from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from langrank.db import Database
from langrank.exports.csv_export import export_csv
from langrank.exports.json_export import export_json_nested
from langrank.models import FetchRequest, QueryFilters
from langrank.plotting.service import PlotService
from langrank.providers.demo import DemoProvider
from langrank.providers.github import (
    METRIC_IG_RANK,
    METRIC_IG_SHARE,
    METRIC_OCTOVERSE_RANK,
    GitHubProvider,
)
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


def test_github_fetch_both_variants_and_query(tmp_path: Path) -> None:
    """Both GitHub variants fetch offline and land as independently queryable rows.

    Octoverse reads its bundled curated CSV (no network); the Innovation Graph
    variant replays a seeded cache (fixture CSV + commit-SHA sidecar, ``offline``)
    so nothing hits the network. Each variant is fetched through the real
    ``FetchService`` -> ``Database`` -> ``QueryService`` pipeline into one database,
    and the assertions check exact ranks/units, not merely a non-empty result.
    """
    fixture = Path(__file__).parents[1] / "fixtures" / "github" / "innovation_graph_languages.csv"
    commit_sha = "054c7dbc527518fa2ecfd316efe2aa01f3986c39"
    csv_bytes = fixture.read_bytes()
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()

    ig_cache = tmp_path / "cache-ig"
    provider_cache = ig_cache / "github"
    provider_cache.mkdir(parents=True)
    (provider_cache / f"github-{csv_sha256[:12]}.csv").write_bytes(csv_bytes)
    (provider_cache / f"github-{csv_sha256[:12]}.meta").write_text(
        json.dumps({"commit_sha": commit_sha, "csv_sha256": csv_sha256}, sort_keys=True),
        encoding="utf-8",
    )

    database = Database(tmp_path / "langrank.sqlite")
    service = FetchService(database)

    ig_summary = service.fetch(GitHubProvider(ig_cache), FetchRequest(offline=True, source="innovation-graph"))
    assert ig_summary.validation_report.ok
    assert ig_summary.records_inserted > 0

    oct_summary = service.fetch(GitHubProvider(tmp_path / "cache-oct"), FetchRequest(source="octoverse"))
    assert oct_summary.validation_report.ok
    assert oct_summary.records_inserted > 0

    # Innovation Graph quarterly rows are queryable and carry the derived rank order.
    ig_ranks = QueryService(database).query(
        QueryFilters(
            rating_id="github",
            metric_id=METRIC_IG_RANK,
            since=date(2025, 1, 1),
            until=date(2026, 3, 31),
        )
    )
    assert ig_ranks
    q4_ranks = {row.language_id: row.rank for row in ig_ranks if row.period_label == "2025-Q4"}
    assert q4_ranks == {"javascript": 1, "python": 2, "c++": 3, "solidity": 4}

    ig_shares = QueryService(database).query(
        QueryFilters(rating_id="github", metric_id=METRIC_IG_SHARE, since=date(2025, 1, 1), until=date(2026, 3, 31))
    )
    assert {row.unit for row in ig_shares} == {"percent"}

    # Octoverse annual ranks are a separate, independently queryable series.
    oct_rows = QueryService(database).query(
        QueryFilters(rating_id="github", metric_id=METRIC_OCTOVERSE_RANK, year=2025)
    )
    assert oct_rows
    assert {row.language_id: row.rank for row in oct_rows} == {"typescript": 1, "python": 2, "javascript": 3}

    # A query for a metric the other variant owns must not bleed across editions.
    cross = QueryService(database).query(
        QueryFilters(
            rating_id="github", metric_id=METRIC_OCTOVERSE_RANK, since=date(2025, 10, 1), until=date(2025, 12, 31)
        )
    )
    assert all(row.granularity.value == "year" for row in cross)
    assert all(row.metric_id == METRIC_OCTOVERSE_RANK for row in cross)
