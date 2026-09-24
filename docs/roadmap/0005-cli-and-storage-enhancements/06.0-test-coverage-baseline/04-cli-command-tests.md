# Subtask 06.0/04 - CLI command tests

**Task:** [06.0 - Test Coverage Baseline](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/README.md) ·
**Role:** Testing Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Exercise every Typer command in `src/langrank/cli.py` (43.8% today) end to end through
`typer.testing.CliRunner`, against a temp DB populated by `fetch demo` and `fetch tiobe`.

## Baseline

- `tests/integration/test_cli.py` has 3 tests; uncovered: `ratings list/show`,
  `languages list/show/aliases`, `import`, `export csv/json`, `plot`, `validate`, `coverage`,
  `status`, `main()` error handling.
- Config precedence: `--db`/`--cache` flags or `LANGRANK_DB`/`LANGRANK_CACHE` env vars.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tests/integration/test_cli_commands.py` | Tests below |
| Modify | `tests/conftest.py` | `cli_env` fixture: tmp DB/cache env vars + pre-fetched `demo`/`tiobe` |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `cli_env` | pytest fixture | `(tmp_path, monkeypatch) -> dict[str, str]` | - | Sets `LANGRANK_DB`, `LANGRANK_CACHE` |

## Behaviour & validators

1. Each command exits 0 on the happy path and prints its key content (provider IDs, language names, row counts).
2. Unknown provider / unknown language exit non-zero with a `LangRankError` message, never a traceback.
3. `export csv` / `export json` write files whose row count equals `query` output.
4. `plot --output x.png` writes a non-empty PNG.
5. `import --rating tiobe tests/fixtures/tiobe/sample.csv --dry-run` writes no observations.
6. Known defect pinned: `plot --rating tiobe --metric tiobe-rank` does not invert the y-axis
   → `xfail(strict=True)` referencing 0006/01.0/02.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ratings_list_and_show` | `tests/integration/test_cli_commands.py` | E2E | rule 1 |
| `test_languages_list_show_aliases` | `tests/integration/test_cli_commands.py` | E2E | rule 1 |
| `test_unknown_provider_and_language_exit_nonzero` | `tests/integration/test_cli_commands.py` | E2E | rule 2 |
| `test_export_csv_and_json_row_counts` | `tests/integration/test_cli_commands.py` | E2E | rule 3 |
| `test_plot_writes_png` | `tests/integration/test_cli_commands.py` | E2E | rule 4 |
| `test_import_dry_run_writes_nothing` | `tests/integration/test_cli_commands.py` | E2E | rule 5 |
| `test_validate_coverage_status_commands` | `tests/integration/test_cli_commands.py` | E2E | rule 1 |
| `test_plot_prefixed_rank_metric_inverts_axis` | `tests/integration/test_cli_commands.py` | E2E | rule 6 (strict xfail) |

## Success criteria

- [ ] `src/langrank/cli.py` ≥ 80%.
- [ ] No test calls `plt.show()` (every `plot` test passes `--output`).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No `src/` changes; defects are pinned, not fixed.

## Out of scope

- New CLI flags from Tasks 02.0-05.0.
