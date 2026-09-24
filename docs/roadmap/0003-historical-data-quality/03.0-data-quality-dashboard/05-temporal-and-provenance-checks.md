# Subtask 03.0/05 - Temporal & provenance checks

**Task:** [03.0 - Data Quality Dashboard](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Implement `latest_source_mismatch`, `stale_providers`, `methodology_boundary_crossings`,
`methodology_orphan_note`, `observation_before_introduction`.

## Baseline

- `StatusService.statuses()` → `ProviderStatus.provider_state`.
- `ValidationService.methodology_breaks()` ([Task 01.0/06](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/06-cli-and-plot-hook.md)).
- `observation_before_introduction` SQL ([Task 02.0/05](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/05-no-zero-fill-guarantee.md)).

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/db/repository.py`        | `quality_latest_by_metric()`, `quality_orphan_methodology_notes(declared)` |
| Modify | `src/langrank/services/quality.py`     | five `CHECKS` entries; `QualityContext` gains optional `status_service`, `declared_notes` |
| Create | `tests/unit/test_quality_temporal.py`  | tests |

## Symbols / fields

| Symbol                                        | Kind   | Type / signature                                                    | Default | Notes |
|-----------------------------------------------|--------|---------------------------------------------------------------------|---------|-------|
| `Database.quality_latest_by_metric`           | method | `(rating_id: str \| None) -> list[sqlite3.Row]` (`MAX(period_start)` per rating/metric) | - | |
| `Database.quality_orphan_methodology_notes`   | method | `(declared: Mapping[str, set[str]]) -> list[sqlite3.Row]`           | -       | rows whose version the provider no longer declares |
| `QualityContext.status_service`               | field  | `StatusService \| None`                                              | `None`  | check skipped (INFO `check_skipped`) when absent |
| `latest_source_mismatch`                      | check  | WARNING                                                             | -       | metrics of one rating disagree on latest period |
| `stale_providers`                             | check  | WARNING                                                             | -       | `provider_state == "stale"` |
| `methodology_boundary_crossings`              | check  | INFO                                                                | -       | one finding per break that falls strictly inside a stored series |
| `methodology_orphan_note`                     | check  | WARNING                                                             | -       | |
| `observation_before_introduction`             | check  | WARNING                                                             | -       | reuses Task 02.0/05 query |

## Behaviour & validators

1. `stale_providers` uses `StatusService` today; when [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates) lands, only the data source of `provider_state` changes — the check code and output stay stable. It never performs network calls.
2. If Task 01.0 or 02.0 columns are absent (feature not merged), the dependent check returns a single INFO `check_skipped` finding instead of failing.
3. `declared_notes` is built from `ProviderRegistry.all()` metadata by the CLI (subtask 06), not by the service reaching into providers.

## Tests

| Test function                                       | File                                  | Type        | Asserts |
|-----------------------------------------------------|---------------------------------------|-------------|---------|
| `test_latest_source_mismatch_flagged`               | `tests/unit/test_quality_temporal.py` | Integration | |
| `test_stale_provider_flagged_without_network`       | `tests/unit/test_quality_temporal.py` | Mock        | `httpx` patched to raise if called |
| `test_methodology_crossing_is_info`                 | `tests/unit/test_quality_temporal.py` | Integration | severity INFO |
| `test_orphan_methodology_note_flagged`              | `tests/unit/test_quality_temporal.py` | Integration | |
| `test_observation_before_introduction_flagged`      | `tests/unit/test_quality_temporal.py` | Integration | |
| `test_missing_status_service_yields_check_skipped`  | `tests/unit/test_quality_temporal.py` | Unit        | |

## Success criteria

- [ ] All six tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No network; read-only DB.

## Out of scope

- Real freshness probing (0004 Task 01.0).
