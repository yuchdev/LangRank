# Subtask 01.0/04 - Plain-`sqlite3` smoke tests for all five views

**Task:** [01.0 - Database Inspection Views](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/README.md) ·
**Role:** Testing Expert · **Depends on:** 01, 02, 03 · **Status:** ⬜ Not started

## Goal

Prove the plan's success criterion literally: each of the five views is queryable with no
LangRank code in the loop, both via Python's stdlib `sqlite3` on a raw connection and (when
available) via the `sqlite3` command-line shell.

## Baseline

- `tests/conftest.py` provides the `database` fixture (a migrated `Database` in `tmp_path`).
- The `demo` provider is offline and deterministic - suitable for populating the DB.

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Create | `tests/integration/test_inspection_views_sqlite.py` | Smoke tests below |

## Symbols / fields

| Symbol                 | Kind     | Type                | Default | Notes |
|------------------------|----------|---------------------|---------|-------|
| `INSPECTION_VIEWS`     | constant | `tuple[str, ...]`   | -       | `("latest_observations", "latest_language_ranks", "language_history", "rating_coverage", "provider_health")` |

## Behaviour & validators

1. The DB is populated once via `FetchService(database).fetch(DemoProvider(...), FetchRequest())`;
   afterwards the test opens a **fresh** `sqlite3.connect(db_path)` (no `Database` object) and runs
   `SELECT * FROM <view> LIMIT 5`.
2. CLI shell check uses `shutil.which("sqlite3")`; when absent the test is `pytest.skip`ped, never
   failed.
3. Each view must return ≥1 row for the demo dataset (empty view = regression).

## Tests

| Test function                                 | File                                               | Type        | Asserts |
|-----------------------------------------------|----------------------------------------------------|-------------|---------|
| `test_view_queryable_with_stdlib_sqlite3` (parametrized over `INSPECTION_VIEWS`) | `tests/integration/test_inspection_views_sqlite.py` | Integration | ≥1 row, no exception |
| `test_view_queryable_with_sqlite3_shell` (parametrized) | `tests/integration/test_inspection_views_sqlite.py` | E2E         | `subprocess.run(["sqlite3", db, "select * from <view> limit 5"])` exit 0, non-empty stdout |
| `test_all_inspection_views_exist`             | `tests/integration/test_inspection_views_sqlite.py` | Integration | `sqlite_master` where `type='view'` ⊇ `INSPECTION_VIEWS` |

## Success criteria

- [ ] All five views pass both checks locally (shell check may skip in CI).
- [ ] Tests use no network; the module sets `pytestmark = pytest.mark.integration`, matching
      `tests/integration/test_cli.py`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No production code changes in this subtask.

## Out of scope

- Performance of the views on large datasets (Milestone 0006 Task 03.0).
