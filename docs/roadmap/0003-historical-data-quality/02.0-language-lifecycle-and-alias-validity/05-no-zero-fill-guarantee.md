# Subtask 02.0/05 - No-zero-fill guarantee & lifecycle validation

**Task:** [02.0 - Language Births, Renames & Alias Validity Ranges](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md) ·
**Role:** Testing Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Pin, with regression tests, that no query/export/plot path fabricates values before a
language's first observation, and add lifecycle validation queries.

## Baseline

- `Database.query_rows` returns stored rows only; `PlotService.plot` skips `None` values;
  `export_csv`/`export_json_*` serialize rows as given. None of this is tested for pre-birth gaps.

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Create | `tests/integration/test_no_zero_fill.py`     | Regression tests across query/export/plot |
| Modify | `src/langrank/db/repository.py`              | `validation_queries()` adds `observation_before_introduction`, `observation_after_retirement` |
| Modify | `src/langrank/services/validation.py`        | Map both to Severity.WARNING |
| Modify | `tests/unit/test_validation_service.py`      | Create if absent |

## Symbols / fields

| Symbol                                     | Kind       | Type / signature | Default | Notes |
|--------------------------------------------|------------|------------------|---------|-------|
| `observation_before_introduction`          | validation code | SQL: `observations.period_end < languages.introduced` | - | WARNING |
| `observation_after_retirement`             | validation code | SQL: `observations.period_start > languages.retired`  | - | WARNING |
| `ValidationService._SEVERITY_BY_CODE`      | const      | `dict[str, Severity]` | ERROR for unlisted codes | keeps existing codes ERROR |

## Behaviour & validators

1. Fixture: a language whose first observation is 2019 queried with `--years 10` returns zero rows before 2019 in query, CSV, JSON, and plot data.
2. `PlotService` receives no synthesized points (assert via mocked `ax.plot` x-values).
3. Validation warnings never block `langrank validate` without `--strict` semantics changing for existing ERROR codes.

## Tests

| Test function                                        | File                                     | Type        | Asserts |
|------------------------------------------------------|------------------------------------------|-------------|---------|
| `test_query_has_no_rows_before_first_observation`    | `tests/integration/test_no_zero_fill.py` | Integration | |
| `test_csv_export_has_no_rows_before_first_observation` | `tests/integration/test_no_zero_fill.py` | Integration | |
| `test_json_export_has_no_rows_before_first_observation` | `tests/integration/test_no_zero_fill.py` | Integration | |
| `test_plot_receives_no_synthetic_points`             | `tests/integration/test_no_zero_fill.py` | Mock        | patched `Axes.plot` |
| `test_observation_before_introduction_warns`         | `tests/unit/test_validation_service.py`  | Integration | WARNING code |
| `test_existing_validation_codes_remain_errors`       | `tests/unit/test_validation_service.py`  | Integration | e.g. `impossible_dates` ERROR |

## Success criteria

- [ ] All six tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No production code change to query/export/plot is expected; if a test fails, fix the path, never add fill logic.

## Out of scope

- Gap *detection* reporting (quality dashboard, [Task 03.0/03](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/03-structural-checks.md)).
