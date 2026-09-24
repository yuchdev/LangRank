# Subtask 01.0/01 - Metric Kind Metadata

**Task:** [01.0 - Provider Capabilities Metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Every metric declares *what kind of number it is* (`MetricKind`), the kind is persisted in
the `metrics` table, and existing databases are backfilled by an append-only migration. This
is the data half of the metric-role fix; subtask 02 switches the consumers over.

## Baseline

- `src/langrank/models.py:MetricDefinition` has no kind field.
- `src/langrank/db/migrations.py`: `SCHEMA_VERSION = 2`, `MIGRATIONS` has versions 1-2;
  `metrics` table columns: `id, rating_id, display_name, unit, higher_is_better, description`.
- `src/langrank/db/repository.py:Database.upsert_provider_metadata` and `Database.list_metrics`
  read/write those six columns only.
- Metric declarations live in each provider's `metadata()`: `demo.py` (`rank`, `rating`),
  `tiobe.py` (`tiobe-rank`, `tiobe-rating`), `pypl.py` (`pypl-rank`, `pypl-share`),
  `redmonk.py` (`redmonk-rank`), `stackoverflow_survey.py` (`worked_with_percent`,
  `stackoverflow-survey-rank`).

## Files

| Action | Path                                         | Purpose                                                   |
|--------|----------------------------------------------|-----------------------------------------------------------|
| Modify | `src/langrank/models.py`                     | Add `MetricKind` StrEnum; add `kind` to `MetricDefinition` |
| Modify | `src/langrank/db/migrations.py`              | Append migration adding `metrics.kind` + backfill; bump `SCHEMA_VERSION` |
| Modify | `src/langrank/db/repository.py`              | Write/read `kind` in `upsert_provider_metadata`/`list_metrics`; add `metric_ids_by_kind` |
| Modify | `src/langrank/providers/demo.py`             | Declare `kind` on each metric                              |
| Modify | `src/langrank/providers/tiobe.py`            | Declare `kind`                                            |
| Modify | `src/langrank/providers/pypl.py`             | Declare `kind`                                            |
| Modify | `src/langrank/providers/redmonk.py`          | Declare `kind`                                            |
| Modify | `src/langrank/providers/stackoverflow_survey.py` | Declare `kind`                                        |
| Create | `tests/unit/test_metric_kind.py`             | Model, migration backfill, repository round-trip tests    |

## Symbols / fields

| Symbol                               | Kind      | Type / signature                                               | Default | Notes |
|--------------------------------------|-----------|----------------------------------------------------------------|---------|-------|
| `MetricKind`                         | StrEnum   | members `RANK="rank"`, `SHARE="share"`, `SCORE="score"`, `COUNT="count"`, `PERCENT="percent"` | - | In `models.py` next to `Granularity` |
| `MetricDefinition.kind`              | field     | `MetricKind`                                                   | none (required) | Appended as the last field; `MetricDefinition` has no defaulted fields, so a required field is legal |
| `metrics.kind`                       | column    | `TEXT NOT NULL DEFAULT 'score'`                                | `'score'` | Added by new migration |
| `SCHEMA_VERSION`                     | constant  | `int`                                                          | next free version (3 at time of writing) | Must equal the highest `MIGRATIONS` version |
| `Database.metric_ids_by_kind`        | method    | `(kind: MetricKind, rating_id: str \| None = None) -> set[str]` | -       | Used by subtask 02 |

Provider declarations:

| Metric ID                   | `kind`    |
|-----------------------------|-----------|
| `rank` (demo)               | `RANK`    |
| `rating` (demo)             | `PERCENT` |
| `tiobe-rank`                | `RANK`    |
| `tiobe-rating`              | `PERCENT` |
| `pypl-rank`                 | `RANK`    |
| `pypl-share`                | `SHARE`   |
| `redmonk-rank`              | `RANK`    |
| `stackoverflow-survey-rank` | `RANK`    |
| `worked_with_percent`       | `PERCENT` |

## Behaviour & validators

1. The migration is a **new** tuple appended to `MIGRATIONS` with the next integer version;
   versions 1 and 2 are not edited (append-only rule, [CLAUDE.md](/CLAUDE.md)).
2. Migration SQL: `ALTER TABLE metrics ADD COLUMN kind TEXT NOT NULL DEFAULT 'score';` then
   backfill: `unit = 'rank'` → `'rank'`; `unit = 'percent'` → `'percent'`;
   `unit IN ('share', 'fraction')` → `'share'`; `unit = 'count'` → `'count'`; else stays `'score'`.
3. `upsert_provider_metadata` writes `metric.kind.value` and its `ON CONFLICT` updates `kind`,
   so a provider declaration always overrides the backfill.
4. `list_metrics` returns `MetricDefinition(kind=MetricKind(row["kind"]))`; an unknown stored
   value raises `StorageError` (not a bare `ValueError`).
5. A `RANK` metric must have `higher_is_better=False`; a provider `validate()` is not the place
   for this - it is asserted by the contract test in
   [subtask 06](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/06-capabilities-contract-test.md).

## Tests

| Test function                                     | File                              | Type        | Asserts |
|---------------------------------------------------|-----------------------------------|-------------|---------|
| `test_metric_kind_values_are_stable_strings`      | `tests/unit/test_metric_kind.py`  | Unit        | Enum string values exactly as table above |
| `test_migration_backfills_kind_from_unit`         | `tests/unit/test_metric_kind.py`  | Integration | Build a v2 DB by applying `MIGRATIONS[:2]`, insert metrics with units `rank`/`percent`/`share`/`other`, run `migrate()`, check `kind` per backfill rule |
| `test_upsert_metadata_overrides_backfilled_kind`  | `tests/unit/test_metric_kind.py`  | Integration | Backfilled `'score'` replaced by provider-declared kind after `upsert_provider_metadata` |
| `test_list_metrics_round_trips_kind`              | `tests/unit/test_metric_kind.py`  | Integration | `list_metrics("pypl")` returns `SHARE` for `pypl-share` |
| `test_metric_ids_by_kind_filters_by_rating`       | `tests/unit/test_metric_kind.py`  | Integration | `metric_ids_by_kind(RANK)` after upserting all providers == the five rank IDs; with `rating_id="tiobe"` == `{"tiobe-rank"}` |
| `test_schema_version_matches_last_migration`      | `tests/unit/test_metric_kind.py`  | Unit        | `SCHEMA_VERSION == max(v for v, _ in MIGRATIONS)` |

## Success criteria

- [ ] `MetricKind` exists and every `MetricDefinition` in `src/langrank/providers/*.py` sets `kind`.
- [ ] Fresh DB and upgraded v2 DB both have `metrics.kind`; `langrank doctor` shows matching schema/expected versions.
- [ ] `grep -n "kind" src/langrank/db/repository.py` shows it in both upsert and list paths.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Append-only migrations; no data loss on upgrade (the column is additive).
- Frozen dataclasses stay frozen; `kind` is required (no silent default in the model - the DB
  default exists only to make the `ALTER TABLE` legal).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Changing query/validation/plot behaviour - [subtask 02](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/02-metric-role-lookups.md).
- Renaming metric IDs (IDs stay provider-prefixed; roles, not names, carry meaning).
