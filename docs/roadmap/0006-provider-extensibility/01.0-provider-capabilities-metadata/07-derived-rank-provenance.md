# Subtask 01.0/07 - Derived-Rank Provenance

**Task:** [01.0 - Provider Capabilities Metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

A rank that LangRank computes (rather than one the source publishes) is stored with
`is_derived=True` and an explicit `derivation_method`, and the metric declares that it is derived.
Fixes the one existing violation of the project's "derived values are flagged" invariant.

## Baseline

- `src/langrank/providers/stackoverflow_survey.py:StackOverflowSurveyProvider.parse` builds
  `stackoverflow-survey-rank` by sorting `worked_with_percent` values per year
  (`rank_map = {… enumerate(ranked, start=1)}`), but `normalize` passes `is_derived=False,
  derivation_method=None` for **every** record - so the computed rank is presented as source data.
- Stack Overflow's survey publishes percentages, not ranks (see
  [docs/source-notes/stackoverflow-survey.md](/docs/source-notes/stackoverflow-survey.md)).
- `MetricKind` / `metrics.kind` come from [subtask 01](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/01-metric-kind-metadata.md).

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/models.py` | `MetricDefinition.derived_from: str \| None = None` |
| Modify | `src/langrank/db/migrations.py` | New append-only migration: `metrics.derived_from TEXT` (nullable) |
| Modify | `src/langrank/db/repository.py` | `upsert_provider_metadata` / `list_metrics` persist and read `derived_from` |
| Modify | `src/langrank/providers/stackoverflow_survey.py` | rank metric `derived_from="worked_with_percent"`; `normalize` sets `is_derived=True, derivation_method="rank_by_value_desc"` for `stackoverflow-survey-rank` only; bump `parser_version` |
| Create | `tests/contract/test_derived_metrics.py` | Tests below |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `MetricDefinition.derived_from` | field | `str \| None` | `None` | ID of the source metric a derived metric is computed from |
| `DERIVATION_RANK_BY_VALUE_DESC` | constant | `str` | `"rank_by_value_desc"` | In `providers/common.py`; ties broken by canonical language ID, documented |
| `StackOverflowSurveyProvider.metadata().parser_version` | field | `str` | bumped | Forces re-hash so stored rows update |

## Behaviour & validators

1. Every observation whose metric has `derived_from` set is `is_derived=True` with a non-null
   `derivation_method`; every other observation of a bootstrap provider is `is_derived=False`.
2. `worked_with_percent` observations are unchanged (`is_derived=False`).
3. Re-fetching an existing DB updates the rank rows in place (natural key unchanged, hash
   changed) - no duplicate rows.
4. A new `ValidationReport` code `derived_flag_mismatch` (ERROR) in the provider's `validate`
   fires if rule 1 is violated.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_derived_metrics_flagged_for_every_provider` | `tests/contract/test_derived_metrics.py` | Integration | rule 1, parametrized over `ProviderRegistry.all()` |
| `test_stackoverflow_survey_percent_not_derived` | `tests/contract/test_derived_metrics.py` | Unit | rule 2 |
| `test_refetch_updates_rank_rows_in_place` | `tests/contract/test_derived_metrics.py` | Integration | rule 3 |
| `test_derived_flag_mismatch_validation_code` | `tests/contract/test_derived_metrics.py` | Unit | rule 4 |

## Success criteria

- [ ] `sqlite3 <db> "select count(*) from observations where metric_id='stackoverflow-survey-rank' and is_derived=0"` returns 0 after `langrank fetch stackoverflow-survey`.
- [ ] `langrank ratings show stackoverflow-survey` shows the rank metric as derived from `worked_with_percent`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Append-only migration; version number decided at merge time (other milestones also add migrations).
- Providers stay pure: derivation happens in `parse`/`normalize`, never in the DB layer.

## Out of scope

- Other derived series (normalized/composite values) - [Milestone 0002](/docs/roadmap/0002-cross-rating-analysis/plan.md), which computes on read.
