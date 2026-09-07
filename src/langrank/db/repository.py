from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from difflib import get_close_matches
from pathlib import Path
from typing import Any
from uuid import uuid4

from langrank.db.migrations import migrate
from langrank.models import (
    FetchRunStatus,
    LanguageAlias,
    MethodologyNote,
    MetricDefinition,
    Observation,
    ProviderMetadata,
    QueryFilters,
    RawArtifact,
)
from langrank.normalization import LanguageNormalizer


@dataclass(frozen=True)
class QueryRow:
    rating_id: str
    metric_id: str
    language_id: str
    display_name: str
    period_start: str
    period_end: str
    period_label: str
    rank: int | None
    value: float | None
    unit: str
    source_url: str


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            migrate(connection)
            self.seed_languages(LanguageNormalizer())

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def schema_version(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(version) AS version FROM schema_migrations"
            ).fetchone()
        return int(row["version"] or 0)

    def seed_languages(self, normalizer: LanguageNormalizer) -> None:
        with self.connect() as connection, connection:
            for language in normalizer.languages():
                connection.execute(
                    """
                    INSERT INTO languages(id, canonical_name, display_name)
                    VALUES(?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        canonical_name = excluded.canonical_name,
                        display_name = excluded.display_name
                    """,
                    (language.id, language.canonical_name, language.display_name),
                )
            for alias in normalizer.aliases():
                connection.execute(
                    """
                    INSERT INTO language_aliases(rating_id, source_name, source_name_norm, language_id, valid_from, valid_to, notes)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(rating_id, source_name_norm) DO UPDATE SET
                        source_name = excluded.source_name,
                        language_id = excluded.language_id,
                        valid_from = excluded.valid_from,
                        valid_to = excluded.valid_to,
                        notes = excluded.notes
                    """,
                    (
                        alias.rating_id,
                        alias.source_name,
                        self._normalize_alias(alias.source_name),
                        alias.language_id,
                        alias.valid_from.isoformat() if alias.valid_from else None,
                        alias.valid_to.isoformat() if alias.valid_to else None,
                        alias.notes,
                    ),
                )

    @staticmethod
    def _normalize_alias(value: str) -> str:
        return "".join(char for char in value.lower().strip() if char.isalnum() or char in "+#/.")

    def upsert_provider_metadata(self, metadata: ProviderMetadata) -> None:
        with self.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO ratings(id, display_name, description, homepage, default_metric, native_granularity)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    display_name = excluded.display_name,
                    description = excluded.description,
                    homepage = excluded.homepage,
                    default_metric = excluded.default_metric,
                    native_granularity = excluded.native_granularity
                """,
                (
                    metadata.provider_id,
                    metadata.display_name,
                    metadata.description,
                    metadata.homepage,
                    metadata.default_metric,
                    metadata.native_granularity.value,
                ),
            )
            for metric in metadata.metrics:
                connection.execute(
                    """
                    INSERT INTO metrics(id, rating_id, display_name, unit, higher_is_better, description)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        rating_id = excluded.rating_id,
                        display_name = excluded.display_name,
                        unit = excluded.unit,
                        higher_is_better = excluded.higher_is_better,
                        description = excluded.description
                    """,
                    (
                        metric.id,
                        metric.rating_id,
                        metric.display_name,
                        metric.unit,
                        int(metric.higher_is_better),
                        metric.description,
                    ),
                )
            for note in metadata.methodology_notes:
                connection.execute(
                    """
                    INSERT INTO methodology_notes(rating_id, methodology_version, valid_from, valid_to, description, source_url)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(rating_id, methodology_version, valid_from, valid_to) DO UPDATE SET
                        description = excluded.description,
                        source_url = excluded.source_url
                    """,
                    (
                        note.rating_id,
                        note.methodology_version,
                        note.valid_from.isoformat() if note.valid_from else "",
                        note.valid_to.isoformat() if note.valid_to else "",
                        note.description,
                        note.source_url,
                    ),
                )

    def create_fetch_run(self, rating_id: str) -> str:
        fetch_run_id = str(uuid4())
        started_at = datetime.now(UTC).isoformat()
        with self.connect() as connection, connection:
            connection.execute(
                "INSERT INTO fetch_runs(id, rating_id, started_at, status) VALUES(?, ?, ?, ?)",
                (fetch_run_id, rating_id, started_at, FetchRunStatus.SUCCESS.value),
            )
        return fetch_run_id

    def finish_fetch_run(
        self,
        fetch_run_id: str,
        *,
        status: FetchRunStatus,
        records_seen: int,
        records_inserted: int,
        records_updated: int,
        warnings: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        with self.connect() as connection, connection:
            connection.execute(
                """
                UPDATE fetch_runs
                   SET completed_at = ?, status = ?, records_seen = ?, records_inserted = ?,
                       records_updated = ?, warnings = ?, error = ?
                 WHERE id = ?
                """,
                (
                    datetime.now(UTC).isoformat(),
                    status.value,
                    records_seen,
                    records_inserted,
                    records_updated,
                    json.dumps(warnings or []),
                    error,
                    fetch_run_id,
                ),
            )

    def record_raw_artifact(self, artifact: RawArtifact) -> None:
        with self.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO raw_artifacts(id, rating_id, url, retrieved_at, sha256, mime_type, local_path, http_etag, http_last_modified, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    artifact.id,
                    artifact.rating_id,
                    artifact.url,
                    artifact.retrieved_at.isoformat(),
                    artifact.sha256,
                    artifact.mime_type,
                    artifact.local_path,
                    artifact.http_etag,
                    artifact.http_last_modified,
                    json.dumps(artifact.metadata_json, sort_keys=True),
                ),
            )

    def upsert_observations(
        self, observations: list[Observation], fetch_run_id: str
    ) -> tuple[int, int]:
        inserted = 0
        updated = 0
        with self.connect() as connection, connection:
            for observation in observations:
                existing = connection.execute(
                    """
                    SELECT id, raw_record_hash
                    FROM observations
                    WHERE rating_id = ? AND metric_id = ? AND language_id = ? AND period_start = ? AND granularity = ?
                    """,
                    (
                        observation.rating_id,
                        observation.metric_id,
                        observation.language_id,
                        observation.period_start.isoformat(),
                        observation.granularity.value,
                    ),
                ).fetchone()
                if existing is None:
                    inserted += 1
                elif existing["raw_record_hash"] != observation.raw_record_hash:
                    updated += 1
                connection.execute(
                    """
                    INSERT INTO observations(
                        rating_id, metric_id, language_id, period_start, period_end, period_label, granularity,
                        rank, value, unit, sample_size, population, source_language_name, source_url,
                        source_document_id, is_derived, derivation_method, retrieved_at, source_published_at,
                        parser_version, raw_record_hash, metadata_json, fetch_run_id
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(rating_id, metric_id, language_id, period_start, granularity) DO UPDATE SET
                        period_end = excluded.period_end,
                        period_label = excluded.period_label,
                        rank = excluded.rank,
                        value = excluded.value,
                        unit = excluded.unit,
                        sample_size = excluded.sample_size,
                        population = excluded.population,
                        source_language_name = excluded.source_language_name,
                        source_url = excluded.source_url,
                        source_document_id = excluded.source_document_id,
                        is_derived = excluded.is_derived,
                        derivation_method = excluded.derivation_method,
                        retrieved_at = excluded.retrieved_at,
                        source_published_at = excluded.source_published_at,
                        parser_version = excluded.parser_version,
                        raw_record_hash = excluded.raw_record_hash,
                        metadata_json = excluded.metadata_json,
                        fetch_run_id = excluded.fetch_run_id
                    """,
                    (
                        observation.rating_id,
                        observation.metric_id,
                        observation.language_id,
                        observation.period_start.isoformat(),
                        observation.period_end.isoformat(),
                        observation.period_label,
                        observation.granularity.value,
                        observation.rank,
                        observation.value,
                        observation.unit,
                        observation.sample_size,
                        observation.population,
                        observation.source_language_name,
                        observation.source_url,
                        observation.source_document_id,
                        int(observation.is_derived),
                        observation.derivation_method,
                        observation.retrieved_at.isoformat(),
                        observation.source_published_at.isoformat()
                        if observation.source_published_at
                        else None,
                        observation.parser_version,
                        observation.raw_record_hash,
                        json.dumps(observation.metadata_json, sort_keys=True),
                        fetch_run_id,
                    ),
                )
        return inserted, updated

    def query_rows(self, filters: QueryFilters) -> list[QueryRow]:
        sql = """
        SELECT o.rating_id, o.metric_id, o.language_id, l.display_name, o.period_start, o.period_end,
               o.period_label, o.rank, o.value, o.unit, o.source_url
          FROM observations o
          JOIN languages l ON l.id = o.language_id
         WHERE 1=1
        """
        params: list[Any] = []
        if filters.rating_id:
            sql += " AND o.rating_id = ?"
            params.append(filters.rating_id)
        if filters.metric_id:
            sql += " AND o.metric_id = ?"
            params.append(filters.metric_id)
        if filters.since:
            sql += " AND o.period_start >= ?"
            params.append(filters.since.isoformat())
        if filters.until:
            sql += " AND o.period_end <= ?"
            params.append(filters.until.isoformat())
        if filters.language_ids:
            placeholders = ",".join("?" for _ in filters.language_ids)
            sql += f" AND o.language_id IN ({placeholders})"
            params.extend(filters.language_ids)
        sql += " ORDER BY o.period_start, o.language_id, o.metric_id"
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [QueryRow(**dict(row)) for row in rows]

    def list_ratings(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute("SELECT * FROM ratings ORDER BY id").fetchall()

    def get_rating(self, rating_id: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM ratings WHERE id = ?",
                (rating_id,),
            ).fetchone()

    def list_metrics(self, rating_id: str) -> list[MetricDefinition]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM metrics WHERE rating_id = ? ORDER BY id",
                (rating_id,),
            ).fetchall()
        return [
            MetricDefinition(
                id=row["id"],
                rating_id=row["rating_id"],
                display_name=row["display_name"],
                unit=row["unit"],
                higher_is_better=bool(row["higher_is_better"]),
                description=row["description"],
            )
            for row in rows
        ]

    def list_methodology_notes(self, rating_id: str) -> list[MethodologyNote]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT rating_id, methodology_version, valid_from, valid_to, description, source_url
                FROM methodology_notes
                WHERE rating_id = ?
                ORDER BY valid_from, methodology_version
                """,
                (rating_id,),
            ).fetchall()
        return [
            MethodologyNote(
                rating_id=row["rating_id"],
                methodology_version=row["methodology_version"],
                valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
                valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
                description=row["description"],
                source_url=row["source_url"],
            )
            for row in rows
        ]

    def list_languages(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute("SELECT * FROM languages ORDER BY canonical_name").fetchall()

    def find_language(self, canonical_name: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM languages WHERE canonical_name = ?",
                (canonical_name,),
            ).fetchone()

    def list_aliases(self, rating_id: str | None = None) -> list[LanguageAlias]:
        sql = "SELECT rating_id, source_name, language_id, valid_from, valid_to, notes FROM language_aliases"
        params: list[Any] = []
        if rating_id is not None:
            sql += " WHERE rating_id IN ('', ?)"
            params.append(rating_id)
        sql += " ORDER BY source_name"
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [
            LanguageAlias(
                rating_id=row["rating_id"],
                source_name=row["source_name"],
                language_id=row["language_id"],
                valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
                valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
                notes=row["notes"],
            )
            for row in rows
        ]

    def alias_to_language(self, source_name: str, rating_id: str | None = None) -> str | None:
        normalized = self._normalize_alias(source_name)
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT language_id
                FROM language_aliases
                WHERE source_name_norm = ? AND rating_id IN ('', COALESCE(?, ''))
                ORDER BY CASE WHEN rating_id = '' THEN 1 ELSE 0 END
                LIMIT 1
                """,
                (normalized, rating_id),
            ).fetchone()
        return None if row is None else str(row["language_id"])

    def language_suggestions(self, source_name: str) -> list[str]:
        choices = [row["canonical_name"] for row in self.list_languages()]
        return get_close_matches(source_name.lower(), choices, n=3)

    def coverage(self, language_id: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT rating_id, earliest, latest, points, languages FROM rating_coverage"
        params: list[Any] = []
        if language_id:
            sql = """
            SELECT rating_id, MIN(period_start) AS earliest, MAX(period_end) AS latest,
                   COUNT(*) AS points, COUNT(DISTINCT language_id) AS languages
              FROM observations
             WHERE language_id = ?
             GROUP BY rating_id
            """
            params.append(language_id)
        sql += " ORDER BY rating_id"
        with self.connect() as connection:
            return connection.execute(sql, params).fetchall()

    def latest_observation_for_provider(self, rating_id: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(period_start) AS latest FROM observations WHERE rating_id = ?",
                (rating_id,),
            ).fetchone()
        return None if row is None else row["latest"]

    def last_fetch_run(self, rating_id: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM fetch_runs WHERE rating_id = ? ORDER BY started_at DESC LIMIT 1",
                (rating_id,),
            ).fetchone()

    def last_failed_fetch_run(self, rating_id: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM fetch_runs
                WHERE rating_id = ? AND status = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (rating_id, FetchRunStatus.FAILED.value),
            ).fetchone()

    def count_observations(self, rating_id: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM observations WHERE rating_id = ?",
                (rating_id,),
            ).fetchone()
        return int(row["count"])

    def provider_versions(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT rating_id, MAX(parser_version) AS parser_version FROM observations GROUP BY rating_id ORDER BY rating_id"
            ).fetchall()

    def validation_queries(self) -> dict[str, list[sqlite3.Row]]:
        with self.connect() as connection:
            return {
                "duplicate_observation_keys": connection.execute(
                    """
                    SELECT rating_id, metric_id, language_id, period_start, granularity, COUNT(*) AS duplicates
                    FROM observations
                    GROUP BY rating_id, metric_id, language_id, period_start, granularity
                    HAVING COUNT(*) > 1
                    """
                ).fetchall(),
                "invalid_ranks": connection.execute(
                    "SELECT rating_id, language_id, period_start, rank FROM observations WHERE metric_id = 'rank' AND rank <= 0"
                ).fetchall(),
                "impossible_dates": connection.execute(
                    "SELECT rating_id, language_id, period_start, period_end FROM observations WHERE period_end < period_start"
                ).fetchall(),
                "duplicate_aliases": connection.execute(
                    "SELECT rating_id, source_name_norm, COUNT(*) AS duplicates FROM language_aliases GROUP BY rating_id, source_name_norm HAVING COUNT(*) > 1"
                ).fetchall(),
                "unknown_languages": connection.execute(
                    "SELECT DISTINCT o.language_id FROM observations o LEFT JOIN languages l ON l.id = o.language_id WHERE l.id IS NULL"
                ).fetchall(),
                "malformed_units": connection.execute(
                    "SELECT DISTINCT metric_id, unit FROM observations WHERE TRIM(unit) = ''"
                ).fetchall(),
                "missing_provider_metadata": connection.execute(
                    "SELECT id FROM ratings WHERE TRIM(display_name) = '' OR TRIM(default_metric) = '' OR TRIM(native_granularity) = ''"
                ).fetchall(),
                "percentage_range": connection.execute(
                    "SELECT rating_id, language_id, period_start, value FROM observations WHERE unit = 'percent' AND (value < 0 OR value > 100)"
                ).fetchall(),
            }

    def resolve_year_bounds(self, rating_id: str | None = None) -> tuple[int | None, int | None]:
        sql = "SELECT MIN(period_start) AS earliest, MAX(period_start) AS latest FROM observations"
        params: list[Any] = []
        if rating_id:
            sql += " WHERE rating_id = ?"
            params.append(rating_id)
        with self.connect() as connection:
            row = connection.execute(sql, params).fetchone()
        earliest = row["earliest"]
        latest = row["latest"]
        return (
            int(str(earliest)[:4]) if earliest else None,
            int(str(latest)[:4]) if latest else None,
        )
