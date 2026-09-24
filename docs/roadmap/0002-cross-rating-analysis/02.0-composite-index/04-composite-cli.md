# Subtask 02.0/04 - `langrank composite` CLI

**Task:** [02.0 - Composite Index](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Expose `CompositeService` as `langrank composite` with **no defaulted ingredients**, and output
formats that make the derived nature and the per-source contributions impossible to miss.

## Baseline

- `src/langrank/cli.py` (Typer, `console`, `_language_ids`, `_parse_date`).
- `src/langrank/exports/json_export.py:write_metadata_sidecar(output, filters, providers)`.
- `build_composite_spec`, `CompositeService` (subtasks 01, 03).

## Files

| Action | Path                                        | Purpose                     |
|--------|---------------------------------------------|-----------------------------|
| Modify | `src/langrank/cli.py`                       | `composite` command + renderers |
| Create | `tests/integration/test_cli_composite.py`   | CLI acceptance tests        |

## Symbols / fields

| Symbol                         | Kind     | Type / signature                                                  | Default   | Notes |
|--------------------------------|----------|-------------------------------------------------------------------|-----------|-------|
| `composite`                    | function | `@app.command()`                                                  | -         | |
| `--ratings`                    | option   | `str = typer.Option(...)`                                         | required  | |
| `--metric`                     | option   | `str = typer.Option(...)`                                         | required  | `rank` or `rating=metric,...` |
| `--normalize`                  | option   | `str = typer.Option(...)`                                         | required  | e.g. `rank-percentile` |
| `--weights`                    | option   | `str = typer.Option(...)`                                         | required  | `1,1,1,2,2` aligned with `--ratings` |
| `--missing`                    | option   | `str = typer.Option(...)`                                         | required  | `require-all` \| `renormalize-weights` \| `drop-language` |
| `--min-sources`                | option   | `int \| None`                                                     | `None`    | Required iff `renormalize-weights` (validated by spec) |
| `--languages` / `--top`        | options  | `str \| None` / `int \| None`                                     | `None`    | |
| `--since` / `--until` / `--years` | options | as `query`                                                      | `None`    | |
| `--rank-population` / `--common-top` | options | as `plot compare`                                          | `None`    | |
| `--explain`                    | option   | `bool`                                                            | `False`   | Adds per-contribution rows in table output |
| `--format`                     | option   | `str` in `{"table", "json", "csv"}`                               | `"table"` | |
| `--output`                     | option   | `Path \| None`                                                    | `None`    | |

## Behaviour & validators

1. Missing any required option → Typer usage error, exit code 2 (test asserts for each of the
   five). `AnalysisError` from `build_composite_spec` → exit 2 with its message (bad parameter,
   not runtime failure).
2. **Table:** first line (bold, before the table) `"DERIVED COMPOSITE - not a source rating"`,
   second line `spec.describe()` plus `"annual grid; latest observation in each year per
   source; missing=<policy>"`. Columns: `year, composite_rank, language, score,
   sources (k/m), label`; `label` column value `derived composite` on every row. `--explain` adds
   indented contribution rows: `rating, metric, source period, raw rank, normalized, weight,
   effective weight`. Gaps listed under the table (`language year: missing <ratings>
   (<reason>)`), then `dropped_languages`, then warnings.
3. **JSON:** `{"label": "derived composite", "spec": {...}, "grid": "year", "points": [...],
   "gaps": [...], "dropped_languages": [...], "warnings": [...]}`; each point includes its
   `contributions`.
4. **CSV:** one row per point with columns `label, year, composite_rank, language_id, score,
   sources_present, sources_total, derivation_method`, plus per rating
   `<rating>_normalized, <rating>_source_period, <rating>_effective_weight` (blank when not
   used). When `--output` is set, `write_metadata_sidecar` records the full spec, gaps, and
   warnings.
5. Never prints a score without the label in the same output unit (row/object).

## Tests

| Test function                                          | File                                       | Type | Asserts |
|--------------------------------------------------------|--------------------------------------------|------|---------|
| `test_cli_composite_missing_required_option_exits_2`   | `tests/integration/test_cli_composite.py`  | E2E  | Parametrized over the five required options |
| `test_cli_composite_plan_example_table`                | `tests/integration/test_cli_composite.py`  | E2E  | Exit 0; banner + `derived composite` on rows |
| `test_cli_composite_json_contributions`                | `tests/integration/test_cli_composite.py`  | E2E  | Every point has `label` and non-empty `contributions` |
| `test_cli_composite_csv_sidecar_has_spec`              | `tests/integration/test_cli_composite.py`  | E2E  | `.metadata.json` contains weights and policy |
| `test_cli_composite_renormalize_without_min_sources_exits_2` | `tests/integration/test_cli_composite.py` | E2E | |
| `test_cli_composite_invalid_weights_exits_2`           | `tests/integration/test_cli_composite.py`  | E2E  | `--weights 1,x` |

## Success criteria

- [ ] `langrank composite --ratings tiobe,pypl,redmonk,stackoverflow-survey --metric rank
      --normalize rank-percentile --weights 1,1,1,2 --missing require-all` runs on bundled data.
- [ ] Omitting any ingredient is a usage error.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- plan.md's example lists `github`; until Milestone 0001 Task 02.0 lands, tests use the four
  bootstrap ratings.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Saving composite specs as named presets.
