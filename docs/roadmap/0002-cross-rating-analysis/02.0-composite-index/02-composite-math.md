# Subtask 02.0/02 - Composite Math

**Task:** [02.0 - Composite Index](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Pure computation of composite scores from already-aligned normalized points, applying the
chosen missing-data policy and recording each cell's full contribution breakdown.

## Baseline

- `CompositeSpec`, `MissingDataPolicy`, `DERIVED_COMPOSITE_LABEL` (subtask 01).
- `NormalizedPoint` (01.0/02).

## Files

| Action | Path                                        | Purpose                       |
|--------|---------------------------------------------|-------------------------------|
| Modify | `src/langrank/analysis/composite.py`        | Result types + `compute_composite` |
| Create | `tests/unit/test_composite_math.py`         | Policy and formula tests      |

## Symbols / fields

| Symbol                               | Kind      | Type / signature                                                                                     | Default | Notes |
|--------------------------------------|-----------|------------------------------------------------------------------------------------------------------|---------|-------|
| `AlignedInputs`                      | type alias | `Mapping[tuple[str, int], Mapping[str, NormalizedPoint]]`                                           | -       | `(language_id, year) → {rating_id: point}` |
| `Contribution`                       | dataclass | frozen: `rating_id`, `metric_id`, `source_period_label: str`, `source_period_start: date`, `raw_rank: int \| None`, `normalized_score: float`, `normalization_label: str`, `weight: float`, `effective_weight: float` | - | `normalization_label` = the point's `derivation_method` |
| `CompositePoint`                     | dataclass | frozen: `language_id`, `display_name`, `year: int`, `score: float`, `composite_rank: int`, `sources_present: int`, `sources_total: int`, `contributions: tuple[Contribution, ...]`, `is_derived: bool = True`, `derivation_method: str`, `label: str = DERIVED_COMPOSITE_LABEL` | - | |
| `CompositeGap`                       | dataclass | frozen: `language_id`, `year: int`, `missing_ratings: tuple[str, ...]`, `reason: str`               | -       | |
| `CompositeResult`                    | dataclass | frozen: `spec: CompositeSpec`, `points: list[CompositePoint]`, `gaps: list[CompositeGap]`, `dropped_languages: list[str]`, `warnings: list[str]` | - | |
| `compute_composite`                  | function  | `(spec: CompositeSpec, inputs: AlignedInputs, *, languages: Sequence[str], years: Sequence[int], display_names: Mapping[str, str]) -> CompositeResult` | - | |

## Behaviour & validators

1. For each `(language, year)` in `languages × years`, `present` = ratings of `spec.rating_ids`
   with a point; `missing` = the rest.
2. **Formula:** `score = Σ w_i · s_i / Σ w_i` over the ratings used; `effective_weight_i =
   w_i / Σ w_i`.
3. **`require-all`:** `missing` non-empty → `CompositeGap(reason="require-all")`.
4. **`renormalize-weights`:** `len(present) < spec.min_sources` → gap `"below min-sources"`;
   otherwise formula over `present` only. If the present ratings' weights sum to 0 → gap
   `"present sources have zero total weight"`.
5. **`drop-language`:** first pass - any `(language, year)` with `missing` → language added to
   `dropped_languages` and **all** its cells omitted (no points, no gaps); remaining languages use
   the formula over all ratings.
6. **Composite rank:** per year, sort points by `score` descending; competition ranking
   ("1, 2, 2, 4"); ties by equal `score` (exact float equality after `round(score, 12)`).
7. `derivation_method = spec.describe()`; `label == "derived composite"` on every point.
8. A cell never gets a score from zero/placeholder inputs; gaps are explicit objects.

## Tests

| Test function                                         | File                                 | Type | Asserts |
|-------------------------------------------------------|--------------------------------------|------|---------|
| `test_composite_weighted_mean_known_values`           | `tests/unit/test_composite_math.py`  | Unit | scores `(1.0, 0.5)`, weights `(1, 3)` → `0.625` |
| `test_composite_require_all_gap`                      | `tests/unit/test_composite_math.py`  | Unit | One rating missing → gap, no point |
| `test_composite_renormalize_rescales_weights`         | `tests/unit/test_composite_math.py`  | Unit | `effective_weight` sums to 1 over present |
| `test_composite_renormalize_below_min_sources_is_gap` | `tests/unit/test_composite_math.py`  | Unit | |
| `test_composite_drop_language_removes_whole_series`   | `tests/unit/test_composite_math.py`  | Unit | Missing in one year → no points in any year; in `dropped_languages` |
| `test_composite_rank_competition_ties`                | `tests/unit/test_composite_math.py`  | Unit | Ties share rank, next rank skips |
| `test_composite_points_carry_label_and_contributions` | `tests/unit/test_composite_math.py`  | Unit | `label`, `is_derived`, contributions length == `sources_present` |

## Success criteria

- [ ] All three policies behave as specified; no imputed values.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Pure; deterministic ordering (`year`, `composite_rank`, `language_id`).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Reading/aligning data - [03-composite-service.md](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/03-composite-service.md).
