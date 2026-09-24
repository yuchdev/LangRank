# Subtask 03.0/02 - Seeded-anomaly fixture builder

**Task:** [03.0 - Data Quality Dashboard](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md) ·
**Role:** Testing Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

A deterministic fixture that builds a DB containing exactly one instance of each anomaly
class, plus a clean baseline, so every check has a positive and a negative test.

## Baseline

- `tests/conftest.py` provides `database` (empty migrated DB) and `app_paths`.
- Observations are inserted through `Database.upsert_observations(observations, fetch_run_id)`.

## Files

| Action | Path                                     | Purpose |
|--------|------------------------------------------|---------|
| Create | `tests/fixtures/quality/__init__.py`     | package |
| Create | `tests/fixtures/quality/builder.py`      | `AnomalyDatasetBuilder` |
| Modify | `tests/conftest.py`                      | `clean_quality_db`, `seeded_quality_db` fixtures |
| Create | `tests/unit/test_quality_fixture.py`     | Fixture self-tests |

## Symbols / fields

| Symbol                                   | Kind     | Type / signature                                           | Default | Notes |
|------------------------------------------|----------|------------------------------------------------------------|---------|-------|
| `AnomalyDatasetBuilder`                  | class    | `(database: Database)`                                     | -       | uses a synthetic `quality-test` rating registered via `upsert_provider_metadata` |
| `AnomalyDatasetBuilder.clean_baseline`   | method   | `() -> None` — 24 monthly periods × 5 languages, consistent ranks/shares | - | |
| `AnomalyDatasetBuilder.seed`             | method   | `(code: str) -> AnomalyLocation`                           | -       | one method branch per check code in the README catalog |
| `AnomalyLocation`                        | dataclass| frozen: `rating_id`, `metric_id`, `language_id`, `period_start` (all optional) | - | expected finding pointer |
| `ANOMALY_CODES`                          | const    | `tuple[str, ...]`                                          | -       | equals README catalog codes |
| `clean_quality_db` / `seeded_quality_db` | fixture  | `-> tuple[Database, dict[str, AnomalyLocation]]`           | -       | seeded = baseline + all codes |

## Behaviour & validators

1. Seeds: a missing month (`missing_periods`), a missing period for the whole rating (`source_gaps`), two languages sharing rank 3 (`duplicate_ranks`), an observation whose `source_language_name` has no alias row (`unmapped_source_names`), a 20-position rank jump (`abrupt_discontinuities`), shares summing to 130 % on an exclusive metric (`suspicious_percentages`), rank metric one month behind value metric (`latest_source_mismatch`), a stale status (`stale_providers`, via stub `upstream_latest_period`), a methodology note boundary inside the series (`methodology_boundary_crossings`), an undeclared note row (`methodology_orphan_note`), an observation before `languages.introduced` (`observation_before_introduction`).
2. Synthetic data is labelled `derivation_method="synthetic-test-fixture"`, `is_derived=True`.
3. Builder output is deterministic (fixed dates/`retrieved_at`).

## Tests

| Test function                                  | File                                 | Type        | Asserts |
|------------------------------------------------|--------------------------------------|-------------|---------|
| `test_builder_seeds_every_catalog_code`        | `tests/unit/test_quality_fixture.py` | Integration | `set(locations) == set(ANOMALY_CODES)` |
| `test_builder_is_deterministic`                | `tests/unit/test_quality_fixture.py` | Integration | two builds → identical `observations` dump |

## Success criteria

- [ ] Fixtures importable by subtasks 03-06 tests.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Tests only; no production code. No network.

## Out of scope

- Check implementations.
