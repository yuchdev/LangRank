# Subtask 03.0/06 - `langrank quality` command

**Task:** [03.0 - Data Quality Dashboard](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md) ·
**Role:** Python Expert · **Depends on:** 03, 04, 05 · **Status:** ⬜ Not started

## Goal

Expose the quality report on the CLI as a table or JSON, with filtering and a strict mode,
and prove the command never modifies the DB.

## Baseline

- `cli.py:validate` is the closest analogue (prints issues, `--strict` exits 1).
- `AppState` provides `database` and `providers`.

## Files

| Action | Path                                      | Purpose |
|--------|-------------------------------------------|---------|
| Modify | `src/langrank/cli.py`                     | `quality` command + `_render_quality_report` |
| Create | `tests/integration/test_quality_cli.py`   | E2E tests |

## Symbols / fields

| Symbol      | Kind | Type / signature                                                                                                             | Default | Notes |
|-------------|------|------------------------------------------------------------------------------------------------------------------------------|---------|-------|
| `quality`   | CLI  | `langrank quality [--rating ID] [--check CODE]... [--min-severity info\|warning\|error] [--format table\|json] [--threshold KEY=VALUE]... [--strict] [--list-checks]` | `--format table`, `--min-severity info` | |

## Behaviour & validators

1. Table: one summary table (code, severity, count) then a findings table (severity, code, rating, metric, language, period, message).
2. JSON: `{"schema_version": 1, "generated_at": ISO, "db_path": str, "summary": {code: count}, "findings": [QualityFinding.to_dict...]}`; dates ISO.
3. Exit codes: 0 normally; with `--strict`, 1 if any WARNING/ERROR finding; 2 for usage errors (unknown check, bad threshold).
4. `--list-checks` prints the registry (code, severity, description) and exits 0.
5. The command builds `declared_notes` from `state.providers.all()` metadata and passes a `StatusService`.

## Tests

| Test function                                  | File                                    | Type | Asserts |
|------------------------------------------------|-----------------------------------------|------|---------|
| `test_quality_json_reports_every_seeded_code`  | `tests/integration/test_quality_cli.py` | E2E  | summary keys ⊇ `ANOMALY_CODES` |
| `test_quality_strict_exit_code`                | `tests/integration/test_quality_cli.py` | E2E  | 1 on seeded, 0 on clean |
| `test_quality_check_filter`                    | `tests/integration/test_quality_cli.py` | E2E  | only selected code |
| `test_quality_unknown_check_exit_2`            | `tests/integration/test_quality_cli.py` | E2E  | |
| `test_quality_list_checks`                     | `tests/integration/test_quality_cli.py` | E2E  | lists all registry codes |
| `test_quality_does_not_modify_database`        | `tests/integration/test_quality_cli.py` | E2E  | sha256 of DB file identical before/after |

## Success criteria

- [ ] `langrank quality --format json` on the seeded fixture reports all anomaly classes (milestone exit criterion).
- [ ] DB byte-identical after a run.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Rendering only in `cli.py`; logic in `QualityService`. Errors via `LangRankError` subclasses.

## Out of scope

- HTML dashboard output; including quality results in releases (0004 Task 02.0 may consume the JSON).
