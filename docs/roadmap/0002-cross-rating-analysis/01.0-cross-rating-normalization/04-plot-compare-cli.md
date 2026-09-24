# Subtask 01.0/04 - `plot compare` CLI & Derived Plot Rendering

**Task:** [01.0 - Cross-Rating Normalization & Comparison](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Expose `ComparisonService` as `langrank plot compare`, rendering derived series on a `[0, 1]`
axis that is visibly labelled as derived, while keeping every existing `langrank plot ...`
invocation working.

## Baseline

- `src/langrank/cli.py:plot` - a single `@app.command()` with options `--rating`, `--metric`,
  `--language(s)`, `--all-languages`, `--top`, `--top-current`, `--since`, `--until`,
  `--years`, `--output`, `--title`, `--width`, `--height`, `--dpi`, `--markers`,
  `--invert-rank/--no-invert-rank`.
- `src/langrank/plotting/service.py:PlotService.plot`.
- Nothing today stops `langrank plot` (no `--rating`) from drawing rows of several ratings on one
  axis if their metric IDs coincide.

## Files

| Action | Path                                       | Purpose                                              |
|--------|--------------------------------------------|------------------------------------------------------|
| Modify | `src/langrank/cli.py`                      | `plot_app` Typer group; legacy callback; `plot_compare` command |
| Modify | `src/langrank/plotting/service.py`         | `PlotService.plot_compare`; `_split_on_gaps` helper  |
| Create | `tests/integration/test_cli_plot_compare.py` | CLI acceptance tests                               |
| Create | `tests/unit/test_plot_compare_rendering.py`  | Rendering tests (Agg backend)                      |

## Symbols / fields

| Symbol                         | Kind      | Type / signature                                                                                   | Default | Notes |
|--------------------------------|-----------|----------------------------------------------------------------------------------------------------|---------|-------|
| `plot_app`                     | Typer     | `typer.Typer(help="Plot rating history", invoke_without_command=True)`                             | -       | `app.add_typer(plot_app, name="plot")` replaces `@app.command() plot` |
| `plot_callback`                | function  | same options as today's `plot`; runs legacy path only when `ctx.invoked_subcommand is None`        | -       | |
| `plot_compare`                 | function  | `@plot_app.command("compare")`                                                                     | -       | |
| `--language`                   | option    | `str`, required                                                                                    | -       | Exactly one language in this task |
| `--ratings`                    | option    | `str`, required, comma-separated                                                                   | -       | ≥ 2 |
| `--normalize`                  | option    | `str`                                                                                              | `"rank-percentile"` | `none` → exit 2 |
| `--metric-map`                 | option    | `str \| None`                                                                                      | `None`  | `rating=metric,...` |
| `--rank-population`            | option    | `str \| None`                                                                                      | `None`  | `rating=N,...` |
| `--common-top`                 | option    | `int \| None`                                                                                      | `None`  | |
| `--since / --until / --years`  | options   | as `plot`                                                                                          | `None`  | |
| `--output / --title / --width / --height / --dpi / --markers` | options | as `plot`                                                             | as `plot` | `--markers` default `True` here (sparse annual series) |
| `--show-values`                | option    | `bool`                                                                                             | `False` | Prints the derived table |
| `--format`                     | option    | `str` in `{"table", "json"}`                                                                       | `"table"` | Applies to `--show-values` output |
| `PlotService.plot_compare`     | method    | `(self, result: ComparisonResult, *, language_label: str, output: Path \| None, title: str \| None, width: float, height: float, dpi: int, markers: bool) -> None` | - | |
| `_split_on_gaps`               | function  | `(points: Sequence[NormalizedPoint]) -> list[list[NormalizedPoint]]`                              | -       | Break where gap > 2 × median spacing of that series |

## Behaviour & validators

1. **Backwards compatibility.** Every existing invocation (`langrank plot --rating tiobe --metric
   rank --languages python,c++ --years 10`, `--output`, etc.) behaves exactly as before;
   `langrank plot --help` lists `compare` as a sub-command.
2. **Legacy guard.** In the legacy path, if the queried rows span more than one `rating_id`, raise
   `LangRankError("Refusing to plot raw values from several ratings on one axis. Use 'langrank
   plot compare' ...")` → non-zero exit.
3. `--normalize none` (case-insensitive) → `typer.BadParameter` / exit code 2 with a message
   explaining raw cross-rating values are not comparable. Unknown method → exit 2 listing
   `NORMALIZATION_METHODS`.
4. `AnalysisError` from the service surfaces as a red message with exit code 1 (existing central
   `LangRankError` handling in `main()`).
5. **Rendering rules** (`plot_compare`):
   - y-axis label `"rank percentile (derived; 1.0 = best)"`, `ylim(-0.02, 1.02)`, **no** inversion.
   - Title default `"<Language>: cross-rating comparison (derived: rank_percentile)"`.
   - One line per rating; legend label `"<rating_id> (<metric_id>)"`.
   - Lines are split by `_split_on_gaps` so no segment visually bridges missing periods.
   - Footer (`fig.text`) lists, per rating, the distinct `population_source`/`n` values used,
     e.g. `"tiobe: n=max_rank(5) · pypl: n=max_rank(5)"`.
   - A rating in `result.missing` gets no line and is named in the footer as `"no data"`.
6. Warnings (`result.warnings`) are printed to the console in yellow before writing the plot.
7. `--show-values` prints columns `rating, metric, period, raw_rank, n, n_source, score,
   derivation_method`; `--format json` prints the same as a JSON array of `NormalizedPoint`
   dicts (dates ISO-formatted).

## Tests

| Test function                                             | File                                          | Type | Asserts |
|-----------------------------------------------------------|-----------------------------------------------|------|---------|
| `test_plot_compare_writes_png`                            | `tests/integration/test_cli_plot_compare.py`  | E2E  | `plot compare --language python --ratings tiobe,pypl,redmonk --years 10 --output x.png` → exit 0, file exists |
| `test_plot_compare_rejects_normalize_none`                | `tests/integration/test_cli_plot_compare.py`  | E2E  | exit code 2; message mentions "not comparable" |
| `test_plot_compare_requires_two_ratings`                  | `tests/integration/test_cli_plot_compare.py`  | E2E  | `--ratings tiobe` → non-zero exit |
| `test_plot_compare_show_values_json_marks_derived`        | `tests/integration/test_cli_plot_compare.py`  | E2E  | Every JSON item has `is_derived: true` and `derivation_method` |
| `test_legacy_plot_invocation_unchanged`                   | `tests/integration/test_cli_plot_compare.py`  | E2E  | Existing `plot --rating demo --metric rating ... --output` still exit 0 |
| `test_legacy_plot_refuses_multiple_ratings`               | `tests/integration/test_cli_plot_compare.py`  | E2E  | Rows from 2 ratings → non-zero exit, message points to `plot compare` |
| `test_plot_compare_axis_labelled_derived`                 | `tests/unit/test_plot_compare_rendering.py`   | Unit | Captured `Axes.get_ylabel()` contains "derived"; ylim within `[-0.02, 1.02]`; y not inverted |
| `test_split_on_gaps_breaks_long_gaps`                     | `tests/unit/test_plot_compare_rendering.py`   | Unit | Monthly series with a 6-month hole → 2 segments |

Tests use the `multi_rating_database` fixture or the `--db` flag with fetched bundled data;
`MPLBACKEND=Agg` is already forced by `tests/conftest.py`.

## Success criteria

- [ ] `langrank plot compare` exists; `langrank plot` legacy usage is unchanged.
- [ ] Cross-rating raw plotting is refused in both the legacy path and `--normalize none`.
- [ ] Rendered plot labels the series as derived and never draws across gaps.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Plotting invariants: missing never rendered as zero; no interpolation; rank axis stays inverted
  in the **legacy** rank plot ([Milestone 0005 § Plotting invariants](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#plotting-invariants)).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Fixing the legacy `invert_rank` check (`metric_id == "rank"` misses `tiobe-rank` etc.) - belongs
  to Milestone 0005 Task 02.0; note it, don't fix it here.
- Multi-language faceting (`--facet`) - Milestone 0005 Task 02.0.
