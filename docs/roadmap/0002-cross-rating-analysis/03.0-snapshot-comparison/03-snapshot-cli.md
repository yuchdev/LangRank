# Subtask 03.0/03 - `langrank snapshot` CLI

**Task:** [03.0 - Snapshot Comparison](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Render a `SnapshotTable` as a Rich table, JSON, or CSV, where blank cells are visibly blank and
every column's true observation date is printed.

## Baseline

- `src/langrank/cli.py` - Typer app, `rich` `Console`, `_render_rows`, `_language_ids`
  (alias resolution with PYPL `c-cpp` hint).
- `SnapshotService` (subtask 02), `parse_snapshot_target`, `parse_metric_map`.

## Files

| Action | Path                                         | Purpose                     |
|--------|----------------------------------------------|-----------------------------|
| Modify | `src/langrank/cli.py`                        | `snapshot` command + renderers |
| Create | `tests/integration/test_cli_snapshot.py`     | CLI acceptance tests        |

## Symbols / fields

| Symbol                       | Kind     | Type / signature                                                  | Default   | Notes |
|------------------------------|----------|-------------------------------------------------------------------|-----------|-------|
| `snapshot`                   | function | `@app.command()`                                                  | -         | |
| `WHEN`                       | argument | `str`                                                             | -         | `YYYY` or `latest` |
| `--ratings`                  | option   | `str \| None`                                                     | `None`    | Comma-separated |
| `--metric-map`               | option   | `str \| None`                                                     | `None`    | |
| `--languages`                | option   | `str \| None`                                                     | `None`    | Resolved via `_language_ids` |
| `--top`                      | option   | `int \| None`                                                     | `None`    | |
| `--sort-by`                  | option   | `str \| None`                                                     | `None`    | |
| `--format`                   | option   | `str` in `{"table", "json", "csv"}`                               | `"table"` | |
| `--output`                   | option   | `Path \| None`                                                    | `None`    | Writes to stdout when absent |
| `_snapshot_to_json`          | function | `(table: SnapshotTable) -> dict[str, Any]`                        | -         | |
| `_snapshot_to_csv_rows`      | function | `(table: SnapshotTable) -> list[dict[str, str]]`                  | -         | |

## Behaviour & validators

1. **Table:** column header `"<rating_id>\n<metric_id>\n<period_label or 'no data'>"`; cell =
   rank as text; blank → `"—"`; a cell from a row with `is_derived` → rank suffixed `"*"` with
   a footnote. `notes` printed below the table, then the rule line:
   `"Cells are stored observations at each column's reference period; blanks are not filled."`
2. **JSON:** `{"target": {...}, "columns": [{rating_id, metric_id, period_label, period_start,
   date_note}], "rows": [{language_id, display_name, cells: {rating_id: {rank, value,
   period_label, period_start, source_url, is_derived, derivation_method} | null}}],
   "notes": [...]}`.
3. **CSV:** one row per language; for each rating the columns `<rating>_rank`,
   `<rating>_period` (blank strings for blank cells - never `0`); notes are written to a
   `<output>.metadata.json` sidecar via `exports/json_export.py:write_metadata_sidecar` when
   `--output` is set.
4. `WHEN` invalid → exit 2 (`typer.BadParameter` wrapping `AnalysisError`).
5. Non-zero exit with message on `AnalysisError`; no traceback.

## Tests

| Test function                                        | File                                      | Type | Asserts |
|------------------------------------------------------|-------------------------------------------|------|---------|
| `test_cli_snapshot_year_table`                       | `tests/integration/test_cli_snapshot.py`  | E2E  | `snapshot 2020` exit 0; headers show `2020-` dates |
| `test_cli_snapshot_latest_prints_dates`              | `tests/integration/test_cli_snapshot.py`  | E2E  | `snapshot latest` output contains each column's `period_label` |
| `test_cli_snapshot_blank_cell_rendered_dash`         | `tests/integration/test_cli_snapshot.py`  | E2E  | `--languages c++ --ratings pypl,tiobe` → `—` in pypl cell |
| `test_cli_snapshot_json_null_cells`                  | `tests/integration/test_cli_snapshot.py`  | E2E  | JSON blank cell is `null`, non-blank has `period_start` |
| `test_cli_snapshot_csv_blank_not_zero`               | `tests/integration/test_cli_snapshot.py`  | E2E  | CSV blank cell is `""` |
| `test_cli_snapshot_invalid_when_exits_2`             | `tests/integration/test_cli_snapshot.py`  | E2E  | `snapshot 20x0` → exit 2 |

## Success criteria

- [ ] `langrank snapshot 2020` and `langrank snapshot latest` work in all three formats.
- [ ] Every non-blank cell's date is recoverable from every format; blanks are never `0`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Rendering only; selection logic stays in the service.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Plotting snapshots (a bar chart would reintroduce a shared axis).
