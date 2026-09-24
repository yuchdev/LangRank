# Subtask 02.0/08 - Validate: named validation codes

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 06, 07 · **Status:** ⬜ Not started

## Goal

Implement `validate()` for both variants.

## Baseline

`ValidationReport.add`; `FetchService` blocks on ERROR.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/github.py` | `validate()` |
| Create | `tests/unit/test_github_validate.py` | One test per code |

## Symbols / fields

| Code | Severity | Condition |
|------|----------|-----------|
| `rank_positive` | ERROR | rank ≤ 0 |
| `count_non_negative` | ERROR | pushers < 0 |
| `share_range` | ERROR | share ∉ 0..100 |
| `duplicate_language_period` | ERROR | duplicate `(language, period, metric)` |
| `aggregate_not_derived` | ERROR | IG observation with `is_derived=False` |
| `mixed_variant` | ERROR | a batch containing both `github-octoverse-*` and `github-innovation-graph-*` |
| `octoverse_rank_gap` | WARNING | ranks within an edition not contiguous from 1 |
| `unmapped_language` | WARNING | per `last_unmapped` |

## Behaviour & validators

1. Messages include variant, language and period label.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_github_validate_flags_each_error_code` | `tests/unit/test_github_validate.py` | Unit | Parametrized over ERROR codes |
| `test_github_validate_warnings_do_not_block` | `tests/unit/test_github_validate.py` | Unit | `report.ok` |

## Success criteria

- [ ] Every code emitted and tested; lint/format/mypy/pytest green.

## Constraints

- Never mutates observations.

## Out of scope

- DB-wide checks.
