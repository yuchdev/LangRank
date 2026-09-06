from __future__ import annotations

import sqlite3
from collections.abc import Sequence

SCHEMA_VERSION = 1

MIGRATIONS: Sequence[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ratings (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            description TEXT NOT NULL,
            homepage TEXT,
            default_metric TEXT NOT NULL,
            native_granularity TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS languages (
            id TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS language_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id TEXT NOT NULL DEFAULT '',
            source_name TEXT NOT NULL,
            source_name_norm TEXT NOT NULL,
            language_id TEXT NOT NULL,
            valid_from TEXT,
            valid_to TEXT,
            notes TEXT,
            UNIQUE(rating_id, source_name_norm),
            FOREIGN KEY(language_id) REFERENCES languages(id)
        );
        CREATE TABLE IF NOT EXISTS metrics (
            id TEXT PRIMARY KEY,
            rating_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            unit TEXT NOT NULL,
            higher_is_better INTEGER NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY(rating_id) REFERENCES ratings(id)
        );
        CREATE TABLE IF NOT EXISTS fetch_runs (
            id TEXT PRIMARY KEY,
            rating_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            records_seen INTEGER NOT NULL DEFAULT 0,
            records_inserted INTEGER NOT NULL DEFAULT 0,
            records_updated INTEGER NOT NULL DEFAULT 0,
            warnings TEXT,
            error TEXT,
            FOREIGN KEY(rating_id) REFERENCES ratings(id)
        );
        CREATE TABLE IF NOT EXISTS raw_artifacts (
            id TEXT PRIMARY KEY,
            rating_id TEXT NOT NULL,
            url TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            local_path TEXT NOT NULL,
            http_etag TEXT,
            http_last_modified TEXT,
            metadata_json TEXT NOT NULL,
            FOREIGN KEY(rating_id) REFERENCES ratings(id)
        );
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id TEXT NOT NULL,
            metric_id TEXT NOT NULL,
            language_id TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            period_label TEXT NOT NULL,
            granularity TEXT NOT NULL,
            rank INTEGER,
            value REAL,
            unit TEXT NOT NULL,
            sample_size INTEGER,
            population TEXT,
            source_language_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_document_id TEXT,
            is_derived INTEGER NOT NULL DEFAULT 0,
            derivation_method TEXT,
            retrieved_at TEXT NOT NULL,
            source_published_at TEXT,
            parser_version TEXT NOT NULL,
            raw_record_hash TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            fetch_run_id TEXT,
            UNIQUE(rating_id, metric_id, language_id, period_start, granularity),
            FOREIGN KEY(rating_id) REFERENCES ratings(id),
            FOREIGN KEY(metric_id) REFERENCES metrics(id),
            FOREIGN KEY(language_id) REFERENCES languages(id),
            FOREIGN KEY(fetch_run_id) REFERENCES fetch_runs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_observations_lookup
            ON observations(rating_id, metric_id, language_id, period_start);
        CREATE INDEX IF NOT EXISTS idx_observations_period
            ON observations(period_start, period_end);
        CREATE INDEX IF NOT EXISTS idx_fetch_runs_rating
            ON fetch_runs(rating_id, started_at);
        CREATE VIEW IF NOT EXISTS latest_observations AS
            SELECT o.*
            FROM observations o
            JOIN (
                SELECT rating_id, metric_id, language_id, MAX(period_start) AS max_period_start
                FROM observations
                GROUP BY rating_id, metric_id, language_id
            ) latest
              ON latest.rating_id = o.rating_id
             AND latest.metric_id = o.metric_id
             AND latest.language_id = o.language_id
             AND latest.max_period_start = o.period_start;
        CREATE VIEW IF NOT EXISTS language_history AS
            SELECT o.rating_id, o.metric_id, l.canonical_name AS language, o.period_start, o.period_end, o.value, o.rank, o.unit
            FROM observations o
            JOIN languages l ON l.id = o.language_id;
        CREATE VIEW IF NOT EXISTS rating_coverage AS
            SELECT rating_id,
                   MIN(period_start) AS earliest,
                   MAX(period_end) AS latest,
                   COUNT(*) AS points,
                   COUNT(DISTINCT language_id) AS languages
            FROM observations
            GROUP BY rating_id;
        """,
    ),
]


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);"
    )
    applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        with connection:
            connection.executescript(sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES(?, datetime('now'))",
                (version,),
            )
