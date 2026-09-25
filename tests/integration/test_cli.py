from __future__ import annotations

import json
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


def _seed_stackoverflow_tags_cache(cache_path: Path) -> None:
    """Write a small offline API artifact so ``fetch --offline`` never hits the network.

    The bytes match the ``api`` JSON shape :meth:`StackOverflowTagsProvider.parse`
    expects; ``--offline`` replays the newest artifact in the provider's cache
    subdirectory (see ``providers.common.load_cached_payload``).
    """
    provider_dir = cache_path / "stackoverflow-tags"
    provider_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "source": "api",
        "denominator": "all_questions",
        "months": [
            {"month": "2020-01", "total": 1000, "tags": {"python": 250, "java": 200}},
            {"month": "2020-02", "total": 1100, "tags": {"python": 260, "java": 190}},
        ],
    }
    (provider_dir / "stackoverflow-tags-seed000000.json").write_bytes(
        json.dumps(document, sort_keys=True).encode("utf-8")
    )


def test_cli_fetch_all_offline_every_implemented_provider_succeeds(tmp_path: Path) -> None:
    db_path = tmp_path / "langrank.sqlite"
    cache_path = tmp_path / "cache"
    # stackoverflow-tags is the only implemented provider that performs a real
    # network fetch; its default 10-year window also overruns the 300/day anonymous
    # Stack Exchange budget. Pre-seed an offline cache artifact and run with
    # --offline so the whole pipeline (fetch->parse->normalize->validate->upsert)
    # stays offline. The bootstrap providers ignore --offline and read their bundled
    # CSVs, so CI never touches the network.
    #
    # github is registered (subtask 02.0/04) but its fetch is still a stub until
    # subtasks 05/07, so `fetch all` reports it FAILED with a clear
    # "lands in subtask" message and exits non-zero. Provider execution is
    # independent, so every implemented provider still reports SUCCESS. The offline
    # cache cannot be seeded for github yet because its parser is unimplemented; this
    # assertion flips back to all-SUCCESS once subtask 05 lands the offline replay.
    _seed_stackoverflow_tags_cache(cache_path)
    result = runner.invoke(
        app,
        ["--db", str(db_path), "--cache", str(cache_path), "fetch", "all", "--offline", "--years", "10"],
    )
    assert result.exit_code == 1, result.stdout
    assert "success tiobe" in result.stdout.lower()
    assert "success pypl" in result.stdout.lower()
    assert "success redmonk" in result.stdout.lower()
    assert "success stackoverflow-survey" in result.stdout.lower()
    assert "success stackoverflow-tags" in result.stdout.lower()
    # The github stub is the only failure and it names the subtask that lands it.
    assert "failed  github" in result.stdout.lower()
    assert "lands in subtask" in result.stdout.lower()
    # A clean offline replay of the implemented providers emits no validation errors.
    assert "[error]" not in result.stdout.lower()
