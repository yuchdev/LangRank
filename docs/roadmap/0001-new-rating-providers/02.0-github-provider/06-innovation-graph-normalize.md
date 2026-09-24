# Subtask 02.0/06 - Innovation Graph normalize: global aggregation, share & rank

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 05 · **Status:** ⬜ Not started

## Goal

Aggregate per-economy records into a global quarterly series and derive share and rank -
every output flagged derived with an explicit method.

## Baseline

`build_observation(..., is_derived=, derivation_method=)`; `raw_record_hash` hashes a
`SourceRecord` - aggregated values need a synthetic aggregate `SourceRecord` whose
`metadata` lists the contributing economy count so the hash changes when inputs change.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/github.py` | `_aggregate_global`, `normalize()` IG branch |
| Create | `tests/unit/test_github_innovation_graph_normalize.py` | Math tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `_aggregate_global` | function | `(records: Sequence[SourceRecord]) -> list[SourceRecord]` | Sums `num_pushers` per (quarter, Linguist language) |
| `IG_SUM_METHOD` | const | `str` | `"sum_over_economies:suppressed_below_100"` |
| `IG_SHARE_METHOD` | const | `str` | `"share_of_all_published_language_pushers"` |
| `IG_RANK_METHOD` | const | `str` | `"rank_by_global_pushers"` |

## Behaviour & validators

1. Aggregate record metadata: `economies_count`, `commit_sha`, `suppression_threshold=100`.
2. Pushers observation: `is_derived=True`, `derivation_method=IG_SUM_METHOD`,
   `population="global (economies ≥100 developers)"`.
3. Share = 100 × language_sum / Σ all Linguist languages' sums in that quarter (including
   unmapped ones); `derivation_method=IG_SHARE_METHOD`; `metadata_json["denominator_count"]`.
4. Rank computed over mapped languages only, ties share rank, `derivation_method=IG_RANK_METHOD`.
5. Unmapped (non-`GITHUB_NON_LANGUAGES`) names → `last_unmapped`.
6. `source_document_id = f"innovationgraph@{commit_sha[:12]}"`.
7. A developer pushing in two economies in a quarter is counted twice by GitHub's data;
   document as a caveat, do not attempt to correct.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ig_global_sum_is_derived` | `tests/unit/test_github_innovation_graph_normalize.py` | Unit | Sum, flag, method, population |
| `test_ig_share_denominator_includes_unmapped` | `tests/unit/test_github_innovation_graph_normalize.py` | Unit | Denominator math |
| `test_ig_rank_ties` | `tests/unit/test_github_innovation_graph_normalize.py` | Unit | Competition ranking |
| `test_ig_hash_changes_with_economy_count` | `tests/unit/test_github_innovation_graph_normalize.py` | Unit | Different inputs → different `raw_record_hash` |

## Success criteria

- [ ] No aggregated value stored with `is_derived=False`.
- [ ] Tests pass; lint/format/mypy/pytest green.

## Constraints

- Missing quarters remain missing (no fill).

## Out of scope

- Per-economy series storage.
