from __future__ import annotations

import hashlib
import json
import sqlite3
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


def _seed_github_innovation_graph_cache(cache_path: Path) -> None:
    """Write an offline Innovation Graph CSV artifact plus its commit-sha sidecar.

    With this cache present, the whole ``github`` innovation-graph pipeline
    (fetch --offline, parse, normalize, validate) completes offline. The sidecar
    name embeds the CSV sha256 prefix and uses a non-cache extension so
    ``load_cached_payload`` returns the CSV, not the sidecar (see
    ``GitHubProvider._replay_innovation_graph_cache``).
    """
    provider_dir = cache_path / "github"
    provider_dir.mkdir(parents=True, exist_ok=True)
    csv_bytes = (
        "num_pushers,language,language_type,iso2_code,year,quarter\n"
        "1200,Python,programming,US,2020,1\n"
        "800,Rust,programming,GB,2020,1\n"
    ).encode("utf-8")
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
    commit_sha = "0123456789abcdef0123456789abcdef01234567"
    (provider_dir / f"github-{csv_sha256[:12]}.csv").write_bytes(csv_bytes)
    (provider_dir / f"github-{csv_sha256[:12]}.meta").write_text(
        json.dumps({"commit_sha": commit_sha, "csv_sha256": csv_sha256}, sort_keys=True),
        encoding="utf-8",
    )


def test_cli_fetch_all_offline_all_providers_succeed(tmp_path: Path) -> None:
    db_path = tmp_path / "langrank.sqlite"
    cache_path = tmp_path / "cache"
    # stackoverflow-tags is the only implemented provider that performs a real
    # network fetch; its default 10-year window also overruns the 300/day anonymous
    # Stack Exchange budget. Pre-seed an offline cache artifact and run with
    # --offline so the whole pipeline (fetch->parse->normalize->validate->upsert)
    # stays offline. The bootstrap providers ignore --offline and read their bundled
    # CSVs, so CI never touches the network.
    #
    # github's innovation-graph pipeline (fetch->parse->normalize->validate) now
    # completes offline (subtasks 05/06/08), so its cache is pre-seeded alongside
    # stackoverflow-tags; --source auto selects innovation-graph (octoverse needs
    # --source octoverse).
    #
    # ieee-spectrum reads its curated bundled CSV in fetch (subtask 03.0/04) and now
    # completes parse/normalize/validate offline (subtasks 05/06), so the whole
    # pipeline runs with zero network requests and reports SUCCESS like every other
    # provider.
    #
    # jetbrains now reads its curated published-percentages CSV in fetch and runs
    # parse/normalize offline (subtask 04.0/05), but validate is still a stub until
    # subtask 07, so the pipeline raises "jetbrains validate lands in subtask 07."
    # The run reports jetbrains FAILED with that "lands in subtask" message and exits
    # non-zero. Provider execution is independent, so every implemented provider still
    # reports SUCCESS; this assertion flips back to all-SUCCESS once subtask 07 lands
    # validation.
    _seed_stackoverflow_tags_cache(cache_path)
    _seed_github_innovation_graph_cache(cache_path)
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
    assert "success github" in result.stdout.lower()
    assert "success ieee-spectrum" in result.stdout.lower()
    # The jetbrains stub is the only failure and it names the subtask that lands it.
    assert "failed  jetbrains" in result.stdout.lower()
    assert "lands in subtask" in result.stdout.lower()
    # A clean offline replay of the implemented providers emits no validation errors.
    assert "[error]" not in result.stdout.lower()


def test_ieee_import_command_round_trip(tmp_path: Path) -> None:
    """``langrank import --rating ieee-spectrum`` loads a curated CSV end to end.

    This is the documented path for adding a future IEEE edition, so it must parse,
    normalize, validate and persist through the real CLI, and the stored rows must be
    queryable per profile without mixing profiles.
    """
    db_path = tmp_path / "langrank.sqlite"
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "ieee-spectrum" / "sample.csv"
    base = ["--db", str(db_path), "--cache", str(tmp_path / "cache")]

    imported = runner.invoke(app, [*base, "import", "--rating", "ieee-spectrum", str(fixture)])
    assert imported.exit_code == 0, imported.stdout
    assert "Imported ieee-spectrum" in imported.stdout
    assert "inserted=48" in imported.stdout

    query = runner.invoke(
        app,
        [*base, "query", "--rating", "ieee-spectrum", "--metric", "ieee-spectrum-jobs-rank", "--language", "python"],
    )
    assert query.exit_code == 0, query.stdout

    with sqlite3.connect(db_path) as connection:
        metrics = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT metric_id FROM observations WHERE rating_id = 'ieee-spectrum'"
            )
        }
        jobs_python = connection.execute(
            "SELECT period_label, rank, is_derived FROM observations "
            "WHERE metric_id = 'ieee-spectrum-jobs-rank' AND language_id = 'python' ORDER BY period_label"
        ).fetchall()
    assert metrics == {
        f"ieee-spectrum-{profile}-{kind}" for profile in ("spectrum", "jobs", "trending") for kind in ("rank", "score")
    }
    assert [(label, bool(derived)) for label, _rank, derived in jobs_python] == [("2022", True), ("2024", True)]
