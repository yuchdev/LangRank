# Subtask 01.0/07 - Fixtures, golden outputs & contract tests

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Testing Expert · **Depends on:** 06 · **Status:** ⬜ Not started

## Goal

Ship raw fixtures (API JSON + SEDE CSV) and golden normalized outputs, and add a reusable
golden-comparison helper that Tasks 02.0-04.0 reuse.

## Baseline

- `tests/contract/test_production_providers.py` - parametrized parse/normalize/validate
  smoke over `tests/fixtures/<id>/sample.csv`; no golden comparison exists yet.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tests/fixtures/stackoverflow-tags/api_sample.json` | 3 months × 5 tags + totals |
| Create | `tests/fixtures/stackoverflow-tags/sede_sample.csv` | Includes a multi-tag month summing >100 % and a renamed tag (`golang`) |
| Create | `tests/fixtures/stackoverflow-tags/expected_observations.json` | Golden normalized output |
| Create | `tests/contract/_golden.py` | `assert_matches_golden` helper |
| Create | `tests/contract/test_stackoverflow_tags_provider.py` | Contract tests |
| Modify | `tests/integration/test_fetch_and_query.py` | Offline fetch → query round trip |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `assert_matches_golden` | function | `(observations: list[Observation], golden: Path, *, update: bool = False) -> None` | Compares `to_dict()` minus `retrieved_at`; `LANGRANK_UPDATE_GOLDEN=1` rewrites |

## Behaviour & validators

1. Golden files are sorted by `(metric_id, language_id, period_start)` for stable diffs.
2. Fixtures are hand-built from real API responses for small windows; no user content.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_stackoverflow_tags_api_fixture_matches_golden` | `tests/contract/test_stackoverflow_tags_provider.py` | Unit | Golden equality |
| `test_stackoverflow_tags_sede_multi_tag_share` | `tests/contract/test_stackoverflow_tags_provider.py` | Unit | Sum of shares > 100, report ok |
| `test_stackoverflow_tags_rename_alias` | `tests/contract/test_stackoverflow_tags_provider.py` | Unit | `golang` row → `go` |
| `test_stackoverflow_tags_offline_fetch_and_query` | `tests/integration/test_fetch_and_query.py` | Integration | `FetchService` + `QueryService` return share rows |

## Success criteria

- [ ] `uv run pytest -m "not integration"` passes with the new tests.
- [ ] `_golden.py` is provider-agnostic (no SO imports).

## Constraints

- No network in any non-`integration` test.

## Out of scope

- Live test (lives in subtask 04).
