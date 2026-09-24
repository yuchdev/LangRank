# Subtask 03.0/05 - `langrank report` command and acceptance test

**Task:** [03.0 - Multi-Chart Report Generation](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/README.md) ·
**Role:** Testing Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Expose the report as `langrank report` and pin the full directory contract with a
fixture-driven acceptance test.

## Baseline

- `cli.py` helpers `_language_ids`, `_parse_date`; `AppState` wiring.
- `tests/integration/test_cli.py` uses `CliRunner` with `--db/--cache` in `tmp_path`.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/cli.py`                  | `report` command |
| Create | `tests/integration/test_report_cli.py` | Acceptance tests |
| Modify | `README.md`                            | Usage example |

## Symbols / fields

| Symbol        | Kind        | Type / signature | Default | Notes |
|---------------|-------------|------------------|---------|-------|
| `report`      | CLI command | `--languages` (required), `--ratings`, `--years`, `--since`, `--until`, `--output` (required), `--force` | - | Thin wrapper over `ReportService.generate` |

## Behaviour & validators

1. Unknown language → same error/suggestions as `query` (reuse `_language_ids`).
2. Output-dir refusal surfaces as exit code 1 with the `LangRankError` message.
3. Prints the list of written files and skipped ratings.

## Tests

| Test function                                  | File                                   | Type        | Asserts |
|------------------------------------------------|----------------------------------------|-------------|---------|
| `test_report_cli_produces_self_contained_dir`  | `tests/integration/test_report_cli.py` | E2E         | After `fetch demo` + bundled fixtures, `report` writes `README.md`, `report.json`, `charts/*.png`, `data/*.csv`; all README links resolve |
| `test_report_cli_refuses_existing_dir`         | `tests/integration/test_report_cli.py` | Integration | Exit 1 without `--force` |
| `test_report_cli_unknown_language`             | `tests/integration/test_report_cli.py` | Integration | Exit ≠0, suggestions printed |

## Success criteria

- [ ] `langrank report --languages python,c++,rust --years 10 --output report/` works on a populated DB.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Module-level `pytestmark = pytest.mark.integration`, like `tests/integration/test_cli.py`; no network.

## Out of scope

- Scheduling/publishing reports (Milestone 0004).
