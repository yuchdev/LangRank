"""Integration tests for the IEEE Spectrum provider: fixture -> DB -> query.

These exercise the real ``Database`` natural-key upsert and ``QueryService`` with
no network (IEEE ships no downloadable dataset; the bundled CSV is the source).
The guarantee under test is that each profile is its own metric pair, so a query
for one profile's metric never returns another profile's rows, and a query that
should match nothing reports an empty result rather than silently borrowing rows.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from langrank.db import Database
from langrank.models import FetchRequest, QueryFilters
from langrank.providers.base import FetchPayload
from langrank.providers.ieee_spectrum import (
    IeeeProfile,
    IeeeSpectrumProvider,
    rank_metric_id,
    score_metric_id,
)
from langrank.services.fetch import FetchService
from langrank.services.query import QueryService

pytestmark = pytest.mark.integration

_FIXTURE = Path(__file__).parents[1] / "fixtures" / "ieee-spectrum" / "sample.csv"


def _seed_fixture(tmp_path: Path) -> tuple[Database, QueryService]:
    """Upsert the sample fixture into a fresh database via the real pipeline.

    Registers the provider metadata (ratings + metrics), opens a fetch run, then
    runs ``parse`` -> ``normalize`` -> ``validate`` -> ``upsert_observations`` on the
    verbatim fixture. No network and no bundled-dataset read.

    :param tmp_path: pytest-provided temp directory for the SQLite file and cache.
    :returns: The seeded database and a query service bound to it.
    """
    database = Database(tmp_path / "langrank.sqlite")
    provider = IeeeSpectrumProvider(tmp_path / "cache")
    database.upsert_provider_metadata(provider.metadata())
    fetch_run_id = database.create_fetch_run(provider.provider_id)

    payload = FetchPayload(artifact=None, content=_FIXTURE.read_bytes())
    observations = provider.normalize(provider.parse(payload))
    report = provider.validate(observations)
    assert report.ok, f"fixture must validate clean: {[i.message for i in report.issues]}"

    inserted, updated = database.upsert_observations(observations, fetch_run_id)
    assert inserted == 48  # 4 mapped languages x 6 (edition x profile) x 2 metrics
    assert updated == 0
    return database, QueryService(database)


def test_ieee_spectrum_fixture_round_trip_isolates_profiles(tmp_path: Path) -> None:
    """One profile's rank query returns only that profile's rows, with exact ranks.

    Querying ``ieee-spectrum-jobs-rank`` for 2024 must return the jobs ranks
    (Python 2, C++ 10, and the Ada/Haskell rank-44 tie) and nothing else; the
    spectrum ranks for the same languages differ, proving the two profiles are
    stored as independent series and are never merged onto one axis.
    """
    _, service = _seed_fixture(tmp_path)

    jobs = service.query(QueryFilters(rating_id="ieee-spectrum", metric_id=rank_metric_id(IeeeProfile.JOBS), year=2024))
    assert jobs
    assert {row.metric_id for row in jobs} == {rank_metric_id(IeeeProfile.JOBS)}
    assert {row.language_id: row.rank for row in jobs} == {"python": 2, "c++": 10, "ada": 44, "haskell": 44}
    assert {row.unit for row in jobs} == {"rank"}

    spectrum = service.query(
        QueryFilters(rating_id="ieee-spectrum", metric_id=rank_metric_id(IeeeProfile.SPECTRUM), year=2024)
    )
    assert {row.language_id: row.rank for row in spectrum} == {"python": 1, "c++": 4, "ada": 50, "haskell": 38}
    # Same language, same year, different profile -> a different rank; the profiles
    # never collapse into one value.
    assert {row.metric_id for row in spectrum} == {rank_metric_id(IeeeProfile.SPECTRUM)}


def test_ieee_spectrum_query_one_profile_excludes_others(tmp_path: Path) -> None:
    """A jobs-rank query never leaks a spectrum or trending row, across every year.

    Guards the core invariant directly: filtering on one profile's metric id must
    return rows carrying only that metric id, so a downstream chart of the jobs
    series can never be contaminated by the spectrum or trending weighting.
    """
    _, service = _seed_fixture(tmp_path)

    jobs = service.query(QueryFilters(rating_id="ieee-spectrum", metric_id=rank_metric_id(IeeeProfile.JOBS)))
    assert {row.period_label for row in jobs} == {"2022", "2024"}
    foreign_metrics = {
        rank_metric_id(IeeeProfile.SPECTRUM),
        rank_metric_id(IeeeProfile.TRENDING),
        score_metric_id(IeeeProfile.SPECTRUM),
        score_metric_id(IeeeProfile.JOBS),
        score_metric_id(IeeeProfile.TRENDING),
    }
    assert all(row.metric_id == rank_metric_id(IeeeProfile.JOBS) for row in jobs)
    assert not (foreign_metrics & {row.metric_id for row in jobs})


def test_ieee_spectrum_query_with_no_match_reports_empty(tmp_path: Path) -> None:
    """A query that should match nothing reports an empty result, not stray rows.

    An un-imported profile (``open``) owns no metric, and an edition year the
    fixture never covered (2019) holds no jobs rows; both must come back empty
    rather than silently returning another profile's or year's data.
    """
    _, service = _seed_fixture(tmp_path)

    # The deliberately un-imported "open" preset has no metric id, so nothing maps.
    unknown_profile = service.query(QueryFilters(rating_id="ieee-spectrum", metric_id="ieee-spectrum-open-rank"))
    assert unknown_profile == []

    # A real metric, but a year the fixture does not cover.
    absent_year = service.query(
        QueryFilters(
            rating_id="ieee-spectrum",
            metric_id=rank_metric_id(IeeeProfile.JOBS),
            since=date(2019, 1, 1),
            until=date(2019, 12, 31),
        )
    )
    assert absent_year == []

    # Sanity contrast: the same metric in a covered year is non-empty.
    present = service.query(
        QueryFilters(rating_id="ieee-spectrum", metric_id=rank_metric_id(IeeeProfile.JOBS), year=2022)
    )
    assert present


def test_ieee_spectrum_offline_fetch_of_bundled_dataset_round_trips(tmp_path: Path) -> None:
    """The real provider fetches the bundled dataset offline and queries per profile.

    Drives the full ``FetchService`` -> ``Database`` -> ``QueryService`` pipeline on
    the committed edition CSV (0 network requests). Asserts stable published facts -
    2024 jobs #1 is SQL while 2024 spectrum #1 is Python - so the two profiles land
    as distinct series, and a jobs query never returns a spectrum metric id.
    """
    database = Database(tmp_path / "langrank.sqlite")
    summary = FetchService(database).fetch(IeeeSpectrumProvider(tmp_path / "cache"), FetchRequest(years=10))
    assert summary.validation_report.ok
    assert summary.records_inserted > 0

    service = QueryService(database)
    jobs_2024 = service.query(
        QueryFilters(rating_id="ieee-spectrum", metric_id=rank_metric_id(IeeeProfile.JOBS), year=2024)
    )
    spectrum_2024 = service.query(
        QueryFilters(rating_id="ieee-spectrum", metric_id=rank_metric_id(IeeeProfile.SPECTRUM), year=2024)
    )
    jobs_top = next(row for row in jobs_2024 if row.rank == 1)
    spectrum_top = next(row for row in spectrum_2024 if row.rank == 1)
    assert jobs_top.language_id == "sql"
    assert spectrum_top.language_id == "python"
    assert all(row.metric_id == rank_metric_id(IeeeProfile.JOBS) for row in jobs_2024)
