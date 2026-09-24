# Subtask 03.0/02 - Raw-Artifact Retention Migration & Queries

**Task:** [03.0 - Source Archival Strategy](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Record retention state per artifact row and add the `Database` methods the planner and
service need.

## Baseline

- `raw_artifacts(id, rating_id, url, retrieved_at, sha256, mime_type, local_path,
  http_etag, http_last_modified, metadata_json)`; written by `Database.record_raw_artifact`.
- `db/migrations.py:MIGRATIONS` is append-only; `SCHEMA_VERSION = 2` today.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/db/migrations.py` | Next-version migration; bump `SCHEMA_VERSION` |
| Modify | `src/langrank/db/repository.py` | Methods below; `record_raw_artifact` writes `size_bytes` |
| Modify | `src/langrank/models.py` | `ArtifactRecord` dataclass |
| Create | `tests/unit/test_raw_artifact_retention_schema.py` | Migration + query tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `raw_artifacts.retention_state` | column | `TEXT NOT NULL` | `'retained'` | `'retained'` \| `'pruned'` \| `'missing'` |
| `raw_artifacts.pruned_at` | column | `TEXT` | `NULL` | ISO UTC |
| `raw_artifacts.size_bytes` | column | `INTEGER` | `NULL` | Filled on insert; back-filled lazily by `cache status` |
| `idx_raw_artifacts_rating_time` | index | `(rating_id, retrieved_at)` | - | |
| `ArtifactRecord` | frozen dataclass | `id`, `rating_id`, `url`, `retrieved_at: datetime`, `sha256`, `local_path`, `size_bytes: int \| None`, `retention_state: str`, `edition: str \| None` | - | `edition` from `metadata_json["edition"]` or `["period"]` if present |
| `Database.list_artifacts` | method | `(rating_id: str \| None = None, *, state: str \| None = "retained") -> list[ArtifactRecord]` | - | ordered `rating_id, retrieved_at, id` |
| `Database.mark_artifacts` | method | `(ids: Sequence[str], *, state: str, at: datetime) -> int` | - | single transaction |
| `Database.retained_paths` | method | `() -> set[str]` | - | `local_path` of all `retained` rows |

## Behaviour & validators

1. Migration uses `ALTER TABLE raw_artifacts ADD COLUMN ...` (SQLite-safe), plus the
   index, as one new `(version, sql)` tuple - never editing an existing tuple.
2. Existing rows migrate to `retention_state='retained'`.
3. `mark_artifacts` rejects states outside the three allowed values (`StorageError`).

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_migration_adds_retention_columns` | `tests/unit/test_raw_artifact_retention_schema.py` | Integration | `PRAGMA table_info` shows columns; `schema_version()` bumped |
| `test_migration_preserves_existing_artifacts_as_retained` | same | Integration | v2 DB with rows → migrated rows `retained` |
| `test_record_raw_artifact_sets_size_bytes` | same | Integration | |
| `test_mark_artifacts_is_transactional_and_validates_state` | same | Integration | bad state → `StorageError`, no rows changed |
| `test_retained_paths_excludes_pruned` | same | Integration | |

## Success criteria

- [ ] Append-only migration convention respected ([CLAUDE.md](/CLAUDE.md)).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Coordinate the migration number with in-flight 0003/0005 migrations at merge time.

## Out of scope

- Deciding what to prune - [03](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/03-retention-planner.md).
