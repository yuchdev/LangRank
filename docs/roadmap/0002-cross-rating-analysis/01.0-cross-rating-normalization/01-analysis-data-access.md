# Subtask 01.0/01 - Analysis Data Access & Rank-Metric Resolution

**Task:** [01.0 - Cross-Rating Normalization & Comparison](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Give the analysis layer a provenance-complete read path (`AnalysisRow`) and a single,
swappable function that decides which metric is a rating's "rank" metric, plus the shared
test fixture every Milestone 0002 subtask uses.

## Baseline

- `src/langrank/db/repository.py:QueryRow` / `Database.query_rows` - used by query, CSV/JSON
  export and plot; lacks `granularity`, `is_derived`, `derivation_method`, `metadata_json`,
  `parser_version`, `source_document_id`. Must stay unchanged (export column stability).
- `src/langrank/db/repository.py:Database.list_metrics(rating_id) -> list[MetricDefinition]`.
- `src/langrank/errors.py` has no analysis-specific error.
- Metric IDs are provider-prefixed (`tiobe-rank`, ...); `demo` uses `rank`.

## Files

| Action | Path                                         | Purpose                                                        |
|--------|----------------------------------------------|----------------------------------------------------------------|
| Create | `src/langrank/analysis/__init__.py`          | Package; re-exports public names                               |
| Create | `src/langrank/analysis/metrics.py`           | `resolve_rank_metric`, `parse_metric_map`, `parse_int_map`     |
| Modify | `src/langrank/db/repository.py`              | Add `AnalysisRow` + `Database.query_analysis_rows`             |
| Modify | `src/langrank/errors.py`                     | Add `AnalysisError(LangRankError)`                             |
| Modify | `tests/conftest.py`                          | Add `multi_rating_database` fixture                            |
| Create | `tests/unit/test_analysis_metrics.py`        | Rank-metric resolution + map parsing tests                     |
| Create | `tests/integration/test_analysis_rows.py`    | `query_analysis_rows` round-trip tests                          |

## Symbols / fields

| Symbol                                   | Kind      | Type / signature                                                                                             | Default | Notes |
|------------------------------------------|-----------|--------------------------------------------------------------------------------------------------------------|---------|-------|
| `AnalysisRow`                            | dataclass | frozen                                                                                                       | -       | In `db/repository.py` next to `QueryRow` |
| `AnalysisRow.rating_id`                  | field     | `str`                                                                                                        | -       | |
| `AnalysisRow.metric_id`                  | field     | `str`                                                                                                        | -       | |
| `AnalysisRow.language_id`                | field     | `str`                                                                                                        | -       | |
| `AnalysisRow.display_name`               | field     | `str`                                                                                                        | -       | From `languages` join |
| `AnalysisRow.period_start`               | field     | `date`                                                                                                       | -       | Parsed, not `str` (unlike `QueryRow`) |
| `AnalysisRow.period_end`                 | field     | `date`                                                                                                       | -       | |
| `AnalysisRow.period_label`               | field     | `str`                                                                                                        | -       | |
| `AnalysisRow.granularity`                | field     | `Granularity`                                                                                                | -       | |
| `AnalysisRow.rank`                       | field     | `int \| None`                                                                                                | -       | |
| `AnalysisRow.value`                      | field     | `float \| None`                                                                                              | -       | |
| `AnalysisRow.unit`                       | field     | `str`                                                                                                        | -       | |
| `AnalysisRow.source_url`                 | field     | `str`                                                                                                        | -       | |
| `AnalysisRow.is_derived`                 | field     | `bool`                                                                                                       | -       | Source row's own flag |
| `AnalysisRow.derivation_method`          | field     | `str \| None`                                                                                                | -       | |
| `AnalysisRow.parser_version`             | field     | `str`                                                                                                        | -       | |
| `AnalysisRow.source_document_id`         | field     | `str \| None`                                                                                                | -       | |
| `AnalysisRow.metadata_json`              | field     | `dict[str, Any]`                                                                                             | -       | Decoded JSON |
| `Database.query_analysis_rows`           | method    | `(self, *, rating_id: str, metric_id: str, since: date \| None = None, until: date \| None = None, language_ids: Sequence[str] = ()) -> list[AnalysisRow]` | - | Read-only; ordered by `period_start, language_id` |
| `AnalysisError`                          | class     | `AnalysisError(LangRankError)`                                                                               | -       | Caught centrally in `cli.main()` like other `LangRankError`s |
| `resolve_rank_metric`                    | function  | `(rating_id: str, metrics: Sequence[MetricDefinition], override: str \| None = None) -> str`                 | -       | Interim rule until 0006/01.0 metric roles |
| `parse_metric_map`                       | function  | `(value: str \| None) -> dict[str, str]`                                                                     | -       | `"tiobe=tiobe-rank,pypl=pypl-rank"` |
| `parse_int_map`                          | function  | `(value: str \| None, *, option_name: str) -> dict[str, int]`                                                | -       | For `--rank-population tiobe=50` |

## Behaviour & validators

1. `query_analysis_rows` selects from `observations JOIN languages` with the same `since`
   (`period_start >= since`) / `until` (`period_end <= until`) semantics as `query_rows`, so
   window resolution stays in `QueryService` (see
   [Milestone 0005 Task 05.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-050---historical-selection-semantics)).
2. `rating_id` and `metric_id` are **required** on `query_analysis_rows` - analysis never reads a
   mixed-rating result set in one call.
3. `resolve_rank_metric`:
   - `override` given → must be one of `metrics[*].id`, else `AnalysisError("Metric '<x>' is not
     available for <rating>. Available: ...")`.
   - otherwise candidates = metrics with `unit == "rank"`; exactly one → return its id;
     zero → `AnalysisError` telling the user to pass `--metric-map <rating>=<metric>`;
     more than one → `AnalysisError` listing candidates.
   - Docstring states: *"Interim rule. Replace the `unit == 'rank'` test with the metric-role
     lookup from Milestone 0006 Task 01.0 once it lands; callers must not re-implement this."*
4. `parse_metric_map` / `parse_int_map`: `None`/empty → `{}`; entries split on `,`, pairs on the
   first `=`; whitespace trimmed; a malformed pair, duplicate key, or (for ints) a non-positive
   or non-integer value → `AnalysisError` naming `option_name`.
5. `multi_rating_database` fixture: builds a `Database` in `tmp_path`, runs
   `FetchService.fetch` for `tiobe`, `pypl`, `redmonk`, `stackoverflow-survey` from a
   `ProviderRegistry(tmp_path / "cache")` (bundled CSVs - no network), returns the `Database`.

## Tests

| Test function                                              | File                                       | Type        | Asserts |
|------------------------------------------------------------|--------------------------------------------|-------------|---------|
| `test_resolve_rank_metric_picks_unique_rank_unit`          | `tests/unit/test_analysis_metrics.py`      | Unit        | `tiobe` metadata → `tiobe-rank`; `demo` → `rank` |
| `test_resolve_rank_metric_override_must_exist`             | `tests/unit/test_analysis_metrics.py`      | Unit        | Unknown override raises `AnalysisError` listing ids |
| `test_resolve_rank_metric_no_rank_metric_raises`           | `tests/unit/test_analysis_metrics.py`      | Unit        | Metrics without `unit == "rank"` → error mentions `--metric-map` |
| `test_resolve_rank_metric_ambiguous_raises`                | `tests/unit/test_analysis_metrics.py`      | Unit        | Two rank-unit metrics → error lists both |
| `test_parse_metric_map_valid_and_empty`                    | `tests/unit/test_analysis_metrics.py`      | Unit        | Parses pairs; `None` → `{}` |
| `test_parse_int_map_rejects_non_positive`                  | `tests/unit/test_analysis_metrics.py`      | Unit        | `tiobe=0`, `tiobe=x`, duplicate key → `AnalysisError` |
| `test_query_analysis_rows_carries_provenance`              | `tests/integration/test_analysis_rows.py`  | Integration | Rows have `granularity`, `is_derived`, `parser_version`, decoded `metadata_json` |
| `test_query_analysis_rows_requires_single_rating_metric`   | `tests/integration/test_analysis_rows.py`  | Integration | All returned rows share the requested `rating_id`/`metric_id` |
| `test_query_rows_shape_unchanged`                          | `tests/integration/test_analysis_rows.py`  | Integration | `QueryRow` field names unchanged (export stability guard) |

## Success criteria

- [ ] `AnalysisRow` and `Database.query_analysis_rows` exist; `QueryRow` is byte-for-byte unchanged.
- [ ] `resolve_rank_metric` returns `tiobe-rank`, `pypl-rank`, `redmonk-rank`,
      `stackoverflow-survey-rank`, `rank` for the five registered providers.
- [ ] `multi_rating_database` fixture is available to all tests and needs no network.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `Database` remains the only SQL-touching class ([CLAUDE.md](/CLAUDE.md) § Storage).
- No migration: this subtask only reads existing columns.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Normalization math - [02-rank-percentile.md](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/02-rank-percentile.md).
- Structured metric roles - Milestone 0006 Task 01.0.
- Fixing `stackoverflow-survey-rank`'s `is_derived=False` - provider provenance, not analysis.
