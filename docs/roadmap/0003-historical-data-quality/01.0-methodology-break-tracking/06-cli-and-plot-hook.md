# Subtask 01.0/06 - CLI surfacing & plot-annotation hook

**Task:** [01.0 - Methodology Break Tracking](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Show methodology segments in the CLI and expose a stable query the plotting work in
[Milestone 0005 Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-020---improved-plotting-options)
calls for `--annotate-methodology`.

## Baseline

- `cli.py:ratings_show` prints name/description/metrics/caveats; no notes.
- `PlotService.plot` has no annotation support (0005 owns the flag).

## Files

| Action | Path                                      | Purpose |
|--------|-------------------------------------------|---------|
| Modify | `src/langrank/cli.py`                     | `ratings show` adds a "Methodology" table; new `ratings methodology <id> [--format table\|json]` |
| Modify | `src/langrank/services/validation.py`     | `methodology_breaks()` |
| Modify | `tests/integration/test_cli.py`           | CLI tests |
| Create | `tests/unit/test_methodology_breaks.py`   | Break-list tests |

## Symbols / fields

| Symbol                                   | Kind      | Type / signature                                                              | Default | Notes |
|------------------------------------------|-----------|-------------------------------------------------------------------------------|---------|-------|
| `MethodologyBreak`                       | dataclass | frozen: `rating_id: str`, `metric_ids: tuple[str, ...]`, `on: date`, `from_version: str \| None`, `to_version: str`, `break_kind: BreakKind`, `source_url: str \| None` | - | in `models.py` |
| `ValidationService.methodology_breaks`   | method    | `(rating_id: str, metric_id: str \| None = None) -> list[MethodologyBreak]`    | -       | excludes `initial` |
| `ratings_methodology`                    | CLI       | `langrank ratings methodology <rating> [--format table\|json]`                | `table` | |

## Behaviour & validators

1. `methodology_breaks` returns breaks sorted by `on`; filtering by `metric_id` keeps breaks
   whose `affects_metrics` is empty or contains it.
2. JSON output: list of objects with the `MethodologyBreak` fields, dates ISO-formatted.
3. Unknown rating → `ProviderError` (exit code 1 via `main()`).

## Tests

| Test function                                     | File                                     | Type        | Asserts |
|---------------------------------------------------|------------------------------------------|-------------|---------|
| `test_methodology_breaks_excludes_initial`        | `tests/unit/test_methodology_breaks.py`  | Integration | demo → 1 break |
| `test_methodology_breaks_metric_filter`           | `tests/unit/test_methodology_breaks.py`  | Integration | scoped break filtered |
| `test_cli_ratings_methodology_json`               | `tests/integration/test_cli.py`          | E2E         | valid JSON with `to_version` |
| `test_cli_ratings_show_lists_methodology`         | `tests/integration/test_cli.py`          | E2E         | output contains version string |

## Success criteria

- [ ] `langrank ratings methodology demo --format json` prints the demo break.
- [ ] `ValidationService.methodology_breaks` documented in its docstring as the hook for `--annotate-methodology`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Business logic in the service, rendering in `cli.py` ([CLAUDE.md](/CLAUDE.md) § Services).

## Out of scope

- Drawing annotations on plots (0005 Task 02.0).
