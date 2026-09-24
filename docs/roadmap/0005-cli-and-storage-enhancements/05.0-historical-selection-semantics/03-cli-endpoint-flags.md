# Subtask 05.0/03 - Uniform CLI flags across query/export/plot

**Task:** [05.0 - Historical Selection Semantics](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Every command that accepts `--years` resolves it through `QueryService` with the same help text,
the same `--endpoint` option, and records the resolved windows in its metadata sidecar.

## Baseline

- `query`, `export csv`, `export json`, `plot` each declare `--since/--until/--years` separately;
  export commands duplicate the per-provider loop; `write_metadata_sidecar(output, filters, versions)`
  writes the unresolved filters of the **last** provider only.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/cli.py`                  | Shared option definitions + `--endpoint`; exports use `QueryService.query_many` |
| Modify | `src/langrank/exports/json_export.py`  | Sidecar accepts `windows: Mapping[str, SelectionWindow]` |
| Modify | `tests/integration/test_cli.py`        | Tests below |

## Symbols / fields

| Symbol                     | Kind     | Type / signature | Default | Notes |
|----------------------------|----------|------------------|---------|-------|
| `YEARS_HELP`               | constant | `str`            | -       | Normative rule text, reused by all four commands |
| `--endpoint`               | CLI option | `EndpointPolicy` (`per-source`/`global`) | `per-source` | On `export csv|json`; `query`/`plot` single-rating accept it but it is a no-op, documented |
| `write_metadata_sidecar`   | function | `(output: Path, filters: dict[str, Any], parser_versions: dict[str, str], windows: Mapping[str, SelectionWindow] \| None = None) -> None` | - | Adds `"selection"` key |

## Behaviour & validators

1. `--help` for `query`, `export csv`, `export json`, `plot` contains `YEARS_HELP` verbatim.
2. `--since` with `--years` → exit 2 with the mutual-exclusion message.
3. Sidecar `selection` lists each rating's `since`, `until`, `endpoint`, `policy`.
4. Export no longer overwrites `sidecar_filters` in a loop; it records all ratings.

## Tests

| Test function                                    | File                            | Type        | Asserts |
|--------------------------------------------------|---------------------------------|-------------|---------|
| `test_years_help_text_identical_across_commands` | `tests/integration/test_cli.py` | Integration | `YEARS_HELP` in each command's `--help` |
| `test_since_and_years_rejected_cli`              | `tests/integration/test_cli.py` | Integration | Exit 2 |
| `test_export_sidecar_records_windows_per_rating` | `tests/integration/test_cli.py` | Integration | Sidecar has one `selection` entry per rating |
| `test_export_endpoint_global`                    | `tests/integration/test_cli.py` | Integration | Same endpoint for all ratings in sidecar |

## Success criteria

- [ ] All four commands share one rule and one help string.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- CLI stays thin: no window arithmetic in `cli.py`.

## Out of scope

- `report` command (Task 03.0 consumes `query_many`).
