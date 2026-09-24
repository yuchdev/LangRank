# Subtask 02.0/01 - Composite Spec & Validation

**Task:** [02.0 - Composite Index](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/README.md) ·
**Role:** Python Expert · **Depends on:** 01.0/02 · **Status:** ⬜ Not started

## Goal

A single immutable `CompositeSpec` that holds every user-stated ingredient of a composite and
refuses to exist if any is missing, contradictory, or silently ignorable.

## Baseline

- `NORMALIZATION_METHODS`, `get_normalization_method`, `MetricKind`, `AnalysisError`
  (01.0/01-02).

## Files

| Action | Path                                         | Purpose                           |
|--------|----------------------------------------------|-----------------------------------|
| Create | `src/langrank/analysis/composite.py`         | `MissingDataPolicy`, `CompositeSpec`, `build_composite_spec`, `parse_weights` |
| Modify | `src/langrank/analysis/__init__.py`          | Re-export                         |
| Create | `tests/unit/test_composite_spec.py`          | Validation tests                  |

## Symbols / fields

| Symbol                          | Kind      | Type / signature                                                                                                   | Default | Notes |
|---------------------------------|-----------|--------------------------------------------------------------------------------------------------------------------|---------|-------|
| `MissingDataPolicy`             | StrEnum   | `REQUIRE_ALL = "require-all"`, `RENORMALIZE_WEIGHTS = "renormalize-weights"`, `DROP_LANGUAGE = "drop-language"`     | -       | |
| `DERIVED_COMPOSITE_LABEL`       | constant  | `str`                                                                                                              | `"derived composite"` | Single source of the label |
| `CompositeSpec`                 | dataclass | frozen                                                                                                             | -       | |
| `CompositeSpec.rating_ids`      | field     | `tuple[str, ...]`                                                                                                  | -       | Order as given |
| `CompositeSpec.metric_selector` | field     | `str \| dict[str, str]`                                                                                            | -       | `"rank"` or explicit map |
| `CompositeSpec.method`          | field     | `str`                                                                                                              | -       | CLI name |
| `CompositeSpec.weights`         | field     | `dict[str, float]`                                                                                                 | -       | Keyed by rating |
| `CompositeSpec.missing`         | field     | `MissingDataPolicy`                                                                                                | -       | |
| `CompositeSpec.min_sources`     | field     | `int \| None`                                                                                                      | -       | Only with `RENORMALIZE_WEIGHTS` |
| `CompositeSpec.describe`        | method    | `(self) -> str`                                                                                                    | -       | `"composite[method=rank_percentile;weights=tiobe:1,pypl:1;missing=require-all]"` |
| `parse_weights`                 | function  | `(value: str, rating_ids: Sequence[str]) -> dict[str, float]`                                                      | -       | Positional list aligned with `rating_ids` |
| `parse_metric_selector`         | function  | `(value: str, rating_ids: Sequence[str]) -> str \| dict[str, str]`                                                 | -       | `"rank"` or `parse_metric_map` covering every rating |
| `build_composite_spec`          | function  | `(*, ratings: str, metric: str, method: str, weights: str, missing: str, min_sources: int \| None) -> CompositeSpec` | -    | All required; raises `AnalysisError` |

## Behaviour & validators

`build_composite_spec` raises `AnalysisError` (each with a distinct, tested message) when:

1. fewer than 2 ratings, or a duplicate rating;
2. `weights` count ≠ ratings count; any weight not a finite float; any weight < 0; all weights 0;
3. `metric` is neither `"rank"` nor a map covering **exactly** the listed ratings;
4. `method` is `none` or unknown (reuse `get_normalization_method`);
5. `missing` is not a `MissingDataPolicy` value (message lists the three values);
6. `missing == renormalize-weights` and `min_sources` is `None` or outside `1..len(ratings)`;
7. `min_sources` given with any other policy (would be silently ignored);
8. a zero-weight rating is allowed but produces a spec-level warning string
   (`CompositeSpec.warnings: tuple[str, ...]`) - "rating X has weight 0 and does not affect the
   score" - rather than being dropped silently.

## Tests

| Test function                                         | File                                 | Type | Asserts |
|-------------------------------------------------------|--------------------------------------|------|---------|
| `test_build_spec_valid_plan_example`                  | `tests/unit/test_composite_spec.py`  | Unit | plan.md's example (5 ratings, `1,1,1,2,2`) builds; `describe()` stable |
| `test_build_spec_weight_count_mismatch`               | `tests/unit/test_composite_spec.py`  | Unit | 3 ratings, 2 weights → error |
| `test_build_spec_rejects_negative_nan_and_all_zero`   | `tests/unit/test_composite_spec.py`  | Unit | parametrized |
| `test_build_spec_metric_map_must_cover_ratings`       | `tests/unit/test_composite_spec.py`  | Unit | Missing or extra key → error |
| `test_build_spec_rejects_normalize_none`              | `tests/unit/test_composite_spec.py`  | Unit | |
| `test_build_spec_renormalize_requires_min_sources`    | `tests/unit/test_composite_spec.py`  | Unit | `None`, `0`, `len+1` → error |
| `test_build_spec_min_sources_with_other_policy_rejected` | `tests/unit/test_composite_spec.py` | Unit | |
| `test_build_spec_zero_weight_warns`                   | `tests/unit/test_composite_spec.py`  | Unit | Warning present |

## Success criteria

- [ ] No `CompositeSpec` can be constructed through `build_composite_spec` with a defaulted or
      ignored ingredient.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Pure module; no DB.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- The arithmetic - [02-composite-math.md](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/02-composite-math.md).
