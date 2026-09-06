from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from langrank.cli import app

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
