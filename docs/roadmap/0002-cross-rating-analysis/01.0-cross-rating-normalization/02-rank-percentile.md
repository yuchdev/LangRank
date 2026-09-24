# Subtask 01.0/02 - `rank_percentile` Normalization Method

**Task:** [01.0 - Cross-Rating Normalization & Comparison](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Implement the `NormalizationMethod` protocol and its first method, `rank_percentile`, as pure
functions over `AnalysisRow`s, producing explicitly-derived `NormalizedPoint`s with a
recorded population `n` and the rule that produced it.

## Baseline

- `AnalysisRow`, `AnalysisError`, `parse_int_map` from
  [01-analysis-data-access.md](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/01-analysis-data-access.md).
- `src/langrank/models.py:Granularity`.

## Files

| Action | Path                                           | Purpose                                              |
|--------|------------------------------------------------|------------------------------------------------------|
| Create | `src/langrank/analysis/models.py`              | `NormalizedPoint`, `PopulationSource`, options/result types |
| Create | `src/langrank/analysis/normalization.py`       | `NormalizationMethod` protocol, `RankPercentile`, registry |
| Modify | `src/langrank/analysis/__init__.py`            | Re-export                                            |
| Create | `tests/unit/test_analysis_rank_percentile.py`  | Math + population-rule tests                         |

## Symbols / fields

| Symbol                                   | Kind      | Type / signature                                                                  | Default | Notes |
|------------------------------------------|-----------|-----------------------------------------------------------------------------------|---------|-------|
| `MetricKind`                             | StrEnum   | `RANK = "rank"`, `VALUE = "value"`                                                | -       | Which rows a method accepts |
| `PopulationSource`                       | StrEnum   | `OVERRIDE = "override"`, `LIST_SIZE = "list_size"`, `MAX_RANK = "max_rank"`, `COMMON_TOP_N = "common_top_n"` | - | |
| `NormalizationOptions`                   | dataclass | frozen: `population_overrides: Mapping[str, int]`, `common_top_n: int \| None`    | `{}`, `None` | Keyed by `rating_id` |
| `NormalizedPoint`                        | dataclass | frozen                                                                            | -       | |
| `NormalizedPoint.rating_id / metric_id / language_id / display_name` | fields | `str` | - | |
| `NormalizedPoint.period_start / period_end` | fields | `date`                                                                            | -       | Copied from source row, never shifted |
| `NormalizedPoint.period_label`           | field     | `str`                                                                             | -       | |
| `NormalizedPoint.granularity`            | field     | `Granularity`                                                                     | -       | |
| `NormalizedPoint.raw_rank`               | field     | `int \| None`                                                                     | -       | |
| `NormalizedPoint.raw_value`              | field     | `float \| None`                                                                   | -       | |
| `NormalizedPoint.score`                  | field     | `float`                                                                           | -       | In `[0.0, 1.0]` |
| `NormalizedPoint.method_id`              | field     | `str`                                                                             | -       | `"rank_percentile"` |
| `NormalizedPoint.population`             | field     | `int \| None`                                                                     | -       | `n` (None for value methods) |
| `NormalizedPoint.population_source`      | field     | `PopulationSource \| None`                                                        | -       | |
| `NormalizedPoint.is_derived`             | field     | `bool`                                                                            | `True`  | Always `True`; kept for uniform provenance |
| `NormalizedPoint.derivation_method`      | field     | `str`                                                                             | -       | See rule 6 |
| `NormalizedPoint.source_is_derived`      | field     | `bool`                                                                            | -       | From `AnalysisRow.is_derived` |
| `NormalizedPoint.source_url`             | field     | `str`                                                                             | -       | |
| `ExcludedRow`                            | dataclass | frozen: `row: AnalysisRow`, `reason: str`                                         | -       | |
| `NormalizationResult`                    | dataclass | frozen: `points: list[NormalizedPoint]`, `excluded: list[ExcludedRow]`, `warnings: list[str]` | - | |
| `NormalizationMethod`                    | Protocol  | `method_id: str`, `cli_name: str`, `applies_to: MetricKind`, `normalize(rows: Sequence[AnalysisRow], options: NormalizationOptions) -> NormalizationResult` | - | |
| `RankPercentile`                         | class     | implements protocol; `method_id="rank_percentile"`, `cli_name="rank-percentile"`, `applies_to=MetricKind.RANK` | - | |
| `rank_percentile_score`                  | function  | `(rank: int, population: int) -> float`                                           | -       | `1 - (rank - 1) / max(population - 1, 1)` |
| `NORMALIZATION_METHODS`                  | constant  | `Mapping[str, NormalizationMethod]` keyed by `cli_name`                          | -       | `{"rank-percentile": RankPercentile()}` |
| `get_normalization_method`               | function  | `(cli_name: str) -> NormalizationMethod`                                          | -       | Unknown → `AnalysisError` listing names; `"none"` → `AnalysisError` explaining cross-rating raw comparison is not allowed |

## Behaviour & validators

1. **Grouping.** Rows are grouped by `(rating_id, metric_id, period_start, granularity)`; `n` is
   resolved once per group. Rows with `rank is None` are excluded with reason `"no rank"`.
2. **Population rules** (first match wins, recorded in `population_source`):
   1. `options.common_top_n` set → `n = common_top_n`, `COMMON_TOP_N`; rows with
      `rank > common_top_n` are **excluded** (reason `"outside common top-N"`), never scored 0.
   2. `rating_id in options.population_overrides` → `n = override`, `OVERRIDE`.
   3. All rows in the group carry the same `int` `metadata_json["list_size"]` → that value,
      `LIST_SIZE`. Mixed/missing values → fall through.
   4. `n = max(rank)` over **all rows in the group**, `MAX_RANK`; add one warning per rating:
      `"<rating>: n inferred from max stored rank (lower bound); scores for low-ranked
      languages are pessimistic. Pass --rank-population or --common-top."`
3. **Population must cover the ranks**: if any `rank > n` under rules 2.2/2.3 →
   `AnalysisError("<rating> <period>: rank <r> exceeds population n=<n>")`. `rank < 1` →
   `AnalysisError`.
4. **Math.** `score = 1 - (r - 1) / max(n - 1, 1)`; `n = 1` → `1.0`. Ties keep equal scores.
5. `normalize` rejects rows whose `unit != "rank"` with `AnalysisError` (method applies to
   `MetricKind.RANK` only) and rejects a call whose rows span more than one `rating_id`
   **within one group** (impossible by construction, asserted).
6. **Derivation label.** `derivation_method = "rank_percentile[n=<n>;n_source=<source>]"`; if
   the source row `is_derived`, append `"<-" + (row.derivation_method or "provider-derived")`.
7. The method is pure: no I/O, no DB, deterministic output order
   (`rating_id, period_start, language_id`).
8. Rows are not filtered by language here - callers pass the full period population so that
   rule 2.4 sees every stored rank (see subtask 03).

## Tests

| Test function                                                     | File                                           | Type | Asserts |
|-------------------------------------------------------------------|------------------------------------------------|------|---------|
| `test_rank_percentile_score_known_values`                         | `tests/unit/test_analysis_rank_percentile.py` | Unit | `(1,20)→1.0`, `(20,20)→0.0`, `(3,5)→0.5`, `(1,1)→1.0` |
| `test_rank_percentile_ties_share_score`                           | `tests/unit/test_analysis_rank_percentile.py` | Unit | Two rows rank 4 → identical scores |
| `test_rank_percentile_population_from_list_size`                  | `tests/unit/test_analysis_rank_percentile.py` | Unit | `metadata_json["list_size"]=50` → `n=50`, `LIST_SIZE` |
| `test_rank_percentile_population_falls_back_to_max_rank_with_warning` | `tests/unit/test_analysis_rank_percentile.py` | Unit | No list_size → `n=max(rank)`, `MAX_RANK`, one warning per rating |
| `test_rank_percentile_override_wins_over_list_size`               | `tests/unit/test_analysis_rank_percentile.py` | Unit | Override 100 beats list_size 50 |
| `test_rank_percentile_override_smaller_than_rank_raises`          | `tests/unit/test_analysis_rank_percentile.py` | Unit | Override 3, rank 5 → `AnalysisError` |
| `test_rank_percentile_common_top_n_excludes_not_zeroes`           | `tests/unit/test_analysis_rank_percentile.py` | Unit | Rank 25 with common top 20 → in `excluded`, absent from `points` |
| `test_rank_percentile_points_are_flagged_derived`                 | `tests/unit/test_analysis_rank_percentile.py` | Unit | `is_derived is True`, `derivation_method` starts with `rank_percentile[` |
| `test_rank_percentile_chains_source_derivation`                   | `tests/unit/test_analysis_rank_percentile.py` | Unit | Source `is_derived=True` → label contains `<-` |
| `test_rank_percentile_rejects_value_unit`                         | `tests/unit/test_analysis_rank_percentile.py` | Unit | `unit="percent"` row → `AnalysisError` |
| `test_get_normalization_method_none_is_rejected`                  | `tests/unit/test_analysis_rank_percentile.py` | Unit | `"none"` → `AnalysisError` mentioning shared axis |

## Success criteria

- [ ] `rank_percentile_score` and `RankPercentile` exist with the signatures above.
- [ ] Every `NormalizedPoint` has `is_derived=True`, a non-empty `derivation_method`, and a
      `population_source`.
- [ ] Absent/excluded rows never appear as a `0.0` score.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No persistence of normalized values (plan § Derived-value labeling: compute-on-read).
- No interpolation, no fabricated values ([CLAUDE.md](/CLAUDE.md) § Conventions).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- `minmax`/`zscore` - [05-minmax-zscore.md](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/05-minmax-zscore.md).
- Providers populating `metadata_json["list_size"]` - optional provider-side follow-up; the
  hook is only consumed here.
