from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from langrank.cli import app

pytestmark = pytest.mark.integration

runner = CliRunner()


def test_cli_fetch_query_and_doctor(tmp_path: Path) -> None:
    db_path = tmp_path / "langrank.sqlite"
    cache_path = tmp_path / "cache"
    result = runner.invoke(app, ["--db", str(db_path), "--cache", str(cache_path), "fetch", "demo"])
    assert result.exit_code == 0, result.stdout
    query = runner.invoke(
        app,
        [
            "--db",
            str(db_path),
            "--cache",
            str(cache_path),
            "query",
            "--rating",
            "demo",
            "--language",
            "python",
            "--years",
            "5",
        ],
    )
    assert query.exit_code == 0, query.stdout
    assert "python" in query.stdout.lower()
    doctor = runner.invoke(app, ["--db", str(db_path), "doctor"])
    assert doctor.exit_code == 0, doctor.stdout
    assert "schema version" in doctor.stdout.lower()


def test_cli_ratings_and_languages_root_commands(tmp_path: Path) -> None:
    db_path = tmp_path / "langrank.sqlite"
    ratings = runner.invoke(app, ["--db", str(db_path), "ratings"])
    languages = runner.invoke(app, ["--db", str(db_path), "languages"])
    assert ratings.exit_code == 0, ratings.stdout
    assert "demo" in ratings.stdout.lower()
    assert "tiobe" in ratings.stdout.lower()
    assert "pypl" in ratings.stdout.lower()
    assert "redmonk" in ratings.stdout.lower()
    assert "stackoverflow" in ratings.stdout.lower()
    assert languages.exit_code == 0, languages.stdout
    assert "c++" in languages.stdout.lower()


def test_cli_fetch_all_independent_provider_execution(tmp_path: Path) -> None:
    db_path = tmp_path / "langrank.sqlite"
    cache_path = tmp_path / "cache"
    result = runner.invoke(
        app,
        ["--db", str(db_path), "--cache", str(cache_path), "fetch", "all", "--years", "10"],
    )
    # The stackoverflow-tags provider now has a real fetch/parse/normalize, but two
    # things still make `fetch all` report it FAILED and exit non-zero, both without
    # any network access: (1) the default 10-year window's request plan exceeds the
    # 300/day anonymous Stack Exchange budget, so fetch() raises before issuing any
    # HTTP request; and (2) validate() is still a stub (subtask 06). The point of
    # this test is provider independence: one failing provider must not stop the
    # others, so every fetchable bootstrap provider still reports SUCCESS.
    assert result.exit_code == 1, result.stdout
    assert "success tiobe" in result.stdout.lower()
    assert "success pypl" in result.stdout.lower()
    assert "success redmonk" in result.stdout.lower()
    assert "success stackoverflow-survey" in result.stdout.lower()
    assert "failed  stackoverflow-tags" in result.stdout.lower()
