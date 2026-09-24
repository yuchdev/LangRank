# Subtask 04.0/02 - Survey question registry

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Encode, per survey year and metric, the question identifier and wording, so every
observation carries the exact question it answers.

## Baseline

None; the SO survey provider tracks schema drift only in free-form metadata.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/jetbrains_questions.py` | Registry |
| Create | `tests/unit/test_jetbrains_questions.py` | Tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `SurveyQuestion` | frozen dataclass | `year: int, metric_id: str, question_id: str \| None, wording: str, raw_column_prefix: str \| None` | `raw_column_prefix` used by subtask 06 |
| `QUESTION_REGISTRY` | const | `tuple[SurveyQuestion, ...]` | From the source note |
| `question_for` | function | `(year: int, metric_id: str) -> SurveyQuestion \| None` | `None` = not asked that year |
| `wording_changes` | function | `(metric_id: str) -> list[tuple[int, str]]` | Years where wording changed (feeds methodology notes) |

## Behaviour & validators

1. `(year, metric_id)` unique - enforced at import time by an assertion in a test.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_question_registry_unique_keys` | `tests/unit/test_jetbrains_questions.py` | Unit | No duplicates |
| `test_question_for_missing_year_returns_none` | `tests/unit/test_jetbrains_questions.py` | Unit | `None` |
| `test_wording_changes_detected` | `tests/unit/test_jetbrains_questions.py` | Unit | Change years listed |

## Success criteria

- [ ] Registry covers every year in the source note for `used_last_12_months`.

## Constraints

- Pure data module; no I/O.

## Out of scope

- Parsing (subtasks 05-06).
